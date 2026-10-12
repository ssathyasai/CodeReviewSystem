import pytest
from backend.app.services.dast_engine import DastEngine

def test_dast_safety_url_validation():
    # Cloud metadata blocked
    is_safe, msg = DastEngine.validate_target_safety("http://169.254.169.254/latest/meta-data")
    assert is_safe is False
    assert "restricted" in msg.lower() or "metadata" in msg.lower()

    # Invalid scheme blocked
    is_safe, msg = DastEngine.validate_target_safety("ftp://example.com")
    assert is_safe is False

    # Empty target blocked
    is_safe, msg = DastEngine.validate_target_safety("")
    assert is_safe is False

    # Valid external target allowed
    is_safe, msg = DastEngine.validate_target_safety("https://httpbin.org")
    assert is_safe is True


@pytest.mark.anyio
async def test_dast_convert_alerts_to_findings():
    result = await DastEngine.run_dast_scan("http://169.254.169.254", "scan-test")
    assert result.status == "BLOCKED"
    assert result.is_authorized is False
