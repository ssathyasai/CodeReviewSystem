import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"


def test_metrics_endpoint():
    response = client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_scans" in data
    assert "severity_distribution" in data


def test_governance_evaluate_api():
    response = client.post(
        "/api/governance/evaluate",
        json={"prompt_text": "Hello world, what is the weather?", "enforce_blocking": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "ALLOW"
    assert data["prompt_injection_detected"] is False


def test_seed_demo_data_api():
    response = client.post("/api/demo/seed")
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"

    # Now verify scans endpoint lists it
    scans_resp = client.get("/api/scans")
    assert scans_resp.status_code == 200
    scans = scans_resp.json()["scans"]
    assert any(s["id"] == "scan-demo-banking-api" for s in scans)


def test_remediate_and_download_api():
    client.post("/api/demo/seed")
    remed_resp = client.post("/api/scans/scan-demo-banking-api/remediate")
    assert remed_resp.status_code == 200
    res_data = remed_resp.json()
    assert res_data["success"] is True
    assert res_data["risk_score"] == 0.0

    dl_resp = client.get("/api/scans/scan-demo-banking-api/download-fixed")
    assert dl_resp.status_code == 200
    assert "zip" in dl_resp.headers.get("content-type", "")

