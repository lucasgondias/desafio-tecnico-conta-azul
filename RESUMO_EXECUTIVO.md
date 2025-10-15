# Resumo Executivo
## Arquitetura de Dados para Conta Azul - Analytics Engineer

---

## Contexto do Desafio

A Conta Azul possui três frentes de dados complementares:
- **Product Analytics**: Análises de uso do produto
- **Data Science**: Modelos preditivos e algoritmos
- **Revenue Operations (RevOps)**: Performance comercial e sucesso do cliente

**Necessidade**: Arquitetura de dados moderna que transforme informações brutas em dados organizados, confiáveis, reutilizáveis e acessíveis.

---

## Solução Proposta: Visão Geral

### Arquitetura
**Medallion Architecture** na Google Cloud Platform (GCP):
- **Bronze Layer**: Dados raw (Cloud Storage)
- **Silver Layer**: Dados limpos (BigQuery)
- **Gold Layer**: Modelos de negócio (BigQuery)

### Princípios
1. Serverless-first (zero gerenciamento de infra)
2. Data Mesh (ownership por domínio)
3. Qualidade como código (testes automatizados)
4. Custo-efetivo (~$700/mês)

---

## Stack Tecnológica

| Componente | Tecnologia | Justificativa |
|------------|------------|---------------|
| **Data Lake** | Cloud Storage | Custo baixo, durável |
| **Data Warehouse** | BigQuery | Serverless, escala automática |
| **Ingestão** | Datastream + Fivetran | CDC real-time + conectores managed |
| **Transformação** | Dataform | Gerenciado pelo Google, custo zero |
| **Orquestração** | Cloud Composer (Airflow) | Padrão da indústria |
| **BI** | Looker / Looker Studio | Integração nativa, self-service |
| **Data Science** | Vertex AI + BigQuery ML | Notebooks + ML em SQL |
| **Governança** | Dataplex + Data Catalog | Catalogação, lineage, DLP |

---

## Estratégia de Ingestão

### Fontes de Dados

**Bancos Transacionais** (PostgreSQL, MySQL)
- **Ferramenta**: Datastream (CDC)
- **Frequência**: Real-time (< 5 min latência)
- **Destino**: Cloud Storage (Bronze) → BigQuery

**Eventos de Produto** (Firebase, GA4)
- **Ferramenta**: BigQuery Export nativo
- **Frequência**: Streaming / Diário
- **Custo**: Gratuito (nativo)

**SaaS / CRM** (Salesforce, HubSpot, Stripe)
- **Ferramenta**: Fivetran
- **Frequência**: Diário
- **Vantagem**: Zero manutenção, 400+ conectores

**APIs Customizadas**
- **Ferramenta**: Cloud Run (serverless)
- **Frequência**: On-demand
- **Flexibilidade**: Total controle

---

## Organização dos Dados (Medallion)

### Bronze Layer (Raw)
**Localização**: `gs://conta-azul-datalake/bronze/`

**Características**:
- Dados brutos, sem transformação
- Formato Parquet (compressão Snappy)
- Particionado por data de ingestão
- Imutável (append-only)
- Retenção: 2 anos

**Exemplo**:
```
bronze/
├── postgres_production/
│   ├── customers/year=2025/month=10/day=10/
│   └── invoices/
├── firebase_analytics/events/
└── salesforce_crm/leads/
```

### Silver Layer (Cleaned & Conformed)
**Localização**: BigQuery datasets `silver_*`

**Características**:
- Dados limpos e padronizados
- Type casting, deduplicação
- Normalização (snake_case)
- Particionado e clusterizado

**Exemplo**:
```sql
-- silver_core.customers
SELECT
  id AS customer_id,
  LOWER(TRIM(email)) AS email,
  CASE WHEN segment IN ('PME', 'MEI', 'Autônomo')
       THEN segment ELSE 'Outros' END AS customer_segment,
  ...
FROM bronze.customers
WHERE email IS NOT NULL
QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1
```

### Gold Layer (Business Ready)
**Localização**: BigQuery datasets `gold_*` (por domínio)

**Características**:
- Modelos dimensionais (star schema)
- Agregações pré-computadas
- Métricas de negócio
- Otimizado para BI e ML

**Domínios**:
- `gold_product_analytics/`: fct_user_engagement, dim_users
- `gold_revenue_ops/`: fct_monthly_recurring_revenue, fct_customer_health
- `gold_data_science/`: features_customer_churn, training_datasets

---

## Transformação e Orquestração

### Dataform (Transformações)

**Estrutura do Projeto**:
```
dataform/
├── staging/          # Silver (1:1 com sources)
├── intermediate/     # Lógica reutilizável
└── marts/            # Gold (consumo final)
    ├── product_analytics/
    ├── revenue_ops/
    └── data_science/
```

**Exemplo de Mart (MRR)**:
```sql
-- fct_monthly_recurring_revenue.sqlx

WITH subscriptions AS (
  SELECT * FROM ${ref("silver_core", "subscriptions")}
  WHERE status = 'active'
)

SELECT
  DATE_TRUNC(start_date, MONTH) AS month,
  customer_segment,
  SUM(monthly_value_brl) AS mrr_brl,
  COUNT(DISTINCT customer_id) AS active_customers
FROM subscriptions
JOIN ${ref("silver_core", "customers")} USING (customer_id)
GROUP BY 1, 2
```

**Por que Dataform?**
- Gerenciado pelo Google (zero ops)
- Git integrado nativamente
- Sintaxe similar ao dbt (migração fácil)
- Custo zero (incluído no BigQuery)

### Cloud Composer (Orquestração)

**Pipeline Diário** (3 AM BRT):
```
1. Validar Bronze Ingestion (sensores GCS)
2. Executar Dataform Silver Layer
3. Testes de qualidade (assertions)
4. Executar Dataform Gold Marts (paralelo por domínio)
5. Dataplex Data Quality checks
6. Refresh Looker dashboards
7. Enviar relatório de observabilidade (Slack)
```

**SLA**: 3 horas (completo até 6 AM BRT)

---

## Qualidade e Governança

### Testes Automatizados (3 níveis)

**Nível 1: Dataform Assertions**
```sql
assertions: {
  uniqueKey: ["customer_id"],
  nonNull: ["email", "created_date"],
  rowConditions: ["email LIKE '%@%'"]
}
```

**Nível 2: Dataplex Data Quality**
- Completeness: 100% de campos obrigatórios
- Validity: Formatos e ranges corretos
- Consistency: Valores permitidos apenas
- Timeliness: Freshness < 24h

**Nível 3: Testes Customizados (pytest)**
```python
def test_mrr_always_positive(bq_client):
    assert all(mrr_brl >= 0)

def test_data_freshness_sla(bq_client):
    assert hours_since_update < 27
```

### Versionamento e CI/CD

**Git Workflow**:
```
main (produção)
├── staging (homologação)
└── feature/* (desenvolvimento)
```

**Pull Request** obrigatório com:
- Code review
- CI/CD automático (Cloud Build)
- Testes devem passar
- Deploy automático para staging

### Monitoramento

**Cloud Monitoring Dashboards**:
- Data freshness por tabela
- Data quality pass rate
- BigQuery costs (alertas > $500/dia)
- Pipeline success rate

**Alertas**:
- SLA breach (> 27h desatualizado) → PagerDuty
- Data quality < 95% → Slack #data-alerts
- Custo anômalo → Finops team

### Governança

**Data Catalog (Dataplex)**:
- Catalogação automática de todas as tabelas
- Metadados técnicos + business glossary
- Lineage: rastreamento origem → destino
- Search & discovery (self-service)

**Segurança (LGPD)**:
```sql
-- Policy Tags (masking automático de PII)
ALTER TABLE customers SET COLUMN OPTIONS (
  email = policy_tags = ['sensitive_pii']
);

-- Row-Level Security
CREATE ROW ACCESS POLICY revops_only_pme
  ON fct_customer_health
  FILTER USING (customer_segment = 'PME');
```

**Auditoria**:
- Cloud Audit Logs (quem acessou o quê)
- BigQuery query history completo
- Retenção: 1 ano

---

## Camada de Consumo

### Para Analistas

**Looker** (BI principal):
- Dashboards interativos (self-service)
- LookML semantic layer
- Scheduled reports (email/Slack)

**BigQuery Studio**:
- SQL editor para análises ad-hoc
- Saved queries compartilháveis
- Autocomplete e sugestões

**Looker Studio** (gratuito):
- Relatórios visuais simples
- Compartilhamento público

### Para Cientistas de Dados

**Vertex AI Workbench**:
- Notebooks Jupyter (Python/R)
- Acesso direto ao BigQuery
- GPUs para treinamento de modelos

**BigQuery ML**:
- Treinar modelos direto em SQL
```sql
CREATE MODEL churn_model
OPTIONS(model_type='LOGISTIC_REG')
AS SELECT * FROM features_customer_churn;
```

**Feature Store**:
- Features versionadas em `gold_data_science/`
- Point-in-time correct joins
- Reutilização entre modelos

### Para Stakeholders

**Dashboards Executivos**:
- Revenue Ops: MRR, Churn, Customer Health
- Product Analytics: DAU, MAU, Feature Adoption
- Auto-refresh diário

**Scheduled Reports**:
- Email/Slack com métricas principais
- Alertas de anomalias

---

## Custos Estimados

### Breakdown Mensal (USD)

| Serviço | Custo |
|---------|-------|
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

### Otimizações

**Particionamento e Clustering**:
- Reduz scan em 80-90%
- Exemplo: Query de 1TB → 100GB scanned ($5 → $0.50)

**BigQuery BI Engine** (cache):
- $40/mês para 10GB cache
- Queries repetitivas grátis

**Storage Lifecycle**:
```
Bronze > 90 dias → Nearline (-75% custo)
Bronze > 2 anos → Delete
```

**Resultado**: Economia de ~40% vs. configuração naive

### Comparação com Concorrentes

| Plataforma | Custo Mensal |
|------------|--------------|
| **GCP (proposta)** | **$700** |
| Snowflake | $1,500-2,000 |
| Databricks | $1,200-1,800 |
| AWS (Redshift + Glue) | $1,000-1,500 |

**Vencedor**: GCP BigQuery (melhor custo-benefício)

---

## Roadmap de Implementação

### Fase 1-2: Foundation (4 semanas)
- Setup GCP, IAM, buckets
- Deploy Cloud Composer
- Estrutura Dataform
- PostgreSQL via Datastream (primeira fonte)

### Fase 3-4: Silver + Gold (3 semanas)
- Modelos staging (Silver)
- Primeiro mart (fct_monthly_recurring_revenue)
- Testes de qualidade

### Fase 5-6: BI + Observabilidade (2 semanas)
- Deploy Looker
- Dashboard Revenue Ops
- Dataplex Data Quality

### Fase 7-8: Expansão (3 semanas)
- Adicionar Firebase, Salesforce, GA4
- Marts Product Analytics e Data Science
- Feature Store

### Fase 9-10: Governança + Otimização (4 semanas)
- Data Catalog completo
- DLP e Row-Level Security
- Performance tuning
- Documentação e handoff

**TOTAL: 16 semanas (4 meses)**

### POC (Proof of Concept) - 2 semanas

**Escopo mínimo**:
- 1 fonte: PostgreSQL
- Pipeline: Bronze → Silver → Gold (1 mart: MRR)
- 1 dashboard Looker

**Meta**: Demonstrar valor end-to-end rapidamente

---

## Diferenciais da Solução

✅ **Serverless-First**: Zero gerenciamento de infraestrutura
✅ **Custo 50% menor**: $700/mês vs $1,500+ concorrentes
✅ **Data Mesh Ready**: Ownership distribuído por domínio
✅ **Qualidade Built-in**: 3 níveis de testes automatizados
✅ **Self-Service**: Analistas autônomos (Looker + BigQuery Studio)
✅ **Observabilidade 24/7**: Monitoramento contínuo, alertas proativos
✅ **LGPD Compliant**: DLP, masking, auditoria completa
✅ **Open Standards**: SQL, Git, Airflow (sem vendor lock-in)
✅ **Time-to-Value**: POC em 2 semanas, produção em 8 semanas

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| **Dataform é menos maduro que dbt** | Médio | Manter compatibilidade conceitual com dbt, migração fácil se necessário |
| **Custo pode crescer com escala** | Alto | Monitoramento contínuo, alertas de budget, otimizações proativas |
| **Falta de expertise em GCP** | Médio | Treinamento do time, documentação detalhada, suporte Google |
| **Dependência de vendor (Google)** | Baixo | Arquitetura baseada em padrões abertos (SQL, Parquet, Airflow) |
| **SLA breach durante implementação** | Médio | Implementação faseada, validações em staging antes de produção |

---

## Métricas de Sucesso

**Técnicas**:
- Data quality > 99%
- SLA compliance > 95% (dados atualizados em < 27h)
- Pipeline success rate > 98%
- Query performance p95 < 10s

**Negócio**:
- Time-to-insight < 24h (requisição → dashboard)
- Adoção: 80% dos analistas usando self-service em 6 meses
- Custo por GB processado < $0.50
- Redução de 50% em tempo gasto com "data wrangling"

**Organizacional**:
- 3 domínios (Product Analytics, RevOps, Data Science) com ownership claro
- 100% dos datasets catalogados e documentados
- Zero incidentes de segurança/compliance

---

## Próximos Passos

### Imediato (Semana 1)
1. Validar arquitetura com stakeholders (CTO, Head of Data)
2. Priorizar fontes de dados (quick wins)
3. Definir SLAs por domínio
4. Aprovar orçamento (~$700/mês + ~$30k implementação)

### Curto Prazo (Semana 2-3)
5. Contratar/alocar time:
   - 1 Senior Analytics Engineer (lead)
   - 2 Analytics Engineers (desenvolvimento)
   - Suporte: 1 Data Engineer part-time
6. Setup ambiente GCP (projeto, billing, IAM)
7. Iniciar POC (2 semanas)

### Médio Prazo (Mês 2-4)
8. Implementação faseada (roadmap de 16 semanas)
9. Iterações quinzenais com feedback de usuários
10. Documentação contínua (Confluence + dbt docs)

### Longo Prazo (6 meses+)
11. Expansão para novos domínios (Finance, Operations)
12. Advanced Analytics (ML em produção)
13. Real-time streaming (Pub/Sub → Dataflow)

---

## Conclusão

Esta proposta apresenta uma **arquitetura moderna, escalável e custo-efetiva** para dados na Conta Azul, baseada em:

- **Best practices da indústria** (Medallion, Data Mesh, ELT)
- **Stack nativa GCP** (serverless, integrada, gerenciada)
- **Qualidade e governança** desde o dia 1
- **Time-to-value rápido** (POC em 2 semanas)

**Investimento**: ~$700/mês operacional + ~16 semanas de implementação

**Retorno esperado**:
- Decisões de negócio baseadas em dados confiáveis
- Autonomia para analistas e cientistas de dados
- Redução de 50% em tempo de "data wrangling"
- Base sólida para crescimento (de PME para Enterprise)

---

## Contato

**Candidato**: Lucas (você)
**Posição**: Analytics Engineer (Especialista)
**Empresa**: Conta Azul
**Data da Proposta**: Outubro 2025

**Materiais Entregues**:
- `README.md`: Documentação completa (40+ páginas)
- `ARCHITECTURE.md`: Diagramas detalhados (Mermaid)
- `RESUMO_EXECUTIVO.md`: Este documento
- `dataform/`: Exemplos de código (Dataform models)
- `examples/airflow/`: DAG de orquestração
- `examples/tests/`: Testes de qualidade (pytest)
- `docs/APRESENTACAO.md`: Slides para apresentação

---

**Pronto para discussão e deep dive técnico!**
