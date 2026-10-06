"""The single-server deploy: inline tasks instead of Celery, the React app served by FastAPI, hosted DB URLs."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import serve
from app.applications.models import Application
from app.core.config import Settings, settings
from app.documents import extraction, tasks
from app.documents.models import Document
from tests.conftest import TestSession
from tests.test_document_processing import GOOD_SLIP, GOOD_STATEMENT, applicant, pdf_bytes, upload  # noqa: F401


@pytest.mark.parametrize("given", ["postgresql://u:p@db.example.com/app?sslmode=require",
                                   "postgres://u:p@db.example.com/app?sslmode=require"])
def test_hosted_database_url_gets_the_psycopg_driver(given):
    url = Settings(database_url=given).database_url
    assert url == "postgresql+psycopg://u:p@db.example.com/app?sslmode=require"


def test_local_database_url_is_unchanged():
    url = "postgresql+psycopg://lendwise:lendwise@localhost:5432/lendwise"
    assert Settings(database_url=url).database_url == url


@pytest.fixture
def inline(monkeypatch, tmp_path):
    """Run uploads like the free deploy does: no Celery worker, the task runs inside the API."""
    monkeypatch.setattr(settings, "run_tasks_inline", True)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(tasks, "SessionLocal", TestSession)  # the task opens its own session: point it at the test DB
    monkeypatch.setattr(tasks, "get_scorer", lambda: None)  # stop at DOCS_VERIFIED; scoring is tested elsewhere


def test_inline_mode_processes_uploads_without_celery(client, db, applicant, inline, monkeypatch, queued_tasks):
    monkeypatch.setattr(extraction, "extract", lambda text: GOOD_SLIP if "Salary" in text else GOOD_STATEMENT)
    headers, app_id = applicant
    upload(client, headers, app_id, "salary_slip", pdf_bytes("Salary slip"))
    upload(client, headers, app_id, "bank_statement", pdf_bytes("Bank statement"))

    db.expire_all()  # the task committed through its own session
    assert queued_tasks == []  # nothing was sent to Redis
    statuses = db.scalars(select(Document.extraction_status).where(Document.application_id == app_id)).all()
    assert statuses == ["DONE", "DONE"]
    assert db.get(Application, app_id).status == "DOCS_VERIFIED"


def test_inline_mode_retries_then_marks_failed(client, db, applicant, inline, monkeypatch):
    calls = []

    def gemini_down(text):
        calls.append(text)
        raise RuntimeError("503 from Gemini")

    monkeypatch.setattr(extraction, "extract", gemini_down)
    headers, app_id = applicant
    doc_id = upload(client, headers, app_id, "salary_slip", pdf_bytes("Salary slip"))

    db.expire_all()
    assert len(calls) == 4  # first try + 3 retries
    assert db.get(Document, doc_id).extraction_status == "FAILED"


@pytest.fixture
def site(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<div id=root></div>")
    (tmp_path / "assets" / "app.js").write_text("console.log('hi')")
    monkeypatch.setattr(serve, "DIST", tmp_path.resolve())
    return TestClient(serve.app)


def test_react_pages_get_index_html(site):
    for path in ["/", "/login", "/applicant/applications/5"]:
        response = site.get(path)
        assert response.status_code == 200 and "root" in response.text


def test_static_files_are_served(site):
    response = site.get("/assets/app.js")
    assert response.text == "console.log('hi')"


def test_api_lives_under_api(site):
    assert site.get("/api/health").json()["status"] == "ok"


def test_files_outside_the_build_folder_are_not_served(site):
    response = site.get("/..%2F..%2F..%2Fetc%2Fpasswd")
    assert "root:" not in response.text and "root" in response.text  # index.html, not /etc/passwd