from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.applications.models import Application
from app.applications.schemas import ApplicationCreate, ApplicationOut, ApplicationUpdate
from app.applications.service import get_application_for_user, snapshot
from app.applications.status import Status
from app.auth.models import User
from app.auth.security import get_current_user, require_roles
from app.core.audit import audit
from app.core.db import get_db

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(
    data: ApplicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("applicant")),
):
    application = Application(**data.model_dump(), user_id=user.id, status=Status.SUBMITTED)
    db.add(application)
    db.flush()  # assigns application.id so the audit row can reference it
    audit(db, actor_id=user.id, action="APPLICATION_CREATED", entity_type="application",
          entity_id=application.id, after=snapshot(application))
    db.commit()
    db.refresh(application)
    return application


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    status_filter: Status | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(Application)
    if user.role == "applicant":
        query = query.where(Application.user_id == user.id)
    if status_filter:
        query = query.where(Application.status == status_filter)
    return db.scalars(query.order_by(Application.created_at.desc())).all()


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_application_for_user(db, application_id, user)


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int,
    data: ApplicationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("applicant")),
):
    application = get_application_for_user(db, application_id, user)
    if application.status != Status.SUBMITTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Application can only be edited while SUBMITTED")
    before = snapshot(application)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    db.flush()
    db.refresh(application)  # reload so amounts come back rounded the way the database stores them
    audit(db, actor_id=user.id, action="APPLICATION_UPDATED", entity_type="application",
          entity_id=application.id, before=before, after=snapshot(application))
    db.commit()
    db.refresh(application)
    return application