from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import Column, String, DateTime, Enum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base  # adjust if Base is defined elsewhere


class StatusEnum(PyEnum):
    pending = "pending"
    processed = "processed"
    failed = "failed"


class Record(Base):
    __tablename__ = "records"

    # primary key as uuid string
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default=StatusEnum.pending.value, nullable=False)

    # fields required by the API/schema
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)

    # free-form JSON payload
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # optional outcome fields
    classification: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    score: Mapped[Optional[float]] = mapped_column("score", String(64), nullable=True)  # change to Float if desired
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Record id={self.id} status={self.status} source={self.source} category={self.category}>"
