from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    source: str = Field(..., example="api")
    category: str = Field(..., example="attendance")
    payload: dict[str, Any] = Field(..., example={"name": "Alice", "priority": 3})


class RecordRead(BaseModel):
    id: str
    created_at: datetime
    status: str
    source: str
    category: str
    payload: dict[str, Any]
    result: dict[str, Any] | None = None
    classification: str | None = None
    score: float | None = None
    error: str | None = None

    class Config:
        orm_mode = True
