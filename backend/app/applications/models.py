from datetime import datetime
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
    status: Mapped[str] = mapped_column(String(20), default="SUBMITTED", index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())