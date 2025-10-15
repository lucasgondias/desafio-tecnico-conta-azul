/**
 * Declaração de fontes de dados Bronze Layer
 * Essas são as external tables do BigLake que apontam para Cloud Storage
 */

// PostgreSQL Production (via Datastream CDC)
declare({
  schema: "bronze_postgres",
  name: "customers",
  description: "Tabela de clientes do PostgreSQL produção (raw)"
});

declare({
  schema: "bronze_postgres",
  name: "invoices",
  description: "Notas fiscais/faturas do PostgreSQL produção (raw)"
});

declare({
  schema: "bronze_postgres",
  name: "payments",
  description: "Pagamentos do PostgreSQL produção (raw)"
});

declare({
  schema: "bronze_postgres",
  name: "subscriptions",
  description: "Assinaturas ativas e canceladas (raw)"
});

// Firebase Analytics
declare({
  schema: "bronze_firebase",
  name: "events",
  description: "Eventos de produto do Firebase Analytics (raw)"
});

// Salesforce CRM
declare({
  schema: "bronze_salesforce",
  name: "leads",
  description: "Leads do Salesforce CRM (raw)"
});

declare({
  schema: "bronze_salesforce",
  name: "opportunities",
  description: "Oportunidades de venda do Salesforce (raw)"
});

// Google Analytics 4
declare({
  schema: "bronze_ga4",
  name: "events",
  description: "Eventos do Google Analytics 4 (raw, tabela diária particionada)"
});
