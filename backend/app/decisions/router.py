from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.applications.service import get_application_for_user
from app.auth.models import User
from app.auth.security import get_current_user
from app.core.db import get_db
from app.decisions.schemas import DecisionOut
from app.decisions.service import latest_decision

router = APIRouter(tags=["decisions"])


@router.get("/applications/{application_id}/decision", response_model=DecisionOut)
def get_decision(application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    application = get_application_for_user(db, application_id, user)
    decision = latest_decision(db, application.id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No decision yet")
    return DecisionOut(application_id=application.id, outcome=decision.outcome, reason=decision.reason,
                       decided_by="system" if decision.decided_by is None else "underwriter",
                       created_at=decision.created_at)