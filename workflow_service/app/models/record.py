import enum
import uuid
from sqlalchemy import Column, String, DateTime, Float, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from ..database import Base

class StatusEnum(str, enum.Enum):
    pending = "pending"
    processed = "processed"
    failed = "failed"

class Record(Base):
    __tablename__ = "records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payload = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default=StatusEnum.pending.value)
    classification = Column(String, nullable=True)
    score = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
