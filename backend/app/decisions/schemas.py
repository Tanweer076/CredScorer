from datetime import datetime

from pydantic import BaseModel


class DecisionOut(BaseModel):
    application_id: int
    outcome: str
    reason: str
    decided_by: str  # "system" for automatic decisions, "underwriter" for manual ones
    created_at: datetime