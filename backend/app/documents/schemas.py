from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    doc_type: str
    mime_type: str
    extraction_status: str
    uploaded_at: datetime


class ExtractionOut(BaseModel):
    document_id: int
    doc_type: str
    extraction_status: str
    confidence: float
    passed: bool
    issues: list[str]
    extracted: dict
    model_name: str
    created_at: datetime