# LCHAI v2.0 — Lung Cancer Histologic Analysis with AI

Oncology Explainable AI system for lung adenocarcinoma histopathological analysis.

## What's New in v2.0

- **Pattern-Informed ABMIL** (Artifact 2): Replaces XGBoost for mutation prediction using gated attention on concat(embeddings\_512d, pattern\_probs\_6d)
- **Fuzzy Choquet MIL** (Artifact 3): Parallel pathway with interpretable Shapley values and interaction indices from a 2-additive fuzzy measure
- **6 genes**: TP53, EGFR, KRAS, STK11, KEAP1, RBM10 (expanded from 3)
- **Confidence labelling**: Conclusive (AUROC ≥ 0.70) vs Inconclusive with gene-specific disclaimers
- **SHAP Decomposition**: DeepSHAP on ABMIL separating embedding dims (0-511) vs pattern dims (512-517) contribution
- **3-card frontend**: Mutation Report, Attention + Pattern Visualisation, Ontology-Grounded Explanation

## Quick Start

```bash
cp .env.example .env
make build
make up
make migrate
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| api-gateway | 8000 | JWT/RBAC proxy |
| case-service | 8001 | Patient & case CRUD |
| image-service | 8002 | Image upload/MinIO |
| inference-service | 8003 | ML pipeline (CTransPath + FuzzyArcLoss v3) |
| ehr-service | 8004 | EHR ingestion & entity extraction |
| graph-service | 8005 | Ontology graph assembly (Fuseki) |
| ontology-admin-service | 8006 | Ontology admin (proposals, publish) |
| audit-service | 8007 | Audit event log |
| webapp | 3000 | React UI |

## Infrastructure

| Component | Port | Purpose |
|-----------|------|---------|
| PostgreSQL 16 | 5432 | Relational DB |
| RabbitMQ | 5672/15672 | Message broker |
| Redis | 6379 | Celery backend |
| MinIO | 9000/9001 | Object storage (S3) |
| Keycloak | 8080 | Auth (OIDC) |
| Fuseki | 3030 | Triple store (SPARQL) |
| Jaeger | 16686 | Distributed tracing |
| Prometheus | 9090 | Metrics |
