"""API Gateway configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    service_name: str = "api-gateway"
    version: str = "0.1.0"
    log_level: str = "INFO"

    # Auth
    keycloak_url: str = "http://keycloak:8080"
    keycloak_realm: str = "oncology"
    jwks_url: str = "http://keycloak:8080/realms/oncology/protocol/openid-connect/certs"

    # Downstream services
    case_service_url: str = "http://case-service:8001"
    image_service_url: str = "http://image-service:8002"
    inference_service_url: str = "http://inference-service:8003"
    ehr_service_url: str = "http://ehr-service:8004"
    graph_service_url: str = "http://graph-service:8005"
    ontology_admin_service_url: str = "http://ontology-admin-service:8006"
    audit_service_url: str = "http://audit-service:8007"

    # Observability
    otel_exporter_otlp_endpoint: str | None = None

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
