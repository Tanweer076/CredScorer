import pytest
from sqlalchemy import select

from app.applications.status import IllegalTransition, check_transition
from app.decisions.models import AuditLog
from tests.conftest import VALID_APPLICATION, signup_and_login, staff_headers


def test_create_application(client, db):
    headers = signup_and_login(client)
    r = client.post("/applications", json=VALID_APPLICATION, headers=headers)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "SUBMITTED"
    assert body["amount_requested"] == "250000.00"
    # every create is written to the audit log
    log = db.scalar(select(AuditLog).where(AuditLog.action == "APPLICATION_CREATED"))
    assert log is not None and log.entity_id == body["id"]


def test_invalid_application_rejected(client):
    headers = signup_and_login(client)
    bad = VALID_APPLICATION | {"amount_requested": "-5", "term_months": 1}
    assert client.post("/applications", json=bad, headers=headers).status_code == 422


def test_applicant_sees_only_own_applications(client):
    asha = signup_and_login(client, email="asha@example.com")
    ravi = signup_and_login(client, email="ravi@example.com", name="Ravi Kumar")
    asha_app = client.post("/applications", json=VALID_APPLICATION, headers=asha).json()
    client.post("/applications", json=VALID_APPLICATION, headers=ravi)

    asha_list = client.get("/applications", headers=asha).json()
    assert [a["id"] for a in asha_list] == [asha_app["id"]]
    # Ravi gets 404 (not 403) for Asha's application
    assert client.get(f"/applications/{asha_app['id']}", headers=ravi).status_code == 404


def test_underwriter_sees_all_and_cannot_create(client, db):
    asha = signup_and_login(client, email="asha@example.com")
    ravi = signup_and_login(client, email="ravi@example.com", name="Ravi Kumar")
    client.post("/applications", json=VALID_APPLICATION, headers=asha)
    client.post("/applications", json=VALID_APPLICATION, headers=ravi)
    uw = staff_headers(client, db)
    assert len(client.get("/applications", headers=uw).json()) == 2
    assert client.post("/applications", json=VALID_APPLICATION, headers=uw).status_code == 403


def test_status_filter(client, db):
    headers = signup_and_login(client)
    client.post("/applications", json=VALID_APPLICATION, headers=headers)
    assert len(client.get("/applications?status_filter=SUBMITTED", headers=headers).json()) == 1
    assert client.get("/applications?status_filter=APPROVED", headers=headers).json() == []


def test_update_while_submitted(client, db):
    headers = signup_and_login(client)
    app_id = client.post("/applications", json=VALID_APPLICATION, headers=headers).json()["id"]
    r = client.patch(f"/applications/{app_id}", json={"amount_requested": "300000"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["amount_requested"] == "300000.00"
    log = db.scalar(select(AuditLog).where(AuditLog.action == "APPLICATION_UPDATED"))
    assert log.before["amount_requested"] == "250000.00"
    assert log.after["amount_requested"] == "300000.00"


def test_cannot_update_after_submitted(client, db):
    from app.applications.models import Application

    headers = signup_and_login(client)
    app_id = client.post("/applications", json=VALID_APPLICATION, headers=headers).json()["id"]
    db.get(Application, app_id).status = "SCORED"
    db.commit()
    r = client.patch(f"/applications/{app_id}", json={"term_months": 12}, headers=headers)
    assert r.status_code == 409


@pytest.mark.parametrize("current,new", [
    ("SUBMITTED", "DOCS_VERIFIED"),
    ("DOCS_VERIFIED", "SCORED"),
    ("SCORED", "MANUAL_REVIEW"),
    ("MANUAL_REVIEW", "APPROVED"),
])
def test_allowed_transitions(current, new):
    assert check_transition(current, new) == new


@pytest.mark.parametrize("current,new", [
    ("SUBMITTED", "APPROVED"),
    ("APPROVED", "REJECTED"),
    ("REJECTED", "SUBMITTED"),
    ("SCORED", "DOCS_VERIFIED"),
])
def test_illegal_transitions(current, new):
    with pytest.raises(IllegalTransition):
        check_transition(current, new)

@pytest.mark.parametrize("field", ["amount_requested", "term_months", "education", "date_of_birth"])
def test_update_cannot_set_a_field_to_null(client, db, field):
    headers = signup_and_login(client)
    app_id = client.post("/applications", json=VALID_APPLICATION, headers=headers).json()["id"]
    r = client.patch(f"/applications/{app_id}", json={field: None}, headers=headers)
    assert r.status_code == 422
    assert client.get(f"/applications/{app_id}", headers=headers).json()[field] is not None
