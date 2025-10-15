# Arquitetura de Dados - Conta Azul
## Proposta de Solução para Analytics Engineer | Google Cloud Platform

### Visão Geral

Esta proposta apresenta uma arquitetura moderna de dados baseada em princípios de **Data Mesh** e **Medallion Architecture**, desenhada para suportar as três frentes de dados da Conta Azul: Product Analytics, Data Science e Revenue Operations.

A solução utiliza **Google Cloud Platform (GCP)** pela sua integração nativa entre serviços, facilidade de uso e custo-benefício competitivo.

### Princípios Norteadores

1. **Simplicidade**: Soluções pragmáticas com serviços gerenciados do GCP
2. **Escalabilidade**: Crescimento horizontal sem reengenharia (serverless-first)
3. **Custo-efetividade**: Pague apenas pelo uso, otimização automática
4. **Manutenibilidade**: Código versionado, testado e documentado
5. **Self-Service**: Autonomia para analistas e cientistas de dados

---

## Índice

1. [Arquitetura Proposta](#arquitetura-proposta)
2. [Stack Tecnológica GCP](#stack-tecnológica-gcp)
3. [Camadas de Dados](#camadas-de-dados)
4. [Estratégia de Ingestão](#estratégia-de-ingestão)
5. [Transformação com Dataform](#transformação-com-dataform)
6. [Orquestração com Cloud Composer](#orquestração-com-cloud-composer)
7. [Qualidade e Governança](#qualidade-e-governança)
8. [Camada de Consumo](#camada-de-consumo)
9. [Estimativa de Custos](#estimativa-de-custos)
10. [Roadmap de Implementação](#roadmap-de-implementação)

---

## Arquitetura Proposta

### Diagrama de Arquitetura (High-Level)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FONTES DE DADOS                                  │
├──────────────┬──────────────┬──────────────┬─────────────────────────────┤
│ PostgreSQL   │  Firebase    │  Salesforce  │  Google Analytics 4         │
│ (Transacional)│  (Eventos)   │  (CRM)       │  (Product Analytics)        │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬──────────────────────┘
       │              │              │              │
       └──────────────┴──────────────┴──────────────┘
                      │
              ┌───────▼────────┐
              │  INGESTÃO      │
              │                │
              │ • Fivetran     │────────┐
              │ • Datastream   │        │
              │ • Cloud Run    │        │
              └───────┬────────┘        │
                      │                 │
       ┌──────────────▼─────────────────▼────────────────┐
       │         CLOUD STORAGE (Data Lake)                │
       │                                                  │
       │  ┌─────────────────────────────────────────┐    │
       │  │  BRONZE LAYER (Raw Data)                │    │
       │  │  • Formato: Avro/Parquet                │    │
       │  │  • Particionado por data ingestão       │    │
       │  └──────────────┬──────────────────────────┘    │
       │                 │                                │
       │  ┌──────────────▼──────────────────────────┐    │
       │  │  SILVER LAYER (Cleaned & Conformed)     │    │
       │  │  • Dados limpos e padronizados          │    │
       │  │  • Type casting e validações            │    │
       │  └──────────────┬──────────────────────────┘    │
       │                 │                                │
       │  ┌──────────────▼──────────────────────────┐    │
       │  │  GOLD LAYER (Business Ready)            │    │
       │  │  • Modelos dimensionais                 │    │
       │  │  • Agregações e métricas                │    │
       │  └─────────────────────────────────────────┘    │
       └──────────────────────────────────────────────────┘
                      │
       ┌──────────────▼─────────────────────────────┐
       │        BIGQUERY (Data Warehouse)           │
       │                                            │
       │  ┌────────────────┐  ┌──────────────────┐ │
       │  │ Product        │  │ Revenue Ops      │ │
       │  │ Analytics      │  │ (RevOps)         │ │
       │  └────────────────┘  └──────────────────┘ │
       │  ┌────────────────────────────────────┐   │
       │  │ Data Science (Feature Store)       │   │
       │  └────────────────────────────────────┘   │
       └──────────────┬─────────────────────────────┘
                      │
       ┌──────────────┴─────────────────────────────┐
       │                                            │
┌──────▼────────┐  ┌──────────┐  ┌────────────────┐
│  Looker /     │  │ Vertex AI│  │ Data Catalog   │
│  Looker Studio│  │ Notebooks│  │ (Governança)   │
└───────────────┘  └──────────┘  └────────────────┘
    (Analistas)    (Cientistas)   (Todos)
```

---

## Stack Tecnológica GCP

### Camada de Armazenamento
- **Cloud Storage**: Data Lake (Bronze/Silver/Gold layers)
- **BigQuery**: Data Warehouse serverless e analytics engine
- **Dataplex**: Governança, catalogação e gerenciamento de metadados

### Camada de Ingestão
- **Fivetran** (managed) ou **Airbyte** (open-source): Conectores ELT
- **Datastream**: CDC (Change Data Capture) para PostgreSQL/MySQL
- **Cloud Functions / Cloud Run**: Ingestão customizada (APIs, webhooks)
- **BigQuery Data Transfer Service**: Google Marketing Platform, SaaS apps

### Camada de Transformação
- **Dataform**: Transformações SQL declarativas (gerenciado pelo Google)
- **BigQuery Scripting**: Processos complexos em SQL procedural
- **Dataproc Serverless**: Spark jobs para transformações pesadas (opcional)

### Camada de Orquestração
- **Cloud Composer (Apache Airflow gerenciado)**: Orquestração de pipelines
- **Cloud Scheduler**: Triggers simples e agendamentos

### Camada de Consumo
- **Looker** ou **Looker Studio**: Business Intelligence
- **Vertex AI Workbench**: Notebooks para Data Science
- **BigQuery ML**: Modelos de ML dentro do BigQuery

### Governança e Qualidade
- **Dataplex Data Quality**: Validações automáticas de dados
- **dbt Tests** (via Dataform): Testes de integridade
- **Cloud Monitoring & Logging**: Observabilidade
- **Cloud Data Loss Prevention (DLP)**: Proteção de dados sensíveis (PII)

---

### Por que Dataform ao invés de dbt?

**Vantagens do Dataform no GCP**:
1. **Nativo do BigQuery**: Gerenciado pelo Google, zero infraestrutura
2. **Integração perfeita**: Git nativo, CI/CD built-in, IAM do GCP
3. **Custo zero de licença**: Incluído no BigQuery (vs dbt Cloud pago)
4. **Performance**: Otimizado para BigQuery (query compilation)
5. **Sintaxe similar ao dbt**: Migração fácil se necessário

**Trade-offs**:
- Ecossistema menor que dbt (menos packages community)
- Documentação menos madura
- Menor adoção no mercado (mas crescendo rápido)

**Decisão**: Usar **Dataform** pela integração nativa e custo-benefício, mas manter compatibilidade conceitual com dbt (caso precise migrar futuramente).

---

## Camadas de Dados (Medallion Architecture)

### Bronze Layer (Raw Data)
**Localização**: `gs://conta-azul-datalake/bronze/`

**Características**:
- Dados brutos, sem transformação (ELT - Extract, Load, Transform)
- Formato: **Parquet** com compressão Snappy (custo-benefício)
- Particionamento: `/year=YYYY/month=MM/day=DD/` (otimização de query)
- Imutável (append-only) - auditoria e reprocessamento
- Retenção: 2 anos (Lifecycle management automático)
- BigLake Tables: Consulta direta do BigQuery sem ingestão

**Estrutura de pastas**:
```
gs://conta-azul-datalake/bronze/
├── sources/
│   ├── postgres_production/
│   │   ├── customers/
│   │   │   └── year=2025/month=10/day=10/data.parquet
│   │   ├── invoices/
│   │   ├── payments/
│   │   └── subscriptions/
│   ├── firebase_analytics/
│   │   └── events/
│   ├── salesforce_crm/
│   │   ├── leads/
│   │   ├── opportunities/
│   │   └── accounts/
│   └── google_analytics_4/
│       └── events/
└── _metadata/
    └── ingestion_logs.json
```

**Exemplo de External Table (BigLake)**:
```sql
-- Permite query direto do Cloud Storage sem copiar dados
CREATE EXTERNAL TABLE `bronze.postgres_customers`
WITH PARTITION COLUMNS (
  year INT64,
  month INT64,
  day INT64
)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://conta-azul-datalake/bronze/sources/postgres_production/customers/*'],
  hive_partition_uri_prefix = 'gs://conta-azul-datalake/bronze/sources/postgres_production/customers/',
  require_hive_partition_filter = TRUE
);
```

### Silver Layer (Cleaned & Conformed)
**Localização**: `BigQuery dataset: silver_*` + backup em `gs://conta-azul-datalake/silver/`

**Características**:
- Dados limpos, padronizados e deduplificados
- Type casting correto (STRING → DATE, TIMESTAMP, NUMERIC)
- Normalização de nomes (snake_case)
- Remoção de duplicatas (QUALIFY ROW_NUMBER())
- Enriquecimento com metadados (_loaded_at, _source_system)
- Particionado por data de evento/transação
- Clustering por colunas de filtro comum

**Estrutura BigQuery**:
```
Project: conta-azul-prod
├── Dataset: silver_core
│   ├── customers (partitioned by created_date, clustered by customer_segment)
│   ├── transactions
│   └── products
├── Dataset: silver_product_analytics
│   ├── events (partitioned by event_date, clustered by event_name, user_id)
│   └── sessions
└── Dataset: silver_crm
    ├── leads
    └── opportunities
```

**Exemplo de tabela Silver**:
```sql
-- Configuração da tabela (Dataform)
-- definitions/silver/core/customers.sqlx

config {
  type: "incremental",
  schema: "silver_core",
  uniqueKey: ["customer_id"],
  bigquery: {
    partitionBy: "created_date",
    clusterBy: ["customer_segment", "country"]
  },
  tags: ["daily", "core"]
}

WITH source AS (
  SELECT * FROM ${ref("bronze", "postgres_customers")}
  ${when(incremental(), `WHERE updated_at > (SELECT MAX(updated_at) FROM ${self()})`)}
),

cleaned AS (
  SELECT
    id AS customer_id,
    LOWER(TRIM(email)) AS email,
    company_name,
    CASE
      WHEN segment IN ('PME', 'MEI', 'Autônomo') THEN segment
      ELSE 'Outros'
    END AS customer_segment,
    CAST(created_at AS DATE) AS created_date,
    created_at,
    updated_at,
    'postgres_production' AS _source_system,
    CURRENT_TIMESTAMP() AS _loaded_at
  FROM source
  WHERE email IS NOT NULL
    AND created_at IS NOT NULL
    -- Deduplicação (pega versão mais recente)
  QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1
)

SELECT * FROM cleaned
```

### Gold Layer (Business Ready)
**Localização**: `BigQuery datasets: gold_*` (por domínio de negócio)

**Características**:
- Modelos dimensionais (Star Schema / Kimball)
- Agregações pré-computadas
- Métricas de negócio calculadas
- SLAs definidos (fresshness, latência)
- Otimizado para consumo (BI, Data Science)
- Documentação rica (business glossary)

**Estrutura por Data Mesh Domains**:
```
Project: conta-azul-prod
├── Dataset: gold_product_analytics (Owner: Product Analytics Team)
│   ├── fct_user_engagement
│   ├── fct_feature_adoption
│   ├── dim_users
│   └── dim_features
├── Dataset: gold_revenue_ops (Owner: RevOps Team)
│   ├── fct_monthly_recurring_revenue
│   ├── fct_sales_pipeline
│   ├── fct_customer_health
│   ├── dim_customers
│   └── dim_subscription_plans
└── Dataset: gold_data_science (Owner: Data Science Team)
    ├── features_customer_churn
    ├── features_revenue_forecast
    └── training_datasets_*
```

**Exemplo de Fact Table (Gold)**:
```sql
-- definitions/gold/revenue_ops/fct_monthly_recurring_revenue.sqlx

config {
  type: "table",
  schema: "gold_revenue_ops",
  description: "Monthly Recurring Revenue por mês e segmento de cliente",
  bigquery: {
    partitionBy: "month",
    clusterBy: ["customer_segment"]
  },
  tags: ["daily", "revenue_ops", "critical"]
}

WITH subscriptions AS (
  SELECT * FROM ${ref("silver_core", "subscriptions")}
  WHERE status = 'active'
),

customers AS (
  SELECT * FROM ${ref("silver_core", "customers")}
),

aggregated AS (
  SELECT
    DATE_TRUNC(s.start_date, MONTH) AS month,
    c.customer_segment,
    c.country,
    COUNT(DISTINCT s.subscription_id) AS active_subscriptions,
    SUM(s.monthly_value_brl) AS mrr_brl,
    SUM(s.annual_value_brl) / 12 AS arr_normalized_brl,
    AVG(s.monthly_value_brl) AS avg_ticket_brl
  FROM subscriptions s
  INNER JOIN customers c USING (customer_id)
  GROUP BY 1, 2, 3
)

SELECT
  *,
  -- Cálculo de growth MoM
  mrr_brl - LAG(mrr_brl) OVER (
    PARTITION BY customer_segment
    ORDER BY month
  ) AS mrr_growth_brl,
  CURRENT_TIMESTAMP() AS _updated_at
FROM aggregated
```

---

## Estratégia de Ingestão

### 1. Dados Transacionais (PostgreSQL, MySQL)

**Opção A: Datastream (CDC em tempo real)**
- **Quando usar**: Dados críticos que precisam de baixa latência (<5 min)
- **Como funciona**: Captura mudanças no banco via CDC (Change Data Capture)
- **Destino**: Cloud Storage (Bronze) → BigQuery (automático)

**Configuração exemplo**:
```yaml
# Datastream connection profile
source:
  type: postgresql
  hostname: prod-db.conta-azul.com.br
  port: 5432
  database: production
  username: datastream_user

destination:
  cloud_storage:
    bucket: gs://conta-azul-datalake/bronze/postgres_production/
    format: AVRO
    partition: daily

tables:
  - customers
  - invoices
  - payments
  - subscriptions

options:
  cdc_strategy: auto  # Log-based CDC
  backfill: true       # Full load inicial + CDC contínuo
```

**Opção B: Fivetran (Managed ELT)**
- **Quando usar**: Múltiplas fontes SaaS (Salesforce, HubSpot, etc.)
- **Vantagem**: Zero manutenção, 400+ conectores
- **Custo**: ~$1.20 por MAR (Monthly Active Row)

**Opção C: Airbyte (Open-Source)**
- **Quando usar**: Redução de custo, controle total
- **Deploy**: Cloud Run (container serverless) ou GKE
- **Custo**: Apenas infraestrutura (~$50-100/mês)

### 2. Eventos de Produto (Firebase, GA4, Custom Events)

**Firebase → BigQuery Export (Nativo)**:
```
Firebase Analytics
    ↓ (streaming, sem código)
BigQuery: analytics_XXXXXX.events_YYYYMMDD
    ↓
Dataform: normalização para silver_product_analytics.events
```

**Google Analytics 4 → BigQuery**:
- Export diário automático (sem custo adicional)
- Tabela particionada: `analytics_XXXXXX.events_YYYYMMDD`

**Custom Events via Cloud Pub/Sub**:
```javascript
// Frontend/Backend envia evento
const {PubSub} = require('@google-cloud/pubsub');
const pubsub = new PubSub();

await pubsub.topic('user-events').publish(
  Buffer.from(JSON.stringify({
    event_name: 'invoice_created',
    user_id: '12345',
    properties: {
      invoice_value: 150.00,
      due_date: '2025-11-10'
    },
    timestamp: new Date().toISOString()
  }))
);
```

**Pub/Sub → Cloud Storage → BigQuery**:
```
Cloud Pub/Sub Topic
    ↓
Dataflow (Streaming)
    ↓
Cloud Storage (Bronze - buffer 5 min)
    ↓
BigQuery (BigLake External Table)
```

### 3. APIs Externas e SaaS (Salesforce, HubSpot, Stripe)

**Fivetran (recomendado para simplicidade)**:
```
Conectores:
- Salesforce (leads, opportunities, accounts)
- HubSpot (contacts, deals)
- Stripe (payments, customers, invoices)

Schedule: Daily at 3 AM BRT
Destination: BigQuery bronze_* datasets
```

**Alternativa - Cloud Run + Cloud Scheduler (custom)**:
```python
# cloud_run/salesforce_extractor/main.py
from simple_salesforce import Salesforce
from google.cloud import storage
import pandas as pd

def extract_salesforce(request):
    sf = Salesforce(username=..., password=..., security_token=...)

    # Query leads modificados nas últimas 24h
    query = """
        SELECT Id, Name, Email, Status, CreatedDate
        FROM Lead
        WHERE LastModifiedDate >= YESTERDAY
    """
    data = sf.query_all(query)

    # Salvar no Cloud Storage (Bronze)
    df = pd.DataFrame(data['records'])
    blob = storage.Client().bucket('conta-azul-datalake').blob(
        f'bronze/salesforce_crm/leads/year={year}/month={month}/day={day}/data.parquet'
    )
    blob.upload_from_string(df.to_parquet(), content_type='application/octet-stream')

    return {'status': 'success', 'records': len(df)}
```

### 4. Arquivos Manuais (CSV, Excel)

**Self-Service Upload**:
```
1. Analista faz upload para gs://conta-azul-datalake/uploads/
2. Cloud Function detecta novo arquivo (trigger)
3. Valida schema e qualidade básica
4. Move para Bronze com metadados
5. Notifica no Slack: "Arquivo X disponível em bronze.manual_uploads"
```

---

## Transformação com Dataform

### Estrutura do Repositório

```
dataform/
├── definitions/              # Modelos SQL
│   ├── sources/             # Declaração de fontes Bronze
│   │   └── sources.js
│   ├── staging/             # Silver layer (1:1 com sources)
│   │   ├── core/
│   │   │   ├── stg_postgres__customers.sqlx
│   │   │   ├── stg_postgres__invoices.sqlx
│   │   │   └── stg_postgres__payments.sqlx
│   │   ├── product_analytics/
│   │   │   └── stg_firebase__events.sqlx
│   │   └── crm/
│   │       └── stg_salesforce__leads.sqlx
│   ├── intermediate/        # Lógica reutilizável
│   │   ├── int_customer_metrics.sqlx
│   │   └── int_invoice_aggregations.sqlx
│   └── marts/               # Gold layer (consumo final)
│       ├── product_analytics/
│       │   ├── fct_user_engagement.sqlx
│       │   └── dim_users.sqlx
│       ├── revenue_ops/
│       │   ├── fct_monthly_recurring_revenue.sqlx
│       │   └── fct_customer_health.sqlx
│       └── data_science/
│           └── features_customer_churn.sqlx
├── includes/                # Funções reutilizáveis (JS)
│   ├── constants.js
│   └── helpers.js
├── tests/                   # Testes customizados
│   └── assert_revenue_positive.sqlx
├── dataform.json            # Configuração do projeto
└── package.json
```

### Exemplo de Modelo Staging (Silver)

```sql
-- definitions/staging/core/stg_postgres__customers.sqlx

config {
  type: "incremental",
  schema: "silver_core",
  uniqueKey: ["customer_id"],
  description: "Customers limpos e normalizados do PostgreSQL",
  bigquery: {
    partitionBy: "created_date",
    clusterBy: ["customer_segment", "country"]
  },
  tags: ["daily", "core"],

  // Assertions (testes inline)
  assertions: {
    uniqueKey: ["customer_id"],
    nonNull: ["customer_id", "email", "created_date"]
  }
}

-- Dependências
${ref("bronze_postgres", "customers")}

-- Lógica de ingestão incremental
pre_operations {
  ${when(incremental(),
    `DELETE FROM ${self()} WHERE customer_id IN (
      SELECT DISTINCT id FROM ${ref("bronze_postgres", "customers")}
      WHERE updated_at > (SELECT MAX(updated_at) FROM ${self()})
    )`
  )}
}

-- Transformação
WITH source AS (
  SELECT * FROM ${ref("bronze_postgres", "customers")}
  ${when(incremental(),
    `WHERE updated_at > (SELECT MAX(updated_at) FROM ${self()})`
  )}
),

cleaned AS (
  SELECT
    -- PKs e IDs
    id AS customer_id,

    -- Dados pessoais (normalizados)
    LOWER(TRIM(email)) AS email,
    INITCAP(TRIM(company_name)) AS company_name,
    REGEXP_REPLACE(phone, r'[^0-9]', '') AS phone_clean,

    -- Classificações
    CASE
      WHEN segment IN ('PME', 'MEI', 'Autônomo') THEN segment
      ELSE 'Outros'
    END AS customer_segment,

    COALESCE(country, 'BR') AS country,

    -- Timestamps
    CAST(created_at AS DATE) AS created_date,
    created_at,
    updated_at,

    -- Metadados
    'postgres_production' AS _source_system,
    CURRENT_TIMESTAMP() AS _loaded_at

  FROM source

  -- Filtros de qualidade
  WHERE email IS NOT NULL
    AND created_at IS NOT NULL
    AND id IS NOT NULL

  -- Deduplicação (última versão)
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY id
    ORDER BY updated_at DESC
  ) = 1
)

SELECT * FROM cleaned

-- Post-hook: registrar estatísticas
post_operations {
  INSERT INTO silver_core._table_metadata (table_name, row_count, updated_at)
  VALUES ('customers', (SELECT COUNT(*) FROM ${self()}), CURRENT_TIMESTAMP())
}
```

### Exemplo de Modelo Intermediate

```sql
-- definitions/intermediate/int_customer_lifetime_metrics.sqlx

config {
  type: "view",  // View (não materializada) - recalcula sempre
  schema: "silver_core",
  description: "Métricas agregadas de lifetime do customer",
  tags: ["intermediate"]
}

WITH customers AS (
  SELECT * FROM ${ref("stg_postgres__customers")}
),

invoices AS (
  SELECT * FROM ${ref("stg_postgres__invoices")}
  WHERE status IN ('paid', 'pending')
),

payments AS (
  SELECT * FROM ${ref("stg_postgres__payments")}
  WHERE payment_status = 'confirmed'
),

customer_metrics AS (
  SELECT
    c.customer_id,
    c.email,
    c.customer_segment,
    c.created_date,

    -- Métricas de receita
    COUNT(DISTINCT i.invoice_id) AS total_invoices,
    SUM(i.total_value_brl) AS total_revenue_brl,
    AVG(i.total_value_brl) AS avg_invoice_value_brl,
    MAX(i.invoice_date) AS last_invoice_date,

    -- Métricas de pagamento
    COUNT(DISTINCT p.payment_id) AS total_payments,
    SUM(CASE WHEN p.payment_method = 'credit_card' THEN 1 ELSE 0 END) AS credit_card_payments,

    -- Métricas de tempo
    DATE_DIFF(CURRENT_DATE(), c.created_date, DAY) AS customer_age_days,
    DATE_DIFF(CURRENT_DATE(), MAX(i.invoice_date), DAY) AS days_since_last_invoice,

    -- Flags
    MAX(i.invoice_date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY) AS is_active_90d

  FROM customers c
  LEFT JOIN invoices i USING (customer_id)
  LEFT JOIN payments p USING (customer_id)

  GROUP BY 1, 2, 3, 4
)

SELECT * FROM customer_metrics
```

### Exemplo de Modelo Mart (Gold)

```sql
-- definitions/marts/revenue_ops/fct_customer_health.sqlx

config {
  type: "table",
  schema: "gold_revenue_ops",
  description: `
    Tabela de Customer Health Score - indicador consolidado de saúde do cliente.

    **Owner**: Revenue Operations Team
    **SLA**: D+1 (atualização diária às 6 AM BRT)
    **Consumidores**: Looker Dashboard "Customer Success Overview"

    **Metodologia Health Score**:
    - 0-40: Churn Risk
    - 41-70: At Risk
    - 71-85: Healthy
    - 86-100: Champion
  `,
  bigquery: {
    partitionBy: "snapshot_date",
    clusterBy: ["health_score_bucket", "customer_segment"]
  },
  tags: ["daily", "revenue_ops", "critical"],

  assertions: {
    nonNull: ["customer_id", "health_score"],
    uniqueKey: ["customer_id", "snapshot_date"]
  }
}

WITH customer_ltv AS (
  SELECT * FROM ${ref("int_customer_lifetime_metrics")}
),

subscription_status AS (
  SELECT
    customer_id,
    MAX(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS has_active_subscription,
    SUM(monthly_value_brl) AS total_mrr
  FROM ${ref("stg_postgres__subscriptions")}
  GROUP BY 1
),

support_tickets AS (
  SELECT
    customer_id,
    COUNT(*) AS tickets_last_30d,
    AVG(CASE WHEN satisfaction_score IS NOT NULL THEN satisfaction_score END) AS avg_csat
  FROM ${ref("stg_zendesk__tickets")}
  WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY 1
),

product_usage AS (
  SELECT
    user_id AS customer_id,
    COUNT(DISTINCT DATE(event_timestamp)) AS active_days_last_30d,
    COUNT(*) AS total_events_last_30d
  FROM ${ref("stg_firebase__events")}
  WHERE event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY 1
),

health_calculation AS (
  SELECT
    c.customer_id,
    c.email,
    c.customer_segment,
    CURRENT_DATE() AS snapshot_date,

    -- Componentes do Health Score (0-100)
    CASE
      WHEN s.has_active_subscription = 1 THEN 30
      ELSE 0
    END AS score_subscription,

    LEAST(c.total_revenue_brl / 1000 * 10, 20) AS score_revenue,  -- Max 20 pts

    CASE
      WHEN c.is_active_90d THEN 15
      ELSE 0
    END AS score_recent_activity,

    LEAST(u.active_days_last_30d * 1.5, 20) AS score_product_usage,  -- Max 20 pts

    LEAST(COALESCE(t.avg_csat, 3) * 2.5, 10) AS score_satisfaction,  -- Max 10 pts (CSAT 1-5)

    CASE
      WHEN COALESCE(t.tickets_last_30d, 0) > 5 THEN -5  -- Penalidade
      ELSE 5
    END AS score_support,

    -- Metadados
    c.total_revenue_brl,
    c.total_invoices,
    c.days_since_last_invoice,
    s.total_mrr,
    u.active_days_last_30d,
    t.tickets_last_30d,
    t.avg_csat

  FROM customer_ltv c
  LEFT JOIN subscription_status s USING (customer_id)
  LEFT JOIN support_tickets t USING (customer_id)
  LEFT JOIN product_usage u USING (customer_id)
),

final AS (
  SELECT
    *,
    -- Health Score consolidado
    score_subscription + score_revenue + score_recent_activity +
    score_product_usage + score_satisfaction + score_support AS health_score,

    -- Classificação
    CASE
      WHEN (score_subscription + score_revenue + score_recent_activity +
            score_product_usage + score_satisfaction + score_support) >= 86 THEN 'Champion'
      WHEN (score_subscription + score_revenue + score_recent_activity +
            score_product_usage + score_satisfaction + score_support) >= 71 THEN 'Healthy'
      WHEN (score_subscription + score_revenue + score_recent_activity +
            score_product_usage + score_satisfaction + score_support) >= 41 THEN 'At Risk'
      ELSE 'Churn Risk'
    END AS health_score_bucket,

    CURRENT_TIMESTAMP() AS _updated_at

  FROM health_calculation
)

SELECT * FROM final
```

### Functions Reutilizáveis (JavaScript)

```javascript
// includes/helpers.js

// Função para gerar código de deduplicação
function deduplicateByColumn(column, orderBy = 'updated_at') {
  return `
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY ${column}
      ORDER BY ${orderBy} DESC
    ) = 1
  `;
}

// Função para adicionar metadados padrão
function addMetadataColumns(sourceSystem) {
  return `
    '${sourceSystem}' AS _source_system,
    CURRENT_TIMESTAMP() AS _loaded_at,
    '${dataform.projectConfig.defaultDatabase}' AS _project,
    '${dataform.projectConfig.defaultSchema}' AS _dataset
  `;
}

// Função para particionamento incremental
function incrementalWhere(timestampColumn) {
  return `
    ${when(incremental(),
      `WHERE ${timestampColumn} > (SELECT MAX(${timestampColumn}) FROM ${self()})`
    )}
  `;
}

module.exports = {
  deduplicateByColumn,
  addMetadataColumns,
  incrementalWhere
};
```

### Configuração do Projeto

```json
// dataform.json
{
  "warehouse": "bigquery",
  "defaultProject": "conta-azul-prod",
  "defaultDataset": "silver_core",
  "assertionSchema": "dataform_assertions",
  "defaultLocation": "southamerica-east1",
  "vars": {
    "environment": "production",
    "bronze_project": "conta-azul-prod",
    "silver_project": "conta-azul-prod",
    "gold_project": "conta-azul-prod"
  }
}
```

---

## Orquestração com Cloud Composer

### Arquitetura de Orquestração

```
Cloud Composer (Managed Airflow)
    ↓
DAGs (Python)
    ├── daily_ingestion_check.py      # Valida completude Bronze
    ├── dataform_silver_layer.py       # Executa modelos staging
    ├── dataform_gold_layer.py         # Executa marts
    ├── data_quality_checks.py         # Dataplex DQ + custom
    └── reporting_refresh.py           # Atualiza dashboards
```

### DAG Principal - Pipeline Diário

```python
# dags/daily_data_pipeline.py

from airflow import DAG
from airflow.providers.google.cloud.operators.dataform import (
    DataformCreateCompilationResultOperator,
    DataformCreateWorkflowInvocationOperator,
)
from airflow.providers.google.cloud.operators.bigquery import (
    BigQueryCheckOperator,
    BigQueryExecuteQueryOperator,
)
from airflow.providers.google.cloud.sensors.gcs import GCSObjectsWithPrefixExistenceSensor
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
from datetime import datetime, timedelta

PROJECT_ID = "conta-azul-prod"
REGION = "southamerica-east1"
DATAFORM_REPO = "dataform-conta-azul"

default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['data-alerts@contaazul.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

with DAG(
    'daily_data_pipeline',
    default_args=default_args,
    description='Pipeline diário completo: Bronze → Silver → Gold',
    schedule_interval='0 3 * * *',  # 3 AM BRT (6 AM UTC)
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['production', 'daily', 'critical'],
    max_active_runs=1,
) as dag:

    # ============================================
    # STEP 1: Validar completude da ingestão Bronze
    # ============================================
    with TaskGroup('validate_bronze_ingestion') as bronze_validation:

        # Checar se arquivos do Datastream chegaram
        check_postgres_ingestion = GCSObjectsWithPrefixExistenceSensor(
            task_id='check_postgres_files',
            bucket='conta-azul-datalake',
            prefix='bronze/sources/postgres_production/customers/year={{ ds_nodash[:4] }}/month={{ ds_nodash[4:6] }}/day={{ ds_nodash[6:8] }}/',
            timeout=1800,  # 30 min timeout
        )

        # Validar contagem mínima de registros
        check_bronze_row_count = BigQueryCheckOperator(
            task_id='check_bronze_row_count',
            sql="""
                SELECT COUNT(*) >= 1000  -- Esperamos pelo menos 1k customers
                FROM `conta-azul-prod.bronze_postgres.customers`
                WHERE DATE(_PARTITIONTIME) = '{{ ds }}'
            """,
            use_legacy_sql=False,
        )

        check_postgres_ingestion >> check_bronze_row_count

    # ============================================
    # STEP 2: Executar Dataform - Silver Layer
    # ============================================
    with TaskGroup('dataform_silver_layer') as silver_layer:

        # Compilar modelos Dataform
        compile_silver = DataformCreateCompilationResultOperator(
            task_id='compile_silver_models',
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
            }
        )

        # Executar modelos staging (Silver)
        run_silver = DataformCreateWorkflowInvocationOperator(
            task_id='run_silver_models',
            project_id=PROJECT_ID,
            region=REGION,
            repository_id=DATAFORM_REPO,
            workflow_invocation={
                'compilation_result': "{{ task_instance.xcom_pull('compile_silver_models')['name'] }}",
                'invocation_config': {
                    'included_tags': ['daily', 'staging'],
                    'transitive_dependencies': True,
                    'fully_refresh_incremental_tables': False
                }
            }
        )

        compile_silver >> run_silver

    # ============================================
    # STEP 3: Testes de qualidade Silver
    # ============================================
    with TaskGroup('silver_quality_checks') as silver_quality:

        # Dataform assertions (built-in)
        run_silver_tests = DataformCreateWorkflowInvocationOperator(
            task_id='run_silver_assertions',
            project_id=PROJECT_ID,
            region=REGION,
            repository_id=DATAFORM_REPO,
            workflow_invocation={
                'compilation_result': "{{ task_instance.xcom_pull('compile_silver_models')['name'] }}",
                'invocation_config': {
                    'included_tags': ['staging'],
                    'transitive_dependencies': False,
                    'actions_only': False,  # Inclui assertions
                }
            }
        )

        # Dataplex Data Quality (managed)
        run_dataplex_dq = BigQueryExecuteQueryOperator(
            task_id='run_dataplex_quality_checks',
            sql="""
                CALL `conta-azul-prod.dataplex_dq.run_quality_checks`(
                    'silver_core',
                    ARRAY['customers', 'invoices', 'payments']
                )
            """,
            use_legacy_sql=False,
        )

        [run_silver_tests, run_dataplex_dq]

    # ============================================
    # STEP 4: Executar Dataform - Gold Layer (Marts)
    # ============================================
    with TaskGroup('dataform_gold_layer') as gold_layer:

        # Compilar modelos Gold
        compile_gold = DataformCreateCompilationResultOperator(
            task_id='compile_gold_models',
            project_id=PROJECT_ID,
            region=REGION,
            repository_id=DATAFORM_REPO,
            compilation_result={
                'git_commitish': 'main',
            }
        )

        # Executar marts por domínio (paralelo)
        for domain in ['product_analytics', 'revenue_ops', 'data_science']:
            run_mart = DataformCreateWorkflowInvocationOperator(
                task_id=f'run_{domain}_mart',
                project_id=PROJECT_ID,
                region=REGION,
                repository_id=DATAFORM_REPO,
                workflow_invocation={
                    'compilation_result': "{{ task_instance.xcom_pull('compile_gold_models')['name'] }}",
                    'invocation_config': {
                        'included_tags': [domain],
                        'transitive_dependencies': True,
                    }
                }
            )
            compile_gold >> run_mart

    # ============================================
    # STEP 5: Testes de qualidade Gold
    # ============================================
    test_gold_metrics = BigQueryCheckOperator(
        task_id='test_gold_revenue_positive',
        sql="""
            SELECT
              LOGICAL_AND(mrr_brl >= 0) AS all_positive,
              COUNT(*) > 0 AS has_data
            FROM `conta-azul-prod.gold_revenue_ops.fct_monthly_recurring_revenue`
            WHERE month = DATE_TRUNC('{{ ds }}', MONTH)
        """,
        use_legacy_sql=False,
    )

    # ============================================
    # STEP 6: Refresh Looker Dashboards (PDTs)
    # ============================================
    def trigger_looker_refresh(**context):
        import looker_sdk
        sdk = looker_sdk.init40()

        # Refresh dashboard críticos
        dashboard_ids = [123, 456, 789]  # Revenue Ops dashboards
        for dash_id in dashboard_ids:
            sdk.run_look(look_id=dash_id, result_format='json')

        return f"Refreshed {len(dashboard_ids)} dashboards"

    refresh_looker = PythonOperator(
        task_id='refresh_looker_dashboards',
        python_callable=trigger_looker_refresh,
    )

    # ============================================
    # STEP 7: Gerar Relatório de Observabilidade
    # ============================================
    def generate_daily_report(**context):
        from google.cloud import bigquery
        import pandas as pd

        client = bigquery.Client()

        # Query estatísticas do pipeline
        stats_query = """
            SELECT
              table_name,
              row_count,
              size_mb,
              last_modified
            FROM `conta-azul-prod.INFORMATION_SCHEMA.TABLE_STORAGE`
            WHERE table_schema IN ('silver_core', 'gold_revenue_ops')
              AND DATE(last_modified) = CURRENT_DATE()
            ORDER BY size_mb DESC
        """

        df = client.query(stats_query).to_dataframe()

        # Enviar para Slack
        # (implementação omitida para brevidade)

        return "Daily report sent to Slack"

    send_daily_report = PythonOperator(
        task_id='send_observability_report',
        python_callable=generate_daily_report,
    )

    # ============================================
    # STEP 8: Update Metadata Catalog
    # ============================================
    update_catalog = BigQueryExecuteQueryOperator(
        task_id='update_data_catalog',
        sql="""
            -- Atualizar estatísticas de freshness
            MERGE `conta-azul-prod.metadata.table_freshness` T
            USING (
              SELECT
                CONCAT(table_schema, '.', table_name) AS full_table_name,
                MAX(TIMESTAMP_MILLIS(creation_time)) AS last_updated
              FROM `conta-azul-prod.INFORMATION_SCHEMA.TABLES`
              WHERE table_schema LIKE 'gold_%'
              GROUP BY 1
            ) S
            ON T.table_name = S.full_table_name
            WHEN MATCHED THEN
              UPDATE SET last_updated = S.last_updated
            WHEN NOT MATCHED THEN
              INSERT (table_name, last_updated) VALUES (S.full_table_name, S.last_updated)
        """,
        use_legacy_sql=False,
    )

    # ============================================
    # Dependências do Pipeline
    # ============================================
    bronze_validation >> silver_layer >> silver_quality
    silver_quality >> gold_layer >> test_gold_metrics
    test_gold_metrics >> [refresh_looker, update_catalog]
    [refresh_looker, update_catalog] >> send_daily_report
```

### Monitoramento do Airflow

```python
# dags/monitoring/pipeline_sla_monitor.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.hooks.bigquery import BigQueryHook
from datetime import datetime, timedelta

def check_pipeline_sla(**context):
    """
    Verifica se tabelas Gold foram atualizadas dentro do SLA (D+1 até 6 AM)
    """
    hook = BigQueryHook()

    query = """
        SELECT
          table_name,
          TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_modified, HOUR) AS hours_since_update
        FROM `conta-azul-prod.gold_revenue_ops.INFORMATION_SCHEMA.TABLES`
        WHERE table_type = 'BASE TABLE'
    """

    df = hook.get_pandas_df(query)

    # SLA: máximo 27 horas (D+1 + 3h de buffer)
    sla_breaches = df[df['hours_since_update'] > 27]

    if not sla_breaches.empty:
        # Enviar alerta crítico
        send_slack_alert(
            channel='#data-alerts',
            message=f"🚨 SLA BREACH: {len(sla_breaches)} tables estão desatualizadas"
        )
        raise Exception(f"SLA breach detected: {sla_breaches.to_dict()}")

    return "All tables within SLA"

with DAG(
    'pipeline_sla_monitor',
    schedule_interval='0 7 * * *',  # 7 AM BRT (1h após deadline)
    start_date=datetime(2025, 1, 1),
    catchup=False,
) as dag:

    check_sla = PythonOperator(
        task_id='check_gold_layer_sla',
        python_callable=check_pipeline_sla,
    )
```

---

## Qualidade e Governança

### 1. Versionamento com Git (Cloud Source Repositories)

**Repositórios**:
```
Cloud Source Repositories (ou GitHub)
├── dataform-conta-azul/          # Modelos Dataform
├── airflow-dags/                  # DAGs do Composer
├── ingestion-scripts/             # Cloud Run/Functions custom
└── data-quality-rules/            # Dataplex DQ configs
```

**Branching Strategy**:
```
main (produção)
├── staging (homologação)
└── feature/* (desenvolvimento)
```

**Pull Request Workflow**:
1. Developer cria branch `feature/add-churn-model`
2. Desenvolve modelo + testes
3. Abre PR para `staging`
4. CI/CD executa:
   - `dataform compile` (syntax check)
   - `dataform run --dry-run` (impacto estimado)
   - Testes unitários
5. Code review por Senior Analytics Engineer
6. Merge para `staging` → deploy automático para env de staging
7. Testes E2E em staging
8. PR de `staging` para `main` → deploy produção

### 2. CI/CD com Cloud Build

```yaml
# cloudbuild.yaml

steps:
  # Step 1: Validar sintaxe SQL
  - name: 'gcr.io/cloud-builders/gcloud'
    id: 'dataform-compile'
    args:
      - 'beta'
      - 'dataform'
      - 'compile'
      - '--project=conta-azul-prod'
      - '--region=southamerica-east1'
      - '--repository=dataform-conta-azul'
      - '--git-commitish=$BRANCH_NAME'

  # Step 2: Executar dry-run (estimar impacto)
  - name: 'gcr.io/cloud-builders/gcloud'
    id: 'dataform-dry-run'
    args:
      - 'beta'
      - 'dataform'
      - 'run'
      - '--project=conta-azul-prod'
      - '--dry-run'
      - '--compilation-result=compilations/latest'

  # Step 3: Executar testes customizados
  - name: 'python:3.11'
    id: 'run-custom-tests'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        pip install -q pytest google-cloud-bigquery pandas
        pytest tests/ -v

  # Step 4: Deploy para staging (se branch = staging)
  - name: 'gcr.io/cloud-builders/gcloud'
    id: 'deploy-staging'
    args:
      - 'beta'
      - 'dataform'
      - 'run'
      - '--project=conta-azul-staging'
      - '--compilation-result=compilations/latest'
      - '--tags=staging'
    waitFor: ['dataform-compile', 'run-custom-tests']
    env:
      - 'BRANCH=$BRANCH_NAME'

# Trigger apenas em branches específicas
options:
  logging: CLOUD_LOGGING_ONLY
  machineType: 'N1_HIGHCPU_8'

# Notificações
substitutions:
  _SLACK_WEBHOOK: 'https://hooks.slack.com/services/...'

# Executar apenas em PRs e merges
trigger:
  branches:
    - ^main$
    - ^staging$
    - ^feature/.*
```

### 3. Testes de Qualidade de Dados

**Nível 1: Dataform Assertions (Inline)**

```sql
-- definitions/staging/core/stg_postgres__customers.sqlx

config {
  assertions: {
    uniqueKey: ["customer_id"],
    nonNull: ["customer_id", "email", "created_date"],
    rowConditions: [
      "email LIKE '%@%'",  -- Email válido
      "created_date <= CURRENT_DATE()",  -- Não futuro
      "customer_segment IN ('PME', 'MEI', 'Autônomo', 'Outros')"
    ]
  }
}
```

**Nível 2: Dataplex Data Quality (Managed)**

```yaml
# dataplex_dq/rules/customers_quality.yaml

entity: silver_core.customers
row_filters: "created_date >= CURRENT_DATE() - 365"  # Últimos 12 meses

rules:
  # Completude
  - column: customer_id
    dimension: COMPLETENESS
    threshold: 100%

  - column: email
    dimension: COMPLETENESS
    threshold: 99.5%  # 0.5% de tolerância

  # Unicidade
  - column: customer_id
    dimension: UNIQUENESS
    threshold: 100%

  # Validade
  - column: email
    dimension: VALIDITY
    rule_type: REGEX
    regex: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    threshold: 99%

  - column: customer_segment
    dimension: VALIDITY
    rule_type: SET_EXPECTATION
    expected_values: ['PME', 'MEI', 'Autônomo', 'Outros']
    threshold: 100%

  # Consistência
  - dimension: CONSISTENCY
    rule_type: CUSTOM_SQL
    sql: |
      SELECT COUNT(*)
      FROM silver_core.customers c
      LEFT JOIN silver_core.subscriptions s USING (customer_id)
      WHERE c.customer_segment = 'PME'
        AND s.plan_type = 'free'  -- Inconsistência: PME não deve ter plano free
    threshold: 0  # Zero ocorrências

  # Atualidade (Freshness)
  - dimension: TIMELINESS
    rule_type: CUSTOM_SQL
    sql: |
      SELECT TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_loaded_at), HOUR)
      FROM silver_core.customers
    threshold: 24  # Máximo 24 horas desatualizado
```

**Nível 3: Testes Customizados (Python + pytest)**

```python
# tests/test_revenue_ops_mart.py

import pytest
from google.cloud import bigquery
import pandas as pd
from datetime import datetime, timedelta

@pytest.fixture
def bq_client():
    return bigquery.Client(project='conta-azul-prod')

def test_mrr_always_positive(bq_client):
    """MRR nunca deve ser negativo"""
    query = """
        SELECT COUNT(*) as negative_count
        FROM `conta-azul-prod.gold_revenue_ops.fct_monthly_recurring_revenue`
        WHERE mrr_brl < 0
    """
    df = bq_client.query(query).to_dataframe()
    assert df['negative_count'][0] == 0, "Found negative MRR values"

def test_mrr_growth_plausible(bq_client):
    """Crescimento de MRR não deve ser > 50% MoM (anomalia)"""
    query = """
        WITH growth AS (
          SELECT
            month,
            mrr_brl,
            LAG(mrr_brl) OVER (ORDER BY month) AS prev_mrr,
            (mrr_brl - LAG(mrr_brl) OVER (ORDER BY month)) /
              LAG(mrr_brl) OVER (ORDER BY month) AS growth_rate
          FROM `conta-azul-prod.gold_revenue_ops.fct_monthly_recurring_revenue`
          WHERE customer_segment = 'PME'
        )
        SELECT MAX(ABS(growth_rate)) AS max_growth
        FROM growth
        WHERE month >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
    """
    df = bq_client.query(query).to_dataframe()
    assert df['max_growth'][0] < 0.5, "MRR growth > 50% detected (potential anomaly)"

def test_customer_health_score_range(bq_client):
    """Health score deve estar entre 0-100"""
    query = """
        SELECT
          MIN(health_score) AS min_score,
          MAX(health_score) AS max_score
        FROM `conta-azul-prod.gold_revenue_ops.fct_customer_health`
        WHERE snapshot_date = CURRENT_DATE()
    """
    df = bq_client.query(query).to_dataframe()
    assert 0 <= df['min_score'][0] <= 100
    assert 0 <= df['max_score'][0] <= 100

def test_data_freshness_sla(bq_client):
    """Gold tables devem ser atualizados D+1 (máximo 27h)"""
    query = """
        SELECT
          table_name,
          TIMESTAMP_DIFF(CURRENT_TIMESTAMP(),
                         TIMESTAMP_MILLIS(last_modified_time), HOUR) AS hours_old
        FROM `conta-azul-prod.gold_revenue_ops.__TABLES__`
        WHERE table_id NOT LIKE '%_temp%'
    """
    df = bq_client.query(query).to_dataframe()
    stale_tables = df[df['hours_old'] > 27]

    assert stale_tables.empty, f"Stale tables found: {stale_tables['table_name'].tolist()}"
```

### 4. Observabilidade e Monitoramento

**Cloud Monitoring Dashboards**:
```
Dashboard: Data Pipeline Health
├── Painel 1: Freshness
│   ├── "Time since last update" (por table)
│   └── Alerta: > 27 horas
├── Painel 2: Data Quality
│   ├── "Dataplex DQ pass rate" (últimas 24h)
│   └── "Dataform assertion failures" (count)
├── Painel 3: Performance
│   ├── "BigQuery slot usage" (timeseries)
│   ├── "Query execution time" (p50, p95, p99)
│   └── "Bytes processed/scanned" (cost proxy)
└── Painel 4: Pipeline Status
    ├── "Airflow DAG success rate" (últimos 7 dias)
    └── "Failed task count" (por DAG)
```

**Alertas Críticos** (Cloud Monitoring + Slack):
```yaml
alerts:
  - name: "Gold Layer SLA Breach"
    condition: "table_freshness > 27 hours"
    severity: CRITICAL
    notification: ["#data-alerts", "data-eng-oncall@contaazul.com"]

  - name: "Data Quality Failure"
    condition: "dataplex_dq_pass_rate < 95%"
    severity: HIGH
    notification: ["#data-alerts"]

  - name: "BigQuery Cost Spike"
    condition: "daily_cost > $500 OR daily_cost > 2x(7d_avg)"
    severity: MEDIUM
    notification: ["#data-eng", "finops@contaazul.com"]

  - name: "Airflow DAG Failure"
    condition: "dag_failure AND dag_id = 'daily_data_pipeline'"
    severity: CRITICAL
    notification: ["#data-alerts", "pagerduty"]
```

### 5. Governança de Dados

**Dataplex Data Catalog** (Auto-discovery + Manual enrichment):

```
Catálogo de Dados
├── Domínio: Product Analytics
│   ├── Dataset: gold_product_analytics.fct_user_engagement
│   │   ├── Descrição: "Engajamento de usuários (DAU, WAU, MAU)"
│   │   ├── Owner: product-analytics@contaazul.com
│   │   ├── Tags: [pii, daily, critical]
│   │   ├── SLA: D+1 6 AM BRT
│   │   └── Consumers: ["Looker Dashboard: Product Overview"]
│   └── ...
├── Domínio: Revenue Operations
└── Domínio: Data Science
```

**Data Classification (DLP)**:
```sql
-- Aplicar tags de sensibilidade automaticamente
-- Policy Tag Taxonomy: conta-azul-prod.data_classification

CREATE POLICY TAG sensitive_pii
  ON `conta-azul-prod.data_classification`
  WITH DESCRIPTION 'Dados pessoais sensíveis (LGPD Art. 5º)'
  AND masking_rule = 'SHA256';  -- Masking para não-autorizados

-- Aplicar em colunas
ALTER TABLE `conta-azul-prod.silver_core.customers`
  SET COLUMN OPTIONS (
    email = (description = 'Email do cliente',
             policy_tags = ['projects/conta-azul-prod/locations/southamerica-east1/taxonomies/123/policyTags/sensitive_pii'])
  );
```

**Row-Level Security (RLS)**:
```sql
-- Analistas de RevOps só veem clientes do segmento PME
CREATE ROW ACCESS POLICY revops_only_pme
  ON `conta-azul-prod.gold_revenue_ops.fct_customer_health`
  GRANT TO ('group:revops-analysts@contaazul.com')
  FILTER USING (customer_segment = 'PME');

-- Data Science team vê todos os dados (anonimizados)
CREATE ROW ACCESS POLICY data_science_all
  ON `conta-azul-prod.gold_data_science.features_customer_churn`
  GRANT TO ('group:data-science@contaazul.com')
  FILTER USING (TRUE);
```

---

## Camada de Consumo

### 1. Para Analistas de Dados (SQL Users)

**BigQuery Studio** (interface SQL nativa):
- Query editor com autocomplete
- Saved queries e notebooks SQL
- Compartilhamento de queries via link

**Looker / Looker Studio**:

**Exemplo de Dashboard (Revenue Operations)**:
```
Dashboard: Revenue Operations Overview
├── KPI Cards (Top)
│   ├── MRR Atual: R$ 1.2M (+8% MoM)
│   ├── Churn Rate: 3.2% (↓ 0.5pp)
│   ├── Customer Health Score Médio: 78/100
│   └── Active Subscriptions: 3,456 (+120 MoM)
├── Charts (Middle)
│   ├── [Line] MRR Evolution (12 meses)
│   ├── [Funnel] Sales Pipeline by Stage
│   ├── [Bar] MRR by Customer Segment
│   └── [Heatmap] Customer Health Score Distribution
└── Table (Bottom)
    └── Top 50 Customers at Churn Risk (Health < 40)
```

**LookML (Looker semantic layer)**:
```lookml
# models/revenue_ops.model.lkml

connection: "bigquery_conta_azul_prod"

include: "/views/**/*.view.lkml"

explore: fct_monthly_recurring_revenue {
  label: "Monthly Recurring Revenue"

  join: dim_customers {
    sql_on: ${fct_monthly_recurring_revenue.customer_id} = ${dim_customers.customer_id} ;;
    relationship: many_to_one
  }

  always_filter: {
    filters: [fct_monthly_recurring_revenue.month: "12 months"]
  }
}

# views/fct_monthly_recurring_revenue.view.lkml

view: fct_monthly_recurring_revenue {
  sql_table_name: `conta-azul-prod.gold_revenue_ops.fct_monthly_recurring_revenue` ;;

  dimension_group: month {
    type: time
    timeframes: [date, month, quarter, year]
    sql: ${TABLE}.month ;;
  }

  dimension: customer_segment {
    type: string
    sql: ${TABLE}.customer_segment ;;
  }

  measure: total_mrr {
    type: sum
    sql: ${TABLE}.mrr_brl ;;
    value_format_name: brl_currency
    label: "Total MRR (R$)"
  }

  measure: mrr_growth_pct {
    type: number
    sql:
      (${total_mrr} - LAG(${total_mrr}) OVER (ORDER BY ${month_month})) /
      LAG(${total_mrr}) OVER (ORDER BY ${month_month})
    ;;
    value_format_name: percent_1
  }
}
```

### 2. Para Cientistas de Dados (Python/R/Notebooks)

**Vertex AI Workbench** (Managed Jupyter):

```python
# notebook: customer_churn_prediction.ipynb

# Conectar ao BigQuery
from google.cloud import bigquery
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

client = bigquery.Client(project='conta-azul-prod')

# Ler feature store
query = """
    SELECT *
    FROM `conta-azul-prod.gold_data_science.features_customer_churn`
    WHERE snapshot_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 MONTH)
"""

df = client.query(query).to_dataframe()

# Features disponíveis (já preparadas pelo Analytics Engineering):
# - customer_lifetime_days
# - total_revenue_brl
# - days_since_last_login
# - feature_usage_score
# - support_tickets_count_30d
# - payment_failure_count
# - health_score
# - has_active_subscription
# - churn_label (target)

X = df.drop(['customer_id', 'snapshot_date', 'churn_label'], axis=1)
y = df['churn_label']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Treinar modelo
model = RandomForestClassifier(n_estimators=100, max_depth=10)
model.fit(X_train, y_train)

# Avaliar
from sklearn.metrics import classification_report, roc_auc_score
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print(f"ROC AUC: {roc_auc_score(y_test, y_proba):.3f}")
print(classification_report(y_test, y_pred))

# Salvar previsões de volta no BigQuery
predictions_df = df[['customer_id']].copy()
predictions_df['churn_probability'] = model.predict_proba(X)[:, 1]
predictions_df['prediction_date'] = pd.Timestamp.now()

# Write to BigQuery
predictions_df.to_gbq(
    destination_table='gold_data_science.customer_churn_predictions',
    project_id='conta-azul-prod',
    if_exists='append'
)
```

**BigQuery ML** (ML direto no SQL - sem Python):

```sql
-- Treinar modelo de churn dentro do BigQuery
CREATE OR REPLACE MODEL `conta-azul-prod.gold_data_science.churn_model_bqml`
OPTIONS(
  model_type='LOGISTIC_REG',
  input_label_cols=['churn_label'],
  auto_class_weights=TRUE,
  max_iterations=50
) AS
SELECT
  -- Features
  customer_lifetime_days,
  total_revenue_brl,
  days_since_last_login,
  feature_usage_score,
  support_tickets_count_30d,
  payment_failure_count,
  health_score,
  has_active_subscription,

  -- Target
  churn_label
FROM `conta-azul-prod.gold_data_science.features_customer_churn`
WHERE snapshot_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH);

-- Avaliar modelo
SELECT
  roc_auc,
  precision,
  recall
FROM ML.EVALUATE(
  MODEL `conta-azul-prod.gold_data_science.churn_model_bqml`,
  (
    SELECT * FROM `conta-azul-prod.gold_data_science.features_customer_churn`
    WHERE snapshot_date = CURRENT_DATE()
  )
);

-- Fazer previsões
SELECT
  customer_id,
  predicted_churn_label,
  predicted_churn_label_probs[OFFSET(1)].prob AS churn_probability
FROM ML.PREDICT(
  MODEL `conta-azul-prod.gold_data_science.churn_model_bqml`,
  (SELECT * FROM `conta-azul-prod.gold_data_science.features_customer_churn`
   WHERE snapshot_date = CURRENT_DATE())
)
ORDER BY churn_probability DESC
LIMIT 100;
```

### 3. Para Stakeholders de Negócio

**Dashboards Executivos** (Looker - auto-refresh):

```
Dashboard: Executive Summary (CEO/CFO)
├── Revenue Metrics
│   ├── MRR: R$ 1.2M (+8% MoM)
│   ├── ARR: R$ 14.4M
│   ├── Net Revenue Retention: 108%
│   └── Customer LTV: R$ 4.2k
├── Growth Metrics
│   ├── New Customers (month): 120
│   ├── Churned Customers: 38 (-3.2%)
│   ├── Expansion Revenue: R$ 45k
│   └── Sales Pipeline: R$ 3.1M
├── Product Metrics
│   ├── MAU (Monthly Active Users): 12.4k (+15%)
│   ├── Feature Adoption Rate: 68%
│   └── NPS: 72 (Promoters - Detractors)
└── [Line Chart] 12-month Revenue & User Growth Trend
```

**Scheduled Reports** (Email/Slack):
```python
# Configuração Looker Schedule
schedule:
  frequency: daily
  time: "08:00 BRT"
  recipients:
    - ceo@contaazul.com
    - cfo@contaazul.com
    - "Slack: #executive-updates"
  format: PDF
  filters:
    date_range: "yesterday"
```

**Data Catalog Self-Service** (Dataplex):
- Busca por keyword: "customer churn"
- Visualiza: datasets, columns, lineage, owners
- Solicita acesso via IAM (self-service approval)

---

## Estimativa de Custos (Mensais)

### Premissas
- **Volume de dados**: ~100 GB novos/mês, 1 TB total armazenado
- **Eventos**: ~500k eventos/dia (product analytics)
- **Queries**: ~2 TB processados/mês (análises + dashboards)
- **Usuários**: 50 analistas/cientistas + 20 dashboards Looker

### Breakdown de Custos (USD)

| Serviço GCP | Descrição | Custo Mensal |
|-------------|-----------|--------------|
| **Cloud Storage** | 1 TB (Standard class) | $20 |
| **BigQuery Storage** | 1 TB active storage + 500 GB long-term | $25 |
| **BigQuery Compute** | 2 TB queries/mês (~$5/TB) | $10 |
| **BigQuery Streaming** | 500k eventos/dia * 30 = 15M rows ($0.01/200MB) | $15 |
| **Datastream** | CDC PostgreSQL (1 stream) | $100 |
| **Fivetran** | 100k MAR * $1.20 | $120 |
| **Cloud Composer** | Small environment (1 vCPU) | $200 |
| **Dataform** | Incluído no BigQuery | $0 |
| **Dataplex** | 50 tables * $1/table | $50 |
| **Cloud Run** | Custom ingestion (1M requests) | $10 |
| **Looker Studio** | Grátis (até 10 users) | $0 |
| **Vertex AI Notebooks** | 2 instâncias n1-standard-4 (8h/dia) | $80 |
| **Cloud Monitoring** | Logs + métricas | $20 |
| **Networking** | Egress + inter-region | $30 |
| **Outros** | Cloud Functions, Pub/Sub, etc. | $20 |
| **TOTAL** | | **~$700/mês** |

### Otimizações de Custo

1. **Particionamento e Clustering**: Reduz scans em 80-90%
   ```sql
   -- Sem particionamento: 1 TB scanned = $5
   -- Com particionamento: 100 GB scanned = $0.50
   ```

2. **BigQuery BI Engine** (cache): $40/mês para 10 GB cache → queries repetitivas grátis

3. **Cloud Storage Lifecycle**:
   ```yaml
   lifecycle:
     - action: SetStorageClass
       storage_class: NEARLINE
       condition:
         age: 90  # Mover para Nearline após 90 dias (75% mais barato)
     - action: Delete
       condition:
         age: 730  # Deletar após 2 anos
   ```

4. **Dataform scheduled runs**: Executar apenas modelos modificados (incremental)

5. **Looker PDT persistence**: Cachear queries pesadas (regenerar 1x/dia)

---

## Roadmap de Implementação

### Fase 0: Preparação (Semana 0)
- [ ] Criar projeto GCP (`conta-azul-prod`)
- [ ] Configurar billing account e budgets/alerts
- [ ] Setup IAM roles e service accounts
- [ ] Criar buckets Cloud Storage (Bronze/Silver)
- [ ] Provisionar BigQuery datasets (bronze_*, silver_*, gold_*)

### Fase 1: Foundation (Semanas 1-2)
- [ ] Deploy Cloud Composer (Airflow) - ambiente Small
- [ ] Setup Cloud Source Repositories para código
- [ ] Configurar CI/CD básico (Cloud Build)
- [ ] Criar estrutura inicial Dataform
- [ ] Deploy Dataplex para catalogação

### Fase 2: Ingestão - Quick Win (Semanas 3-4)
**Objetivo**: 1 fonte de dados end-to-end

- [ ] Conectar PostgreSQL produção via Datastream (CDC)
- [ ] Tabelas prioritárias: customers, invoices, payments, subscriptions
- [ ] Validar chegada de dados no Bronze (Cloud Storage)
- [ ] Criar BigLake external tables

### Fase 3: Transformação - Silver Layer (Semanas 5-6)
- [ ] Dataform: modelos staging para tabelas do PostgreSQL
- [ ] Implementar deduplicação e limpeza
- [ ] Testes de qualidade básicos (not null, unique)
- [ ] DAG Airflow para orquestração Silver

### Fase 4: Transformação - Gold Layer (Semana 7)
- [ ] Dataform: primeiro mart (`fct_monthly_recurring_revenue`)
- [ ] Modelos dimensionais (dim_customers)
- [ ] Documentação inline (descriptions, owners)
- [ ] Testes de qualidade avançados

### Fase 5: Consumo - BI (Semana 8)
- [ ] Deploy Looker ou Looker Studio
- [ ] Criar LookML views para Gold layer
- [ ] Primeiro dashboard (Revenue Ops Overview)
- [ ] Treinamento para analistas

### Fase 6: Qualidade & Observabilidade (Semana 9)
- [ ] Configurar Dataplex Data Quality rules
- [ ] Implementar testes customizados (pytest)
- [ ] Cloud Monitoring dashboards
- [ ] Alertas críticos (SLA, DQ failures)

### Fase 7: Expansão de Fontes (Semanas 10-11)
- [ ] Adicionar Firebase Analytics export
- [ ] Conectar Salesforce via Fivetran
- [ ] Google Analytics 4 → BigQuery
- [ ] Normalizar para Silver layer

### Fase 8: Product Analytics & Data Science (Semana 12)
- [ ] Marts de Product Analytics (fct_user_engagement)
- [ ] Feature store para Data Science
- [ ] Deploy Vertex AI Workbench
- [ ] Primeiro modelo BigQuery ML (churn prediction)

### Fase 9: Governança (Semana 13)
- [ ] Implementar Data Catalog completo
- [ ] DLP para classificação de PII
- [ ] Row-Level Security (RLS) por domínio
- [ ] Políticas de retenção automatizadas

### Fase 10: Otimização & Scale (Semanas 14-16)
- [ ] Performance tuning (clustering, BI Engine)
- [ ] Cost optimization audit
- [ ] Documentação completa (Confluence/Notion)
- [ ] Handoff para time de Analytics Engineering

---

## Diferenciais da Solução

### 1. Serverless-First
- **Zero gerenciamento de infraestrutura**: BigQuery, Dataform, Cloud Run
- **Escala automática**: De 0 a milhões de queries sem reconfiguração
- **Custo variável**: Paga apenas pelo uso real

### 2. Data Mesh Ready
- **Domínios claros**: Product Analytics, RevOps, Data Science
- **Ownership distribuído**: Cada time mantém seus marts
- **Self-service**: Analistas criam novos modelos sem depender de engenharia

### 3. Qualidade como Código
- **Testes versionados**: Git + CI/CD
- **Múltiplas camadas**: Dataform assertions + Dataplex DQ + pytest
- **Automação**: Falhas bloqueiam deploy

### 4. Observabilidade Completa
- **Lineage automático**: Dataplex rastreia origem dos dados
- **Freshness tracking**: SLAs monitorados 24/7
- **Cost monitoring**: Alertas de custo anômalo

---

## Próximos Passos

1. **Validação da Proposta**
   - Apresentar arquitetura para stakeholders técnicos (CTO, Head of Data)
   - Alinhar prioridades de fontes de dados com Product Analytics, RevOps e Data Science

2. **Priorização de Use Cases**
   - Identificar "quick win": dashboard mais crítico para negócio
   - Exemplo: MRR Dashboard → impacto direto em RevOps

3. **Estimativa Detalhada**
   - Refinar custos com volume real de dados
   - Sizing de Cloud Composer (pode começar menor)

4. **POC (Proof of Concept) - 2 semanas**
   - Fonte: PostgreSQL produção
   - Pipeline: Bronze → Silver → Gold (1 mart)
   - Consumo: 1 dashboard Looker
   - **Meta**: Demonstrar valor end-to-end

5. **Formação de Time**
   - 1 Senior Analytics Engineer (arquitetura + mentoria)
   - 2 Analytics Engineers (desenvolvimento)
   - Suporte: 1 Data Engineer (ingestão complexa)

---

## Apêndice

### Glossário de Termos

- **ELT**: Extract, Load, Transform (vs ETL - transformação após load)
- **CDC**: Change Data Capture (captura mudanças em tempo real)
- **Medallion Architecture**: Bronze (raw) → Silver (clean) → Gold (business)
- **Data Mesh**: Arquitetura descentralizada por domínios de negócio
- **SLA**: Service Level Agreement (acordo de nível de serviço)
- **MAR**: Monthly Active Rows (métrica de custo Fivetran)
- **MRR**: Monthly Recurring Revenue
- **DAU/WAU/MAU**: Daily/Weekly/Monthly Active Users

### Referências

- [Google Cloud Data Analytics Reference Patterns](https://cloud.google.com/architecture/reference-patterns/overview)
- [Dataform Best Practices](https://cloud.google.com/dataform/docs/best-practices)
- [Medallion Architecture (Databricks)](https://www.databricks.com/glossary/medallion-architecture)
- [Data Mesh Principles](https://www.datamesh-architecture.com/)
- [BigQuery Optimization Guide](https://cloud.google.com/bigquery/docs/best-practices-performance-overview)

### Contato

**Proposta elaborada para**: Conta Azul
**Posição**: Analytics Engineer (Especialista)
**Data**: Outubro 2025
**Plataforma**: Google Cloud Platform (GCP)

---

**Observação**: Esta é uma proposta de arquitetura (desenho da solução). A implementação completa seguiria o roadmap de 16 semanas descrito acima.
