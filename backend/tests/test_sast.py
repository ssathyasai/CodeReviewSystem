from pathlib import Path
from backend.app.services.sast_engine import SastEngine
from backend.app.models.finding import FindingCategoryEnum, SeverityEnum

def test_sast_on_vulnerable_project(tmp_path):
    app_file = tmp_path / "app.py"
    app_file.write_text(
        'AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"\n'
        'AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n'
        'def get_user(user_id):\n'
        '    query = f"SELECT * FROM users WHERE id = \'{user_id}\' AND active = 1"\n'
        '    return query\n'
    )
    reqs_file = tmp_path / "requirements.txt"
    reqs_file.write_text("pyyaml==5.3.1\nurllib3==1.26.5\n")

    findings = SastEngine.run_sast(tmp_path, "test-scan-123")
    
    assert len(findings) > 0
    rule_ids = {f.rule_id for f in findings}
    
    # Check that key vulnerabilities were identified
    assert any("SQLI" in r or "89" in str(r) for r in rule_ids)
    assert any("AWS" in r or "GITLEAKS" in r for r in rule_ids)
    assert any("CVE" in f.rule_id or "VULN" in str(f.category) for f in findings)


def test_secret_detection_and_masking(tmp_path):
    secret_file = tmp_path / "credentials.py"
    secret_file.write_text("AWS_ACCESS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'\n")

    findings = SastEngine._run_secret_scanner(tmp_path, "scan-sec")
    assert len(findings) >= 1
    assert findings[0].severity == SeverityEnum.CRITICAL
    assert "AKIA" in findings[0].code_snippet
    assert "***" in findings[0].code_snippet


def test_code_quality_and_linting_checks(tmp_path):
    # File with syntax error
    bad_syntax_file = tmp_path / "broken.py"
    bad_syntax_file.write_text("def broken_syntax(\n")

    # File with code quality issues (unused import, mutable default, zero division, unused var, high complexity)
    quality_file = tmp_path / "quality_issues.py"
    quality_file.write_text(
        "import math\n"
        "import os\n"
        "def compute(data, items=[]):\n"
        "    unused_val = 100\n"
        "    crash = 10 / 0\n"
        "    if data == 1:\n"
        "        return 1\n"
        "    elif data == 2:\n"
        "        return 2\n"
        "    elif data == 3:\n"
        "        return 3\n"
        "    elif data == 4:\n"
        "        return 4\n"
        "    elif data == 5:\n"
        "        return 5\n"
        "    elif data == 6:\n"
        "        return 6\n"
        "    elif data == 7:\n"
        "        return 7\n"
        "    elif data == 8:\n"
        "        return 8\n"
        "    elif data == 9:\n"
        "        return 9\n"
        "    elif data == 10:\n"
        "        return 10\n"
        "    elif data == 11:\n"
        "        return 11\n"
        "    return 0\n"
    )

    findings = SastEngine._run_code_quality_and_lint(tmp_path, "scan-qual")
    rule_ids = {f.rule_id for f in findings}
    
    assert "CODE-SYNTAX-ERROR" in rule_ids
    assert "CODE-MUTABLE-DEFAULT" in rule_ids
    assert "CODE-ZERO-DIVISION" in rule_ids
    assert "CODE-UNUSED-IMPORT" in rule_ids
    assert "CODE-UNUSED-VARIABLE" in rule_ids
    assert "CODE-HIGH-COMPLEXITY" in rule_ids


def test_sast_ssrf_and_access_control(tmp_path):
    vuln_file = tmp_path / "api_routes.py"
    vuln_file.write_text(
        "import requests\n"
        "import random\n"
        "def fetch_remote(request):\n"
        "    res = requests.get(request.args['url'])\n"
        "    token = random.random()\n"
        "    user = User.objects.get(id=request.GET['id'])\n"
        "    admin_pass = 'admin'\n"
        "    return res.text\n"
    )

    findings = SastEngine._run_pattern_rules(tmp_path, "scan-ssrf")
    rule_ids = {f.rule_id for f in findings}

    assert "SEC-SSRF-UNVALIDATED" in rule_ids
    assert "SEC-IDOR-QUERY" in rule_ids
    assert "SEC-WEAK-RNG-AUTH" in rule_ids
    assert "SEC-DEFAULT-CREDENTIALS" in rule_ids
