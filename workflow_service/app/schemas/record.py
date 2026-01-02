from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, root_validator, validator


class RecordCreate(BaseModel):
    source: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    payload: Dict[str, Any] = Field(...)

    @validator("source", "category")
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class RecordRead(BaseModel):
    id: str
    created_at: datetime
    status: str
    source: str
    category: str
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    classification: Optional[str] = None
    score: Optional[float] = None
    error: Optional[str] = None

    class Config:
        orm_mode = True


class RecordList(BaseModel):
    items: List[RecordRead]
    count: int
