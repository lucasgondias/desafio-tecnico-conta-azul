# Diagrama de Arquitetura Detalhado

## Visão Geral - High Level

```mermaid
graph TB
    subgraph "FONTES DE DADOS"
        A1[PostgreSQL<br/>Transacional]
        A2[Firebase<br/>Events]
        A3[Salesforce<br/>CRM]
        A4[Google Analytics 4]
        A5[APIs Externas]
    end

    subgraph "INGESTÃO"
        B1[Datastream<br/>CDC]
        B2[BigQuery<br/>Transfer Service]
        B3[Fivetran]
        B4[Cloud Run<br/>Custom]
    end

    subgraph "ARMAZENAMENTO - Data Lake"
        C1[Cloud Storage<br/>Bronze Layer]
        C2[Cloud Storage<br/>Silver Layer]
        C3[Cloud Storage<br/>Gold Layer]
    end

    subgraph "PROCESSAMENTO"
        D1[Dataform<br/>Transformações]
        D2[BigQuery<br/>Data Warehouse]
        D3[Cloud Composer<br/>Orquestração]
    end

    subgraph "QUALIDADE & GOVERNANÇA"
        E1[Dataplex<br/>Data Quality]
        E2[Data Catalog]
        E3[Cloud Monitoring]
    end

    subgraph "CONSUMO"
        F1[Looker<br/>BI Dashboards]
        F2[Vertex AI<br/>Data Science]
        F3[BigQuery ML<br/>Machine Learning]
    end

    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B2
    A5 --> B4

    B1 --> C1
    B2 --> C1
    B3 --> C1
    B4 --> C1

    C1 --> D1
    D1 --> C2
    C2 --> D1
    D1 --> C3

    C1 --> D2
    C2 --> D2
    C3 --> D2

    D3 -.orquestra.-> D1
    D3 -.monitora.-> E1

    D2 --> E1
    D2 --> E2
    D1 --> E3

    D2 --> F1
    D2 --> F2
    D2 --> F3
```

## Fluxo de Dados Detalhado

```mermaid
sequenceDiagram
    participant Source as PostgreSQL Prod
    participant DS as Datastream (CDC)
    participant Bronze as Cloud Storage<br/>Bronze Layer
    participant BQ as BigQuery
    participant DF as Dataform
    participant Silver as BigQuery<br/>Silver Layer
    participant Gold as BigQuery<br/>Gold Layer
    participant Looker as Looker BI
    participant Alert as Cloud Monitoring

    Note over Source,Alert: Pipeline Diário (3 AM BRT)

    Source->>DS: Change Data Capture (contínuo)
    DS->>Bronze: Write Avro files<br/>(particionado por data)

    Note over Bronze: Bronze Layer<br/>Dados Raw, Imutáveis

    Bronze->>BQ: BigLake External Table
    BQ->>DF: Trigger Dataform (Airflow)

    DF->>DF: Compile models (staging)
    DF->>Silver: Executar transformações<br/>(limpeza, dedup)

    Note over Silver: Silver Layer<br/>Dados Limpos, Conformed

    Silver->>DF: Models intermediários
    DF->>DF: Compile models (marts)
    DF->>Gold: Executar agregações<br/>(modelos dimensionais)

    Note over Gold: Gold Layer<br/>Business Ready

    Gold->>Alert: Validar SLA (freshness)
    Alert-->>Alert: Check: updated < 27h?

    alt SLA OK
        Alert->>Looker: Trigger refresh dashboards
        Looker->>Gold: Query marts
        Gold-->>Looker: Retorna dados
    else SLA Breach
        Alert->>Alert: Send Slack alert<br/>#data-alerts
    end
```

## Arquitetura de Camadas (Medallion)

```mermaid
graph LR
    subgraph "BRONZE - Raw Data"
        B1[postgres_production/<br/>customers/]
        B2[firebase_analytics/<br/>events/]
        B3[salesforce_crm/<br/>leads/]
    end

    subgraph "SILVER - Cleaned & Conformed"
        S1[silver_core.<br/>customers]
        S2[silver_product_analytics.<br/>events]
        S3[silver_crm.<br/>leads]
    end

    subgraph "GOLD - Business Ready"
        G1[gold_revenue_ops.<br/>fct_mrr]
        G2[gold_product_analytics.<br/>fct_user_engagement]
        G3[gold_data_science.<br/>features_churn]
    end

    B1 -->|Dataform<br/>stg_postgres__customers| S1
    B2 -->|Dataform<br/>stg_firebase__events| S2
    B3 -->|Dataform<br/>stg_salesforce__leads| S3

    S1 -->|Dataform<br/>marts| G1
    S2 -->|Dataform<br/>marts| G2
    S1 -->|Dataform<br/>marts| G3
    S2 -->|Dataform<br/>marts| G3

    style B1 fill:#cd7f32
    style B2 fill:#cd7f32
    style B3 fill:#cd7f32
    style S1 fill:#c0c0c0
    style S2 fill:#c0c0c0
    style S3 fill:#c0c0c0
    style G1 fill:#ffd700
    style G2 fill:#ffd700
    style G3 fill:#ffd700
```

## Data Mesh - Domínios de Negócio

```mermaid
graph TB
    subgraph "SILVER LAYER - Shared Foundations"
        SF1[silver_core<br/>customers, invoices, payments]
        SF2[silver_product_analytics<br/>events, sessions]
        SF3[silver_crm<br/>leads, opportunities]
    end

    subgraph "DOMAIN: Product Analytics"
        PA1[gold_product_analytics]
        PA2[Owner: Product Analytics Team]
        PA3[Consumers: Product Managers, UX]
        PA4[fct_user_engagement<br/>fct_feature_adoption<br/>dim_users]
    end

    subgraph "DOMAIN: Revenue Operations"
        RO1[gold_revenue_ops]
        RO2[Owner: RevOps Team]
        RO3[Consumers: Sales, Finance, CS]
        RO4[fct_monthly_recurring_revenue<br/>fct_customer_health<br/>fct_sales_pipeline]
    end

    subgraph "DOMAIN: Data Science"
        DS1[gold_data_science]
        DS2[Owner: Data Science Team]
        DS3[Consumers: DS Team, ML Models]
        DS4[features_customer_churn<br/>features_revenue_forecast<br/>training_datasets]
    end

    SF1 --> PA1
    SF2 --> PA1
    SF1 --> RO1
    SF3 --> RO1
    SF1 --> DS1
    SF2 --> DS1
    SF3 --> DS1

    PA1 --> PA4
    RO1 --> RO4
    DS1 --> DS4

    style PA1 fill:#4285f4
    style RO1 fill:#ea4335
    style DS1 fill:#34a853
```

## Pipeline de Qualidade de Dados

```mermaid
graph LR
    A[Ingestão Bronze] --> B{Bronze<br/>Completeness<br/>Check}

    B -->|OK| C[Dataform<br/>Silver Layer]
    B -->|Falha| Z1[Slack Alert<br/>#data-alerts]

    C --> D{Dataform<br/>Assertions}

    D -->|Pass| E[Silver Layer<br/>Persistido]
    D -->|Fail| Z2[Block Pipeline<br/>Slack Alert]

    E --> F{Dataplex<br/>Data Quality<br/>Rules}

    F -->|Pass| G[Dataform<br/>Gold Layer]
    F -->|Fail| Z3[Warning Alert<br/>Continue com flag]

    G --> H{Custom Tests<br/>pytest}

    H -->|Pass| I[Gold Layer<br/>Disponível]
    H -->|Fail| Z4[Critical Alert<br/>Rollback]

    I --> J{SLA Check<br/>Freshness < 27h}

    J -->|OK| K[Refresh<br/>Looker Dashboards]
    J -->|Breach| Z5[SLA Alert<br/>PagerDuty]

    style B fill:#ffeb3b
    style D fill:#ff9800
    style F fill:#ff5722
    style H fill:#f44336
    style J fill:#9c27b0
```

## Orquestração - Airflow DAG

```mermaid
graph TB
    START([Trigger Daily<br/>3 AM BRT])

    START --> V1[Validate Bronze<br/>Ingestion]

    V1 --> D1[Dataform Compile<br/>Silver Models]
    D1 --> D2[Dataform Run<br/>Staging Layer]
    D2 --> T1[Dataform Test<br/>Silver Assertions]

    T1 --> D3[Dataform Compile<br/>Gold Models]

    D3 --> P1[Run Product<br/>Analytics Marts]
    D3 --> P2[Run RevOps<br/>Marts]
    D3 --> P3[Run Data Science<br/>Feature Store]

    P1 --> T2[Test Gold<br/>Metrics]
    P2 --> T2
    P3 --> T2

    T2 --> Q1[Dataplex<br/>Data Quality]

    Q1 --> R1[Refresh Looker<br/>Dashboards]
    Q1 --> R2[Update Data<br/>Catalog Metadata]

    R1 --> REP[Generate Daily<br/>Observability Report]
    R2 --> REP

    REP --> END([Pipeline<br/>Completo])

    style START fill:#4caf50
    style END fill:#4caf50
    style T1 fill:#ff9800
    style T2 fill:#ff9800
    style Q1 fill:#ff5722
```

## Segurança e Governança

```mermaid
graph TB
    subgraph "IAM & Access Control"
        I1[Service Accounts<br/>dataform@, airflow@]
        I2[Groups<br/>revops-analysts@<br/>data-science@]
        I3[Row-Level Security<br/>BigQuery Policies]
    end

    subgraph "Data Classification"
        C1[Dataplex Taxonomy]
        C2[Policy Tags<br/>PII, Sensitive]
        C3[DLP Scanning<br/>Auto-detection]
    end

    subgraph "Audit & Compliance"
        A1[Cloud Audit Logs<br/>Quem acessou o quê?]
        A2[BigQuery Query Logs<br/>Histórico de queries]
        A3[Data Lineage<br/>Origem → Destino]
    end

    subgraph "Data Catalog"
        D1[Metadados Técnicos<br/>Schema, Types]
        D2[Metadados de Negócio<br/>Descrições, Owners]
        D3[Search & Discovery<br/>Self-Service]
    end

    I2 --> I3
    C1 --> C2
    C2 --> I3
    C3 --> C2

    I1 --> A1
    I2 --> A1
    I3 --> A2
    A2 --> A3

    D1 --> D3
    D2 --> D3
    A3 --> D3
```

## Custo e Performance - Otimização

```mermaid
graph LR
    subgraph "Estratégias de Otimização"
        O1[Particionamento<br/>por Data]
        O2[Clustering<br/>por Filtros Comuns]
        O3[BigQuery<br/>BI Engine Cache]
        O4[Materialized Views<br/>Queries Pesadas]
    end

    subgraph "Monitoramento de Custo"
        M1[Query Cost<br/>Tracking]
        M2[Storage<br/>Lifecycle Policies]
        M3[Alerts<br/>Budget Thresholds]
    end

    subgraph "Impacto"
        R1[Redução de<br/>Scans: 80-90%]
        R2[Queries Repetitivas:<br/>Free]
        R3[Storage Cost:<br/>-75% após 90d]
    end

    O1 --> R1
    O2 --> R1
    O3 --> R2
    O4 --> R2

    M1 --> M3
    M2 --> R3
    M3 --> R3

    style R1 fill:#4caf50
    style R2 fill:#4caf50
    style R3 fill:#4caf50
```

## Disaster Recovery & Backup

```mermaid
graph TB
    subgraph "Camada de Proteção"
        P1[Cloud Storage<br/>Versioning Enabled]
        P2[BigQuery<br/>Time Travel 7 dias]
        P3[Snapshots<br/>Tabelas Críticas]
    end

    subgraph "Recovery Procedures"
        R1[Restore from<br/>Cloud Storage Version]
        R2[Query Historical<br/>State BigQuery]
        R3[Restore from<br/>Snapshot]
    end

    subgraph "Backup Policies"
        B1[Bronze: 2 anos<br/>Nearline após 90d]
        B2[Silver: 5 anos<br/>Coldline após 1 ano]
        B3[Gold: Indefinido<br/>Snapshots mensais]
    end

    P1 --> R1
    P2 --> R2
    P3 --> R3

    R1 --> B1
    R2 --> B2
    R3 --> B3
```

## Roadmap Visual

```mermaid
gantt
    title Roadmap de Implementação (16 semanas)
    dateFormat  YYYY-MM-DD
    section Fase 0-1
    Setup GCP & Infra           :done, f0, 2025-01-01, 2w
    section Fase 2
    Ingestão PostgreSQL (CDC)   :active, f2, after f0, 2w
    section Fase 3
    Dataform Silver Layer       :f3, after f2, 2w
    section Fase 4
    Dataform Gold - Primeiro Mart :f4, after f3, 1w
    section Fase 5
    Deploy Looker & Dashboards  :f5, after f4, 1w
    section Fase 6
    Qualidade & Observabilidade :f6, after f5, 2w
    section Fase 7
    Expansão Fontes (Firebase, SF) :f7, after f6, 2w
    section Fase 8
    Product Analytics & DS      :f8, after f7, 1w
    section Fase 9
    Governança Completa         :f9, after f8, 1w
    section Fase 10
    Otimização & Handoff        :f10, after f9, 3w
```

---

## Notas de Arquitetura

### Decisões Arquiteturais

**1. Por que Dataform ao invés de dbt Core?**
- Gerenciado pelo Google (zero ops)
- Integração nativa com BigQuery e IAM
- Git built-in
- Custo zero (incluído no BigQuery)
- Trade-off: Ecossistema menor (mas conceitos compatíveis com dbt)

**2. Por que Cloud Storage + BigQuery ao invés de só BigQuery?**
- Custo: Storage no GCS é 10x mais barato que BigQuery
- Flexibilidade: Dados raw disponíveis para reprocessamento
- Auditoria: Bronze imutável (compliance)
- BigLake: Query direto do GCS sem cópia

**3. Por que Fivetran e não só Airbyte?**
- Fivetran: SaaS conectores (zero manutenção) para fontes críticas
- Airbyte: Open-source para fontes customizadas e controle de custo
- Híbrido: Melhor custo-benefício

**4. Por que Cloud Composer (Airflow) e não Cloud Workflows?**
- Airflow: Padrão da indústria, comunidade enorme
- Python: Flexibilidade total para lógica complexa
- Histórico: Melhor observabilidade e retry logic
- Trade-off: Mais caro ($200/mês vs $20/mês Workflows)

### Princípios de Design

1. **Idempotência**: Pipelines podem ser re-executados sem efeitos colaterais
2. **Imutabilidade**: Bronze layer nunca é modificado
3. **Incremental-First**: Processar apenas dados novos (custo e performance)
4. **Testing in Production**: Deploy com feature flags, rollback fácil
5. **Documentation as Code**: Metadados versionados junto com código

### Anti-Patterns Evitados

- ❌ Transformações no Bronze (manter raw)
- ❌ Joins no Silver (deixar para Gold)
- ❌ Código não versionado (tudo no Git)
- ❌ Queries sem particionamento (custo alto)
- ❌ Dashboards consultando Bronze/Silver (usar Gold)
