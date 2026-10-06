import io

import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import select

from app.applications.models import Application
from app.core.config import settings
from app.decisions.models import AuditLog
from app.documents import tasks
from app.documents.extraction import ExtractedDoc, MonthEntry
from app.documents.models import Document
from app.documents.service import process_document
from app.scoring.models import CreditScore
from tests.conftest import VALID_APPLICATION, signup_and_login
from tests.test_scoring import scorer, tiny_bundle  # noqa: F401  (reuse the tiny test model)

GOOD_SLIP = ExtractedDoc(doc_type="salary_slip", person_name="Asha Rao", employer="Acme Ltd", pay_period="2026-09",
                         monthly_gross_salary=60000, monthly_net_salary=52800, months=[])
GOOD_STATEMENT = ExtractedDoc(doc_type="bank_statement", person_name="ASHA RAO", employer=None, pay_period=None,
                              monthly_gross_salary=None, monthly_net_salary=None,
                              months=[MonthEntry(month=f"2026-0{m}", salary_credit=52800, closing_balance=90000)
                                      for m in range(1, 7)])
WRONG_NAME_SLIP = GOOD_SLIP.model_copy(update={"person_name": "Vikram Iyer"})


@pytest.fixture(autouse=True)
def temp_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))


def pdf_bytes(text="Salary slip") -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    if text:
        c.drawString(50, 800, text)
    c.save()
    return buffer.getvalue()


def upload(client, headers, app_id, doc_type, content=None) -> int:
    response = client.post(f"/applications/{app_id}/documents", data={"doc_type": doc_type},
                           files={"file": ("doc.pdf", content or pdf_bytes(), "application/pdf")}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def returns(doc: ExtractedDoc):
    """A fake Gemini that always returns `doc`."""
    return lambda text: doc


@pytest.fixture
def applicant(client):
    headers = signup_and_login(client)  # Asha Rao, the name on the GOOD_* documents
    app_id = client.post("/applications", json=VALID_APPLICATION, headers=headers).json()["id"]
    return headers, app_id


def test_upload_queues_extraction(client, applicant, queued_tasks):
    headers, app_id = applicant
    doc_id = upload(client, headers, app_id, "salary_slip")
    assert queued_tasks == [doc_id]


def test_both_good_documents_verify_the_application(client, db, applicant):
    headers, app_id = applicant
    slip_id = upload(client, headers, app_id, "salary_slip")
    statement_id = upload(client, headers, app_id, "bank_statement")

    assert process_document(db, slip_id, returns(GOOD_SLIP)) is None  # one document is not enough
    assert db.get(Application, app_id).status == "SUBMITTED"
    assert process_document(db, statement_id, returns(GOOD_STATEMENT)) == app_id

    assert db.get(Application, app_id).status == "DOCS_VERIFIED"
    extraction = client.get(f"/applications/{app_id}/documents/{slip_id}/extraction", headers=headers).json()
    assert extraction["passed"] is True and extraction["confidence"] == 1.0
    assert extraction["extracted"]["monthly_gross_salary"] == 60000


def test_failed_check_keeps_application_submitted(client, db, applicant):
    headers, app_id = applicant
    slip_id = upload(client, headers, app_id, "salary_slip")
    statement_id = upload(client, headers, app_id, "bank_statement")
    process_document(db, slip_id, returns(WRONG_NAME_SLIP))
    process_document(db, statement_id, returns(GOOD_STATEMENT))

    assert db.get(Application, app_id).status == "SUBMITTED"
    extraction = client.get(f"/applications/{app_id}/documents/{slip_id}/extraction", headers=headers).json()
    assert extraction["passed"] is False
    assert "does not match the applicant" in extraction["issues"][0]


def test_reupload_replaces_a_failed_document(client, db, applicant):
    headers, app_id = applicant
    process_document(db, upload(client, headers, app_id, "salary_slip"), returns(WRONG_NAME_SLIP))
    process_document(db, upload(client, headers, app_id, "bank_statement"), returns(GOOD_STATEMENT))

    new_slip_id = upload(client, headers, app_id, "salary_slip")

    assert process_document(db, new_slip_id, returns(GOOD_SLIP)) == app_id


def test_scanned_pdf_is_marked_failed(client, db, applicant):
    headers, app_id = applicant
    doc_id = upload(client, headers, app_id, "salary_slip", content=pdf_bytes(text=""))

    process_document(db, doc_id, returns(GOOD_SLIP))

    assert db.get(Document, doc_id).extraction_status == "FAILED"
    extraction = client.get(f"/applications/{app_id}/documents/{doc_id}/extraction", headers=headers).json()
    assert extraction["passed"] is False and "scanned" in extraction["issues"][0]


def test_processing_twice_is_harmless(client, db, applicant):
    headers, app_id = applicant
    doc_id = upload(client, headers, app_id, "salary_slip")
    process_document(db, doc_id, returns(GOOD_SLIP))

    def should_not_be_called(text):
        raise AssertionError("Gemini called twice")

    assert process_document(db, doc_id, should_not_be_called) is None


def test_extraction_not_ready_yet_returns_404(client, applicant):
    headers, app_id = applicant
    doc_id = upload(client, headers, app_id, "salary_slip")
    response = client.get(f"/applications/{app_id}/documents/{doc_id}/extraction", headers=headers)
    assert response.status_code == 404


def test_other_applicants_cannot_see_extraction(client, db, applicant):
    headers, app_id = applicant
    doc_id = upload(client, headers, app_id, "salary_slip")
    process_document(db, doc_id, returns(GOOD_SLIP))
    other = signup_and_login(client, email="ravi@example.com", name="Ravi Kumar")

    response = client.get(f"/applications/{app_id}/documents/{doc_id}/extraction", headers=other)
    assert response.status_code == 404


def test_verified_application_is_scored_and_decided_automatically(client, db, applicant, scorer, monkeypatch):
    headers, app_id = applicant
    monkeypatch.setattr(tasks, "_scorer", scorer)
    process_document(db, upload(client, headers, app_id, "salary_slip"), returns(GOOD_SLIP))
    process_document(db, upload(client, headers, app_id, "bank_statement"), returns(GOOD_STATEMENT))

    tasks.score_verified_application(db, app_id)

    assert db.get(Application, app_id).status in {"APPROVED", "REJECTED", "MANUAL_REVIEW"}
    assert db.scalar(select(CreditScore).where(CreditScore.application_id == app_id)) is not None
    actions = db.scalars(select(AuditLog.action).where(AuditLog.entity_type == "application",
                                                       AuditLog.entity_id == app_id).order_by(AuditLog.id)).all()
    # DOCS_VERIFIED, SCORED, scored, decided
    assert actions[-5:] == ["STATUS_CHANGE", "STATUS_CHANGE", "APPLICATION_SCORED", "STATUS_CHANGE", "AUTO_DECISION"]