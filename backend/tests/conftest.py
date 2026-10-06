import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.core.db import Base, get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+psycopg://lendwise:lendwise@localhost:5432/lendwise_test"
engine = create_engine(TEST_DATABASE_URL)
TestSession = sessionmaker(bind=engine, autoflush=False)


@pytest.fixture
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def signup_and_login(client, email="asha@example.com", password="secret123", name="Asha Rao"):
    client.post("/auth/signup", json={"email": email, "password": password, "full_name": name})
    token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def staff_headers(client, db, role="underwriter", email="uw@example.com", password="staffpass"):
    from app.auth.models import User
    from app.auth.security import hash_password

    db.add(User(email=email, full_name="Staff Member", password_hash=hash_password(password), role=role))
    db.commit()
    token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


VALID_APPLICATION = {
    "amount_requested": "250000.00",
    "term_months": 24,
    "purpose": "Home renovation",
    "declared_monthly_income": "60000.00",
    "employment_type": "salaried",
    "employment_years": 3.5,
    "date_of_birth": "1992-05-14",
    "children": 1,
    "family_members": 3,
    "owns_car": False,
    "owns_home": True,
    "education": "higher",
    "family_status": "married",
    "housing_type": "owned",
}