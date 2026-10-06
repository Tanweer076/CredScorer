"""Scoring logic shared by the API (POST /score) and the background worker."""
from sqlalchemy.orm import Session

from app.applications.models import Application
from app.applications.status import Status, check_transition
from app.auth.models import User
from app.core.audit import audit
from app.scoring.bureau import get_bureau_record
from app.scoring.features import build_feature_row
from app.scoring.model import Scorer
from app.scoring.models import CreditScore
from app.scoring.reasons import top_reasons


def features_for(db: Session, application: Application, overrides: dict | None = None) -> dict:
    """Feature row for this application. Raises MissingApplicationData if form fields are missing."""
    owner = db.get(User, application.user_id)
    return build_feature_row(application, get_bureau_record(db, owner), overrides)


def score_and_save(db: Session, application: Application, scorer: Scorer, actor_id: int | None) -> tuple[CreditScore, dict]:
    """Score the application and store the result. The caller commits.

    actor_id is None when the system scores automatically (after documents are verified).
    """
    row = features_for(db, application)
    result = scorer.score(row)
    # Store every feature's impact (sorted, biggest first) so underwriters can see the full picture later.
    all_reasons = top_reasons(result["shap"], row, n=len(result["shap"]))
    credit_score = CreditScore(application_id=application.id, pd=result["pd"], score=result["score"],
                               model_version=scorer.version, features=row, shap_reasons=all_reasons)
    db.add(credit_score)

    # Only a verified application moves forward in the status flow. Before documents are
    # verified, the score is stored as a preliminary result.
    if application.status == Status.DOCS_VERIFIED:
        old = application.status
        application.status = check_transition(old, Status.SCORED)
        audit(db, actor_id=actor_id, action="STATUS_CHANGE", entity_type="application",
              entity_id=application.id, before={"status": old}, after={"status": application.status})
    db.flush()
    audit(db, actor_id=actor_id, action="APPLICATION_SCORED", entity_type="application", entity_id=application.id,
          after={"credit_score_id": credit_score.id, "pd": result["pd"], "score": result["score"],
                 "model_version": scorer.version})
    return credit_score, result