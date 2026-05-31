"""Tests for LLM model CRUD routes."""


def test_create_model(client, auth_headers):
    resp = client.post("/api/v1/models/", json={
        "name": "GPT-4",
        "provider": "openai",
        "model_id": "gpt-4",
        "description": "OpenAI GPT-4",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "GPT-4"
    assert data["provider"] == "openai"
    assert data["safety_score"] == 0.0


def test_create_model_duplicate_name(client, auth_headers):
    payload = {"name": "Dup", "provider": "openai", "model_id": "gpt-4"}
    client.post("/api/v1/models/", json=payload, headers=auth_headers)
    resp = client.post("/api/v1/models/", json=payload, headers=auth_headers)
    assert resp.status_code == 400
    assert "already exists" in resp.json()["detail"]


def test_list_models(client, auth_headers):
    client.post("/api/v1/models/", json={"name": "M1", "provider": "openai", "model_id": "gpt-4"}, headers=auth_headers)
    client.post("/api/v1/models/", json={"name": "M2", "provider": "anthropic", "model_id": "claude-3"}, headers=auth_headers)
    resp = client.get("/api/v1/models/", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_model(client, auth_headers):
    create = client.post("/api/v1/models/", json={
        "name": "GetMe", "provider": "openai", "model_id": "gpt-4",
    }, headers=auth_headers)
    model_id = create.json()["id"]
    resp = client.get(f"/api/v1/models/{model_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetMe"


def test_get_model_404(client, auth_headers):
    resp = client.get("/api/v1/models/9999", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_model(client, admin_headers):
    create = client.post("/api/v1/models/", json={
        "name": "DeleteMe", "provider": "openai", "model_id": "gpt-4",
    }, headers=admin_headers)
    model_id = create.json()["id"]
    resp = client.delete(f"/api/v1/models/{model_id}", headers=admin_headers)
    assert resp.status_code == 204
    assert client.get(f"/api/v1/models/{model_id}", headers=admin_headers).status_code == 404


def test_delete_model_404(client, admin_headers):
    resp = client.delete("/api/v1/models/9999", headers=admin_headers)
    assert resp.status_code == 404


def test_list_models_unauthenticated(client):
    resp = client.get("/api/v1/models/")
    assert resp.status_code in (401, 403)


def test_delete_model_non_admin(client, auth_headers):
    """Non-admin users should get 403 on delete."""
    create = client.post("/api/v1/models/", json={
        "name": "NoDelete", "provider": "openai", "model_id": "gpt-4",
    }, headers=auth_headers)
    model_id = create.json()["id"]
    resp = client.delete(f"/api/v1/models/{model_id}", headers=auth_headers)
    assert resp.status_code in (401, 403)
