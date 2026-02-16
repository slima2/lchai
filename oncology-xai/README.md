# LCHAI v1.2 — Lung Cancer Histologic Analysis with AI

Oncology Explainable AI system for lung cancer histopathological analysis.

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
