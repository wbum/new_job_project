from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    source: str = Field(..., example="api")
    category: str = Field(..., example="attendance")
    payload: Dict[str, Any] = Field(..., example={"name": "Alice", "priority": 3})


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


class RecordResponse(BaseModel):
    id: str
    status: str


class RecordDetail(BaseModel):
    id: str
    payload: Dict[str, Any]
    status: str
    classification: Optional[str] = None
    score: Optional[float] = None
    error: Optional[str] = None
