import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.applications.service import get_application_for_user
from app.applications.status import Status
from app.auth.models import User
from app.auth.security import get_current_user, require_roles
from app.core.audit import audit
from app.core.config import settings
from app.core.db import get_db
from app.documents.models import Document
from app.documents.schemas import DocumentOut

router = APIRouter(prefix="/applications/{application_id}/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    application_id: int,
    doc_type: Literal["salary_slip", "bank_statement"] = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("applicant")),
):
    application = get_application_for_user(db, application_id, user)
    if application.status != Status.SUBMITTED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Documents can only be uploaded while SUBMITTED")

    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File is larger than 5 MB")
    # Check the file's real content, not just its name or the browser's claim.
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are accepted")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / f"{uuid.uuid4().hex}.pdf"  # never trust the user's filename
    path.write_bytes(content)

    document = Document(application_id=application.id, doc_type=doc_type, file_path=str(path),
                        mime_type="application/pdf", extraction_status="PENDING")
    db.add(document)
    db.flush()
    audit(db, actor_id=user.id, action="DOCUMENT_UPLOADED", entity_type="document",
          entity_id=document.id, after={"application_id": application.id, "doc_type": doc_type})
    db.commit()
    db.refresh(document)
    # Phase 5: queue the Celery extraction task here, e.g. extract_document.delay(document.id)
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(application_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    get_application_for_user(db, application_id, user)
    return db.scalars(select(Document).where(Document.application_id == application_id)
                      .order_by(Document.uploaded_at)).all()