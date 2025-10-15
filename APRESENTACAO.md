# Arquitetura de Dados - Conta Azul
**Analytics Engineer | Lucas Gonçalves Dias**

---

## 1. Contexto e Desafio (30s)

**Necessidade:**
- 3 times de dados (Product Analytics, RevOps, Data Science)
- Fontes heterogêneas (PostgreSQL, Firebase, Salesforce, GA4)
- Dados confiáveis, escaláveis, com custo controlado

**Solução proposta:**
- **Medallion Architecture** (Bronze/Silver/Gold)
- **Data Mesh** (ownership por domínio)
- **Stack GCP** (BigQuery, Dataform, Cloud Composer)

---

## 2. Arquitetura High-Level (1 min)

```
PostgreSQL ──→ Datastream (CDC) ──→ Bronze (Cloud Storage)
Firebase ────→ Export nativo ─────→   │
Salesforce ──→ Fivetran ──────────→   │
                                      ↓
                              Silver (BigQuery)
                              - Limpeza
                              - Deduplicação
                              - Type casting
                                      ↓
                              Gold (BigQuery)
                              - gold_product_analytics/
                              - gold_revenue_ops/
                              - gold_data_science/
                                      ↓
                        Looker | Vertex AI | BigQuery ML
```

**Princípios:**
- ELT (não ETL) - transformar depois de carregar
- Incremental-first - processar apenas novos dados
- Idempotente - re-executável sem efeitos colaterais

---

## 3. Código Real: Transformação SQL (1.5 min)

### Silver Layer - Limpeza
```sql
-- dataform/definitions/staging/core/stg_postgres__customers.sqlx

config {
  type: "incremental",
  uniqueKey: ["customer_id"],
  bigquery: {
    partitionBy: "created_date",
    clusterBy: ["customer_segment", "country"]
  }
}

WITH source AS (
  SELECT * FROM ${ref("bronze_postgres", "customers")}
  ${when(incremental(),
    `WHERE updated_at > (SELECT MAX(updated_at) FROM ${self()})`
  )}
),

cleaned AS (
  SELECT
    id AS customer_id,
    LOWER(TRIM(email)) AS email,
    CASE WHEN segment IN ('PME', 'MEI', 'Autônomo')
         THEN segment ELSE 'Outros' END AS customer_segment,
    CAST(created_at AS DATE) AS created_date,
    CURRENT_TIMESTAMP() AS _loaded_at
  FROM source
  WHERE email IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1
)

SELECT * FROM cleaned
```

**Key points:**
- Incremental (apenas delta)
- Deduplicação com QUALIFY
- Particionamento + Clustering (reduz custo 80-90%)

---

## 4. Orquestração: Airflow DAG (1.5 min)

```python
# examples/airflow/daily_pipeline_dag.py (snippet)

with DAG('daily_data_pipeline', schedule_interval='0 3 * * *') as dag:

    # 1. Validar Bronze
    validate_bronze = GCSObjectsWithPrefixExistenceSensor(...)

    # 2. Dataform Silver
    compile_silver = DataformCreateCompilationResultOperator(...)
    run_silver = DataformCreateWorkflowInvocationOperator(...)

    # 3. Testes de qualidade
    test_silver = DataformCreateWorkflowInvocationOperator(
        workflow_invocation={'invocation_config': {'actions_only': False}}
    )

    # 4. Dataform Gold (paralelo por domínio)
    for domain in ['product_analytics', 'revenue_ops', 'data_science']:
        run_mart = DataformCreateWorkflowInvocationOperator(
            workflow_invocation={'invocation_config': {'included_tags': [domain]}}
        )

    # 5. Validar SLA + Refresh Looker
    validate_bronze >> compile_silver >> run_silver >> test_silver >> run_mart
```

**SLA:** Pipeline completo em < 3h (3 AM → 6 AM BRT)

---

## 5. Qualidade de Dados (1 min)

### 3 Níveis de Testes

**Nível 1: Dataform Assertions (inline)**
```sql
config {
  assertions: {
    uniqueKey: ["customer_id"],
    nonNull: ["email", "created_date"],
    rowConditions: ["email LIKE '%@%'"]
  }
}
```

**Nível 2: Dataplex Data Quality**
- Completeness: 100% de campos obrigatórios
- Validity: Regex de email, ranges de data
- Freshness: < 27h (SLA)

**Nível 3: Custom Tests (pytest)**
```python
def test_mrr_always_positive(bq_client):
    assert all(mrr_brl >= 0)

def test_data_freshness_sla(bq_client):
    assert hours_since_update < 27
```

**Estratégia:** Fail-fast → Pipeline PARA se qualidade falhar no Silver

---

## 6. Decisões Técnicas e Trade-offs (1 min)

### Por que GCP?
✅ BigQuery = melhor DW serverless (custo/performance)
✅ Integração nativa (Dataform, Datastream, Composer)
❌ Trade-off: Vendor lock-in (mitigado por SQL padrão, Parquet, Airflow)

### Por que Dataform vs dbt?
✅ Gerenciado (zero ops)
✅ Custo zero (vs dbt Cloud $100+/dev)
✅ Sintaxe similar (migração viável)
❌ Trade-off: Ecossistema menor

### Por que Cloud Composer ($200/mês) vs Cloud Workflows ($20/mês)?
✅ Airflow = padrão da indústria
✅ Observabilidade robusta
✅ Python completo (flexibilidade)
❌ Trade-off: 10x mais caro, mas vale pela **visibilidade** em produção

---

## 7. Custos e Implementação (1 min)

### Custos Mensais: ~$700
| Serviço | Custo |
|---------|-------|
| BigQuery (storage + compute) | $35 |
| Datastream CDC | $100 |
| Fivetran | $120 |
| Cloud Composer | $200 |
| Dataplex + Outros | $245 |

**50% mais barato** que Snowflake ($1.5k+) ou Databricks ($1.2k+)

### Roadmap: 16 semanas
- **Semana 8:** Primeiro dashboard (MRR) em produção
- **Semana 12:** 3 domínios completos (Product, RevOps, DS)
- **Semana 16:** Governança + handoff

**POC:** 2 semanas (PostgreSQL → Bronze → Silver → Gold → Looker)

---

## 8. Resultados Esperados (30s)

### Técnicos
- Data quality > 99%
- SLA compliance > 95%
- Query p95 < 10s

### Negócio
- **50% redução** em tempo de "data wrangling" (analistas)
- **Autonomia** para 3 times (self-service)
- **ROI:** Payback em ~6 meses

### Arquitetura
- **Escalável:** 0 → 1TB/mês sem reengenharia
- **Manutenível:** Git + CI/CD + Testes
- **Simples:** Serverless (zero infra)

---

## Repositório

**GitHub:** https://github.com/lucasgondias/desafio-tecnico-conta-azul

**Inclui:**
- 10+ diagramas Mermaid (renderizados)
- 1.100+ linhas de código (SQL, Python)
- Documentação completa (80 páginas)
- Exemplos executáveis

---

## Obrigado! Perguntas?

**Lucas Gonçalves Dias**
github.com/lucasgondias
