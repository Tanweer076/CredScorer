from app.applications.models import Application
from tests.conftest import VALID_APPLICATION, signup_and_login, staff_headers
from tests.test_scoring import scorer, tiny_bundle  # noqa: F401  (reuse the tiny test model)


def admin_headers(client, db):
    return staff_headers(client, db, role="admin", email="admin@example.com")


def test_admin_updates_thresholds_and_it_is_audited(client, db):
    admin = admin_headers(client, db)
    new = {"approve_min_score": 640, "reject_max_score": 420, "max_emi_share": 0.45}

    response = client.put("/admin/thresholds", json=new, headers=admin)

    assert response.status_code == 200
    assert client.get("/admin/thresholds", headers=admin).json() == {**new, "source": "settings"}
    logs = client.get("/admin/audit-logs", params={"action": "THRESHOLD_UPDATE"}, headers=admin).json()
    assert logs[0]["after"] == new


def test_reject_threshold_cannot_be_above_approve(client, db):
    response = client.put("/admin/thresholds", json={"approve_min_score": 500, "reject_max_score": 600},
                          headers=admin_headers(client, db))
    assert response.status_code == 422


def test_only_admins_change_thresholds(client, db):
    underwriter = staff_headers(client, db)
    response = client.put("/admin/thresholds", json={"approve_min_score": 0, "reject_max_score": 0},
                          headers=underwriter)
    assert response.status_code == 403


def test_new_thresholds_apply_to_the_next_decision(client, db, scorer):
    admin = admin_headers(client, db)
    client.put("/admin/thresholds", json={"approve_min_score": 0, "reject_max_score": 0}, headers=admin)
    applicant = signup_and_login(client)
    app_id = client.post("/applications", json=VALID_APPLICATION, headers=applicant).json()["id"]
    db.get(Application, app_id).status = "DOCS_VERIFIED"
    db.commit()

    assert client.post(f"/applications/{app_id}/score", headers=applicant).json()["status"] == "APPROVED"
    stats = client.get("/admin/stats", headers=admin).json()
    assert stats["applications_by_status"] == {"APPROVED": 1}
    assert stats["decisions"] == {"APPROVED (system)": 1}
    assert stats["approval_rate"] == 1.0


def test_audit_logs_can_be_filtered(client, db):
    admin = admin_headers(client, db)
    applicant = signup_and_login(client)
    app_id = client.post("/applications", json=VALID_APPLICATION, headers=applicant).json()["id"]

    logs = client.get("/admin/audit-logs", params={"entity_type": "application", "entity_id": app_id},
                      headers=admin).json()

    assert [log["action"] for log in logs] == ["APPLICATION_CREATED"]