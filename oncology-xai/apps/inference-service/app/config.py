"""Inference Service configuration — v2.0."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "inference-service"
    version: str = "2.0.0"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"
    postgres_dsn_sync: str = "postgresql://oncology:oncology_secret@postgres:5432/oncology_xai"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    redis_url: str = "redis://redis:6379/0"

    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "oncology-xai"

    # Model — v1 backbone (CTransPath + FuzzyArcLoss pattern classifier)
    model_backend: str = "mock"  # mock | local | triton
    triton_url: str = "http://triton:8001"
    ctranspath_checkpoint: str = "/data/models/ctranspath.pth"
    fuzzyarc_checkpoint: str = "/data/models/fuzzyarcloss_v3_subcenters.pth"

    # Model — v1 legacy (XGBoost mutation, kept for backward compat)
    mutation_model_dir: str = "/data/models/mutation_xgboost/"

    # Model — v2 ABMIL + Choquet checkpoints
    v2_checkpoint_dir: str = "/data/checkpoints"
    use_choquet: bool = True
    v2_top_k_tiles: int = 200

    # v2 genes (expanded from v1's EGFR/KRAS/TP53)
    v2_genes: str = "TP53,EGFR,KRAS,STK11,KEAP1,RBM10"

    # Thresholds
    pattern_threshold: float = 0.55
    mutation_threshold: float = 0.60
    auroc_conclusive_threshold: float = 0.70

    # SHAP / XAI
    shap_enabled: bool = True
    shap_decomposition_enabled: bool = True

    otel_exporter_otlp_endpoint: str | None = None

    model_config = {"env_file": ".env", "case_sensitive": False}

    @property
    def genes_list(self) -> list[str]:
        return [g.strip() for g in self.v2_genes.split(",") if g.strip()]


settings = Settings()
