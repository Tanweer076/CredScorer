import pytest

from app.applications.models import Application
from tests.conftest import VALID_APPLICATION, signup_and_login, staff_headers
from tests.test_decisions import set_thresholds
from tests.test_scoring import scorer, tiny_bundle  # noqa: F401  (reuse the tiny test model)

REASON = "Bureau history is thin but income is verified and stable."


@pytest.fixture
def in_review(client, db, scorer):
    """An application the system sent to MANUAL_REVIEW."""
    set_thresholds(db, approve_min=1001, reject_max=0)  # nobody is auto-approved or auto-rejected
    applicant = signup_and_login(client)
    app_id = client.post("/applications", json=VALID_APPLICATION, headers=applicant).json()["id"]
    db.get(Application, app_id).status = "DOCS_VERIFIED"
    db.commit()
    assert client.post(f"/applications/{app_id}/score", headers=applicant).json()["status"] == "MANUAL_REVIEW"
    return applicant, app_id


def test_queue_lists_applications_waiting_for_review(client, db, in_review):
    _, app_id = in_review
    queue = client.get("/underwriter/queue", headers=staff_headers(client, db)).json()
    assert [item["application_id"] for item in queue] == [app_id]
    assert queue[0]["applicant_name"] == "Asha Rao"
    assert "needs a person to review" in queue[0]["review_reason"]


def test_applicants_cannot_see_the_queue(client, in_review):
    applicant, _ = in_review
    assert client.get("/underwriter/queue", headers=applicant).status_code == 403


def test_review_page_has_score_documents_and_decisions(client, db, in_review):
    _, app_id = in_review
    detail = client.get(f"/underwriter/applications/{app_id}", headers=staff_headers(client, db)).json()
    assert detail["applicant_email"] == "asha@example.com"
    assert len(detail["score"]["reasons"]) == 5
    assert [d["outcome"] for d in detail["decisions"]] == ["MANUAL_REVIEW"]


def test_underwriter_approves_with_a_reason(client, db, in_review):
    applicant, app_id = in_review
    staff = staff_headers(client, db)

    response = client.post(f"/underwriter/applications/{app_id}/decision",
                           json={"outcome": "APPROVED", "reason": REASON}, headers=staff)

    assert response.status_code == 200
    assert response.json()["decided_by"] == "underwriter"
    decision = client.get(f"/applications/{app_id}/decision", headers=applicant).json()
    assert decision["outcome"] == "APPROVED" and decision["reason"] == REASON
    assert client.get("/underwriter/queue", headers=staff).json() == []


def test_reason_is_required(client, db, in_review):
    _, app_id = in_review
    response = client.post(f"/underwriter/applications/{app_id}/decision",
                           json={"outcome": "REJECTED", "reason": "no"}, headers=staff_headers(client, db))
    assert response.status_code == 422


def test_cannot_decide_twice(client, db, in_review):
    _, app_id = in_review
    staff = staff_headers(client, db)
    client.post(f"/underwriter/applications/{app_id}/decision", json={"outcome": "REJECTED", "reason": REASON},
                headers=staff)
    again = client.post(f"/underwriter/applications/{app_id}/decision", json={"outcome": "APPROVED", "reason": REASON},
                        headers=staff)
    assert again.status_code == 409


def test_cannot_decide_an_application_not_in_review(client, db):
    applicant = signup_and_login(client)
    app_id = client.post("/applications", json=VALID_APPLICATION, headers=applicant).json()["id"]
    response = client.post(f"/underwriter/applications/{app_id}/decision",
                           json={"outcome": "APPROVED", "reason": REASON}, headers=staff_headers(client, db))
    assert response.status_code == 409

def test_reason_of_only_spaces_is_rejected(client, db, in_review):
    _, app_id = in_review
    response = client.post(f"/underwriter/applications/{app_id}/decision",
                           json={"outcome": "APPROVED", "reason": " " * 12 + "ok"}, headers=staff_headers(client, db))
    assert response.status_code == 422
