# Como Usar Esta Proposta

Este documento explica como navegar e utilizar os materiais entregues para o desafio técnico.

---

## Estrutura dos Arquivos

```
desafio-tecnico-conta-azul/
├── README.md                          # 📖 Documentação completa (COMEÇAR AQUI)
├── RESUMO_EXECUTIVO.md               # 📊 Resumo executivo (para apresentação)
├── ARCHITECTURE.md                    # 🏗️ Diagramas detalhados da arquitetura
├── COMO_USAR.md                      # 📋 Este arquivo (guia de uso)
│
├── dataform/                          # 💻 Código Dataform (transformações)
│   ├── dataform.json                 # Configuração do projeto
│   ├── definitions/
│   │   ├── sources/
│   │   │   └── sources.js            # Declaração de fontes Bronze
│   │   ├── staging/
│   │   │   └── core/
│   │   │       └── stg_postgres__customers.sqlx  # Exemplo Silver
│   │   └── marts/
│   │       └── revenue_ops/
│   │           └── fct_monthly_recurring_revenue.sqlx  # Exemplo Gold
│
├── examples/                          # 📁 Exemplos de código
│   ├── airflow/
│   │   └── daily_pipeline_dag.py     # DAG principal do Airflow
│   └── tests/
│       └── test_data_quality.py      # Testes de qualidade (pytest)
│
└── docs/
    └── APRESENTACAO.md                # 🎤 Slides para apresentação
```

---

## Roteiro de Leitura

### Para Avaliadores Técnicos (CTO, Head of Data, Engenheiros)

**1. Visão Geral (15 min)**
- Ler: `RESUMO_EXECUTIVO.md`
- Objetivo: Entender proposta, stack, custos

**2. Arquitetura Detalhada (30 min)**
- Ler: `README.md` (seções 1-7)
- Ler: `ARCHITECTURE.md` (diagramas)
- Objetivo: Entender camadas, fluxos de dados, decisões arquiteturais

**3. Código e Implementação (30 min)**
- Revisar: `dataform/` (modelos SQL)
- Revisar: `examples/airflow/daily_pipeline_dag.py`
- Revisar: `examples/tests/test_data_quality.py`
- Objetivo: Avaliar qualidade de código, padrões, boas práticas

**Total: ~1h15min**

---

### Para Gestores de Produto / Negócio

**1. Resumo Executivo (10 min)**
- Ler: `RESUMO_EXECUTIVO.md` (seções: Visão Geral, Stack, Custos, Roadmap)
- Objetivo: Entender valor de negócio, investimento, prazos

**2. Apresentação Visual (20 min)**
- Ler: `docs/APRESENTACAO.md` (slides formatados)
- Objetivo: Visão completa preparada para apresentação

**Total: ~30min**

---

### Para Times de Dados (Analistas, Cientistas)

**1. Como os dados serão organizados (15 min)**
- Ler: `README.md` seções:
  - Camadas de Dados (Bronze/Silver/Gold)
  - Estratégia de Ingestão
  - Camada de Consumo

**2. Como consumir os dados (15 min)**
- Ler: `README.md` seção "Camada de Consumo"
- Ver exemplos de queries em `dataform/definitions/marts/`
- Objetivo: Entender como acessar dados (Looker, BigQuery, Notebooks)

**Total: ~30min**

---

## Principais Arquivos por Objetivo

### Quero entender a arquitetura geral
→ `ARCHITECTURE.md`
- Diagramas Mermaid (fluxos, camadas, domínios)
- Decisões arquiteturais explicadas
- Anti-patterns evitados

### Quero ver código de transformação (SQL)
→ `dataform/definitions/`
- `staging/core/stg_postgres__customers.sqlx`: Exemplo de Silver (limpeza)
- `marts/revenue_ops/fct_monthly_recurring_revenue.sqlx`: Exemplo de Gold (agregação)

### Quero entender orquestração
→ `examples/airflow/daily_pipeline_dag.py`
- Pipeline diário completo (Bronze → Silver → Gold)
- Validações, testes, monitoramento
- Comentários explicativos em cada etapa

### Quero ver testes de qualidade
→ `examples/tests/test_data_quality.py`
- Testes de Silver layer (duplicatas, formatos, valores)
- Testes de Gold layer (regras de negócio)
- Testes de freshness (SLA)
- Testes de consistência cross-table

### Quero apresentar para stakeholders
→ `docs/APRESENTACAO.md`
- 17 slides prontos
- Resumo executivo, stack, custos, roadmap
- Diferenciais e próximos passos

### Quero números (custos, prazos, métricas)
→ `RESUMO_EXECUTIVO.md`
- Breakdown de custos ($700/mês)
- Comparação com concorrentes
- Roadmap de 16 semanas
- Métricas de sucesso

---

## Como Executar os Exemplos (Opcional)

### Pré-requisitos
- Conta GCP (free tier é suficiente para testes)
- gcloud CLI instalado
- Python 3.9+

### 1. Validar SQL do Dataform

```bash
cd dataform/

# Instalar Dataform CLI (opcional)
npm install -g @dataform/cli

# Compilar modelos (syntax check)
dataform compile

# Ver DAG de dependências
dataform compile --json | jq '.tables[] | {name: .name, dependencies: .dependencies}'
```

### 2. Executar Testes de Qualidade

```bash
cd examples/tests/

# Instalar dependências
pip install pytest google-cloud-bigquery pandas

# Configurar credenciais GCP
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"

# Executar testes (mock - sem BigQuery real)
pytest test_data_quality.py -v --tb=short
```

### 3. Visualizar DAG do Airflow

```bash
cd examples/airflow/

# Instalar Airflow localmente (opcional)
pip install apache-airflow[google]

# Copiar DAG para pasta do Airflow
cp daily_pipeline_dag.py ~/airflow/dags/

# Iniciar Airflow UI
airflow webserver -p 8080
# Acessar: http://localhost:8080
```

---

## Perguntas Frequentes

### Q: Preciso ter conta GCP para avaliar?
**A**: Não! Todos os códigos são exemplos didáticos. Você pode avaliar a arquitetura, lógica SQL e qualidade de código sem executar nada.

### Q: Quanto tempo levaria para implementar isso?
**A**: POC em 2 semanas. Implementação completa em 16 semanas (ver `RESUMO_EXECUTIVO.md` → Roadmap).

### Q: E se a Conta Azul quiser usar AWS ao invés de GCP?
**A**: A arquitetura é adaptável. Equivalências:
- BigQuery → Redshift / Athena
- Dataform → dbt Core
- Cloud Storage → S3
- Datastream → AWS DMS
- Cloud Composer → MWAA (Managed Airflow)

Conceitos (Medallion, Data Mesh, ELT) permanecem os mesmos.

### Q: Por que Dataform ao invés de dbt?
**A**: Dataform é gerenciado pelo Google (zero ops), integrado nativamente com BigQuery, e tem custo zero. Para GCP, é a escolha mais pragmática. Se migrar para outra cloud, dbt seria preferível.

### Q: Quanto custaria realmente implementar?
**A**:
- **Operacional**: ~$700/mês (ver breakdown em `RESUMO_EXECUTIVO.md`)
- **Implementação**: ~$30-40k (considerando 1 Senior + 2 Pleno AE por 4 meses)
- **ROI**: Economia de tempo de analistas (50% menos "data wrangling") paga o investimento em ~6 meses

### Q: Como garantir que dados sensíveis não vazam?
**A**:
- DLP (Data Loss Prevention) detecta PII automaticamente
- Policy Tags aplicam masking (hash SHA256) para não-autorizados
- Row-Level Security (RLS) limita acesso por grupo
- Audit Logs rastreiam todos os acessos
- Ver `README.md` seção "Governança de Dados"

---

## Feedback e Contato

**Dúvidas sobre a proposta?**
- Revisar `README.md` (documentação completa)
- Revisar `RESUMO_EXECUTIVO.md` (perguntas frequentes)

**Quer agendar apresentação técnica?**
- Usar slides de `docs/APRESENTACAO.md`
- Duração sugerida: 45 min apresentação + 15 min Q&A

**Quer deep dive em algum componente?**
- Dataform: `dataform/definitions/`
- Airflow: `examples/airflow/`
- Testes: `examples/tests/`
- Diagramas: `ARCHITECTURE.md`

---

## Checklist de Avaliação

Para facilitar a revisão, aqui está um checklist do que foi entregue:

### Documentação
- [x] Arquitetura geral (README.md)
- [x] Diagramas detalhados (ARCHITECTURE.md)
- [x] Resumo executivo (RESUMO_EXECUTIVO.md)
- [x] Slides para apresentação (docs/APRESENTACAO.md)
- [x] Guia de uso (COMO_USAR.md)

### Código e Exemplos
- [x] Configuração Dataform (dataform.json)
- [x] Declaração de sources (sources.js)
- [x] Modelo Silver (stg_postgres__customers.sqlx)
- [x] Modelo Gold (fct_monthly_recurring_revenue.sqlx)
- [x] DAG Airflow completo (daily_pipeline_dag.py)
- [x] Testes de qualidade (test_data_quality.py)

### Especificações Técnicas
- [x] Estratégia de ingestão ✓
- [x] Organização dos dados (Bronze/Silver/Gold) ✓
- [x] Transformações e orquestração ✓
- [x] Versionamento, testes, monitoramento ✓
- [x] Camada de consumo confiável ✓
- [x] Estimativa de custos ✓
- [x] Roadmap de implementação ✓

### Diferenciais
- [x] Documentação rica com exemplos práticos
- [x] Código comentado e didático
- [x] Decisões arquiteturais justificadas
- [x] Considerações de custo e performance
- [x] Estratégia de governança e segurança (LGPD)
- [x] Múltiplos níveis de leitura (executivo → técnico)

---

## Próximos Passos Sugeridos

1. **Primeira Leitura** (30 min)
   - Ler `RESUMO_EXECUTIVO.md`
   - Navegar pelos diagramas em `ARCHITECTURE.md`

2. **Avaliação Técnica** (1h)
   - Revisar código em `dataform/` e `examples/`
   - Avaliar decisões arquiteturais em `README.md`

3. **Discussão Interna** (Conta Azul)
   - Validar fit com necessidades dos 3 times (Product Analytics, RevOps, DS)
   - Avaliar viabilidade de budget (~$700/mês + implementação)
   - Priorizar fontes de dados (quick wins)

4. **Apresentação** (se aprovado)
   - Agendar sessão de deep dive técnico
   - Usar slides de `docs/APRESENTACAO.md`
   - Q&A com times técnicos

5. **POC** (se aprovado)
   - 2 semanas: PostgreSQL → Bronze → Silver → Gold → Looker
   - Demonstrar valor end-to-end

---

**Boa leitura e avaliação! 🚀**
