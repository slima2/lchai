"""SQLAlchemy models for images."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from oncology_common.database import Base


class ImageDB(Base):
    __tablename__ = "images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(10), nullable=False, default="png")
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stain: Mapped[str | None] = mapped_column(String(100))
    magnification: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(String(2000))
    uploaded_by: Mapped[str | None] = mapped_column(String(255))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
