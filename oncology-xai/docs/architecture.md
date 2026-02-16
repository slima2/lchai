# LCHAI v1.2 — Architecture Overview

> Reference: DERCAS_LCHAI_v1_2_CONSOLIDADO.md

## System Overview

LCHAI v1.2 (Lung Cancer Histologic Analysis with AI) is a microservices-based
research platform for explainable AI-assisted histopathological analysis of
lung adenocarcinoma. It integrates morphological pattern classification,
mutation prediction, knowledge graph assembly, and clinical explanation
generation.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          React Webapp (:3000)                        │
│   CaseSelector │ ImagePanel │ EHRPanel │ GraphPanel │ ShapPanel │ Admin │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ HTTP
                    ┌──────────────▼──────────────┐
                    │     API Gateway (:8000)       │
                    │   JWT + RBAC + Reverse Proxy  │
                    └─┬──────┬──────┬──────┬──────┬┘
                      │      │      │      │      │
          ┌───────────▼─┐  ┌▼────┐ ┌▼────┐ ┌▼────┐ ┌▼──────────┐
          │case-service │  │image│ │infer│ │ehr  │ │graph-svc   │
          │  :8001      │  │:8002│ │:8003│ │:8004│ │  :8005     │
          └──────┬──────┘  └──┬──┘ └──┬──┘ └──┬──┘ └──┬────────┘
                 │            │       │       │       │
          ┌──────▼────────────▼───────▼───────▼───────▼──────┐
          │              PostgreSQL 16 (:5432)                 │
          │  patients │ cases │ images │ ml_jobs │ ehr_docs   │
          │  result_bundles │ pattern_results │ genetic_results│
          │  xai_artifacts │ morphologic_profiles │ audit_events│
          └───────────────────────────────────────────────────┘

  ┌──────────────┐  ┌──────────┐  ┌────────┐  ┌──────────┐
  │  RabbitMQ    │  │  Redis   │  │  MinIO  │  │ Fuseki   │
  │  :5672       │  │  :6379   │  │  :9000  │  │  :3030   │
  │  Event Bus   │  │  Celery  │  │  S3/Obj │  │  SPARQL  │
  └──────────────┘  └──────────┘  └────────┘  └──────────┘

  ┌──────────────────────┐  ┌──────────────────────┐
  │ ontology-admin :8006 │  │  audit-service :8007 │
  └──────────────────────┘  └──────────────────────┘

  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  Keycloak    │  │   Jaeger     │  │  Prometheus  │
  │  :8080       │  │   :16686     │  │   :9090      │
  │  AuthN/AuthZ │  │   Tracing    │  │   Metrics    │
  └──────────────┘  └──────────────┘  └──────────────┘
```

## ML Pipeline (CTransPath + FuzzyArcLoss V3 SubCenters)

1. **Image upload** → MinIO with SHA-256 checksum
2. **Tile extraction** — 384px tiles, no overlap, background filtering (>90%)
3. **CTransPath backbone** — `swin_tiny_patch4_window7_224` + ConvStem (3→12→24→96)
4. **Projection head** — `Linear(768→512) → LayerNorm → GELU → Dropout(0.15)`
5. **FuzzyArcLoss V3 SubCenters** — K=3 sub-centers per class, V2-inverse fuzzy membership
   - Confident (|cos θ| ≥ τ): μ = 0.8 + 0.2·|cos θ| (full margin)
   - Uncertain (|cos θ| < τ): μ = 0.3 + 0.4·|cos θ| (reduced margin)
6. **Pattern composition** — 6 patterns: lepidic, acinar, papillary, micropapillary, solid, mucinous
7. **Morphologic profile** — Case-level aggregation: n_tiles_total + 6 pct_* features
8. **XGBoost mutation prediction** — Per gene (EGFR, KRAS, TP53): n_estimators=300, max_depth=3
9. **SHAP explanations** — TreeExplainer: bar + beeswarm (global), force plot (case-level)
10. **Overlay** — RGBA combined overlay with fixed pattern color palette

## LangGraph Workflows (Section 13)

| Workflow | Nodes | Purpose |
|----------|-------|---------|
| ImageAnalysisGraph | 14 | End-to-end inference: validate → load → tile → embed → classify → mutate → SHAP → persist |
| EHRToOntologyGraph | 7 | NER → lookup → disambiguate → map to NCIt/MONDO |
| GraphAssemblerGraph | 6 | Fetch findings → SPARQL subgraph → fuse provenance → layout → persist |
| ExplanationComposerGraph | 6 | Gather evidence → conflicts → draft → guardrails → publish |
| OntologyUpdateWorkflow | 12 | Source discovery → fetch → validate → diff → reasoner → impact → HITL → publish |

## Security Model

- **AuthN**: Keycloak (OIDC/JWT) with realm `oncology`
- **AuthZ**: RBAC (3 roles: clinician, admin, auditor) + ABAC (owner-based filtering)
- **Guardrails**: Prohibited clinical claim phrases, mandatory disclaimers
- **Audit**: All events to `audit_events` table via RabbitMQ consumer, idempotent by event_id
- **PHI**: No PHI in logs; correlation_id for distributed tracing via OTel

## Data Model (19 tables)

| Service | Tables |
|---------|--------|
| case-service | patients, cases |
| image-service | images |
| inference-service | ml_jobs, result_bundles, pattern_results, genetic_results, xai_artifacts, morphologic_profiles |
| ehr-service | ehr_documents, ehr_entities, ehr_mappings |
| graph-service | case_graph_snapshots |
| ontology-admin-service | ontology_versions, ontology_update_proposals, explanation_reports |
| audit-service | audit_events |

## Infrastructure

| Component | Version | Port | Purpose |
|-----------|---------|------|---------|
| PostgreSQL | 16 | 5432 | Primary database |
| RabbitMQ | 3.12 | 5672 | Event bus (topic exchange) |
| Redis | 7 | 6379 | Celery result backend |
| MinIO | latest | 9000 | Object storage (S3-compatible) |
| Keycloak | 23.0 | 8080 | Identity & access management |
| Apache Fuseki | latest | 3030 | SPARQL triplestore |
| Jaeger | 1.52 | 16686 | Distributed tracing |
| Prometheus | 2.48 | 9090 | Metrics collection |

## Key Constants

- `MODEL_BACKEND`: `mock` (default) | `local` | `triton`
- `evidence_source`: `THESIS_INTERNAL`
- `intended_use`: `research / decision support (non-diagnostic)`
- Pattern palette: lepidic=#FFEB3B, acinar=#4CAF50, papillary=#2196F3, micropapillary=#E91E63, solid=#F44336, mucinous=#FF9800
