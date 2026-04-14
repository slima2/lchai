"""Active Learning Service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "active-learning-service"
    version: str = "0.1.0"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"
    postgres_dsn_sync: str = "postgresql://oncology:oncology_secret@postgres:5432/oncology_xai"

    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "oncology-xai"

    inference_service_url: str = "http://inference-service:8003"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"

    delta_train_epochs: int = 10
    delta_train_lr: float = 1e-5
    delta_train_buffer_ratio: float = 0.3

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
