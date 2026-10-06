"""Apply the decision rules to a scored application and record the result."""
import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.applications.models import Application
from app.applications.status import check_transition
from app.core.audit import audit
from app.core.config import settings
from app.decisions.engine import DEFAULT_THRESHOLDS, decide
from app.decisions.models import Decision, Setting
from app.scoring.models import CreditScore

log = logging.getLogger(__name__)
THRESHOLDS_KEY = "decision_thresholds"


def get_thresholds(db: Session) -> dict:
    """Thresholds from the settings table (set by an admin), else ml/artifacts/thresholds.json, else defaults."""
    row = db.get(Setting, THRESHOLDS_KEY)
    if row is not None:
        return {**DEFAULT_THRESHOLDS, **row.value, "source": "settings"}
    path = Path(settings.thresholds_path)
    if path.exists():
        data = json.loads(path.read_text())
        return {**DEFAULT_THRESHOLDS, "approve_min_score": data["approve_min_score"],
                "reject_max_score": data["reject_max_score"], "source": str(path)}
    log.warning("No thresholds found; using built-in defaults")
    return {**DEFAULT_THRESHOLDS, "source": "defaults"}


def decide_application(db: Session, application: Application, credit_score: CreditScore) -> Decision:
    """SCORED -> APPROVED / REJECTED / MANUAL_REVIEW. The caller commits."""
    thresholds = get_thresholds(db)
    features = credit_score.features
    emi_share = features["annuity"] / features["annual_income"]  # both are monthly amounts
    outcome, reasons = decide(credit_score.score, emi_share, thresholds)

    old = application.status
    application.status = check_transition(old, outcome)
    decision = Decision(application_id=application.id, outcome=outcome, decided_by=None, reason=" ".join(reasons))
    db.add(decision)
    db.flush()
    audit(db, actor_id=None, action="STATUS_CHANGE", entity_type="application", entity_id=application.id,
          before={"status": old}, after={"status": application.status})
    # Record the exact thresholds used, so the decision can be explained even after they change.
    audit(db, actor_id=None, action="AUTO_DECISION", entity_type="application", entity_id=application.id,
          after={"decision_id": decision.id, "outcome": outcome, "score": credit_score.score,
                 "credit_score_id": credit_score.id, "emi_share": round(emi_share, 4), "thresholds": thresholds})
    return decision


def latest_decision(db: Session, application_id: int) -> Decision | None:
    return db.scalars(select(Decision).where(Decision.application_id == application_id)
                      .order_by(Decision.id.desc()).limit(1)).first()