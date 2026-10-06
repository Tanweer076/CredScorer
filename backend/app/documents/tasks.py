"""Background jobs, run by the Celery worker (not by the API)."""
import logging

from app.applications.models import Application
from app.core.celery_app import celery
from app.core.config import settings
from app.core.db import SessionLocal
from app.documents.models import Document
from app.documents.service import process_document, save_failure
from app.scoring.features import MissingApplicationData
from app.scoring.model import Scorer
from app.scoring.service import score_and_save

log = logging.getLogger(__name__)
_scorer: Scorer | None = None


def get_scorer() -> Scorer | None:
    # The worker is a separate process from the API, so it loads its own copy of the model, once.
    global _scorer
    if _scorer is None:
        _scorer = Scorer.load(settings.model_path)
    return _scorer


@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def extract_document(self, document_id: int) -> str:
    with SessionLocal() as db:
        try:
            verified_application_id = process_document(db, document_id)
        except Exception as exc:  # Gemini timeout, rate limit, bad JSON...
            db.rollback()
            if self.request.retries < self.max_retries:
                log.warning("Extraction of document %s failed (%s); retrying", document_id, exc)
                raise self.retry(exc=exc)
            save_failure(db, db.get(Document, document_id), f"extraction failed after retries: {exc}")
            return "failed"

        if verified_application_id is not None:
            score_verified_application(db, verified_application_id)
            return "verified"
        return "done"


def score_verified_application(db, application_id: int) -> None:
    """DOCS_VERIFIED -> SCORED automatically. Phase 6 adds the decision after this."""
    scorer = get_scorer()
    if scorer is None:
        log.warning("No model loaded; application %s stays DOCS_VERIFIED", application_id)
        return
    try:
        score_and_save(db, db.get(Application, application_id), scorer, actor_id=None)
        db.commit()
    except MissingApplicationData as exc:
        db.rollback()
        log.warning("Application %s cannot be scored: %s", application_id, exc)