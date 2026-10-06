from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.admin.schemas import AuditLogOut, StatsOut, ThresholdsIn, ThresholdsOut
from app.applications.models import Application
from app.applications.status import Status
from app.auth.models import User
from app.auth.security import require_roles
from app.core.db import get_db
from app.decisions.models import AuditLog, Decision
from app.decisions.service import get_thresholds, save_thresholds
from app.scoring.models import CreditScore

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_roles("admin"))])


@router.get("/thresholds", response_model=ThresholdsOut)
def read_thresholds(db: Session = Depends(get_db)):
    return get_thresholds(db)


@router.put("/thresholds", response_model=ThresholdsOut)
def update_thresholds(data: ThresholdsIn, db: Session = Depends(get_db),
                      admin: User = Depends(require_roles("admin"))):
    """Takes effect for the next decision. Past decisions keep the thresholds they used (see the audit log)."""
    result = save_thresholds(db, data.model_dump(), admin_id=admin.id)
    db.commit()
    return result


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    db: Session = Depends(get_db),
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    actor_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """Newest first. Read-only: there is no endpoint that changes or deletes audit rows."""
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.where(AuditLog.entity_id == entity_id)
    if actor_id is not None:
        query = query.where(AuditLog.actor_id == actor_id)
    return db.scalars(query.order_by(AuditLog.id.desc()).limit(limit)).all()


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    by_status = dict(db.execute(select(Application.status, func.count()).group_by(Application.status)).all())

    decisions: dict[str, int] = {}
    rows = db.execute(select(Decision.outcome, Decision.decided_by.is_(None), func.count())
                      .group_by(Decision.outcome, Decision.decided_by.is_(None))).all()
    for outcome, automatic, count in rows:
        key = f"{outcome} ({'system' if automatic else 'underwriter'})"
        decisions[key] = decisions.get(key, 0) + count

    approved, rejected = by_status.get(Status.APPROVED, 0), by_status.get(Status.REJECTED, 0)
    average = db.scalar(select(func.avg(CreditScore.score)))
    return StatsOut(
        applications_by_status=by_status,
        decisions=decisions,
        approval_rate=round(approved / (approved + rejected), 3) if approved + rejected else None,
        average_score=round(float(average), 1) if average is not None else None,
        waiting_for_review=by_status.get(Status.MANUAL_REVIEW, 0),
    )