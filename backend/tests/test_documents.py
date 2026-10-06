import pytest

from app.core.config import settings
from tests.conftest import VALID_APPLICATION, signup_and_login

PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"


@pytest.fixture(autouse=True)
def temp_upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    return tmp_path


def _new_application(client, headers):
    return client.post("/applications", json=VALID_APPLICATION, headers=headers).json()["id"]


def test_upload_pdf(client, temp_upload_dir):
    headers = signup_and_login(client)
    app_id = _new_application(client, headers)
    r = client.post(f"/applications/{app_id}/documents", data={"doc_type": "salary_slip"},
                    files={"file": ("my slip.pdf", PDF_BYTES, "application/pdf")}, headers=headers)
    assert r.status_code == 201
    assert r.json()["extraction_status"] == "PENDING"
    saved = list(temp_upload_dir.iterdir())
    assert len(saved) == 1 and saved[0].name != "my slip.pdf"  # server picks the name

    listed = client.get(f"/applications/{app_id}/documents", headers=headers).json()
    assert [d["doc_type"] for d in listed] == ["salary_slip"]


def test_non_pdf_rejected_even_if_named_pdf(client):
    headers = signup_and_login(client)
    app_id = _new_application(client, headers)
    r = client.post(f"/applications/{app_id}/documents", data={"doc_type": "salary_slip"},
                    files={"file": ("evil.pdf", b"MZ\x90\x00 not a pdf", "application/pdf")}, headers=headers)
    assert r.status_code == 400


def test_too_large_rejected(client):
    headers = signup_and_login(client)
    app_id = _new_application(client, headers)
    big = PDF_BYTES + b"0" * (5 * 1024 * 1024)
    r = client.post(f"/applications/{app_id}/documents", data={"doc_type": "bank_statement"},
                    files={"file": ("big.pdf", big, "application/pdf")}, headers=headers)
    assert r.status_code == 413


def test_wrong_doc_type_rejected(client):
    headers = signup_and_login(client)
    app_id = _new_application(client, headers)
    r = client.post(f"/applications/{app_id}/documents", data={"doc_type": "selfie"},
                    files={"file": ("a.pdf", PDF_BYTES, "application/pdf")}, headers=headers)
    assert r.status_code == 422


def test_cannot_upload_to_someone_elses_application(client):
    asha = signup_and_login(client, email="asha@example.com")
    ravi = signup_and_login(client, email="ravi@example.com", name="Ravi Kumar")
    app_id = _new_application(client, asha)
    r = client.post(f"/applications/{app_id}/documents", data={"doc_type": "salary_slip"},
                    files={"file": ("a.pdf", PDF_BYTES, "application/pdf")}, headers=ravi)
    assert r.status_code == 404