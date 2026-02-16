"""Audit Service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "audit-service"
    version: str = "0.1.0"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"
    postgres_dsn_sync: str = "postgresql://oncology:oncology_secret@postgres:5432/oncology_xai"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    otel_exporter_otlp_endpoint: str | None = None

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
