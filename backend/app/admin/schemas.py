from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ThresholdsIn(BaseModel):
    approve_min_score: int = Field(ge=0, le=1000)
    reject_max_score: int = Field(ge=0, le=1000)
    max_emi_share: float = Field(default=0.5, gt=0, le=1)

    @model_validator(mode="after")
    def reject_below_approve(self):
        if self.reject_max_score > self.approve_min_score:
            raise ValueError("reject_max_score must not be higher than approve_min_score")
        return self


class ThresholdsOut(BaseModel):
    approve_min_score: int
    reject_max_score: int
    max_emi_share: float
    source: str  # "settings", the thresholds.json path, or "defaults"


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    before: dict | None
    after: dict | None
    created_at: datetime


class StatsOut(BaseModel):
    applications_by_status: dict[str, int]
    decisions: dict[str, int]  # e.g. {"APPROVED (system)": 12, "REJECTED (underwriter)": 2}
    approval_rate: float | None  # approved / all decided applications
    average_score: float | None
    waiting_for_review: int