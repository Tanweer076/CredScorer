from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CreditScore(Base):
    __tablename__ = "credit_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    pd: Mapped[float]
    score: Mapped[int]
    model_version: Mapped[str] = mapped_column(String(50))
    features: Mapped[dict] = mapped_column(JSONB)
    shap_reasons: Mapped[list] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())