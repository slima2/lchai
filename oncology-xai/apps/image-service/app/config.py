"""Image Service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "image-service"
    version: str = "0.1.0"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "oncology-xai"
    otel_exporter_otlp_endpoint: str | None = None

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
