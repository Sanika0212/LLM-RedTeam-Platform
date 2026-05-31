"""Tests for authentication routes."""


def test_register_success(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "strongpass",
        "full_name": "New User",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert "user_id" in data


def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "password": "pass123", "full_name": "A"}
    client.post("/api/v1/auth/register", json=payload)
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "already registered" in resp.json()["detail"]


def test_login_success(client):
    client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "mypassword",
        "full_name": "Login User",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "login@example.com"
    assert "access_token" in data


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json={
        "email": "wrong@example.com",
        "password": "correct",
        "full_name": "Wrong",
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com",
        "password": "incorrect",
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": "ghost@example.com",
        "password": "whatever",
    })
    assert resp.status_code == 401
