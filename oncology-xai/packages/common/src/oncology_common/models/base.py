"""Base Pydantic models and response schemas."""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel as PydanticBaseModel, ConfigDict, Field


class BaseModel(PydanticBaseModel):
    """Base model with common config."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
    )


T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Standard API response."""

    data: T
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response."""

    data: list[T]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False
    correlation_id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response (DERCAS 5.2)."""

    error_code: str = Field(..., alias="errorCode")
    message: str
    correlation_id: str | None = Field(None, alias="correlationId")
    details: dict[str, Any] | None = None

    model_config = ConfigDict(populate_by_name=True)


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    service: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
