"""Tests for evaluation routes."""


def test_create_evaluation(client, seed_model, auth_headers):
    resp = client.post("/api/v1/evaluations/", json={
        "name": "Safety Eval",
        "description": "Testing safety",
        "model_id": seed_model.id,
        "eval_type": "safety",
    }, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Safety Eval"
    assert data["status"] == "pending"
    assert data["model_id"] == seed_model.id


def test_create_evaluation_missing_model(client, auth_headers):
    resp = client.post("/api/v1/evaluations/", json={
        "name": "Bad Eval",
        "model_id": 9999,
        "eval_type": "safety",
    }, headers=auth_headers)
    assert resp.status_code == 404


def test_list_evaluations(client, seed_model, auth_headers):
    client.post("/api/v1/evaluations/", json={
        "name": "E1", "model_id": seed_model.id, "eval_type": "safety",
    }, headers=auth_headers)
    client.post("/api/v1/evaluations/", json={
        "name": "E2", "model_id": seed_model.id, "eval_type": "jailbreak",
    }, headers=auth_headers)
    resp = client.get("/api/v1/evaluations/", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_evaluations_filter_by_type(client, seed_model, auth_headers):
    client.post("/api/v1/evaluations/", json={
        "name": "E1", "model_id": seed_model.id, "eval_type": "safety",
    }, headers=auth_headers)
    client.post("/api/v1/evaluations/", json={
        "name": "E2", "model_id": seed_model.id, "eval_type": "jailbreak",
    }, headers=auth_headers)
    resp = client.get("/api/v1/evaluations/", params={"eval_type": "safety"}, headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["eval_type"] == "safety"


def test_get_evaluation(client, seed_evaluation, auth_headers):
    resp = client.get(f"/api/v1/evaluations/{seed_evaluation.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test Eval"


def test_get_evaluation_404(client, auth_headers):
    resp = client.get("/api/v1/evaluations/9999", headers=auth_headers)
    assert resp.status_code == 404


def test_get_evaluation_results_empty(client, seed_evaluation, auth_headers):
    resp = client.get(f"/api/v1/evaluations/{seed_evaluation.id}/results", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_delete_evaluation(client, seed_evaluation, auth_headers):
    resp = client.delete(f"/api/v1/evaluations/{seed_evaluation.id}", headers=auth_headers)
    assert resp.status_code == 204
    assert client.get(f"/api/v1/evaluations/{seed_evaluation.id}", headers=auth_headers).status_code == 404


def test_delete_evaluation_404(client, auth_headers):
    resp = client.delete("/api/v1/evaluations/9999", headers=auth_headers)
    assert resp.status_code == 404


def test_evaluation_stats_empty(client, auth_headers):
    resp = client.get("/api/v1/evaluations/stats/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_evaluations"] == 0
    assert data["average_safety_score"] == 0
