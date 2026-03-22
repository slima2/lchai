# LCHAI v2.0 — Lung Cancer Histologic Analysis with AI

**Explainable AI system for predicting oncogenic mutations from H&E whole-slide images of lung adenocarcinoma, integrating fuzzy logic, attention-based MIL, and ontology-grounded explanations.**

> Research tool — NOT for clinical diagnosis.

---

## About

LCHAI (Lung Cancer Histologic Analysis with AI) is the translational software artefact of a PhD thesis in Computer Science at the University of Fribourg, Switzerland. It demonstrates the end-to-end integration of three novel machine learning artefacts into a clinical decision-support prototype for computational pathology.

**Author:** Servio Fernando Lima Reina  
**Institution:** University of Fribourg, Switzerland  
**Degree:** PhD in Computer Science  
**Thesis:** *Fuzzy Margin Representation Learning for Explainable Architecture–Genotype Associations in Lung Adenocarcinoma*

---

## Thesis Abstract

Predicting oncogenic mutations from haematoxylin-and-eosin-stained (H&E) whole-slide images (WSIs) has emerged as a promising avenue for rapid, cost-effective molecular profiling in lung adenocarcinoma (LUAD). State-of-the-art approaches rely on end-to-end deep learning or foundation models pretrained on tens of thousands of slides, achieving high AUROC values but offering limited interpretability and requiring data resources beyond the reach of most research groups.

This thesis addresses a complementary question guided by the design science research paradigm: *Can the explicit incorporation of validated histopathological pattern knowledge via fuzzy logic improve — or at least preserve — mutation prediction performance while providing an interpretable reasoning pathway, even under severe data scarcity?*

Following a fuzzy design science research framework, we design, implement and rigorously evaluate three interconnected artefacts:

### Artefact 1 — FuzzyArcLoss V2
A novel angular margin loss function in which a fuzzy membership function μ adaptively modulates the angular penalty on a per-sample basis according to prediction confidence. Trained on the expert-annotated Zenodo–Anorak histopathology atlas, FuzzyArcLoss V2 achieves a mean macro-F1 of **92.31% ± 2.04** across 15 runs (5-fold × 3 seeds), significantly outperforming SphereFace (p = 0.001, Cohen's d = 1.00) and ranking first among 18 compared loss functions.

### Artefact 2 — Pattern-Informed ABMIL
A pattern-informed attention-based multiple-instance learning (ABMIL) architecture that concatenates CTransPath visual embeddings (512-d) with the 6-class fuzzy pattern probabilities produced by Artefact 1, thereby injecting validated histological domain knowledge as a structured prior into the mutation prediction pipeline.

### Artefact 3 — Fuzzy Choquet MIL
A Fuzzy Choquet integral aggregation module that replaces standard attention pooling, modelling supra-additive interactions among histological patterns through a learned fuzzy measure with Shapley values and second-order interaction indices.

### Results

All artefacts are evaluated on the TCGA–LUAD cohort (N = 687 slides, 668 patients, 6 genes) using stratified 5-fold patient-level cross-validation:

| Gene | Best Method | AUROC (mean ± std) |
|------|-------------|-------------------|
| **TP53** | B2 (embeddings-only ABMIL) | 0.718 ± 0.053 |
| **EGFR** | B2 (embeddings-only ABMIL) | 0.701 ± 0.049 |
| **STK11** | P (pattern-informed ABMIL) | 0.695 ± 0.023 |
| **RBM10** | FC (Fuzzy Choquet) | 0.661 ± 0.063 |
| **KEAP1** | P (pattern-informed ABMIL) | 0.610 ± 0.071 |
| **KRAS** | FC (Fuzzy Choquet) | 0.609 ± 0.059 |

These results are competitive with similarly-scaled studies such as Saldanha et al. (AUROC = 0.65 for TP53) and Logan et al. (AUROC = 0.69 for TP53), while providing a **dual-interpretability channel** absent from all prior work: spatial attention maps *and* human-readable histological pattern attributions.

### Keywords

Fuzzy logic · Angular margin loss · Multiple-instance learning · Choquet integral · Histopathological patterns · Lung adenocarcinoma · Mutation prediction · Design science research · Computational pathology

---

## System Architecture

LCHAI v2.0 is a microservice-based platform deployed via Docker Compose with GPU acceleration.

![System Architecture](docs/lchai_full_system.png)

### ML Pipeline

```
WSI (SVS/TIFF/BIF)
  │
  ├─ OpenSlide decode → Thumbnail + full-res handle
  │
  ├─ Full-resolution tiling (224px, stride-adaptive)
  │   └─ Artifact rejection (dark, pen markers, saturation)
  │
  ├─ CTransPath Swin Tiny (GPU, batch=64)
  │   └─ 512-d embeddings per tile
  │
  ├─ FuzzyArcLoss V2 cosine head
  │   └─ 6-class pattern probabilities (acinar, lepidic,
  │      papillary, micropapillary, solid, mucinous)
  │
  ├─ Gene-specific optimal model (thesis Finding 2):
  │   ├─ B2: ABMIL on embeddings only (TP53, EGFR)
  │   ├─ P:  ABMIL on concat(emb₅₁₂, pat₆) (STK11, KEAP1)
  │   └─ FC: Fuzzy Choquet MIL (KRAS, RBM10)
  │
  ├─ Ablation comparison (Proposed vs B2 vs B3)
  ├─ Permutation importance (pattern contribution %)
  ├─ DeepSHAP decomposition (emb vs pattern dims)
  └─ Choquet Shapley values + interaction indices
```

### Frontend

- **Images tab**: Upload WSI, process with v2.0 pipeline, view mutation report with confidence labels, pattern overlay, and clinical summary
- **Viewer tab**: QuPath-like zoom/pan viewer with Original, Patterns, Attention, and Combined overlay layers
- **Graph tab**: Ontology-grounded knowledge graph (NCIt + MONDO) with LLM-generated explanations and treatment associations
- **Explainability tab**: Per-gene SHAP decomposition, Choquet Shapley values, ablation study, permutation importance, and LLM-powered explanations
- **Admin tab**: Editable system parameters (AUROC values, threshold, methods, inference settings)

---

## Quick Start

### Prerequisites

- Docker Desktop with **NVIDIA Container Toolkit** (for GPU acceleration)
- NVIDIA GPU with CUDA support (tested on RTX 4060, 8 GB VRAM)
- Model checkpoints:
  - CTransPath backbone: `ctranspath.pth`
  - FuzzyArcLoss V2 head: `best_fuzzyarcloss_v2.pth`
  - ABMIL/Choquet per-gene checkpoints (5-fold × 6 conditions × 6 genes)

### Setup

```bash
# 1. Clone the repository
git clone https://gitlab.com/serviolimareina/lchaiv2.git
cd lchaiv2

# 2. Configure environment
cp .env.example .env
# Edit .env: set checkpoint paths, API keys, etc.

# 3. Build and start all services
make build
make up

# 4. Run database migrations
make migrate

# 5. Access the system
#    Frontend:  http://localhost:3000
#    API:       http://localhost:8000/api/v1/
#    RabbitMQ:  http://localhost:15672
#    MinIO:     http://localhost:9001
```

### GPU Verification

```bash
# Verify GPU is accessible inside the inference worker
docker exec oncology-inference-worker python3 -c \
  "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')"
```

---

## Services

| Service | Port | Description |
|---------|------|-------------|
| **api-gateway** | 8000 | FastAPI reverse proxy with JWT/RBAC, routes to 7 services |
| **case-service** | 8001 | Patient & case CRUD, dynamic case creation per upload |
| **image-service** | 8002 | Image upload (PNG, JPEG, TIFF, SVS, BIF), SHA-256, MinIO storage |
| **inference-service** | 8003 | ML pipeline orchestrator, job management, progress tracking, runtime parameters API |
| **inference-worker** | — | Celery worker with GPU (NVIDIA RTX 4060), executes ML pipeline |
| **ehr-service** | 8004 | EHR ingestion, regex NER, ontology mapping (NCIt/MONDO) |
| **graph-service** | 8005 | Knowledge graph assembly, SPARQL queries, LLM explanations |
| **ontology-admin** | 8006 | Ontology versioning, DeepSearch (PubMed/arXiv/Semantic Scholar) |
| **audit-service** | 8007 | Event consumer, idempotent audit log |
| **webapp** | 3000 | React 18 + Vite + Tailwind + TanStack Query |

## Infrastructure

| Component | Port | Purpose |
|-----------|------|---------|
| PostgreSQL 16 | 5432 | Relational DB (19 tables across 7 services, Alembic migrations) |
| RabbitMQ | 5672 / 15672 | Message broker (topic exchange + Celery broker) |
| Redis | 6379 | Celery result backend + job progress tracking |
| MinIO | 9000 / 9001 | S3-compatible object storage (images, tiles, overlays, XAI artifacts) |
| Keycloak | 8080 | OIDC / JWT authentication (realm: oncology) |
| Apache Fuseki | 3030 | SPARQL triplestore (NCIt + MONDO ontologies) |
| Jaeger | 16686 | Distributed tracing (OpenTelemetry) |
| Prometheus | 9090 | Metrics scraping |

---

## Project Structure

```
├── apps/
│   ├── api-gateway/          # FastAPI reverse proxy
│   ├── audit-service/        # Event audit log
│   ├── case-service/         # Patient/case management
│   ├── ehr-service/          # EHR ingestion + NER
│   ├── graph-service/        # Knowledge graph + LLM explain
│   ├── image-service/        # Image upload + MinIO
│   ├── inference-service/    # ML pipeline (CTransPath, ABMIL, Choquet)
│   │   └── app/
│   │       ├── ml/           # Model definitions (ABMIL, Choquet, CTransPath)
│   │       ├── roi_inference_ctranspath_fuzzyarcloss_v3.py  # Main pipeline
│   │       ├── tasks.py      # Celery GPU worker
│   │       └── routes.py     # REST API + parameters
│   ├── ontology-admin-service/  # Ontology management + DeepSearch
│   └── webapp/               # React frontend
│       └── src/panels/       # ImagePanel, ViewerPanel, ShapPanel, etc.
├── packages/
│   ├── common/               # Shared: JWT, storage, Pydantic, OTel
│   ├── event-contracts/      # EventEnvelope, publisher, consumer
│   └── langgraph-workflows/  # 5 LangGraph state machines
├── infra/
│   └── docker-compose.yml    # Full stack orchestration with GPU support
├── scripts/                  # Analysis scripts (mutation report, GDC download)
├── docs/                     # Architecture diagrams (Graphviz)
└── ontologies/               # NCIt + MONDO (downloaded at runtime via Fuseki)
```

---

## Key Technologies

| Layer | Technologies |
|-------|-------------|
| **ML/DL** | PyTorch (CUDA 12.4), CTransPath (Swin Tiny), FuzzyArcLoss V2, Gated Attention ABMIL, Fuzzy Choquet MIL, DeepSHAP, XGBoost (legacy) |
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Celery, Alembic, Pydantic |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, TanStack React Query, D3.js |
| **Knowledge** | Apache Fuseki (SPARQL), RDFLib, NCIt + MONDO + SO ontologies, LangGraph, OpenAI API |
| **Infrastructure** | Docker Compose, PostgreSQL 16, RabbitMQ, Redis, MinIO, Keycloak, OpenTelemetry, Jaeger, Prometheus |
| **Image Processing** | OpenSlide (SVS/TIFF/BIF), PIL/Pillow, OpenCV, NumPy |

---

## Citation

If you use LCHAI or any of the artefacts described in this thesis, please cite:

```bibtex
@phdthesis{lima2026fuzzy,
  author  = {Lima Reina, Servio Fernando},
  title   = {Fuzzy Margin Representation Learning for Explainable
             Architecture--Genotype Associations in Lung Adenocarcinoma},
  school  = {University of Fribourg},
  year    = {2026},
  address = {Fribourg, Switzerland}
}
```

---

## License

This project is part of a PhD thesis and is provided for academic and research purposes. Contact the author for licensing inquiries.

## Contact

- **Author:** Servio Fernando Lima Reina
- **Institution:** University of Fribourg, Department of Informatics
- **GitLab:** [gitlab.com/serviolimareina/lchaiv2](https://gitlab.com/serviolimareina/lchaiv2)
