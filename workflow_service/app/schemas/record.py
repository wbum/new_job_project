from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class RecordCreate(BaseModel):
    subject: str = Field(..., example="Example subject")
    metrics: Dict[str, float]
    metadata: Optional[Dict[str, Any]] = None

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
