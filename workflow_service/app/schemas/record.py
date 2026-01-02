from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class RecordCreate(BaseModel):
    source: str = Field(..., example="api")
    category: str = Field(..., example="attendance")
    payload: Dict[str, Any]

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
