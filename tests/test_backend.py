import sys
import os
import pytest
import httpx

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from main import app
from db import get_scans, init_db
from engines.sast_engine import run_ast_sast_scan
from github_integration import github_integration

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.mark.anyio
async def test_health_check():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "MongoDB"

@pytest.mark.anyio
async def test_list_scans():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/scans")
        assert response.status_code == 200
        assert "scans" in response.json()

def test_sast_engine_sqli_detection(tmp_path):
    test_file = tmp_path / "vulnerable.py"
    code = "import sqlite3\nuser_input = '1 OR 1=1'\nconn = sqlite3.connect(':memory:')\ncursor = conn.cursor()\ncursor.execute(f'SELECT * FROM users WHERE id = {user_input}')\n"
    test_file.write_text(code)
    
    findings = run_ast_sast_scan(str(test_file))
    assert len(findings) > 0
    assert any("SQL Injection" in f["rule"] for f in findings)

def test_github_webhook_signature_verification():
    payload = b'{"ref": "refs/heads/main"}'
    
    # Without signature when secret is set -> should fail
    github_integration.webhook_secret = "secret123"
    assert not github_integration.verify_signature(payload, "")
    
    # Valid signature calculation
    import hmac, hashlib
    valid_sig = 'sha256=' + hmac.new(b"secret123", payload, hashlib.sha256).hexdigest()
    assert github_integration.verify_signature(payload, valid_sig)
