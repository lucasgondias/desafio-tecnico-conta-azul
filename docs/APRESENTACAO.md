# Apresentação da Solução
## Arquitetura de Dados Moderna para Conta Azul

### Slide 1: Visão Geral da Proposta

**Problema**:
- 3 times de dados (Product Analytics, Data Science, RevOps) com necessidades distintas
- Dados fragmentados em múltiplas fontes
- Falta de governança e qualidade de dados
- Necessidade de self-service para analistas

**Solução Proposta**:
- Arquitetura Data Lake + Data Warehouse na Google Cloud Platform
- Medallion Architecture (Bronze/Silver/Gold)
- Transformações com Dataform (managed dbt)
- Orquestração com Cloud Composer (Airflow)
- Custo estimado: **~$700/mês**

---

### Slide 2: Princípios da Arquitetura

1. **Serverless-First**
   - Zero gerenciamento de infraestrutura
   - Escala automática (de 0 a milhões de queries)
   - Custo variável (paga apenas pelo uso)

2. **Data Mesh Ready**
   - Domínios claros por time (Product Analytics, RevOps, Data Science)
   - Ownership distribuído
   - Self-service para analistas

3. **Qualidade como Código**
   - Testes automatizados (Dataform + Dataplex + pytest)
   - Versionamento Git + CI/CD
   - Observabilidade completa

4. **Custo-efetivo**
   - Particionamento e clustering (economia de 80-90%)
   - Storage lifecycle automático
   - Monitoramento de custos com alertas

---

### Slide 3: Stack Tecnológica (GCP)

| Camada | Ferramenta | Justificativa |
|--------|------------|---------------|
| **Armazenamento** | Cloud Storage + BigQuery | Custo baixo (10x diferença), flexibilidade |
| **Ingestão** | Datastream (CDC) + Fivetran | Real-time + zero manutenção |
| **Transformação** | Dataform | Nativo GCP, gerenciado, custo zero |
| **Orquestração** | Cloud Composer (Airflow) | Padrão da indústria, flexível |
| **BI** | Looker / Looker Studio | Integração nativa, self-service |
| **Data Science** | Vertex AI + BigQuery ML | Notebooks + ML dentro do SQL |
| **Governança** | Dataplex + Data Catalog | Catalogação, DLP, lineage |

**Por que GCP?**
- Integração nativa entre serviços
- BigQuery: melhor custo-benefício para analytics
- Dataform: gerenciado pelo Google (vs dbt Cloud pago)
- Maturidade em data analytics

---

### Slide 4: Arquitetura - Camadas de Dados

```
┌─────────────────────────────────────────┐
│  BRONZE LAYER (Cloud Storage)           │
│  • Dados raw, imutáveis                 │
│  • Formato Parquet particionado         │
│  • Retenção: 2 anos                     │
└─────────────┬───────────────────────────┘
              │ Dataform
              ▼
┌─────────────────────────────────────────┐
│  SILVER LAYER (BigQuery)                │
│  • Dados limpos e padronizados          │
│  • Type casting, deduplicação           │
│  • 1:1 com fontes (staging)             │
└─────────────┬───────────────────────────┘
              │ Dataform
              ▼
┌─────────────────────────────────────────┐
│  GOLD LAYER (BigQuery)                  │
│  • Modelos dimensionais (star schema)  │
│  • Agregações e métricas de negócio    │
│  • Pronto para consumo (BI, ML)         │
└─────────────────────────────────────────┘
```

**Vantagens**:
- Separação clara de responsabilidades
- Reprocessamento fácil (Bronze imutável)
- Performance otimizada (Gold agregado)
- Custo controlado (Storage barato no Bronze)

---

### Slide 5: Domínios de Dados (Data Mesh)

**Product Analytics** (Owner: Product Analytics Team)
- `fct_user_engagement`: DAU, WAU, MAU
- `fct_feature_adoption`: Uso de features
- `dim_users`: Dimensão de usuários

**Revenue Operations** (Owner: RevOps Team)
- `fct_monthly_recurring_revenue`: MRR por segmento
- `fct_customer_health`: Health score consolidado
- `fct_sales_pipeline`: Pipeline de vendas

**Data Science** (Owner: Data Science Team)
- `features_customer_churn`: Features para modelo de churn
- `features_revenue_forecast`: Features para previsão de receita
- `training_datasets_*`: Datasets de treino versionados

**Benefício**: Cada time tem autonomia sobre seus dados, mas compartilham fundações (Silver Layer)

---

### Slide 6: Ingestão de Dados

| Fonte | Ferramenta | Frequência | Estratégia |
|-------|------------|------------|------------|
| PostgreSQL (Transacional) | Datastream | Real-time | CDC (Change Data Capture) |
| Firebase Analytics | BigQuery Export | Streaming | Nativo (gratuito) |
| Google Analytics 4 | BigQuery Transfer | Diário | Nativo (gratuito) |
| Salesforce CRM | Fivetran | Diário | Managed connector |
| APIs Customizadas | Cloud Run | On-demand | Serverless functions |

**Decisão: Híbrido (Datastream + Fivetran)**
- Datastream: CDC para bancos transacionais (low latency)
- Fivetran: SaaS connectors (zero manutenção)
- Cloud Run: Customizações quando necessário

---

### Slide 7: Transformações com Dataform

**Estrutura do Projeto**:
```
dataform/
├── staging/          # Silver layer (1:1 com sources)
│   ├── stg_postgres__customers.sqlx
│   └── stg_firebase__events.sqlx
├── intermediate/     # Lógica reutilizável
│   └── int_customer_lifetime_metrics.sqlx
└── marts/            # Gold layer (consumo final)
    ├── product_analytics/
    ├── revenue_ops/
    └── data_science/
```

**Exemplo: MRR Calculation**
```sql
-- marts/revenue_ops/fct_monthly_recurring_revenue.sqlx

WITH subscriptions AS (
  SELECT * FROM ${ref("silver_core", "subscriptions")}
  WHERE status = 'active'
),

aggregated AS (
  SELECT
    DATE_TRUNC(start_date, MONTH) AS month,
    customer_segment,
    SUM(monthly_value_brl) AS mrr_brl,
    COUNT(DISTINCT customer_id) AS active_customers
  FROM subscriptions
  GROUP BY 1, 2
)

SELECT * FROM aggregated
```

**Vantagens do Dataform**:
- SQL declarativo (fácil para analistas)
- Versionamento Git built-in
- Testes inline (assertions)
- Gerenciado pelo Google (zero ops)

---

### Slide 8: Orquestração - Pipeline Diário

```
3 AM BRT: Trigger Airflow DAG
    ↓
[1] Validar Bronze Ingestion ✓
    ↓
[2] Dataform: Executar Silver Layer ✓
    ↓
[3] Testes de Qualidade (assertions) ✓
    ↓
[4] Dataform: Executar Gold Marts (paralelo) ✓
    ↓
[5] Dataplex Data Quality Checks ✓
    ↓
[6] Refresh Looker Dashboards ✓
    ↓
[7] Enviar Relatório de Observabilidade (Slack)
```

**SLA**: Pipeline completo em 3 horas (máximo 6 AM BRT)

**Monitoramento**:
- Alertas Slack em caso de falha
- Dashboard de observabilidade (freshness, quality, custo)
- PagerDuty para falhas críticas

---

### Slide 9: Qualidade de Dados (Multi-Layer)

**Nível 1: Dataform Assertions** (inline no código)
```sql
assertions: {
  uniqueKey: ["customer_id"],
  nonNull: ["email", "created_date"],
  rowConditions: [
    "email LIKE '%@%'",
    "mrr_brl >= 0"
  ]
}
```

**Nível 2: Dataplex Data Quality** (managed rules)
- Completeness: 100% de customer_id preenchido
- Validity: Email com formato válido
- Consistency: Segmento apenas valores permitidos
- Timeliness: Dados atualizados em < 24h

**Nível 3: Testes Customizados** (pytest)
```python
def test_mrr_always_positive(bq_client):
    assert all(mrr >= 0)

def test_customer_health_score_range(bq_client):
    assert 0 <= health_score <= 100
```

**Resultado**: Qualidade > 99% (medido automaticamente)

---

### Slide 10: Governança e Segurança

**Data Catalog (Dataplex)**:
- Catalogação automática de todas as tabelas
- Search & discovery (analistas encontram dados facilmente)
- Lineage: Rastreamento de origem → destino

**Classificação de Dados (DLP)**:
```sql
-- Policy Tags para dados sensíveis (LGPD)
ALTER TABLE customers SET COLUMN OPTIONS (
  email = policy_tags = ['sensitive_pii']  -- Masking automático
);
```

**Row-Level Security**:
```sql
-- Analistas de RevOps só veem clientes PME
CREATE ROW ACCESS POLICY revops_only_pme
  ON fct_customer_health
  FILTER USING (customer_segment = 'PME');
```

**Auditoria**:
- Cloud Audit Logs: Quem acessou o quê e quando
- Query history completo (BigQuery logs)

---

### Slide 11: Camada de Consumo

**Para Analistas**:
- **Looker**: Dashboards interativos (Revenue Ops, Product Analytics)
- **BigQuery Studio**: SQL editor para análises ad-hoc
- **Looker Studio**: Relatórios self-service (gratuito)

**Para Cientistas de Dados**:
- **Vertex AI Workbench**: Notebooks (Python/R)
- **BigQuery ML**: Treinar modelos direto no SQL (sem Python)
  ```sql
  CREATE MODEL churn_model
  OPTIONS(model_type='LOGISTIC_REG')
  AS SELECT * FROM features_customer_churn;
  ```

**Para Stakeholders**:
- **Dashboards Executivos**: MRR, Churn, Growth (auto-refresh)
- **Scheduled Reports**: Email/Slack diário
- **Data Catalog**: Busca por dataset (self-service)

---

### Slide 12: Custos Estimados

| Serviço | Custo Mensal (USD) |
|---------|-------------------|
| Cloud Storage (1TB) | $20 |
| BigQuery Storage | $25 |
| BigQuery Compute (2TB queries) | $10 |
| Datastream (CDC) | $100 |
| Fivetran (100k MAR) | $120 |
| Cloud Composer (Small) | $200 |
| Dataplex | $50 |
| Vertex AI Notebooks | $80 |
| Outros (Monitoring, Network) | $95 |
| **TOTAL** | **~$700/mês** |

**Otimizações**:
- Particionamento: -80% de scan costs
- BI Engine: Queries repetitivas grátis (cache)
- Lifecycle policies: Storage -75% após 90 dias
- Redshift Serverless: Pausar fora do horário

**Comparação**:
- Snowflake equivalente: ~$1,500-2,000/mês
- Databricks: ~$1,200-1,800/mês
- **GCP BigQuery: ~$700/mês** ✓

---

### Slide 13: Roadmap de Implementação

**Fase 1-2: Foundation (4 semanas)**
- Setup GCP + IAM roles
- Deploy Cloud Composer (Airflow)
- Estrutura inicial Dataform
- PostgreSQL via Datastream (primeira fonte)

**Fase 3-4: Silver + Gold (3 semanas)**
- Modelos staging (Silver)
- Primeiro mart (fct_monthly_recurring_revenue)
- Testes de qualidade

**Fase 5-6: BI + Observabilidade (2 semanas)**
- Deploy Looker
- Dashboards (Revenue Ops)
- Dataplex Data Quality

**Fase 7-8: Expansão (3 semanas)**
- Adicionar Firebase, Salesforce, GA4
- Marts de Product Analytics e Data Science
- Feature Store para ML

**Fase 9-10: Governança + Otimização (4 semanas)**
- Data Catalog completo
- DLP e Row-Level Security
- Performance tuning
- Documentação e handoff

**TOTAL: 16 semanas (4 meses)**

---

### Slide 14: Diferenciais da Solução

✅ **Serverless-First**: Zero ops, escala automática
✅ **Custo-efetivo**: $700/mês (vs $1,500+ concorrentes)
✅ **Data Mesh Ready**: Ownership por domínio
✅ **Qualidade Built-in**: Testes em 3 níveis
✅ **Self-Service**: Analistas autônomos
✅ **Observabilidade**: Monitoramento 24/7
✅ **LGPD Compliant**: DLP, masking, audit logs
✅ **Open Standards**: SQL, Git, Airflow (sem vendor lock-in)

---

### Slide 15: Próximos Passos

**Curto Prazo (Semana 1-2)**:
1. Validar arquitetura com stakeholders técnicos
2. Priorizar fontes de dados (quick wins)
3. Definir SLAs por domínio

**POC (Proof of Concept) - 2 semanas**:
- Fonte: PostgreSQL produção
- Pipeline: Bronze → Silver → Gold (1 mart: MRR)
- Consumo: Dashboard Looker básico
- **Meta**: Demonstrar valor end-to-end

**Implementação Full (16 semanas)**:
- Seguir roadmap descrito
- Iterações quinzenais (Agile)
- Review contínuo com times consumidores

---

### Slide 16: Perguntas Frequentes

**Q: Por que Dataform e não dbt Core?**
A: Dataform é gerenciado pelo Google (zero ops), integração nativa com BigQuery, custo zero. Trade-off: ecossistema menor, mas conceitos compatíveis com dbt (migração fácil se necessário).

**Q: E se precisarmos migrar de cloud?**
A: Arquitetura baseada em padrões abertos (SQL, Airflow, Parquet). Dataform → dbt migration é direta (mesma sintaxe).

**Q: Como garantir que dados sensíveis não vazam?**
A: DLP (Data Loss Prevention) auto-detecta PII, policy tags aplicam masking, Row-Level Security limita acesso, audit logs rastreiam tudo.

**Q: Quanto tempo para primeiro valor?**
A: POC em 2 semanas. Primeiro dashboard de produção em 8 semanas.

---

### Slide 17: Contato e Materiais

**Repositório**:
- `README.md`: Documentação completa
- `ARCHITECTURE.md`: Diagramas detalhados (Mermaid)
- `dataform/`: Exemplos de código
- `examples/`: Airflow DAGs, testes pytest

**Próxima Ação**:
- Agendar sessão técnica (deep dive em componentes)
- Definir escopo do POC
- Estimar esforço de time (2-3 Analytics Engineers)

---

**Obrigado!**

Lucas - Analytics Engineer Candidate
Proposta para: Conta Azul
Data: Outubro 2025
