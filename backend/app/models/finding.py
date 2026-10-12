from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingCategoryEnum(str, Enum):
    INJECTION = "Injection (SQL/Command/LDAP)"
    BROKEN_AUTH = "Broken Authentication & Session"
    SENSITIVE_DATA = "Sensitive Data & Secret Exposure"
    SECURITY_MISCONFIG = "Security Misconfiguration"
    VULNERABLE_DEPENDENCY = "Vulnerable Dependency"
    INSECURE_DESERIALIZATION = "Insecure Deserialization"
    SSRF = "Server-Side Request Forgery (SSRF)"
    XSS = "Cross-Site Scripting (XSS)"
    WEAK_CRYPTO = "Cryptographic Failure"
    ACCESS_CONTROL = "Broken Access Control"
    AI_SECURITY = "LLM & AI Integration Security"
    CODE_QUALITY = "Code Quality & Maintainability"
    OTHER = "Other Security Issue"


class FindingStatusEnum(str, Enum):
    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    CONFIRMED = "CONFIRMED"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    RESOLVED = "RESOLVED"


class ScannerTypeEnum(str, Enum):
    BANDIT = "Bandit (Python SAST)"
    SEMGREP = "Semgrep AST Rules"
    GITLEAKS = "Gitleaks Secret Scanner"
    DEPENDENCY = "OSV Dependency Scanner"
    MULTI_LANG_SAST = "Multi-Language Static Engine"
    CODE_QUALITY_LINTER = "Code Quality & AST Analyzer"
    OWASP_ZAP = "OWASP ZAP / DAST Engine"
    LLM_GOVERNANCE = "LLM Governance Guardrails"
    AI_REVIEW = "AI Code Review Engine"


class Finding(BaseModel):
    id: str = Field(..., description="Unique finding ID")
    scan_id: str = Field(..., description="Associated Scan ID")
    title: str = Field(..., description="Concise vulnerability title")
    description: str = Field(..., description="Technical explanation of the flaw")
    severity: SeverityEnum = Field(..., description="Severity level")
    category: FindingCategoryEnum = Field(FindingCategoryEnum.OTHER, description="Vulnerability category")
    scanner: ScannerTypeEnum = Field(..., description="Tool or scanner name")
    rule_id: str = Field(..., description="Specific rule or CVE ID")
    
    file_path: Optional[str] = Field(None, description="Path to affected file relative to project root")
    line_number: Optional[int] = Field(None, description="Starting line number")
    end_line: Optional[int] = Field(None, description="Ending line number")
    code_snippet: Optional[str] = Field(None, description="Affected source code snippet or evidence")
    
    cwe_ids: List[str] = Field(default_factory=list, description="CWE IDs e.g. CWE-89")
    remediation_guidance: Optional[str] = Field(None, description="Step-by-step remediation advice")
    suggested_fix: Optional[str] = Field(None, description="Suggested replacement code")
    
    confidence: str = Field("HIGH", description="HIGH, MEDIUM, LOW")
    status: FindingStatusEnum = Field(FindingStatusEnum.OPEN, description="Status of the finding")
    is_false_positive: bool = Field(False, description="Flagged as false positive")
    review_notes: Optional[str] = Field(None, description="Security engineer or AI review notes")
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(use_enum_values=True)
