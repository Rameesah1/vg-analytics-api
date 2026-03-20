import pytest


def test_register_success(client):
    import uuid
    username = f"user_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register", json={
        "username": username,
        "email": f"{username}@test.com",
        "password": "password123"
    })
    assert r.status_code == 201
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_register_duplicate_username(client):
    payload = {"username": "dupuser", "email": "dup@test.com", "password": "password123"}
    client.post("/api/auth/register", json=payload)
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 409


def test_login_success(client):
    client.post("/api/auth/register", json={
        "username": "loginuser",
        "email": "login@test.com",
        "password": "password123"
    })
    r = client.post("/api/auth/login", json={
        "username": "loginuser",
        "password": "password123"
    })
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={
        "username": "wrongpass",
        "email": "wrongpass@test.com",
        "password": "correctpassword"
    })
    r = client.post("/api/auth/login", json={
        "username": "wrongpass",
        "password": "wrongpassword"
    })
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/api/auth/login", json={
        "username": "doesnotexist",
        "password": "password123"
    })
    assert r.status_code == 401


def test_me_returns_profile(auth_client):
    r = auth_client.get("/api/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert "username" in body
    assert "email" in body
    assert "role" in body
    assert "id" in body


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code in (401, 403)


def test_me_does_not_expose_password(auth_client):
    r = auth_client.get("/api/auth/me")
    assert r.status_code == 200
    assert "password" not in r.json()
    assert "password_hash" not in r.json()
