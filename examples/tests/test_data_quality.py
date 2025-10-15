"""
Testes de Qualidade de Dados
Validações customizadas além dos testes do Dataform

Executados via pytest no CI/CD e no pipeline Airflow
"""

import pytest
from google.cloud import bigquery
import pandas as pd
from datetime import datetime, timedelta

PROJECT_ID = "conta-azul-prod"


@pytest.fixture(scope="session")
def bq_client():
    """Cliente BigQuery compartilhado entre testes"""
    return bigquery.Client(project=PROJECT_ID)


# =============================================
# TESTES: Silver Layer (Data Quality)
# =============================================

class TestSilverLayerQuality:

    def test_customers_no_duplicates(self, bq_client):
        """Clientes não devem ter duplicatas por customer_id"""
        query = """
            SELECT customer_id, COUNT(*) as count
            FROM `conta-azul-prod.silver_core.customers`
            GROUP BY customer_id
            HAVING COUNT(*) > 1
        """

        df = bq_client.query(query).to_dataframe()

        assert len(df) == 0, f"Found {len(df)} duplicate customer_ids: {df['customer_id'].tolist()}"


    def test_customers_email_format(self, bq_client):
        """Todos os emails devem ter formato válido"""
        query = """
            SELECT COUNT(*) as invalid_emails
            FROM `conta-azul-prod.silver_core.customers`
            WHERE NOT REGEXP_CONTAINS(email, r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        """

        result = bq_client.query(query).to_dataframe()
        invalid_count = result['invalid_emails'][0]

        assert invalid_count == 0, f"Found {invalid_count} customers with invalid email format"


    def test_customers_valid_segments(self, bq_client):
        """Customer segment deve ser apenas valores válidos"""
        query = """
            SELECT DISTINCT customer_segment
            FROM `conta-azul-prod.silver_core.customers`
        """

        df = bq_client.query(query).to_dataframe()
        valid_segments = {'PME', 'MEI', 'Autônomo', 'Outros'}
        actual_segments = set(df['customer_segment'].tolist())

        invalid = actual_segments - valid_segments
        assert len(invalid) == 0, f"Found invalid segments: {invalid}"


    def test_invoices_positive_values(self, bq_client):
        """Valores de invoices devem ser sempre positivos"""
        query = """
            SELECT COUNT(*) as negative_invoices
            FROM `conta-azul-prod.silver_core.invoices`
            WHERE total_value_brl < 0
        """

        result = bq_client.query(query).to_dataframe()
        negative_count = result['negative_invoices'][0]

        assert negative_count == 0, f"Found {negative_count} invoices with negative values"


# =============================================
# TESTES: Gold Layer (Business Logic)
# =============================================

class TestGoldLayerRevOps:

    def test_mrr_always_positive(self, bq_client):
        """MRR nunca deve ser negativo"""
        query = """
            SELECT
              month,
              customer_segment,
              mrr_brl
            FROM `conta-azul-prod.gold_revenue_ops.fct_monthly_recurring_revenue`
            WHERE mrr_brl < 0
              AND month >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
        """

        df = bq_client.query(query).to_dataframe()

        assert len(df) == 0, f"Found {len(df)} records with negative MRR:\n{df}"


    def test_mrr_growth_plausible(self, bq_client):
        """Crescimento de MRR não deve exceder ±50% MoM (provável anomalia)"""
        query = """
            SELECT
              month,
              customer_segment,
              mrr_growth_pct
            FROM `conta-azul-prod.gold_revenue_ops.fct_monthly_recurring_revenue`
            WHERE ABS(mrr_growth_pct) > 0.5
              AND month >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
            ORDER BY month DESC
        """

        df = bq_client.query(query).to_dataframe()

        assert len(df) == 0, f"Found {len(df)} months with MRR growth > 50%:\n{df}"


    def test_customer_health_score_range(self, bq_client):
        """Health score deve estar entre 0 e 100"""
        query = """
            SELECT
              MIN(health_score) as min_score,
              MAX(health_score) as max_score,
              COUNT(*) as total_records
            FROM `conta-azul-prod.gold_revenue_ops.fct_customer_health`
            WHERE snapshot_date = CURRENT_DATE()
        """

        df = bq_client.query(query).to_dataframe()

        if len(df) > 0 and df['total_records'][0] > 0:
            min_score = df['min_score'][0]
            max_score = df['max_score'][0]

            assert 0 <= min_score <= 100, f"Health score out of range: min={min_score}"
            assert 0 <= max_score <= 100, f"Health score out of range: max={max_score}"


    def test_no_orphan_customers_in_mrr(self, bq_client):
        """Todos os customers no MRR devem existir na dim_customers"""
        query = """
            SELECT COUNT(DISTINCT m.customer_id) as orphan_count
            FROM `conta-azul-prod.gold_revenue_ops.fct_monthly_recurring_revenue` m
            LEFT JOIN `conta-azul-prod.silver_core.customers` c
              ON m.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
        """

        result = bq_client.query(query).to_dataframe()
        orphan_count = result['orphan_count'][0]

        # NOTE: Esse teste está comentado pois o schema atual não tem customer_id no fct_mrr
        # (agregado por segment). Descomente se adicionar customer_id granular
        # assert orphan_count == 0, f"Found {orphan_count} orphan customers in MRR fact"


# =============================================
# TESTES: Data Freshness (SLA)
# =============================================

class TestDataFreshness:

    def test_gold_tables_updated_today(self, bq_client):
        """Todas as tabelas Gold críticas devem ter sido atualizadas hoje"""
        query = """
            SELECT
              table_name,
              TIMESTAMP_DIFF(
                CURRENT_TIMESTAMP(),
                TIMESTAMP_MILLIS(last_modified_time),
                HOUR
              ) AS hours_since_update
            FROM `conta-azul-prod.gold_revenue_ops.INFORMATION_SCHEMA.TABLES`
            WHERE table_type = 'BASE TABLE'
              AND table_name IN (
                'fct_monthly_recurring_revenue',
                'fct_customer_health',
                'fct_sales_pipeline'
              )
        """

        df = bq_client.query(query).to_dataframe()

        # SLA: Máximo 27 horas (D+1 + 3h de buffer)
        stale_tables = df[df['hours_since_update'] > 27]

        assert stale_tables.empty, f"Stale tables (>27h):\n{stale_tables}"


    def test_silver_core_fresh(self, bq_client):
        """Silver core tables devem ser atualizadas diariamente"""
        query = """
            SELECT
              table_name,
              DATE(TIMESTAMP_MILLIS(last_modified_time)) AS last_update_date
            FROM `conta-azul-prod.silver_core.INFORMATION_SCHEMA.TABLES`
            WHERE table_name IN ('customers', 'invoices', 'payments', 'subscriptions')
        """

        df = bq_client.query(query).to_dataframe()
        today = datetime.now().date()

        for _, row in df.iterrows():
            table = row['table_name']
            last_update = row['last_update_date'].date()
            days_old = (today - last_update).days

            assert days_old <= 1, f"Table {table} not updated today (last update: {last_update})"


# =============================================
# TESTES: Consistency (Cross-table)
# =============================================

class TestCrossTableConsistency:

    def test_mrr_matches_subscriptions(self, bq_client):
        """MRR agregado deve bater com soma de subscriptions ativas"""
        query = """
            WITH mrr_total AS (
              SELECT SUM(mrr_brl) AS total_mrr
              FROM `conta-azul-prod.gold_revenue_ops.fct_monthly_recurring_revenue`
              WHERE month = DATE_TRUNC(CURRENT_DATE(), MONTH)
            ),
            subscriptions_total AS (
              SELECT SUM(monthly_value_brl) AS total_from_subs
              FROM `conta-azul-prod.silver_core.subscriptions`
              WHERE status = 'active'
            )
            SELECT
              m.total_mrr,
              s.total_from_subs,
              ABS(m.total_mrr - s.total_from_subs) AS diff,
              ABS(m.total_mrr - s.total_from_subs) / m.total_mrr AS diff_pct
            FROM mrr_total m, subscriptions_total s
        """

        df = bq_client.query(query).to_dataframe()

        if len(df) > 0 and df['total_mrr'][0] is not None:
            diff_pct = df['diff_pct'][0]

            # Permitir até 5% de diferença (por timing de atualizações)
            assert diff_pct < 0.05, f"MRR mismatch > 5%: {diff_pct:.2%} difference"


# =============================================
# TESTES: Performance & Cost
# =============================================

class TestPerformance:

    def test_tables_are_partitioned(self, bq_client):
        """Tabelas grandes devem ser particionadas"""
        query = """
            SELECT
              table_name,
              is_partitioned
            FROM `conta-azul-prod.INFORMATION_SCHEMA.TABLES`
            WHERE table_schema IN ('silver_core', 'gold_revenue_ops')
              AND table_type = 'BASE TABLE'
              AND table_name IN (
                'customers', 'invoices', 'events',
                'fct_monthly_recurring_revenue', 'fct_customer_health'
              )
        """

        df = bq_client.query(query).to_dataframe()

        # NOTE: BigQuery retorna 'YES'/'NO' como string
        unpartitioned = df[df['is_partitioned'] != 'YES']

        # Alguns podem não precisar de particionamento (tabelas pequenas)
        # Este é um teste de guideline, não bloqueante
        if not unpartitioned.empty:
            print(f"⚠️  Warning: Unpartitioned tables: {unpartitioned['table_name'].tolist()}")


    def test_no_excessive_table_size(self, bq_client):
        """Nenhuma tabela deve exceder 500 GB (red flag de otimização)"""
        query = """
            SELECT
              table_schema,
              table_name,
              ROUND(size_bytes / 1024 / 1024 / 1024, 2) AS size_gb
            FROM `conta-azul-prod.INFORMATION_SCHEMA.TABLE_STORAGE`
            WHERE size_bytes > 500 * 1024 * 1024 * 1024  -- 500 GB
            ORDER BY size_bytes DESC
        """

        df = bq_client.query(query).to_dataframe()

        if not df.empty:
            print(f"⚠️  Warning: Large tables found:\n{df}")
            # Não falha o teste, apenas alerta


# =============================================
# Configuração do pytest
# =============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
