from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EmploymentType = Literal["salaried", "self_employed", "unemployed", "student", "retired"]
Education = Literal["lower_secondary", "secondary", "incomplete_higher", "higher", "academic_degree"]
FamilyStatus = Literal["single", "married", "civil_marriage", "separated", "widow"]
HousingType = Literal["owned", "rented", "with_parents", "municipal", "office", "co_op"]


def _check_age(value: date | None) -> date | None:
    if value is None:
        return value
    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if not 18 <= age <= 100:
        raise ValueError("Applicant must be between 18 and 100 years old")
    return value


class ApplicationCreate(BaseModel):
    amount_requested: Decimal = Field(gt=0, le=100_000_000, decimal_places=2)
    term_months: int = Field(ge=3, le=360)
    purpose: str = Field(min_length=2, max_length=100)
    declared_monthly_income: Decimal = Field(ge=0, le=100_000_000, decimal_places=2)
    employment_type: EmploymentType
    employment_years: float = Field(ge=0, le=60)
    date_of_birth: date
    children: int = Field(ge=0, le=20)
    family_members: int = Field(ge=1, le=30)
    owns_car: bool
    owns_home: bool
    education: Education
    family_status: FamilyStatus
    housing_type: HousingType

    _age = field_validator("date_of_birth")(_check_age)


class ApplicationUpdate(BaseModel):
    """All fields optional: send only what changed."""

    amount_requested: Decimal | None = Field(default=None, gt=0, le=100_000_000, decimal_places=2)
    term_months: int | None = Field(default=None, ge=3, le=360)
    purpose: str | None = Field(default=None, min_length=2, max_length=100)
    declared_monthly_income: Decimal | None = Field(default=None, ge=0, le=100_000_000, decimal_places=2)
    employment_type: EmploymentType | None = None
    employment_years: float | None = Field(default=None, ge=0, le=60)
    date_of_birth: date | None = None
    children: int | None = Field(default=None, ge=0, le=20)
    family_members: int | None = Field(default=None, ge=1, le=30)
    owns_car: bool | None = None
    owns_home: bool | None = None
    education: Education | None = None
    family_status: FamilyStatus | None = None
    housing_type: HousingType | None = None

    _age = field_validator("date_of_birth")(_check_age)

    @field_validator("*", mode="before")
    @classmethod
    def not_null(cls, value):
        # Runs only for fields the client sent: leaving a field out keeps it, sending null is an error.
        if value is None:
            raise ValueError("cannot be null; leave the field out to keep its current value")
        return value


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
    date_of_birth: date | None
    children: int | None
    family_members: int | None
    owns_car: bool | None
    owns_home: bool | None
    education: str | None
    family_status: str | None
    housing_type: str | None
    status: str
    created_at: datetime
    updated_at: datetime