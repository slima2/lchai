# LCHAI v2.0 — Lung Cancer Histologic Analysis with AI

**Interpretable and explainable AI system for predicting oncogenic mutations from H&E whole-slide images of lung adenocarcinoma, integrating fuzzy logic, attention-based MIL, fuzzy Choquet aggregation, and ontology-grounded LLM explanations.**

> Research tool — NOT for clinical diagnosis.

**Live demo:** [https://lchai.gptfy.biz/](https://lchai.gptfy.biz/) (credentials: `unifr1` / `unifr1`)

---

## About

LCHAI (Lung Cancer Histologic Analysis with AI) is the translational software artefact of a PhD thesis in Computer Science at the University of Fribourg, Switzerland. It demonstrates the end-to-end integration of three novel machine learning artefacts into a clinical decision-support prototype for computational pathology.

**Author:** Servio Fernando Lima Reina  
**Institution:** University of Fribourg, Switzerland  
**Degree:** PhD in Computer Science  
**Thesis:** *Fuzzy Margin Representation Learning for Interpretable Architecture–Genotype Associations in Lung Adenocarcinoma*

### Interpretability vs. Explainability

LCHAI distinguishes the two terms following Lipton (2018) and Doshi-Velez & Kim (2017):

- **Interpretability** is a model property: every artefact exposes inspectable internal structure (per-sample fuzzy margins, attention weights, Choquet Shapley values, pattern attributions). This is empirically evaluated in the thesis.
- **Explainability** is a system capability: the LCHAI prototype generates LLM rationales grounded in a curated NCIt/MONDO knowledge graph and constrained by fuzzy linguistic labels. Formal evaluation (faithfulness study, expert reader study) is short-term future work.

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

All artefacts are evaluated on the TCGA–LUAD cohort (N = 687 slides, 668 patients, **multi-label** mutation supervision over 6 genes) using stratified 5-fold patient-level cross-validation. Each slide may carry several co-mutations (e.g. TP53+KRAS, STK11+KEAP1):

| Gene  | Best Method                | AUROC (mean ± std) | Conclusive? (AUROC ≥ 0.70) |
|-------|----------------------------|--------------------|----------------------------|
| **TP53**  | B2 (embeddings-only ABMIL) | 0.718 ± 0.053 | Yes |
| **EGFR**  | B2 (embeddings-only ABMIL) | 0.701 ± 0.049 | Yes |
| **STK11** | PI-ABMIL (ours)            | 0.695 ± 0.023 | Inconclusive |
| **RBM10** | FC-MIL (ours)              | 0.661 ± 0.063 | Inconclusive |
| **KEAP1** | PI-ABMIL (ours)            | 0.610 ± 0.071 | Inconclusive |
| **KRAS**  | FC-MIL (ours)              | 0.609 ± 0.059 | Inconclusive |

The **Conclusive / Inconclusive** flag is a per-gene, **cohort-level** verdict (not per-slide) derived solely from AUROC against the Hosmer–Lemeshow criterion (AUROC ≥ 0.70).

These results are competitive with similarly-scaled studies (Saldanha et al. 0.65 for TP53; Logan et al. 0.69 for TP53), while providing a **dual-interpretability channel** absent from prior work: spatial attention maps *and* human-readable histological pattern attributions.

### Three-regime structural taxonomy (analytical contribution)

The per-gene Inconclusive verdicts decompose into three named structural regimes that bound what any morphology-only model can recover from H&E alone:

1. **Encoder saturation** *(TP53, EGFR)* — the pretrained CTransPath encoder already captures the relevant morphology; the explicit pattern channel adds no further information.
2. **Inter-pattern co-occurrence** *(KRAS)* — discriminative signal lives in pairwise pattern interactions, not in any single pattern; only an aggregator that reads joint pattern activations (FC-MIL's Choquet integral) recovers it.
3. **Out-of-ontology** *(STK11, KEAP1, RBM10)* — no representation within the 6-pattern ANORAK simplex carries the signal. This regime decomposes into three named mechanisms:
   - *label-space mismatch* (Lipton et al. 2018, label shift)
   - *no morphological projection* (this thesis)
   - *collapse-to-prior* (Bowman et al. 2016, posterior collapse)

Genes in regime (iii) require **fusing additional data sources** (gene-expression, radiology, expanded pattern taxonomy with mucinous/IMA), not further architectural refinement.

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
  │   └─ 6-class pattern probabilities (lepidic, acinar,
  │      papillary, micropapillary, solid, cribriform)
  │      [ANORAK 2024 ontology — Pan et al.]
  │
  ├─ Gene-specific optimal model (thesis Finding 2):
  │   ├─ B2:        ABMIL on embeddings only (TP53, EGFR)
  │   ├─ PI-ABMIL:  ABMIL on concat(emb₅₁₂, pat₆) (STK11, KEAP1)
  │   └─ FC-MIL:    Fuzzy Choquet MIL (KRAS, RBM10)
  │
  ├─ Ablation comparison (Proposed vs B2 vs B3)
  ├─ Permutation importance (pattern contribution %)
  ├─ DeepSHAP decomposition (emb vs pattern dims)
  └─ Choquet Shapley values + interaction indices
```

### Six-level interpretability framework

Every prediction exposes inspectable internal structure across six complementary levels, integrated end-to-end in the prototype:

| Level | Output | Source artefact |
|-------|--------|-----------------|
| 1. Tile-level pattern probabilities | 6-d soft pattern vector per tile | FuzzyArcLoss V2 |
| 2. Spatial attention maps | Per-tile attention weight | PI-ABMIL / FC-MIL |
| 3. Pattern attribution | Permutation importance over the 6 patterns | PI-ABMIL ablation |
| 4. SHAP decomposition | Embedding-vs-pattern dimensional split | DeepSHAP |
| 5. Choquet Shapley + interaction indices | 6 Shapley values + 15 pairwise interactions | FC-MIL fuzzy measure |
| 6. Fuzzy linguistic labels + ontology-grounded LLM rationale | Calibrated intensity terms + NCIt/MONDO-anchored natural language | KG explainer |

### Dual anti-hallucination mechanism (explainability layer)

LLM-generated rationales are constrained on two axes simultaneously:

- **HOW the model speaks**: trapezoidal fuzzy membership functions translate every numeric output into a calibrated linguistic intensity term, eliminating fabricated quantitative claims.
- **WHAT the model can claim**: a curated three-tier knowledge graph (NCIt + MONDO ontologies + per-case dynamic filter + DeepSearch literature enrichment) bounds the set of admissible mutation–pattern–treatment relations.

All ontology IRIs in the graph have been **verified canonical** against the NCI EVS REST API (NCIt v26.04d, April 2026) and the MONDO OLS API.

### Frontend

- **Images tab**: Upload WSI, process with v2.0 pipeline, view mutation report with fuzzy linguistic confidence labels, pattern overlay, and clinical summary
- **Viewer tab**: QuPath-like zoom/pan viewer with Original, Patterns, Attention, and Combined overlay layers
- **Graph tab**: Ontology-grounded knowledge graph (NCIt + MONDO + DeepSearch literature enrichment) with LLM rationales and treatment associations
- **Explainability tab**: Per-gene SHAP decomposition, Choquet Shapley + interaction indices, ablation study, permutation importance, fuzzy-label-constrained LLM explanations
- **Active Learning tab**: Pathologist correction loop with audit trail (Keycloak username, RabbitMQ events, Correction History panel)
- **Admin tab**: Editable system parameters (AUROC values, threshold, methods, inference settings); ontology versioning and DeepSearch tools

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
  title   = {Fuzzy Margin Representation Learning for Interpretable
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
- **GitHub:** [github.com/slima2/lchai](https://github.com/slima2/lchai)
- **Live demo:** [lchai.gptfy.biz](https://lchai.gptfy.biz/) (credentials: `unifr1` / `unifr1`)
