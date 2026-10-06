from app.auth.models import User
from app.auth.security import hash_password
from tests.conftest import signup_and_login


def test_signup_creates_applicant(client):
    r = client.post("/auth/signup", json={"email": "Asha@Example.com", "password": "secret123", "full_name": "Asha Rao"})
    assert r.status_code == 201
    body = r.json()
    assert body["role"] == "applicant"
    assert body["email"] == "asha@example.com"
    assert "password" not in body and "password_hash" not in body


def test_duplicate_email_rejected(client):
    data = {"email": "asha@example.com", "password": "secret123", "full_name": "Asha Rao"}
    client.post("/auth/signup", json=data)
    assert client.post("/auth/signup", json=data).status_code == 409


def test_short_password_rejected(client):
    r = client.post("/auth/signup", json={"email": "a@example.com", "password": "123", "full_name": "Asha"})
    assert r.status_code == 422


def test_login_and_me(client):
    headers = signup_and_login(client)
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "asha@example.com"


def test_wrong_password_401(client):
    signup_and_login(client)
    r = client.post("/auth/login", data={"username": "asha@example.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_me_without_token_401(client):
    assert client.get("/auth/me").status_code == 401


def test_garbage_token_401(client):
    assert client.get("/auth/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401


def test_applicant_cannot_create_staff(client):
    headers = signup_and_login(client)
    r = client.post(
        "/auth/staff",
        json={"email": "uw@example.com", "password": "secret123", "full_name": "Uma W", "role": "underwriter"},
        headers=headers,
    )
    assert r.status_code == 403


def test_admin_can_create_underwriter(client, db):
    db.add(User(email="admin@example.com", full_name="Admin", password_hash=hash_password("adminpass"), role="admin"))
    db.commit()
    token = client.post("/auth/login", data={"username": "admin@example.com", "password": "adminpass"}).json()["access_token"]
    r = client.post(
        "/auth/staff",
        json={"email": "uw@example.com", "password": "secret123", "full_name": "Uma W", "role": "underwriter"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "underwriter"