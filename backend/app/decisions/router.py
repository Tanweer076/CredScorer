from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.applications.models import Application
from app.applications.schemas import ApplicationOut
from app.applications.service import get_application_for_user
from app.applications.status import Status
from app.auth.models import User
from app.auth.security import get_current_user, require_roles
from app.core.db import get_db
from app.decisions.models import Decision
from app.decisions.schemas import DecisionOut, DocumentReview, ManualDecisionIn, QueueItem, ReviewDetail, ScoreSummary
from app.decisions.service import latest_decision, manual_decision
from app.documents.models import Document, ExtractedData
from app.documents.schemas import ExtractionOut
from app.documents.validation import PASS_CONFIDENCE
from app.scoring.models import CreditScore
from app.scoring.reasons import score_band

router = APIRouter(tags=["decisions"])
underwriter = APIRouter(prefix="/underwriter", tags=["underwriter"],
                        dependencies=[Depends(require_roles("underwriter", "admin"))])


def _decision_out(decision: Decision) -> DecisionOut:
    return DecisionOut(application_id=decision.application_id, outcome=decision.outcome, reason=decision.reason,
                       decided_by="system" if decision.decided_by is None else "underwriter",
                       created_at=decision.created_at)


def _latest_score(db: Session, application_id: int) -> CreditScore | None:
    return db.scalars(select(CreditScore).where(CreditScore.application_id == application_id)
                      .order_by(CreditScore.id.desc()).limit(1)).first()


@router.get("/applications/{application_id}/decision", response_model=DecisionOut)
def get_decision(application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    application = get_application_for_user(db, application_id, user)
    decision = latest_decision(db, application.id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No decision yet")
    return _decision_out(decision)


@underwriter.get("/queue", response_model=list[QueueItem])
def review_queue(db: Session = Depends(get_db)):
    """Applications waiting for a person, oldest first."""
    applications = db.scalars(select(Application).where(Application.status == Status.MANUAL_REVIEW)
                              .order_by(Application.updated_at, Application.id)).all()
    items = []
    for application in applications:
        score = _latest_score(db, application.id)
        decision = latest_decision(db, application.id)
        items.append(QueueItem(
            application_id=application.id, applicant_name=db.get(User, application.user_id).full_name,
            amount_requested=application.amount_requested,
            declared_monthly_income=application.declared_monthly_income,
            score=score.score if score else None, band=score_band(score.score) if score else None,
            pd=score.pd if score else None,
            review_reason=decision.reason if decision else "",
            waiting_since=decision.created_at if decision else application.updated_at,
        ))
    return items


@underwriter.get("/applications/{application_id}", response_model=ReviewDetail)
def review_detail(application_id: int, db: Session = Depends(get_db)):
    """Everything an underwriter needs on one page: form, score and reasons, documents, past decisions."""
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    applicant = db.get(User, application.user_id)
    score = _latest_score(db, application.id)

    documents = []
    for document in db.scalars(select(Document).where(Document.application_id == application.id)
                               .order_by(Document.id)).all():
        data = db.scalar(select(ExtractedData).where(ExtractedData.document_id == document.id))
        extraction = None
        if data is not None:
            extraction = ExtractionOut(
                document_id=document.id, doc_type=document.doc_type, extraction_status=document.extraction_status,
                confidence=data.confidence,
                passed=document.extraction_status == "DONE" and data.confidence >= PASS_CONFIDENCE,
                issues=data.issues, extracted=data.payload, model_name=data.model_name, created_at=data.created_at)
        documents.append(DocumentReview(id=document.id, doc_type=document.doc_type,
                                        extraction_status=document.extraction_status, extraction=extraction))

    decisions = db.scalars(select(Decision).where(Decision.application_id == application.id)
                           .order_by(Decision.id)).all()
    return ReviewDetail(
        application=ApplicationOut.model_validate(application),
        applicant_name=applicant.full_name, applicant_email=applicant.email,
        score=ScoreSummary(score=score.score, pd=score.pd, band=score_band(score.score),
                           model_version=score.model_version, reasons=score.shap_reasons[:5]) if score else None,
        documents=documents,
        decisions=[_decision_out(d) for d in decisions],
    )


@underwriter.post("/applications/{application_id}/decision", response_model=DecisionOut)
def decide_manually(application_id: int, data: ManualDecisionIn, db: Session = Depends(get_db),
                    user: User = Depends(require_roles("underwriter", "admin"))):
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if application.status != Status.MANUAL_REVIEW:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Application is {application.status}; only MANUAL_REVIEW can be decided manually")
    decision = manual_decision(db, application, data.outcome, data.reason.strip(), underwriter_id=user.id)
    db.commit()
    db.refresh(decision)
    return _decision_out(decision)