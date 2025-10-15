# Perguntas Frequentes Técnicas
## Complemento à Proposta de Arquitetura de Dados

Este documento antecipa perguntas técnicas que um especialista em Analytics Engineering provavelmente fará durante a apresentação.

---

## 1. Decisões de Arquitetura e Trade-offs

### Por que GCP e não AWS/Azure?

**GCP (escolhido)**:
✅ BigQuery é o melhor Data Warehouse serverless do mercado (performance/custo)
✅ Integração nativa entre serviços (Dataform, Datastream, Composer)
✅ Dataform incluído no BigQuery (custo zero vs dbt Cloud)
✅ BigQuery ML permite modelos em SQL (acessível para analistas)

**AWS (não escolhido)**:
❌ Redshift é mais caro e menos performático que BigQuery
❌ Glue ETL tem curva de aprendizado maior
❌ S3 + Athena é bom, mas não compete com BigQuery em queries complexas
✅ Maior ecossistema e adoção no mercado

**Azure (não escolhido)**:
❌ Synapse ainda está amadurecendo
❌ Integração entre serviços menos fluida que GCP
✅ Boa escolha se empresa já usa Azure AD/Office 365

**Decisão**: GCP oferece o melhor custo-benefício para uma arquitetura moderna de dados, especialmente com BigQuery + Dataform. **Risco de vendor lock-in é mitigado** por usar padrões abertos (SQL, Parquet, Airflow).

---

### Por que Dataform e não dbt Core?

**Dataform (escolhido)**:
✅ Gerenciado pelo Google (zero ops, sem servidor para manter)
✅ Git integrado nativamente
✅ Custo zero (incluído no BigQuery)
✅ Otimizado para BigQuery (query compilation)
✅ Sintaxe similar ao dbt (migração futura é viável)

**dbt Core (não escolhido)**:
❌ Requer infraestrutura (Docker, Cloud Run, ou VM)
❌ Manutenção de dependências Python
❌ dbt Cloud é pago ($100+/mês por developer)
✅ Maior ecossistema (packages, community)
✅ Melhor documentação

**Trade-off aceito**: Menor ecossistema do Dataform vs. facilidade operacional. Se futuramente precisarmos migrar para dbt, a estrutura de projeto é compatível (staging → intermediate → marts).

**Estratégia de saída**: Manter compatibilidade conceitual com dbt. Usar CTEs ao invés de macros complexas. Documentar dependências explicitamente.

---

### Por que Cloud Composer ($200/mês) e não Cloud Workflows ($20/mês)?

**Cloud Composer (Airflow)**:
✅ Padrão da indústria (portabilidade)
✅ Python completo (flexibilidade total)
✅ Retry logic, backfilling, SLA tracking robusto
✅ UI rica para debugging
✅ Operadores nativos para GCP (Dataform, BigQuery)

**Cloud Workflows (não escolhido)**:
❌ YAML-based (menos expressivo que Python)
❌ Debugging mais difícil
❌ Menos ferramentas de observabilidade
✅ 10x mais barato ($20 vs $200)

**Decisão**: Airflow vale o investimento pela robustez e observabilidade. Em um ambiente de produção, economia de $180/mês não justifica perder visibilidade e controle sobre pipelines críticos.

---

## 2. Aspectos Práticos de Implementação

### Como lidar com Schema Evolution?

**Cenário**: Tabela `customers` no PostgreSQL adiciona nova coluna `customer_tier`.

**Estratégia**:

1. **Bronze Layer**: Schema evolution automático
   - Datastream e Fivetran detectam novas colunas automaticamente
   - BigLake external tables leem schema do Parquet (compatível)

2. **Silver Layer**: Atualização manual controlada
   ```sql
   -- definitions/staging/core/stg_postgres__customers.sqlx

   -- Adicionar nova coluna com NULL safety
   COALESCE(customer_tier, 'standard') AS customer_tier,
   ```
   - Pull request obrigatório (code review)
   - Deploy em staging primeiro
   - Testes validam que coluna não quebrou queries existentes

3. **Gold Layer**: Impact analysis antes de propagar
   - Verificar quais marts usam `customers`
   - Decidir se `customer_tier` deve ser dimensão ou métrica
   - Comunicar mudança para consumidores (Slack #data-changes)

**Breaking Changes** (ex: coluna removida):
- Manter coluna antiga como `DEPRECATED_` por 30 dias
- Alertar consumidores via Slack e email
- Criar issue no Jira para rastrear migração
- Após 30 dias, remover com feature flag

---

### Como fazer Backfilling de dados históricos?

**Cenário**: Novo modelo `fct_customer_health` precisa de dados dos últimos 12 meses.

**Estratégia**:

1. **Validar disponibilidade de dados Bronze**
   ```sql
   SELECT
     MIN(DATE(_PARTITIONTIME)) AS oldest_date,
     MAX(DATE(_PARTITIONTIME)) AS newest_date,
     COUNT(DISTINCT DATE(_PARTITIONTIME)) AS days_available
   FROM `bronze_postgres.customers`;
   ```

2. **Criar DAG de backfill separado** (não o DAG diário)
   ```python
   # dags/backfill_customer_health.py

   from airflow import DAG
   from datetime import datetime, timedelta

   with DAG(
       'backfill_customer_health',
       start_date=datetime(2024, 1, 1),  # 12 meses atrás
       end_date=datetime(2025, 1, 1),
       schedule_interval='@daily',
       catchup=True,  # IMPORTANTE: True para backfill
       max_active_runs=5,  # Paralelizar 5 dias por vez
   ) as dag:

       run_customer_health = DataformCreateWorkflowInvocationOperator(
           task_id='backfill_customer_health',
           workflow_invocation={
               'invocation_config': {
                   'included_tables': ['fct_customer_health'],
                   'vars': {
                       'execution_date': '{{ ds }}'  # Cada dia
                   }
               }
           }
       )
   ```

3. **Monitorar custos**
   - Backfill de 12 meses pode custar ~$50-100 (scan de dados históricos)
   - Executar em horário de menor tráfego (madrugada)

4. **Validar consistência**
   - Comparar contagens por dia com expectativa
   - Rodar testes de qualidade em amostra (1%, 5%, 10%)

---

### Como fazer Rollback de modelo com erro?

**Cenário**: Deploy de `fct_monthly_recurring_revenue` v2 tem bug (MRR negativo).

**Estratégia de Rollback**:

1. **Identificação rápida** (< 5 min)
   - Alerta automático: "MRR negativo detectado"
   - Slack #data-alerts notifica on-call

2. **Rollback Git** (< 10 min)
   ```bash
   git revert abc123  # Commit com erro
   git push origin main
   ```
   - CI/CD deploya automaticamente versão anterior
   - Cloud Composer re-executa DAG com código correto

3. **Se dados já foram consumidos** (Looker, notebooks):
   ```sql
   -- Deletar dados errados
   DELETE FROM `gold_revenue_ops.fct_monthly_recurring_revenue`
   WHERE _updated_at >= '2025-10-14 10:00:00';

   -- Re-executar pipeline correto
   -- (via Airflow UI ou gcloud)
   ```

4. **Post-mortem** (24h depois)
   - Documentar causa raiz
   - Adicionar teste para prevenir regressão
   - Atualizar runbook de rollback

**Prevenção**:
- Sempre testar em staging antes de produção
- Usar feature flags para rollout gradual
- Manter versões antigas de tabelas por 7 dias (snapshots)

---

### Como onboardar nova fonte de dados?

**Processo padronizado** (exemplo: adicionar Zendesk para tickets de suporte):

**Semana 1: Discovery**
1. Reunião com stakeholder (Customer Success)
   - Entender use cases (dashboard de CSAT, time to resolution)
   - Definir SLA (D+1 é suficiente?)
   - Identificar campos críticos (ticket_id, customer_id, status, satisfaction_score)

2. Análise técnica
   - Verificar API do Zendesk (rate limits, autenticação)
   - Estimar volume (100k tickets/mês?)
   - Calcular custo (Fivetran: ~$120/mês)

**Semana 2: Implementação Bronze**
3. Setup de conector
   - Configurar Fivetran: Zendesk → Cloud Storage (Bronze)
   - Validar ingestão: 1 semana de dados históricos

4. Criar external table
   ```sql
   CREATE EXTERNAL TABLE `bronze_zendesk.tickets` ...
   ```

**Semana 3: Transformação Silver**
5. Modelo staging
   ```sql
   -- definitions/staging/support/stg_zendesk__tickets.sqlx
   ```
   - Deduplicação, type casting, normalização

6. Testes de qualidade
   - Dataform assertions (uniqueKey, nonNull)
   - Dataplex DQ rules (completeness > 99%)

**Semana 4: Consumo Gold**
7. Mart de negócio
   ```sql
   -- definitions/marts/support/fct_support_tickets.sqlx
   ```
   - Join com `customers`, `products`
   - Calcular métricas (avg resolution time, CSAT by segment)

8. Dashboard Looker
   - "Customer Support Overview"
   - KPIs: CSAT, backlog, time to resolution

**Checklist de conclusão**:
- [ ] Dados em Bronze (validado)
- [ ] Modelo Silver com testes
- [ ] Modelo Gold documentado
- [ ] Dashboard em produção
- [ ] Treinamento para analistas
- [ ] Documentação no Data Catalog

---

## 3. Governança e Compliance

### Como garantir LGPD/GDPR compliance?

**Right to be Forgotten** (Art. 17 GDPR, Art. 18 LGPD):

**Processo**:
1. Cliente solicita exclusão de dados pessoais
2. Sistema CRM registra solicitação
3. Trigger automático no Airflow:
   ```python
   # dags/gdpr_right_to_be_forgotten.py

   def anonymize_customer_data(customer_id):
       # Anonimizar em todas as camadas
       queries = [
           # Silver
           f"""
           UPDATE `silver_core.customers`
           SET
             email = 'anonymized_{customer_id}@deleted.com',
             company_name = 'ANONYMIZED',
             phone_clean = NULL,
             document_number = NULL,
             _anonymized_at = CURRENT_TIMESTAMP()
           WHERE customer_id = '{customer_id}'
           """,
           # Gold (propagação)
           f"""
           UPDATE `gold_revenue_ops.fct_customer_health`
           SET customer_id = 'ANONYMIZED_{customer_id}'
           WHERE customer_id = '{customer_id}'
           """
       ]

       for q in queries:
           client.query(q).result()
   ```

4. **Bronze Layer**: Dados raw permanecem (auditoria legal), mas com flag
   ```sql
   UPDATE bronze.customers
   SET _gdpr_deleted = TRUE
   WHERE customer_id = '{customer_id}'
   ```

5. Confirmação para cliente (email automático)

**Data Minimization** (coletar apenas o necessário):
- Policy tags identificam PII automaticamente (Cloud DLP)
- Revisão trimestral: "Esta coluna ainda é necessária?"

**Access Logs**:
```sql
-- Auditoria: quem acessou dados de customer_id X?
SELECT
  principal_email,
  query,
  start_time
FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE query LIKE '%customer_id = \'12345\'%'
  AND start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
ORDER BY start_time DESC;
```

---

### Como funciona Disaster Recovery?

**Cenário 1: Tabela Gold deletada acidentalmente**

**Recovery**:
```sql
-- BigQuery Time Travel (até 7 dias)
CREATE TABLE `gold_revenue_ops.fct_monthly_recurring_revenue` AS
SELECT * FROM `gold_revenue_ops.fct_monthly_recurring_revenue`
  FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR);
```

**Cenário 2: Corrupção de dados (bug em transformação)**

**Recovery**:
1. Identificar timestamp do erro
2. Restaurar de snapshot:
   ```sql
   -- Snapshots diários automáticos (via Cloud Composer)
   CREATE TABLE `gold_revenue_ops.fct_monthly_recurring_revenue` AS
   SELECT * FROM `gold_revenue_ops.fct_monthly_recurring_revenue_snapshot_20251013`;
   ```

3. Re-executar pipeline a partir do Bronze (dados raw imutáveis)

**Cenário 3: Região GCP inteira cai (raro, mas possível)**

**Mitigation**:
- **Cross-region replication** (Bronze layer):
  ```bash
  gsutil rsync -r \
    gs://conta-azul-datalake/bronze/ \
    gs://conta-azul-datalake-backup-us/bronze/
  ```
  - Cron diário (via Cloud Scheduler)
  - Custo: ~$50/mês (network egress)

- **BigQuery snapshots cross-region**:
  ```sql
  -- Snapshot semanal para região US
  EXPORT DATA OPTIONS(
    uri='gs://conta-azul-datalake-backup-us/snapshots/gold_revenue_ops/*',
    format='PARQUET'
  ) AS
  SELECT * FROM `gold_revenue_ops.fct_monthly_recurring_revenue`;
  ```

**RTO (Recovery Time Objective)**: 4 horas
**RPO (Recovery Point Objective)**: 24 horas (dados até ontem)

---

## 4. Crescimento e Escala

### Como os custos escalam com crescimento?

**Cenário de crescimento** (próximos 2 anos):

| Métrica | Hoje | 6 meses | 1 ano | 2 anos |
|---------|------|---------|-------|--------|
| **Dados novos/mês** | 100 GB | 200 GB | 400 GB | 1 TB |
| **Eventos/dia** | 500k | 1M | 2M | 5M |
| **Queries/mês** | 2 TB | 4 TB | 8 TB | 20 TB |
| **Usuários ativos** | 50 | 75 | 100 | 150 |

**Projeção de custos**:

| Serviço | Hoje | 6 meses | 1 ano | 2 anos |
|---------|------|---------|-------|--------|
| **Cloud Storage** | $20 | $35 | $60 | $150 |
| **BigQuery Storage** | $25 | $45 | $80 | $200 |
| **BigQuery Compute** | $10 | $20 | $40 | $100 |
| **Fivetran** | $120 | $180 | $240 | $360 |
| **Cloud Composer** | $200 | $300* | $500* | $800* |
| **Outros** | $325 | $420 | $580 | $890 |
| **TOTAL/mês** | **$700** | **$1,000** | **$1,500** | **$2,500** |

*Composer: Small → Medium → Large environment

**Breaking points** (quando ajustar infra):

- **6 meses**:
  - Aumentar Cloud Composer para Medium (2 vCPUs)
  - Adicionar BigQuery BI Engine ($100/mês) para cache de dashboards

- **1 ano**:
  - Avaliar BigQuery Reservations (slots dedicados) se queries > 10 TB/mês
  - Implementar partitioning mais granular (hourly em eventos)

- **2 anos**:
  - Considerar Cloud Composer Large ou Kubernetes (GKE) para Airflow
  - Implementar data archiving (mover Bronze > 6 meses para Coldline)

**Otimizações para conter crescimento de custos**:
1. Materialized views ao invés de tables em Gold (recompute apenas o necessário)
2. Clustering agressivo em colunas de filtro
3. Looker PDT caching (reduzir queries repetitivas)
4. Educação de usuários (evitar `SELECT *`)

---

## 5. Data Quality em Produção

### O que acontece se dados falharem em testes Silver?

**Cenário**: Ingestão de `customers` tem 50% de emails nulos (deveria ser < 1%).

**Fluxo de tratamento**:

1. **Detecção automática** (Dataform assertion falha)
   ```
   [ERROR] silver_core.customers: Assertion failed
   - Rule: nonNull(email)
   - Expected: 100%
   - Actual: 50%
   ```

2. **Pipeline para e notifica** (fail-fast)
   - Airflow task marca como FAILED
   - Slack #data-alerts: "🚨 CRITICAL: Silver layer quality check failed"
   - Email para data-eng-oncall

3. **Dados vão para Quarantine**
   ```sql
   -- Isolar dados problemáticos
   CREATE TABLE `quarantine.customers_failed_20251014` AS
   SELECT * FROM ${ref("bronze_postgres", "customers")}
   WHERE email IS NULL;

   -- Processar apenas dados bons
   INSERT INTO silver_core.customers
   SELECT * FROM cleaned
   WHERE email IS NOT NULL;
   ```

4. **Investigação** (SLA: 2 horas)
   - Checar fonte (PostgreSQL): Bug na aplicação?
   - Checar Datastream: Falha na captura CDC?
   - Checar Bronze: Arquivos Parquet corrompidos?

5. **Resolução**:
   - **Se bug na fonte**: Abrir ticket para time de Engineering
   - **Se problema temporário**: Re-executar ingestão após correção
   - **Se problema estrutural**: Ajustar lógica Silver para tolerar (com documentação)

6. **Comunicação**:
   ```
   Slack #data-updates:
   "⚠️ Delay em silver_core.customers (14/10 10h)
   - Causa: Bug na aplicação (email nulls)
   - Impacto: Dashboards de RevOps desatualizados
   - ETA resolução: 14/10 14h
   - Ticket: JIRA-12345"
   ```

**Quarantine Retention**: 30 dias (depois deletar ou arquivar)

---

### Como notificar data producers de problemas?

**Data Contract** (SLA reverso: fonte → warehouse):

```yaml
# contracts/postgres_customers.yaml

source: postgres_production.customers
owner: engineering@contaazul.com
sla:
  freshness: < 5 minutes  # CDC real-time
  completeness:
    email: 99.5%
    created_at: 100%
  uniqueness:
    id: 100%

alerts:
  - condition: email_null_rate > 1%
    severity: HIGH
    notify:
      - engineering@contaazul.com
      - Slack: #engineering-alerts

  - condition: cdc_lag > 15 minutes
    severity: CRITICAL
    notify:
      - sre-oncall@contaazul.com
      - PagerDuty
```

**Monitoramento automático**:
```python
# dags/data_contract_monitor.py

def check_data_contracts():
    for contract in load_contracts():
        actual_stats = get_table_stats(contract.source)

        violations = []
        if actual_stats['email_null_rate'] > 0.01:  # 1%
            violations.append({
                'rule': 'email completeness',
                'expected': '99.5%',
                'actual': f"{(1-actual_stats['email_null_rate'])*100}%"
            })

        if violations:
            send_alert(
                recipients=contract.owner,
                subject=f"Data Contract Violation: {contract.source}",
                violations=violations
            )
```

**Dashboard de Data Contracts**:
- Looker dashboard: "Data Source Health"
- Métricas: Uptime, freshness, quality score
- Por fonte: PostgreSQL (✅ 99.8%), Salesforce (⚠️ 95.2%)

---

## 6. Perguntas de Arquitetura Avançadas

### Como garantir idempotência nos pipelines?

**Problema**: Re-executar pipeline não deve duplicar dados nem causar inconsistências.

**Solução por camada**:

**Bronze** (naturalmente idempotente):
- Datastream: CDC usa log sequence number (LSN) → não duplica
- Fivetran: Usa cursor de última execução → idempotente
- Cloud Storage: Particionamento por data (`year=2025/month=10/day=14/`) → sobrescreve

**Silver** (incremental idempotente):
```sql
-- definitions/staging/core/stg_postgres__customers.sqlx

pre_operations {
  -- DELETAR registros que serão re-processados
  ${when(incremental(),
    `DELETE FROM ${self()}
     WHERE customer_id IN (
       SELECT DISTINCT id
       FROM ${ref("bronze_postgres", "customers")}
       WHERE DATE(_loaded_at) = '{{ ds }}'
     )`
  )}
}

-- INSERT apenas dados do dia (idempotente)
INSERT INTO ${self()}
SELECT * FROM cleaned
WHERE DATE(_loaded_at) = '{{ ds }}';
```

**Gold** (full refresh idempotente):
```sql
-- Marts são sempre full refresh (recompute tudo)
-- Idempotente por design: DROP + CREATE

CREATE OR REPLACE TABLE gold_revenue_ops.fct_monthly_recurring_revenue AS
SELECT ... FROM silver_core.customers;
```

**Teste de idempotência**:
```python
# tests/test_idempotency.py

def test_silver_customers_idempotent():
    # Executar pipeline 2x para mesma data
    run_dataform(execution_date='2025-10-14')
    count_1 = get_row_count('silver_core.customers', date='2025-10-14')

    run_dataform(execution_date='2025-10-14')  # Re-executar
    count_2 = get_row_count('silver_core.customers', date='2025-10-14')

    assert count_1 == count_2, "Pipeline não é idempotente!"
```

---

### Como lidar com late-arriving data?

**Problema**: Evento de 14/10 chega no warehouse dia 16/10.

**Estratégia**:

**Silver** (partition by event_date, not ingestion_date):
```sql
-- Particionamento por data DO EVENTO (não da ingestão)
config {
  bigquery: {
    partitionBy: "event_date"  -- ✅ Correto
    -- NÃO: partitionBy: "_loaded_at"  -- ❌ Errado
  }
}

-- Late data vai para partição correta
INSERT INTO silver_product_analytics.events
SELECT
  event_id,
  CAST(event_timestamp AS DATE) AS event_date,  -- Partition key
  ...
WHERE DATE(event_timestamp) BETWEEN '2025-10-01' AND CURRENT_DATE();
```

**Gold** (lookback window de 3 dias):
```sql
-- Reprocessar últimos 3 dias para capturar late data
CREATE OR REPLACE TABLE gold_product_analytics.fct_daily_active_users AS
SELECT
  event_date,
  COUNT(DISTINCT user_id) AS dau
FROM silver_product_analytics.events
WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
GROUP BY 1;
```

**Monitoramento**:
```sql
-- Alertar se late data > 5% do volume
SELECT
  event_date,
  COUNT(*) AS total_events,
  COUNT(CASE WHEN DATE(_loaded_at) > DATE_ADD(event_date, INTERVAL 2 DAY) THEN 1 END) AS late_events,
  SAFE_DIVIDE(late_events, total_events) AS late_percentage
FROM silver_product_analytics.events
WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
HAVING late_percentage > 0.05;
```

---

## Conclusão

Esta documentação complementar antecipa as perguntas mais comuns de um **Analytics Engineer especialista** e demonstra:

1. **Profundidade técnica**: Não apenas "o que", mas "como" e "por quê"
2. **Experiência prática**: Problemas reais e soluções testadas
3. **Pensamento crítico**: Trade-offs explícitos, não apenas benefícios
4. **Maturidade**: Processos, não apenas tecnologia

**Recomendação**: Use este documento como **anexo técnico** durante a apresentação. Não precisa cobrir tudo, mas demonstra que você pensou nos detalhes.
