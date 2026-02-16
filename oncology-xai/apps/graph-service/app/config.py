"""Graph Service configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "graph-service"
    version: str = "0.1.0"
    log_level: str = "INFO"

    postgres_dsn: str = "postgresql+asyncpg://oncology:oncology_secret@postgres:5432/oncology_xai"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    fuseki_url: str = "http://fuseki:3030"
    fuseki_dataset: str = "oncology"
    otel_exporter_otlp_endpoint: str | None = None

    # Ontology OWL paths (real ontologies for graph when Fuseki has no case data)
    ncit_owl_path: str = ""
    mondo_owl_path: str = ""

    # LLM for graph explanation (mock | openai | anthropic)
    llm_provider: str = "mock"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
