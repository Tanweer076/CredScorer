import json

import pytest

from app.applications.models import Application
from app.core.config import settings
from app.decisions.engine import decide
from app.decisions.models import Setting
from app.decisions.service import THRESHOLDS_KEY, get_thresholds
from tests.conftest import VALID_APPLICATION, signup_and_login
from tests.test_scoring import scorer, tiny_bundle  # noqa: F401  (reuse the tiny test model)

T = {"approve_min_score": 600, "reject_max_score": 450, "max_emi_share": 0.5}


@pytest.mark.parametrize("score, emi_share, expected", [
    (700, 0.2, "APPROVED"),
    (600, 0.2, "APPROVED"),  # exactly at the threshold
    (599, 0.2, "MANUAL_REVIEW"),
    (450, 0.2, "MANUAL_REVIEW"),
    (449, 0.2, "REJECTED"),
    (700, 0.6, "MANUAL_REVIEW"),  # good score, but the EMI is not affordable
    (300, 0.9, "REJECTED"),
])
def test_decision_rules(score, emi_share, expected):
    outcome, reasons = decide(score, emi_share, T)
    assert outcome == expected
    assert reasons


def test_review_lists_every_reason():
    outcome, reasons = decide(500, 0.7, T)
    assert outcome == "MANUAL_REVIEW" and len(reasons) == 2


def test_thresholds_come_from_settings_then_file_then_defaults(db, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "thresholds_path", str(tmp_path / "missing.json"))
    assert get_thresholds(db)["source"] == "defaults"

    path = tmp_path / "thresholds.json"
    path.write_text(json.dumps({"approve_min_score": 530, "reject_max_score": 300, "approve_share": 0.7}))
    monkeypatch.setattr(settings, "thresholds_path", str(path))
    assert get_thresholds(db)["approve_min_score"] == 530

    db.add(Setting(key=THRESHOLDS_KEY, value={"approve_min_score": 650, "reject_max_score": 400}))
    db.commit()
    thresholds = get_thresholds(db)
    assert (thresholds["approve_min_score"], thresholds["source"]) == (650, "settings")
    assert thresholds["max_emi_share"] == 0.5  # missing keys fall back to the defaults


def set_thresholds(db, approve_min, reject_max):
    db.add(Setting(key=THRESHOLDS_KEY, value={"approve_min_score": approve_min, "reject_max_score": reject_max}))
    db.commit()


def verified_application(client, db):
    headers = signup_and_login(client)
    app_id = client.post("/applications", json=VALID_APPLICATION, headers=headers).json()["id"]
    db.get(Application, app_id).status = "DOCS_VERIFIED"
    db.commit()
    return headers, app_id


@pytest.mark.parametrize("approve_min, reject_max, expected", [
    (0, 0, "APPROVED"),  # every score is high enough
    (1001, 0, "MANUAL_REVIEW"),  # no score is high enough to approve, none low enough to reject
    (1001, 1001, "REJECTED"),  # every score is too low
])
def test_scored_application_is_decided(client, db, scorer, approve_min, reject_max, expected):
    set_thresholds(db, approve_min, reject_max)
    headers, app_id = verified_application(client, db)

    response = client.post(f"/applications/{app_id}/score", headers=headers)

    assert response.json()["status"] == expected
    decision = client.get(f"/applications/{app_id}/decision", headers=headers).json()
    assert decision["outcome"] == expected
    assert decision["decided_by"] == "system"


def test_unaffordable_emi_goes_to_review(client, db, scorer):
    set_thresholds(db, 0, 0)
    headers = signup_and_login(client)
    app_id = client.post("/applications", json={**VALID_APPLICATION, "declared_monthly_income": "15000.00"},
                         headers=headers).json()["id"]  # EMI of about 11,800 on 15,000 income
    db.get(Application, app_id).status = "DOCS_VERIFIED"
    db.commit()

    client.post(f"/applications/{app_id}/score", headers=headers)

    decision = client.get(f"/applications/{app_id}/decision", headers=headers).json()
    assert decision["outcome"] == "MANUAL_REVIEW"
    assert "of monthly income" in decision["reason"]


def test_preliminary_score_is_not_decided(client, db, scorer):
    headers = signup_and_login(client)
    app_id = client.post("/applications", json=VALID_APPLICATION, headers=headers).json()["id"]

    client.post(f"/applications/{app_id}/score", headers=headers)  # still SUBMITTED: documents not verified

    assert client.get(f"/applications/{app_id}/decision", headers=headers).status_code == 404


def test_others_cannot_see_the_decision(client, db, scorer):
    set_thresholds(db, 0, 0)
    headers, app_id = verified_application(client, db)
    client.post(f"/applications/{app_id}/score", headers=headers)
    other = signup_and_login(client, email="ravi@example.com", name="Ravi Kumar")

    assert client.get(f"/applications/{app_id}/decision", headers=other).status_code == 404