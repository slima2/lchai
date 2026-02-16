"""Inference Service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "inference-service"
    version: str = "0.1.0"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"
    postgres_dsn_sync: str = "postgresql://oncology:oncology_secret@postgres:5432/oncology_xai"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    redis_url: str = "redis://redis:6379/0"

    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "oncology-xai"

    # Model
    model_backend: str = "mock"  # mock | local | triton
    triton_url: str = "http://triton:8001"
    ctranspath_checkpoint: str = "/data/models/ctranspath.pth"
    fuzzyarc_checkpoint: str = "/data/models/fuzzyarcloss_v3_subcenters.pth"
    mutation_model_dir: str = "/data/models/mutation_xgboost/"

    # Thresholds
    pattern_threshold: float = 0.55
    mutation_threshold: float = 0.60

    # SHAP
    shap_enabled: bool = True

    otel_exporter_otlp_endpoint: str | None = None

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
