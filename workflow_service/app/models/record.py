import uuid
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.types import JSON
from sqlalchemy.sql import func
from app.database import Base


class Record(Base):
    __tablename__ = "records"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(String, nullable=False, default='pending')
    source = Column(String, nullable=False)
    category = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)

    __table_args__ = (
        Index('idx_records_created_at', 'created_at'),
        Index('idx_records_status', 'status'),
        Index('idx_records_category', 'category'),
    )
