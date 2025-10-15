# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a technical challenge submission for a Analytics Engineer (Specialist) position at Conta Azul. It proposes a complete data architecture for a data platform on Google Cloud Platform (GCP) that serves three data teams: Product Analytics, Data Science, and Revenue Operations.

The proposal includes comprehensive documentation, code examples, and implementation guidance for a Medallion Architecture (Bronze/Silver/Gold) with Data Mesh principles.

## Architecture Pattern

**Medallion Architecture on GCP:**
- **Bronze Layer**: Raw data stored in Cloud Storage (Parquet format, partitioned by date)
- **Silver Layer**: Cleaned and conformed data in BigQuery (deduplicated, typed, normalized)
- **Gold Layer**: Business-ready dimensional models in BigQuery (aggregated, optimized for consumption)

**Data Mesh Approach:**
Three domain-specific datasets in Gold layer:
- `gold_product_analytics/`: User engagement, feature adoption
- `gold_revenue_ops/`: MRR, customer health, sales pipeline
- `gold_data_science/`: Feature stores, training datasets

## Technology Stack

- **Data Lake**: Cloud Storage (gs://conta-azul-datalake/bronze/, silver/, gold/)
- **Data Warehouse**: BigQuery
- **Transformation**: Dataform (SQL-based, managed by Google)
- **Orchestration**: Cloud Composer (managed Apache Airflow)
- **Ingestion**: Datastream (CDC), Fivetran (SaaS connectors), Cloud Run (custom APIs)
- **BI**: Looker / Looker Studio
- **ML/DS**: Vertex AI Workbench, BigQuery ML
- **Governance**: Dataplex, Data Catalog, Cloud DLP

## Directory Structure

```
desafio-tecnico-conta-azul/
├── README.md                    # Main documentation (~40 pages)
├── RESUMO_EXECUTIVO.md         # Executive summary (~20 pages)
├── ARCHITECTURE.md             # Detailed diagrams (10+ Mermaid diagrams)
├── COMO_USAR.md               # Usage guide
├── INDICE.md                  # Index and navigation guide
├── desafio.md                 # Original challenge description
├── dataform/                  # SQL transformation code
│   ├── dataform.json         # Dataform project config
│   └── definitions/
│       ├── sources/          # Bronze layer source declarations
│       ├── staging/          # Silver layer (cleaned data)
│       │   └── core/
│       │       └── stg_postgres__customers.sqlx
│       └── marts/            # Gold layer (business models)
│           └── revenue_ops/
│               └── fct_monthly_recurring_revenue.sqlx
├── examples/
│   ├── airflow/
│   │   └── daily_pipeline_dag.py    # Main orchestration DAG
│   └── tests/
│       └── test_data_quality.py     # Data quality tests
└── docs/
    └── APRESENTACAO.md              # Presentation slides
```

## Dataform Models

### Naming Conventions

**Staging (Silver):**
- `stg_{source}__{table}.sqlx`
- Example: `stg_postgres__customers.sqlx`, `stg_firebase__events.sqlx`

**Intermediate:**
- `int_{description}.sqlx`
- Example: `int_customer_lifetime_metrics.sqlx`

**Marts (Gold):**
- `fct_{fact_name}.sqlx` for fact tables
- `dim_{dimension_name}.sqlx` for dimension tables
- Example: `fct_monthly_recurring_revenue.sqlx`, `dim_customers.sqlx`

### Dataform Configuration (dataform.json)

```json
{
  "warehouse": "bigquery",
  "defaultProject": "conta-azul-prod",
  "defaultDataset": "silver_core",
  "defaultLocation": "southamerica-east1",
  "assertionSchema": "dataform_assertions"
}
```

### Key Dataform Patterns

**Incremental Processing:**
```sql
config {
  type: "incremental",
  uniqueKey: ["customer_id"],
}

pre_operations {
  ${when(incremental(),
    `DELETE FROM ${self()} WHERE customer_id IN (...)`
  )}
}

WITH source AS (
  SELECT * FROM ${ref("bronze_postgres", "customers")}
  ${when(incremental(),
    `WHERE updated_at > (SELECT MAX(updated_at) FROM ${self()})`
  )}
)
```

**Deduplication Pattern:**
```sql
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY id
  ORDER BY updated_at DESC
) = 1
```

**Assertions (Data Quality):**
```sql
config {
  assertions: {
    uniqueKey: ["customer_id"],
    nonNull: ["customer_id", "email", "created_date"],
    rowConditions: [
      "email LIKE '%@%'",
      "created_date <= CURRENT_DATE()"
    ]
  }
}
```

## Airflow DAG Structure

**Main DAG:** `daily_pipeline_dag.py`
- **Schedule:** Daily at 3 AM BRT (6 AM UTC)
- **SLA:** 3 hours (must complete by 6 AM BRT)

**Pipeline Flow:**
1. Validate Bronze ingestion (GCS sensors)
2. Compile Dataform models
3. Run Silver layer (incremental on weekdays, full refresh on Sundays)
4. Run Silver assertions
5. Run Gold marts (parallel by domain: product_analytics, revenue_ops, data_science)
6. Run Gold quality checks
7. Refresh Looker dashboards
8. Update metadata catalog
9. Generate observability report

**Key Operators:**
- `DataformCreateCompilationResultOperator`: Compile Dataform models
- `DataformCreateWorkflowInvocationOperator`: Execute Dataform workflows
- `BigQueryCheckOperator`: Data quality assertions
- `GCSObjectsWithPrefixExistenceSensor`: Wait for Bronze data

## Data Quality Testing

**Three-layer approach:**

1. **Dataform Assertions** (inline in .sqlx files)
   - uniqueKey, nonNull, rowConditions

2. **Dataplex Data Quality** (managed service)
   - Completeness, Validity, Consistency, Timeliness checks

3. **Custom pytest Tests** (examples/tests/test_data_quality.py)
   - Business rule validations (e.g., MRR always positive)
   - Cross-table consistency checks
   - Freshness SLA checks (< 27 hours)
   - Performance checks (partitioning effectiveness)

## Common Development Tasks

### Testing Dataform Models Locally

```bash
cd dataform/

# Compile models (syntax check)
dataform compile

# Run a specific model
dataform run --tags=staging

# Test assertions
dataform test
```

### Running Quality Tests

```bash
cd examples/tests/

# Install dependencies
pip install pytest google-cloud-bigquery pandas

# Run all tests
pytest test_data_quality.py -v

# Run specific test
pytest test_data_quality.py::test_mrr_always_positive -v
```

### Understanding the Pipeline

Key files to understand the complete data flow:
1. `README.md` sections: "Estratégia de Ingestão" → "Transformação com Dataform" → "Orquestração"
2. `ARCHITECTURE.md`: Flow diagram (sequence diagram showing Bronze → Silver → Gold)
3. `examples/airflow/daily_pipeline_dag.py`: Actual orchestration implementation

## Important Patterns and Conventions

### BigQuery Table Configuration

**Partitioning:** Always partition by date for cost optimization
- Silver: `partitionBy: "created_date"` or `"event_date"`
- Gold: `partitionBy: "month"` for aggregated facts

**Clustering:** Add clustering for common filter columns
- Example: `clusterBy: ["customer_segment", "country"]`

### Metadata Columns

All transformed tables include:
```sql
'postgres_production' AS _source_system,
'datastream_cdc' AS _ingestion_method,
CURRENT_TIMESTAMP() AS _loaded_at,
'production' AS _environment
```

### SQL Style

- Use CTEs (WITH clauses) for readability
- Always include comments for business logic
- Deduplication using QUALIFY (not subqueries)
- Use ${ref("schema", "table")} for dependencies (Dataform)

## Cost Optimization

**Key strategies implemented:**

1. **Partitioning:** Reduces query scans by 80-90%
   - All tables partitioned by date
   - `require_hive_partition_filter = TRUE` on external tables

2. **Clustering:** Reduces costs for filtered queries
   - Common filter columns (segment, country, status)

3. **Incremental Processing:** Only process new/changed data
   - Dataform incremental models
   - CDC via Datastream for real-time sources

4. **Storage Lifecycle:**
   - Bronze > 90 days → Nearline (-75% cost)
   - Bronze > 2 years → Delete

## Git Workflow

**Branching:**
- `main`: Production
- `staging`: Staging environment
- `feature/*`: Development branches

**Pull Request Requirements:**
- Code review mandatory
- CI/CD checks must pass (Cloud Build)
- Dataform compile succeeds
- Tests pass

## Documentation Standards

**For Dataform models:**
- Always include `description` in config block
- Document business logic in comments
- Specify owner and SLA for Gold marts
- List downstream consumers (dashboards, ML models)

**Example:**
```sql
config {
  description: `
    # Fato: Monthly Recurring Revenue

    **Owner**: Revenue Operations Team
    **SLA**: D+1 (updated by 6 AM BRT)
    **Consumers**: Looker Dashboard "Revenue Ops Overview"
  `
}
```

## Key Business Metrics

**Revenue Operations:**
- MRR (Monthly Recurring Revenue): `gold_revenue_ops.fct_monthly_recurring_revenue`
- Customer Health Score: `gold_revenue_ops.fct_customer_health`

**Product Analytics:**
- User Engagement: `gold_product_analytics.fct_user_engagement`
- Feature Adoption: `gold_product_analytics.fct_feature_adoption`

**Data Science:**
- Churn Prediction Features: `gold_data_science.features_customer_churn`

## Troubleshooting

**Dataform compilation errors:**
- Check `dataform.json` for correct project/dataset
- Verify source references use ${ref("schema", "table")}
- Ensure all dependencies are declared

**Airflow DAG failures:**
- Check Cloud Monitoring logs: `daily_pipeline_dag.py:442`
- Common issue: Bronze data not available (GCS sensor timeout)
- Retry logic: 2 retries with 5 min delay

**Data quality test failures:**
- Review Dataform assertions output
- Check Dataplex DQ dashboard
- Run pytest with -v for detailed output

## External Resources

- **Dataform Documentation**: https://cloud.google.com/dataform/docs
- **BigQuery Best Practices**: https://cloud.google.com/bigquery/docs/best-practices-performance-overview
- **Airflow Providers (GCP)**: https://airflow.apache.org/docs/apache-airflow-providers-google/

## Cost Estimate

**Monthly operational cost:** ~$700 USD
- Cloud Storage: $20
- BigQuery (storage + compute): $35
- Datastream: $100
- Fivetran: $120
- Cloud Composer: $200
- Dataplex: $50
- Vertex AI Notebooks: $80
- Other (monitoring, networking): $95

See `RESUMO_EXECUTIVO.md` for detailed breakdown and optimization strategies.

## Implementation Timeline

**POC (Proof of Concept):** 2 weeks
- 1 source (PostgreSQL)
- Pipeline: Bronze → Silver → Gold (1 mart)
- 1 Looker dashboard

**Full Implementation:** 16 weeks
- See `README.md` section "Roadmap de Implementação" for detailed phases

## Support and Contact

**Documentation Files:**
- Technical questions: `README.md` (comprehensive)
- Architecture decisions: `ARCHITECTURE.md`
- Business overview: `RESUMO_EXECUTIVO.md`
- Navigation guide: `COMO_USAR.md`

**Code Examples:**
- Dataform transformations: `dataform/definitions/`
- Airflow orchestration: `examples/airflow/`
- Quality tests: `examples/tests/`
