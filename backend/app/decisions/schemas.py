from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.applications.schemas import ApplicationOut
from app.documents.schemas import ExtractionOut
from app.scoring.schemas import Reason


class DecisionOut(BaseModel):
    application_id: int
    outcome: str
    reason: str
    decided_by: str  # "system" for automatic decisions, "underwriter" for manual ones
    created_at: datetime


class QueueItem(BaseModel):
    application_id: int
    applicant_name: str
    amount_requested: Decimal
    declared_monthly_income: Decimal
    score: int | None
    band: str | None
    pd: float | None
    review_reason: str
    waiting_since: datetime


class ScoreSummary(BaseModel):
    score: int
    pd: float
    band: str
    model_version: str
    reasons: list[Reason]  # the 5 factors that moved the risk most


class DocumentReview(BaseModel):
    id: int
    doc_type: str
    extraction_status: str
    extraction: ExtractionOut | None


class ReviewDetail(BaseModel):
    application: ApplicationOut
    applicant_name: str
    applicant_email: str
    score: ScoreSummary | None
    documents: list[DocumentReview]
    decisions: list[DecisionOut]


class ManualDecisionIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # so spaces don't count towards the 10 characters

    outcome: Literal["APPROVED", "REJECTED"]
    reason: str = Field(min_length=10, max_length=2000, description="Why; shown to auditors. At least 10 characters.")