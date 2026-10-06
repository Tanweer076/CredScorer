import numpy as np
import pandas as pd
import pytest
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator
from sqlalchemy import select

from app.applications.models import Application
from app.decisions.models import AuditLog
from app.main import app
from app.scoring.features import EDUCATION, FAMILY_STATUS, HOUSING, INCOME_TYPE
from app.scoring.model import Scorer
from tests.conftest import VALID_APPLICATION, signup_and_login

FEATURES = [
    "annual_income", "credit_amount", "annuity", "term_months", "credit_to_income", "payment_to_income",
    "age_years", "employment_years", "not_employed", "children", "family_members", "owns_car", "owns_realty",
    "education", "income_type", "family_status", "housing_type",
    "ext_source_1", "ext_source_2", "ext_source_3", "ext_source_mean", "late_payment_ratio", "avg_days_late",
    "max_days_late", "underpaid_ratio", "n_installments", "active_loans", "total_debt", "total_overdue",
    "debt_to_income", "credit_utilisation", "prev_applications", "prev_refused", "prev_refused_ratio",
]
CATEGORIES = {
    "education": list(EDUCATION.values()),
    "income_type": list(INCOME_TYPE.values()),
    "family_status": list(FAMILY_STATUS.values()),
    "housing_type": list(HOUSING.values()),
}


@pytest.fixture(scope="session")
def tiny_bundle():
    """A small model trained on random data, so tests don't need the real 300k-row model."""
    rng = np.random.default_rng(0)
    n = 2000
    data = {}
    for name in FEATURES:
        if name in CATEGORIES:
            data[name] = pd.Categorical(rng.choice(CATEGORIES[name], n), categories=CATEGORIES[name])
        else:
            data[name] = rng.random(n)
    X = pd.DataFrame(data)
    # Default is more likely with a high payment_to_income, so a higher income should help.
    y = (rng.random(n) < 0.05 + 0.4 * X["payment_to_income"]).astype(int)
    booster = xgb.XGBClassifier(n_estimators=30, max_depth=3, enable_categorical=True,
                                tree_method="hist", early_stopping_rounds=5)
    booster.fit(X[:1500], y[:1500], eval_set=[(X[1500:1750], y[1500:1750])], verbose=False)
    model = CalibratedClassifierCV(FrozenEstimator(booster), method="isotonic")
    model.fit(X[1750:], y[1750:])
    return {"model": model, "booster": booster, "features": FEATURES, "categories": CATEGORIES,
            "version": "test-model", "metrics": {}, "best_iteration": booster.best_iteration}


@pytest.fixture
def scorer(tiny_bundle):
    app.state.scorer = Scorer(tiny_bundle)
    yield app.state.scorer
    app.state.scorer = None


def create_application(client, headers, **changes):
    response = client.post("/applications", json={**VALID_APPLICATION, **changes}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_score_returns_score_and_three_reasons(client, scorer):
    headers = signup_and_login(client)
    app_id = create_application(client, headers)

    response = client.post(f"/applications/{app_id}/score", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert 0 <= body["pd"] <= 1
    assert 0 <= body["score"] <= 1000
    assert body["model_version"] == "test-model"
    assert len(body["reasons"]) == 3
    assert body["status"] == "SUBMITTED"  # not verified yet, so the status doesn't move


def test_latest_score_is_returned(client, scorer):
    headers = signup_and_login(client)
    app_id = create_application(client, headers)
    assert client.get(f"/applications/{app_id}/score", headers=headers).status_code == 404

    scored = client.post(f"/applications/{app_id}/score", headers=headers).json()
    latest = client.get(f"/applications/{app_id}/score", headers=headers).json()

    assert latest["score"] == scored["score"]
    assert latest["reasons"] == scored["reasons"]
    assert latest["recommendations"] == scored["recommendations"]


def test_returns_503_when_no_model_is_loaded(client):
    app.state.scorer = None
    headers = signup_and_login(client)
    app_id = create_application(client, headers)

    assert client.post(f"/applications/{app_id}/score", headers=headers).status_code == 503


def test_cannot_score_someone_elses_application(client, scorer):
    owner = signup_and_login(client)
    app_id = create_application(client, owner)
    other = signup_and_login(client, email="ravi@example.com", name="Ravi Kumar")

    assert client.post(f"/applications/{app_id}/score", headers=other).status_code == 404


def test_old_application_without_new_fields_gets_422(client, db, scorer):
    headers = signup_and_login(client)
    app_id = create_application(client, headers)
    db.get(Application, app_id).education = None  # like a row created before Phase 4
    db.commit()

    response = client.post(f"/applications/{app_id}/score", headers=headers)

    assert response.status_code == 422
    assert "education" in response.json()["detail"]


def test_verified_application_moves_to_scored(client, db, scorer):
    headers = signup_and_login(client)
    app_id = create_application(client, headers)
    db.get(Application, app_id).status = "DOCS_VERIFIED"  # Phase 5 will do this for real
    db.commit()

    response = client.post(f"/applications/{app_id}/score", headers=headers)

    assert response.json()["status"] == "SCORED"
    actions = db.scalars(select(AuditLog.action).where(AuditLog.entity_id == app_id).order_by(AuditLog.id)).all()
    assert actions[-2:] == ["STATUS_CHANGE", "APPLICATION_SCORED"]


def test_decided_application_cannot_be_rescored(client, db, scorer):
    headers = signup_and_login(client)
    app_id = create_application(client, headers)
    db.get(Application, app_id).status = "APPROVED"
    db.commit()

    assert client.post(f"/applications/{app_id}/score", headers=headers).status_code == 409


def test_what_if_compares_scenarios_without_saving(client, scorer):
    headers = signup_and_login(client)
    app_id = create_application(client, headers)

    response = client.post(f"/applications/{app_id}/what-if", json={"term_months": 48}, headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["changes"] == {"term_months": 48}
    assert body["scenario"]["monthly_emi"] < body["current"]["monthly_emi"]  # longer term, smaller EMI
    assert body["score_change"] == body["scenario"]["score"] - body["current"]["score"]
    assert client.get(f"/applications/{app_id}/score", headers=headers).status_code == 404  # nothing saved


def test_what_if_needs_at_least_one_change(client, scorer):
    headers = signup_and_login(client)
    app_id = create_application(client, headers)

    assert client.post(f"/applications/{app_id}/what-if", json={}, headers=headers).status_code == 422