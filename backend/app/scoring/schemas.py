from datetime import datetime

from pydantic import BaseModel, Field


class Reason(BaseModel):
    feature: str
    impact: float
    direction: str
    text: str


class ScoreOut(BaseModel):
    application_id: int
    pd: float
    score: int
    band: str
    model_version: str
    reasons: list[Reason]
    recommendations: list[str]
    status: str
    created_at: datetime | None = None


class WhatIfIn(BaseModel):
    """Only send the values you want to try. Everything else stays as in the application."""

    monthly_income: float | None = Field(default=None, gt=0, le=100_000_000)
    amount_requested: float | None = Field(default=None, gt=0, le=100_000_000)
    term_months: int | None = Field(default=None, ge=3, le=360)
    employment_years: float | None = Field(default=None, ge=0, le=60)


class ScenarioOut(BaseModel):
    pd: float
    score: int
    band: str
    monthly_emi: float
    reasons: list[Reason]


class WhatIfOut(BaseModel):
    application_id: int
    changes: dict
    current: ScenarioOut
    scenario: ScenarioOut
    score_change: int