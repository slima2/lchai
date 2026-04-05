"""Domain entity models for Oncology XAI — LCHAI v1.2."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field

from oncology_common.models.base import BaseModel


# ── Enums ──────────────────────────────────────────────────────────────

class CaseStatus(str, Enum):
    CREATED = "CREATED"
    READY = "READY"
    PROCESSING = "PROCESSING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED = "REVIEWED"
    CLOSED = "CLOSED"


class ImageFormat(str, Enum):
    PNG = "png"
    BIFF = "biff"


class PatternType(str, Enum):
    LEPIDIC = "lepidic"
    ACINAR = "acinar"
    PAPILLARY = "papillary"
    MICROPAPILLARY = "micropapillary"
    SOLID = "solid"
    CRIBRIFORM = "cribriform"


class MutationType(str, Enum):
    EGFR = "EGFR"
    KRAS = "KRAS"
    TP53 = "TP53"
    STK11 = "STK11"
    KEAP1 = "KEAP1"
    RBM10 = "RBM10"


class MutationStatus(str, Enum):
    POSITIVE = "POS"
    NEGATIVE = "NEG"
    INCONCLUSIVE = "INCONCLUSIVE"


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(str, Enum):
    IMAGE_INFERENCE = "IMAGE_INFERENCE"
    EHR_EXTRACTION = "EHR_EXTRACTION"
    GRAPH_REBUILD = "GRAPH_REBUILD"
    ONTOLOGY_UPDATE = "ONTOLOGY_UPDATE"
    EXPLANATION_GENERATION = "EXPLANATION_GENERATION"


class ProposalStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


# ── Patient ────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    external_id: str | None = None
    demographics: dict[str, Any] = Field(default_factory=dict)


class Patient(BaseModel):
    patient_id: UUID
    external_id: str | None = None
    demographics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime | None = None


# ── Case ───────────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    patient_id: UUID
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Case(BaseModel):
    case_id: UUID
    patient_id: UUID
    status: CaseStatus = CaseStatus.CREATED
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class CaseUpdate(BaseModel):
    status: CaseStatus | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


# ── Image ──────────────────────────────────────────────────────────────

class ImageUploadMeta(BaseModel):
    format: ImageFormat = ImageFormat.PNG
    stain: str | None = None
    magnification: str | None = None
    notes: str | None = None


class ImageEntity(BaseModel):
    image_id: UUID
    case_id: UUID
    format: ImageFormat
    storage_uri: str
    checksum: str
    size_bytes: int
    stain: str | None = None
    magnification: str | None = None
    notes: str | None = None
    uploaded_by: str | None = None
    uploaded_at: datetime


# ── ML Job ─────────────────────────────────────────────────────────────

class MLJobEntity(BaseModel):
    job_id: UUID
    case_id: UUID | None = None
    image_id: UUID | None = None
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    error_code: str | None = None
    error_detail: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime


# ── Pattern / Genetic results ──────────────────────────────────────────

class PatternResult(BaseModel):
    pattern: PatternType
    score: float = Field(..., ge=0.0, le=1.0)
    percentage: float = Field(0.0, ge=0.0, le=100.0)
    is_conclusive: bool = True
    overlay_uri: str | None = None


class SHAPDecomposition(BaseModel):
    embedding_contribution_pct: float | None = None
    pattern_contribution_pct: float | None = None
    top_pattern_dims: list[str] | None = None


class ChoquetShapley(BaseModel):
    shapley_values: dict[str, float] | None = None
    interaction_indices: dict[str, float] | None = None


class GeneticResult(BaseModel):
    mutation: MutationType
    score: float = Field(..., ge=0.0, le=1.0)
    status: MutationStatus
    confidence_label: str | None = None  # Conclusive | Inconclusive
    auroc_threshold: float | None = None
    prediction_method: str | None = None  # abmil | choquet | xgboost
    disclaimer: str | None = None
    shap_decomposition: SHAPDecomposition | None = None
    choquet_shapley: ChoquetShapley | None = None
    evidence_source: str = "THESIS_INTERNAL"
    intended_use: str = "research / decision support (non-diagnostic)"
    evidence_uri: str | None = None


class MorphologicProfile(BaseModel):
    n_tiles_total: int = 0
    pct_lepidic: float = 0.0
    pct_acinar: float = 0.0
    pct_papillary: float = 0.0
    pct_micropapillary: float = 0.0
    pct_solid: float = 0.0
    pct_cribriform: float = 0.0


class XAIArtifactEntity(BaseModel):
    artifact_id: UUID
    artifact_type: str
    gene: str | None = None
    uri: str
    hash: str
    created_at: datetime


class ProcessImageRequest(BaseModel):
    model_profile: str = "ctranspath_fuzzyarcloss_v3"
    thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "lepidic": 0.55, "acinar": 0.55, "papillary": 0.55,
            "micropapillary": 0.55, "solid": 0.55,
            "EGFR": 0.60, "KRAS": 0.60, "TP53": 0.60,
        }
    )
    roi: dict[str, Any] | None = None


class ResultBundle(BaseModel):
    result_bundle_id: UUID
    case_id: UUID
    image_id: UUID
    job_id: UUID
    model_profile: str
    model_version: str
    thresholds: dict[str, float]
    pattern_results: list[PatternResult]
    pattern_composition: dict[str, float] = Field(default_factory=dict)
    predominant_pattern: str | None = None
    morphologic_profile: MorphologicProfile | None = None
    genetic_results: list[GeneticResult]
    xai_artifacts: list[XAIArtifactEntity] = Field(default_factory=list)
    evidence_source: str = "THESIS_INTERNAL"
    intended_use: str = "research / decision support (non-diagnostic)"
    created_at: datetime


# ── EHR ────────────────────────────────────────────────────────────────

class EHRIngestRequest(BaseModel):
    source: str = "paste"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class EHRDocument(BaseModel):
    ehr_id: UUID
    case_id: UUID
    version: int = 1
    source: str
    content_uri: str | None = None
    content_text: str | None = None
    checksum: str
    created_by: str | None = None
    created_at: datetime


class EHREntity(BaseModel):
    entity_id: UUID
    ehr_id: UUID
    text: str
    entity_type: str
    start: int
    end: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    section: str | None = None


class EHRMapping(BaseModel):
    mapping_id: UUID
    entity_id: UUID
    ontology: str
    iri: str
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    mapping_method: str


# ── Graph ──────────────────────────────────────────────────────────────

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    iri: str | None = None
    source: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    label: str
    type: str
    provenance: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphSnapshot(BaseModel):
    graph_snapshot_id: UUID
    case_id: UUID
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    ontology_versions: dict[str, str]
    created_at: datetime


# ── Explanation ────────────────────────────────────────────────────────

class ExplanationReport(BaseModel):
    report_id: UUID
    case_id: UUID
    result_bundle_id: UUID | None = None
    ehr_id: UUID | None = None
    graph_snapshot_id: UUID | None = None
    report_uri: str
    format: str = "html"
    guardrails_passed: bool = True
    guardrails_violations: list[str] = Field(default_factory=list)
    created_at: datetime


# ── Ontology ───────────────────────────────────────────────────────────

class OntologyVersion(BaseModel):
    ontology_version_id: UUID
    name: str
    version_tag: str
    source_uri: str
    hash: str
    is_active: bool = False
    imported_at: datetime


class UpdateProposal(BaseModel):
    proposal_id: UUID
    targets: list[str]
    mode: str
    status: ProposalStatus = ProposalStatus.DRAFT
    diff_report_uri: str | None = None
    impact: dict[str, Any] = Field(default_factory=dict)
    reasoner_report_uri: str | None = None
    created_by: str | None = None
    approved_by: str | None = None
    created_at: datetime
    published_at: datetime | None = None


# ── Audit ──────────────────────────────────────────────────────────────

class AuditEvent(BaseModel):
    event_id: UUID
    timestamp: datetime
    user_id: str | None = None
    case_id: UUID | None = None
    entity_type: str
    entity_id: str
    action: str
    status: str = "SUCCESS"
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
