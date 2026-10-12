from pathlib import Path
from backend.app.models.scan import Scan, InputTypeEnum, ScanSummary
from backend.app.models.finding import Finding, SeverityEnum, FindingCategoryEnum, ScannerTypeEnum
from backend.app.services.report_generator import ReportGenerator

def test_json_and_pdf_report_generation(tmp_path):
    scan = Scan(
        id="scan-test-report",
        project_name="SecureBankingApp",
        input_type=InputTypeEnum.ZIP,
        source_identifier="sample.zip",
        summary=ScanSummary(
            total_findings=2,
            critical=1,
            high=1,
            risk_score=75.0,
            files_analyzed=10,
            total_lines_of_code=1500
        )
    )

    findings = [
        Finding(
            id="f-1",
            scan_id=scan.id,
            title="SQL Injection Vulnerability",
            description="Direct string formatting in SQL query allows arbitrary query execution.",
            severity=SeverityEnum.CRITICAL,
            category=FindingCategoryEnum.INJECTION,
            scanner=ScannerTypeEnum.MULTI_LANG_SAST,
            rule_id="RULE-SQLI-01",
            file_path="app.py",
            line_number=42,
            code_snippet="cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')",
            cwe_ids=["CWE-89"],
            remediation_guidance="Use parameterized queries."
        ),
        Finding(
            id="f-2",
            scan_id=scan.id,
            title="Hardcoded AWS Access Key",
            description="Exposed AWS credential in cleartext.",
            severity=SeverityEnum.HIGH,
            category=FindingCategoryEnum.SENSITIVE_DATA,
            scanner=ScannerTypeEnum.GITLEAKS,
            rule_id="GITLEAKS-AWS-KEY",
            file_path="config.py",
            line_number=10,
            code_snippet="AWS_KEY = 'AKIA************'",
            cwe_ids=["CWE-798"],
            remediation_guidance="Use environment variables or Secrets Manager."
        )
    ]

    # Test JSON report
    json_data = ReportGenerator.generate_json_report(scan, findings)
    assert json_data["project_name"] == "SecureBankingApp"
    assert len(json_data["findings"]) == 2
    assert "OWASP Top 10 2021" in json_data["compliance_matrix"]

    # Test PDF report
    pdf_path = tmp_path / "test_report.pdf"
    generated_path = ReportGenerator.generate_pdf_report(scan, findings, output_path=pdf_path)
    assert generated_path.exists()
    assert generated_path.stat().st_size > 1000  # Non-empty PDF
