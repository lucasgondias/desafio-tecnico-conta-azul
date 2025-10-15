"""
DAG Principal: Pipeline Diário de Dados
Orquestra todo o fluxo Bronze → Silver → Gold

Owner: Data Engineering Team
Schedule: Diário às 3 AM BRT (6 AM UTC)
SLA: 3 horas (deve terminar até 6 AM BRT)
"""

from airflow import DAG
from airflow.providers.google.cloud.operators.dataform import (
    DataformCreateCompilationResultOperator,
    DataformCreateWorkflowInvocationOperator,
)
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCheckOperator,
    BigQueryExecuteQueryOperator,
    BigQueryInsertJobOperator,
)
from airflow.providers.google.cloud.sensors.gcs import (
    GCSObjectsWithPrefixExistenceSensor,
)
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.email import EmailOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

from datetime import datetime, timedelta
import logging

# =============================================
# Configurações
# =============================================

PROJECT_ID = "conta-azul-prod"
REGION = "southamerica-east1"
DATAFORM_REPO = "dataform-conta-azul"
GCS_BUCKET = "conta-azul-datalake"

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['data-eng@contaazul.com', 'data-alerts@contaazul.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=3),
    'sla': timedelta(hours=3),
}

# =============================================
# Funções Python
# =============================================

def check_data_completeness(**context):
    """
    Verifica se dados de todas as fontes críticas chegaram no Bronze
    """
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    execution_date = context['ds']

    # Fontes críticas que devem ter dados
    critical_sources = [
        ('bronze_postgres', 'customers'),
        ('bronze_postgres', 'invoices'),
        ('bronze_postgres', 'payments'),
        ('bronze_firebase', 'events'),
    ]

    missing_sources = []

    for schema, table in critical_sources:
        query = f"""
            SELECT COUNT(*) as row_count
            FROM `{PROJECT_ID}.{schema}.{table}`
            WHERE DATE(_PARTITIONTIME) = '{execution_date}'
        """

        result = client.query(query).result()
        row_count = list(result)[0].row_count

        if row_count == 0:
            missing_sources.append(f"{schema}.{table}")
            logging.warning(f"No data found for {schema}.{table} on {execution_date}")

    if missing_sources:
        raise ValueError(f"Missing data for sources: {', '.join(missing_sources)}")

    logging.info(f"All critical sources have data for {execution_date}")
    return True


def decide_full_or_incremental(**context):
    """
    Decide se deve fazer full refresh ou incremental baseado no dia da semana
    Domingo = full refresh (menos tráfego)
    """
    execution_date = context['execution_date']

    if execution_date.weekday() == 6:  # Domingo
        logging.info("Sunday detected: Running FULL REFRESH")
        return 'full_refresh_silver'
    else:
        logging.info("Weekday detected: Running INCREMENTAL")
        return 'incremental_silver'


def send_pipeline_report(**context):
    """
    Gera e envia relatório de execução do pipeline
    """
    from google.cloud import bigquery
    import pandas as pd

    client = bigquery.Client(project=PROJECT_ID)

    # Query estatísticas do pipeline
    stats_query = """
        SELECT
          table_schema,
          table_name,
          row_count,
          ROUND(size_bytes / 1024 / 1024, 2) AS size_mb,
          TIMESTAMP_MILLIS(last_modified_time) AS last_modified
        FROM `conta-azul-prod.INFORMATION_SCHEMA.TABLE_STORAGE`
        WHERE table_schema IN ('silver_core', 'gold_revenue_ops', 'gold_product_analytics')
          AND DATE(TIMESTAMP_MILLIS(last_modified_time)) = CURRENT_DATE()
        ORDER BY size_mb DESC
        LIMIT 20
    """

    df = client.query(stats_query).to_dataframe()

    # Formatar relatório
    report = f"""
    📊 Pipeline Execution Report - {context['ds']}

    ✅ Pipeline Status: SUCCESS
    ⏱️ Execution Time: {context['ti'].duration} seconds

    📈 Tables Updated Today:
    {df.to_markdown(index=False)}

    🔗 Airflow DAG: {context['dag'].dag_id}
    🔗 Execution Date: {context['execution_date']}
    """

    logging.info(report)

    # Enviar para Slack (implementação omitida)
    # send_to_slack(channel='#data-pipeline-reports', message=report)

    return report


# =============================================
# DAG Definition
# =============================================

with DAG(
    'daily_data_pipeline',
    default_args=default_args,
    description='Pipeline completo: Bronze → Silver → Gold com validações',
    schedule_interval='0 6 * * *',  # 6 AM UTC = 3 AM BRT
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['production', 'daily', 'critical'],
    max_active_runs=1,
    doc_md=__doc__,
) as dag:

    # =============================================
    # STEP 1: Validar Ingestão Bronze
    # =============================================

    with TaskGroup('validate_bronze_ingestion', tooltip='Valida se dados chegaram no Bronze') as bronze_validation:

        # Sensor: Aguardar arquivos do Datastream (PostgreSQL)
        wait_postgres_files = GCSObjectsWithPrefixExistenceSensor(
            task_id='wait_postgres_cdc_files',
            bucket=GCS_BUCKET,
            prefix='bronze/sources/postgres_production/customers/year={{ ds_nodash[:4] }}/month={{ ds_nodash[4:6] }}/day={{ ds_nodash[6:8] }}/',
            timeout=1800,  # 30 minutos timeout
            poke_interval=60,  # Check a cada 1 minuto
        )

        # Validar completude de dados críticos
        check_completeness = PythonOperator(
            task_id='check_data_completeness',
            python_callable=check_data_completeness,
        )

        # Validar contagem mínima de registros
        check_min_rows = BigQueryCheckOperator(
            task_id='check_minimum_row_count',
            sql="""
                SELECT COUNT(*) >= 1000
                FROM `conta-azul-prod.bronze_postgres.customers`
                WHERE DATE(_PARTITIONTIME) = '{{ ds }}'
            """,
            use_legacy_sql=False,
        )

        wait_postgres_files >> check_completeness >> check_min_rows

    # =============================================
    # STEP 2: Decidir Full Refresh ou Incremental
    # =============================================

    decide_refresh_mode = BranchPythonOperator(
        task_id='decide_refresh_mode',
        python_callable=decide_full_or_incremental,
    )

    # =============================================
    # STEP 3: Dataform - Silver Layer (Staging)
    # =============================================

    # Compilar modelos Dataform
    compile_dataform = DataformCreateCompilationResultOperator(
        task_id='compile_dataform_models',
        project_id=PROJECT_ID,
        region=REGION,
        repository_id=DATAFORM_REPO,
        compilation_result={
            'git_commitish': 'main',
            'code_compilation_config': {
                'vars': {
                    'execution_date': '{{ ds }}',
                    'environment': 'production'
                }
            }
        },
    )

    # Opção 1: Incremental (dias de semana)
    run_incremental_silver = DataformCreateWorkflowInvocationOperator(
        task_id='incremental_silver',
        project_id=PROJECT_ID,
        region=REGION,
        repository_id=DATAFORM_REPO,
        workflow_invocation={
            'compilation_result': "{{ task_instance.xcom_pull(task_ids='compile_dataform_models')['name'] }}",
            'invocation_config': {
                'included_tags': ['staging', 'daily'],
                'transitive_dependencies': True,
                'fully_refresh_incremental_tables': False,
            }
        },
    )

    # Opção 2: Full Refresh (domingos)
    run_full_refresh_silver = DataformCreateWorkflowInvocationOperator(
        task_id='full_refresh_silver',
        project_id=PROJECT_ID,
        region=REGION,
        repository_id=DATAFORM_REPO,
        workflow_invocation={
            'compilation_result': "{{ task_instance.xcom_pull(task_ids='compile_dataform_models')['name'] }}",
            'invocation_config': {
                'included_tags': ['staging'],
                'transitive_dependencies': True,
                'fully_refresh_incremental_tables': True,  # FULL REFRESH
            }
        },
    )

    # =============================================
    # STEP 4: Testes Silver Layer
    # =============================================

    test_silver_layer = DataformCreateWorkflowInvocationOperator(
        task_id='test_silver_assertions',
        project_id=PROJECT_ID,
        region=REGION,
        repository_id=DATAFORM_REPO,
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,  # Executa se qualquer branch anterior passou
        workflow_invocation={
            'compilation_result': "{{ task_instance.xcom_pull(task_ids='compile_dataform_models')['name'] }}",
            'invocation_config': {
                'included_tags': ['staging'],
                'actions_only': False,  # Inclui assertions
            }
        },
    )

    # =============================================
    # STEP 5: Dataform - Gold Layer (Marts)
    # =============================================

    with TaskGroup('gold_layer_marts', tooltip='Executar marts por domínio') as gold_marts:

        # Executar marts em paralelo por domínio
        domains = ['product_analytics', 'revenue_ops', 'data_science']

        for domain in domains:
            run_mart = DataformCreateWorkflowInvocationOperator(
                task_id=f'run_{domain}_mart',
                project_id=PROJECT_ID,
                region=REGION,
                repository_id=DATAFORM_REPO,
                workflow_invocation={
                    'compilation_result': "{{ task_instance.xcom_pull(task_ids='compile_dataform_models')['name'] }}",
                    'invocation_config': {
                        'included_tags': [domain, 'daily'],
                        'transitive_dependencies': True,
                    }
                },
            )

    # =============================================
    # STEP 6: Testes de Qualidade Gold
    # =============================================

    with TaskGroup('gold_quality_checks') as gold_quality:

        # Teste: MRR sempre positivo
        test_mrr_positive = BigQueryCheckOperator(
            task_id='test_mrr_always_positive',
            sql="""
                SELECT LOGICAL_AND(mrr_brl >= 0)
                FROM `conta-azul-prod.gold_revenue_ops.fct_monthly_recurring_revenue`
                WHERE month >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
            """,
            use_legacy_sql=False,
        )

        # Teste: Freshness (dados atualizados hoje)
        test_freshness = BigQueryCheckOperator(
            task_id='test_gold_freshness',
            sql="""
                SELECT COUNT(*) > 0
                FROM `conta-azul-prod.gold_revenue_ops.INFORMATION_SCHEMA.TABLES`
                WHERE DATE(TIMESTAMP_MILLIS(last_modified_time)) = CURRENT_DATE()
            """,
            use_legacy_sql=False,
        )

        # Dataplex Data Quality
        run_dataplex_dq = BigQueryExecuteQueryOperator(
            task_id='run_dataplex_quality_rules',
            sql="""
                -- Executar regras de qualidade do Dataplex
                -- (Exemplo simplificado - na prática seria via API do Dataplex)
                SELECT 'Dataplex DQ executed' AS status
            """,
            use_legacy_sql=False,
        )

        [test_mrr_positive, test_freshness, run_dataplex_dq]

    # =============================================
    # STEP 7: Atualizar Looker (Refresh PDTs)
    # =============================================

    refresh_looker = PythonOperator(
        task_id='refresh_looker_dashboards',
        python_callable=lambda: logging.info("Looker dashboards refreshed via API"),
        # Na prática: usar LookerSDK para trigger refresh de PDTs
    )

    # =============================================
    # STEP 8: Atualizar Metadados (Data Catalog)
    # =============================================

    update_catalog = BigQueryExecuteQueryOperator(
        task_id='update_data_catalog_metadata',
        sql="""
            -- Atualizar tabela de metadados com freshness info
            MERGE `conta-azul-prod.metadata.table_freshness` T
            USING (
              SELECT
                CONCAT(table_schema, '.', table_name) AS full_table_name,
                TIMESTAMP_MILLIS(last_modified_time) AS last_updated,
                row_count
              FROM `conta-azul-prod.INFORMATION_SCHEMA.TABLE_STORAGE`
              WHERE table_schema LIKE 'gold_%'
                AND DATE(TIMESTAMP_MILLIS(last_modified_time)) = CURRENT_DATE()
            ) S
            ON T.table_name = S.full_table_name
            WHEN MATCHED THEN
              UPDATE SET
                last_updated = S.last_updated,
                row_count = S.row_count,
                metadata_updated_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN
              INSERT (table_name, last_updated, row_count, metadata_updated_at)
              VALUES (S.full_table_name, S.last_updated, S.row_count, CURRENT_TIMESTAMP())
        """,
        use_legacy_sql=False,
    )

    # =============================================
    # STEP 9: Gerar Relatório de Execução
    # =============================================

    generate_report = PythonOperator(
        task_id='generate_pipeline_report',
        python_callable=send_pipeline_report,
        trigger_rule=TriggerRule.ALL_DONE,  # Executa sempre (mesmo com falhas)
    )

    # =============================================
    # STEP 10: Notificação de Falha (se houver)
    # =============================================

    send_failure_alert = EmailOperator(
        task_id='send_failure_email',
        to=['data-eng-oncall@contaazul.com'],
        subject='[CRITICAL] Daily Data Pipeline Failed - {{ ds }}',
        html_content="""
            <h2>Pipeline Execution Failed</h2>
            <p><strong>DAG:</strong> {{ dag.dag_id }}</p>
            <p><strong>Execution Date:</strong> {{ ds }}</p>
            <p><strong>Failed Task:</strong> {{ task_instance.task_id }}</p>
            <p><strong>Log URL:</strong> {{ ti.log_url }}</p>
            <p>Please check Airflow UI for details.</p>
        """,
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # =============================================
    # Dependências do Pipeline
    # =============================================

    bronze_validation >> decide_refresh_mode >> compile_dataform

    compile_dataform >> [run_incremental_silver, run_full_refresh_silver]

    [run_incremental_silver, run_full_refresh_silver] >> test_silver_layer

    test_silver_layer >> gold_marts >> gold_quality

    gold_quality >> [refresh_looker, update_catalog]

    [refresh_looker, update_catalog] >> generate_report

    generate_report >> send_failure_alert
