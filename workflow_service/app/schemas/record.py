from typing import Any, Dict, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class RecordCreate(BaseModel):
    source: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1)
    payload: Dict[str, Any]

    @field_validator('source')
    @classmethod
    def source_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('source must not be empty')
        return v

    @field_validator('category')
    @classmethod
    def category_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('category must not be empty')
        return v


class RecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    created_at: datetime
    status: Literal['pending', 'processed', 'failed']
    source: str
    category: str
    payload: Dict[str, Any]


class RecordList(BaseModel):
    records: List[RecordRead]
    total: int
