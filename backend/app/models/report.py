from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.models.scan import Scan, ScanSummary
from backend.app.models.finding import Finding
from backend.app.models.dast import DastScanResult
from backend.app.models.governance import GovernanceEvaluationResult, SourceCodeAiRisk
from backend.app.models.ai_review import AiReviewSummary


class UnifiedSecurityReport(BaseModel):
    report_id: str
    scan_id: str
    project_name: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    scan_metadata: Scan
    summary: ScanSummary
    findings: List[Finding] = Field(default_factory=list)
    dast_results: Optional[DastScanResult] = None
    ai_review: Optional[AiReviewSummary] = None
    governance_risks: List[SourceCodeAiRisk] = Field(default_factory=list)
    compliance_matrix: Dict[str, str] = Field(default_factory=dict)
    executive_summary: str
    scanner_coverage_notes: List[str] = Field(default_factory=list)
