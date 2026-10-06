from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EmploymentType = Literal["salaried", "self_employed", "unemployed", "student", "retired"]


class ApplicationCreate(BaseModel):
    amount_requested: Decimal = Field(gt=0, le=100_000_000, decimal_places=2)
    term_months: int = Field(ge=3, le=360)
    purpose: str = Field(min_length=2, max_length=100)
    declared_monthly_income: Decimal = Field(ge=0, le=100_000_000, decimal_places=2)
    employment_type: EmploymentType
    employment_years: float = Field(ge=0, le=60)


class ApplicationUpdate(BaseModel):
    """All fields optional: send only what changed."""

    amount_requested: Decimal | None = Field(default=None, gt=0, le=100_000_000, decimal_places=2)
    term_months: int | None = Field(default=None, ge=3, le=360)
    purpose: str | None = Field(default=None, min_length=2, max_length=100)
    declared_monthly_income: Decimal | None = Field(default=None, ge=0, le=100_000_000, decimal_places=2)
    employment_type: EmploymentType | None = None
    employment_years: float | None = Field(default=None, ge=0, le=60)


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    amount_requested: Decimal
    term_months: int
    purpose: str
    declared_monthly_income: Decimal
    employment_type: str
    employment_years: float
    status: str
    created_at: datetime
    updated_at: datetime