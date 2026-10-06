from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount_requested: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    term_months: Mapped[int]
    purpose: Mapped[str] = mapped_column(String(100))
    declared_monthly_income: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    employment_type: Mapped[str] = mapped_column(String(30))
    employment_years: Mapped[float]
    # Added in Phase 4: extra details the scoring model uses.
    # Nullable in the database so older applications still load; required by the API for new ones.
    date_of_birth: Mapped[date | None]
    children: Mapped[int | None]
    family_members: Mapped[int | None]
    owns_car: Mapped[bool | None]
    owns_home: Mapped[bool | None]
    education: Mapped[str | None] = mapped_column(String(30))
    family_status: Mapped[str | None] = mapped_column(String(30))
    housing_type: Mapped[str | None] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED", index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())