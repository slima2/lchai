-- ============================================================
-- LCHAI v1.2 — PostgreSQL initialisation
-- 19 tables + extensions (matches SQLAlchemy ORM models)
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─── case-service ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS patients (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    external_id     VARCHAR(255)  UNIQUE,
    demographics    JSONB         DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_patients_external_id ON patients(external_id);

CREATE TABLE IF NOT EXISTS cases (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    patient_id      VARCHAR(36)   NOT NULL REFERENCES patients(id),
    status          VARCHAR(50)   NOT NULL DEFAULT 'CREATED',
    tags            JSONB         DEFAULT '[]'::jsonb,
    metadata        JSONB         DEFAULT '{}'::jsonb,
    created_by      VARCHAR(255),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_cases_patient_id ON cases(patient_id);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);

-- ─── image-service ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS images (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    case_id         VARCHAR(36)   NOT NULL,
    format          VARCHAR(10)   NOT NULL DEFAULT 'png',
    storage_uri     VARCHAR(1024) NOT NULL,
    checksum        VARCHAR(64)   NOT NULL,
    size_bytes      BIGINT        NOT NULL,
    stain           VARCHAR(100),
    magnification   VARCHAR(50),
    notes           VARCHAR(2000),
    uploaded_by     VARCHAR(255),
    uploaded_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_images_case_id ON images(case_id);

-- ─── inference-service ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS ml_jobs (
    id               VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    case_id          VARCHAR(36),
    image_id         VARCHAR(36)   NOT NULL,
    job_type         VARCHAR(50)   NOT NULL DEFAULT 'IMAGE_INFERENCE',
    status           VARCHAR(20)   NOT NULL DEFAULT 'PENDING',
    progress         DOUBLE PRECISION DEFAULT 0.0,
    celery_task_id   VARCHAR(255),
    result_bundle_id VARCHAR(36),
    error_code       VARCHAR(100),
    error_detail     TEXT,
    started_at       TIMESTAMPTZ,
    ended_at         TIMESTAMPTZ,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ml_jobs_image_id ON ml_jobs(image_id);
CREATE INDEX IF NOT EXISTS idx_ml_jobs_case_id ON ml_jobs(case_id);
CREATE INDEX IF NOT EXISTS idx_ml_jobs_status ON ml_jobs(status);

CREATE TABLE IF NOT EXISTS result_bundles (
    id                   VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    case_id              VARCHAR(36)   NOT NULL,
    image_id             VARCHAR(36)   NOT NULL,
    job_id               VARCHAR(36)   NOT NULL REFERENCES ml_jobs(id),
    model_profile        VARCHAR(100)  NOT NULL,
    model_version        VARCHAR(100)  NOT NULL,
    thresholds           JSONB         DEFAULT '{}'::jsonb,
    pattern_composition  JSONB         DEFAULT '{}'::jsonb,
    predominant_pattern  VARCHAR(50),
    summary_json         JSONB,
    evidence_source      VARCHAR(50)   NOT NULL DEFAULT 'THESIS_INTERNAL',
    intended_use         VARCHAR(200)  NOT NULL DEFAULT 'research / decision support (non-diagnostic)',
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_result_bundles_case_id ON result_bundles(case_id);
CREATE INDEX IF NOT EXISTS idx_result_bundles_image_id ON result_bundles(image_id);

CREATE TABLE IF NOT EXISTS pattern_results (
    id               VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    result_bundle_id VARCHAR(36)   NOT NULL REFERENCES result_bundles(id) ON DELETE CASCADE,
    pattern          VARCHAR(50)   NOT NULL,
    score            DOUBLE PRECISION NOT NULL,
    percentage       DOUBLE PRECISION DEFAULT 0.0,
    is_conclusive    BOOLEAN       DEFAULT TRUE,
    overlay_uri      VARCHAR(1024),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pattern_results_bundle ON pattern_results(result_bundle_id);

CREATE TABLE IF NOT EXISTS genetic_results (
    id               VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    result_bundle_id VARCHAR(36)   NOT NULL REFERENCES result_bundles(id) ON DELETE CASCADE,
    mutation         VARCHAR(20)   NOT NULL,
    score            DOUBLE PRECISION NOT NULL,
    status           VARCHAR(20)   NOT NULL,
    evidence_source  VARCHAR(50)   DEFAULT 'THESIS_INTERNAL',
    intended_use     VARCHAR(200)  DEFAULT 'research / decision support (non-diagnostic)',
    evidence_uri     VARCHAR(1024),
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_genetic_results_bundle ON genetic_results(result_bundle_id);

CREATE TABLE IF NOT EXISTS xai_artifacts (
    id               VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    result_bundle_id VARCHAR(36)   NOT NULL REFERENCES result_bundles(id) ON DELETE CASCADE,
    artifact_type    VARCHAR(100)  NOT NULL,
    gene             VARCHAR(20),
    uri              VARCHAR(1024) NOT NULL,
    hash             VARCHAR(64)   NOT NULL,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_xai_artifacts_bundle ON xai_artifacts(result_bundle_id);

CREATE TABLE IF NOT EXISTS morphologic_profiles (
    id               VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    result_bundle_id VARCHAR(36)   NOT NULL UNIQUE REFERENCES result_bundles(id) ON DELETE CASCADE,
    n_tiles_total    INTEGER       DEFAULT 0,
    pct_lepidic      DOUBLE PRECISION DEFAULT 0.0,
    pct_acinar       DOUBLE PRECISION DEFAULT 0.0,
    pct_papillary    DOUBLE PRECISION DEFAULT 0.0,
    pct_micropapillary DOUBLE PRECISION DEFAULT 0.0,
    pct_solid        DOUBLE PRECISION DEFAULT 0.0,
    pct_mucinous     DOUBLE PRECISION DEFAULT 0.0,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- ─── ehr-service ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS ehr_documents (
    id            VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    case_id       VARCHAR(36)   NOT NULL,
    version       INTEGER       DEFAULT 1,
    source        VARCHAR(50)   DEFAULT 'paste',
    content_text  TEXT,
    content_uri   VARCHAR(1024),
    checksum      VARCHAR(64)   NOT NULL,
    created_by    VARCHAR(255),
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ehr_documents_case_id ON ehr_documents(case_id);

CREATE TABLE IF NOT EXISTS ehr_entities (
    id            VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    ehr_id        VARCHAR(36)   NOT NULL REFERENCES ehr_documents(id),
    text          VARCHAR(500)  NOT NULL,
    entity_type   VARCHAR(50)   NOT NULL,
    start         INTEGER       NOT NULL,
    "end"         INTEGER       NOT NULL,
    confidence    DOUBLE PRECISION DEFAULT 1.0,
    section       VARCHAR(100),
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ehr_entities_ehr_id ON ehr_entities(ehr_id);

CREATE TABLE IF NOT EXISTS ehr_mappings (
    id             VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    entity_id      VARCHAR(36)   NOT NULL REFERENCES ehr_entities(id),
    ontology       VARCHAR(20)   NOT NULL,
    iri            VARCHAR(500)  NOT NULL,
    label          VARCHAR(500)  NOT NULL,
    confidence     DOUBLE PRECISION DEFAULT 1.0,
    mapping_method VARCHAR(100)  DEFAULT 'keyword_lookup',
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ehr_mappings_entity_id ON ehr_mappings(entity_id);

-- ─── graph-service ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS case_graph_snapshots (
    id                    VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    case_id               VARCHAR(36)   NOT NULL,
    triplestore_graph_iri VARCHAR(500),
    nodes_json            JSONB         DEFAULT '[]'::jsonb,
    edges_json            JSONB         DEFAULT '[]'::jsonb,
    ontology_versions     JSONB         DEFAULT '{}'::jsonb,
    layout_json           JSONB,
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_graph_snapshots_case_id ON case_graph_snapshots(case_id);

-- ─── ontology-admin-service ──────────────────────────────────

CREATE TABLE IF NOT EXISTS ontology_versions (
    id          VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name        VARCHAR(50)   NOT NULL,
    version_tag VARCHAR(100)  NOT NULL,
    source_uri  VARCHAR(1024) NOT NULL,
    hash        VARCHAR(64)   NOT NULL,
    is_active   BOOLEAN       DEFAULT FALSE,
    imported_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ontology_versions_name ON ontology_versions(name);
CREATE INDEX IF NOT EXISTS idx_ontology_versions_active ON ontology_versions(is_active);

CREATE TABLE IF NOT EXISTS ontology_update_proposals (
    id                   VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    targets              JSONB         DEFAULT '[]'::jsonb,
    mode                 VARCHAR(20)   DEFAULT 'offline',
    status               VARCHAR(30)   NOT NULL DEFAULT 'DRAFT',
    diff_report_uri      VARCHAR(1024),
    impact               JSONB,
    reasoner_report_uri  VARCHAR(1024),
    validation_results   JSONB,
    created_by           VARCHAR(255),
    approved_by          VARCHAR(255),
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT now(),
    published_at         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON ontology_update_proposals(status);

CREATE TABLE IF NOT EXISTS explanation_reports (
    id                    VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    case_id               VARCHAR(36)   NOT NULL,
    result_bundle_id      VARCHAR(36),
    ehr_id                VARCHAR(36),
    graph_snapshot_id     VARCHAR(36),
    report_uri            VARCHAR(1024) NOT NULL,
    format                VARCHAR(20)   DEFAULT 'html',
    guardrails_passed     BOOLEAN       DEFAULT TRUE,
    guardrails_violations JSONB,
    created_at            TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_explanation_reports_case_id ON explanation_reports(case_id);

-- ─── deep-search & KG versioning ────────────────────────────

CREATE TABLE IF NOT EXISTS kg_snapshots (
    id           VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    version_tag  VARCHAR(100)  NOT NULL,
    description  TEXT,
    nodes_count  INTEGER       DEFAULT 0,
    edges_count  INTEGER       DEFAULT 0,
    snapshot_uri VARCHAR(1024),
    format       VARCHAR(20)   DEFAULT 'jsonld',
    sources      JSONB,
    created_by   VARCHAR(255),
    created_at   TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kg_snapshots_version ON kg_snapshots(version_tag);

CREATE TABLE IF NOT EXISTS kg_changelog (
    id            VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    snapshot_id   VARCHAR(36)   NOT NULL REFERENCES kg_snapshots(id) ON DELETE CASCADE,
    action        VARCHAR(20)   NOT NULL,
    entity_type   VARCHAR(30)   NOT NULL,
    entity_id     VARCHAR(200)  NOT NULL,
    detail        TEXT,
    provenance    VARCHAR(200),
    created_at    TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_kg_changelog_snapshot ON kg_changelog(snapshot_id);

CREATE TABLE IF NOT EXISTS deep_search_jobs (
    id                   VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    status               VARCHAR(30)   NOT NULL DEFAULT 'PENDING',
    source_text          TEXT,
    source_type          VARCHAR(30)   DEFAULT 'text',
    extracted_relations  JSONB,
    linked_entities      JSONB,
    validation_result    JSONB,
    snapshot_id          VARCHAR(36),
    error                TEXT,
    created_by           VARCHAR(255),
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_deep_search_jobs_status ON deep_search_jobs(status);

-- ─── audit-service ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_events (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    event_id        VARCHAR(64)   UNIQUE NOT NULL,
    event_type      VARCHAR(100)  NOT NULL,
    timestamp       TIMESTAMPTZ   NOT NULL,
    correlation_id  VARCHAR(64),
    user_id         VARCHAR(255),
    case_id         VARCHAR(36),
    entity_type     VARCHAR(100)  NOT NULL,
    entity_id       VARCHAR(255)  NOT NULL,
    action          VARCHAR(100)  NOT NULL,
    status          VARCHAR(50)   DEFAULT 'SUCCESS',
    details         JSONB,
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_events_event_id ON audit_events(event_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_events_correlation ON audit_events(correlation_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_case_id ON audit_events(case_id);
