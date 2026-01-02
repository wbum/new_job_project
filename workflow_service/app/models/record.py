from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Column, Index, String, DateTime, Text, Float
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Record(Base):
    __tablename__ = "records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)

    # Store JSON as text for sqlite. Endpoints/services will json.dumps / json.loads as needed.
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=True)

    # Convenience denormalized columns for tests/queries
    classification: Mapped[str] = mapped_column(String(20), nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=True)

    error: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_records_created_at", "created_at"),
        Index("ix_records_status", "status"),
        Index("ix_records_category", "category"),
    )
