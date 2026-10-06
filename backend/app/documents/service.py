"""Process one uploaded document: PDF text -> Gemini -> validation -> database.

Called by the Celery task in tasks.py. Kept separate from Celery so it can be
tested directly with a fake extractor.
"""
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.applications.models import Application
from app.applications.status import Status, check_transition
from app.auth.models import User
from app.core.audit import audit
from app.core.config import settings
from app.documents import extraction
from app.documents.extraction import ExtractedDoc, ScannedPDFError, pdf_text
from app.documents.models import Document, ExtractedData
from app.documents.validation import PASS_CONFIDENCE, validate

REQUIRED_DOCS = ("salary_slip", "bank_statement")


def process_document(db: Session, document_id: int,
                     extractor: Callable[[str], ExtractedDoc] | None = None) -> int | None:
    """Extract and validate one document, then commit.

    Returns the application id if this document completed verification (the application
    just moved to DOCS_VERIFIED), otherwise None. Gemini errors are raised so Celery can retry.
    """
    document = db.get(Document, document_id)
    if document is None or document.extraction_status != "PENDING":
        return None  # already processed: running a task twice must be harmless
    application = db.get(Application, document.application_id)
    owner = db.get(User, application.user_id)

    try:
        text = pdf_text(document.file_path)
    except ScannedPDFError as exc:
        save_failure(db, document, str(exc))
        return None

    extracted = (extractor or extraction.extract)(text)
    result = validate(extracted, document.doc_type, float(application.declared_monthly_income), owner.full_name)
    db.add(ExtractedData(document_id=document.id, payload=extracted.model_dump(), confidence=result.confidence,
                         issues=result.issues, model_name=settings.gemini_model))
    document.extraction_status = "DONE"
    audit(db, actor_id=None, action="DOCUMENT_EXTRACTED", entity_type="document", entity_id=document.id,
          after={"confidence": result.confidence, "passed": result.passed, "issues": result.issues})
    db.flush()

    verified = verify_application(db, application)
    db.commit()
    return application.id if verified else None


def save_failure(db: Session, document: Document, reason: str) -> None:
    """Mark the document FAILED with a reason the applicant and underwriter can see."""
    if db.scalar(select(ExtractedData).where(ExtractedData.document_id == document.id)) is None:
        db.add(ExtractedData(document_id=document.id, payload={}, confidence=0.0, issues=[reason],
                             model_name=settings.gemini_model))
    document.extraction_status = "FAILED"
    audit(db, actor_id=None, action="DOCUMENT_FAILED", entity_type="document", entity_id=document.id,
          after={"reason": reason})
    db.commit()


def latest_documents(db: Session, application_id: int) -> dict[str, Document]:
    """The most recent upload of each document type (a re-upload replaces an earlier one)."""
    documents = db.scalars(select(Document).where(Document.application_id == application_id)
                           .order_by(Document.id)).all()
    return {d.doc_type: d for d in documents}


def verify_application(db: Session, application: Application) -> bool:
    """Move the application to DOCS_VERIFIED when every required document passed."""
    if application.status != Status.SUBMITTED:
        return False
    latest = latest_documents(db, application.id)
    for doc_type in REQUIRED_DOCS:
        document = latest.get(doc_type)
        if document is None or document.extraction_status != "DONE":
            return False
        data = db.scalar(select(ExtractedData).where(ExtractedData.document_id == document.id))
        if data is None or data.confidence < PASS_CONFIDENCE:
            return False
    old = application.status
    application.status = check_transition(old, Status.DOCS_VERIFIED)
    audit(db, actor_id=None, action="STATUS_CHANGE", entity_type="application", entity_id=application.id,
          before={"status": old}, after={"status": application.status})
    return True