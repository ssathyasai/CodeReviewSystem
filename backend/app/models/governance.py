from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PolicyDecisionEnum(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"


class RiskCategoryEnum(str, Enum):
    PROMPT_INJECTION = "Prompt Injection / Jailbreak"
    INDIRECT_PROMPT_INJECTION = "Indirect Prompt Injection / Hidden Context"
    PII_SENSITIVE_DATA = "PII & Sensitive Data Exposure"
    HARMFUL_CONTENT = "Prohibited & Harmful Content"
    SYSTEM_OVERRIDE = "System Instruction Override"
    SYSTEM_PROMPT_EXFILTRATION = "System Prompt Exfiltration"
    CREDENTIAL_LEAK = "API Key / Credential Exposure"
    UNSAFE_TOOL_USE = "Unsafe Code / Tool Invocation"
    UNAUTHORIZED_MODEL_ACCESS = "Unauthorized Model Access"
    RAG_DATA_LEAKAGE = "RAG Data Leakage & Cross-Tenant Violation"


class PolicyRule(BaseModel):
    id: str
    name: str
    description: str
    category: RiskCategoryEnum
    action_on_match: PolicyDecisionEnum = PolicyDecisionEnum.BLOCK
    is_enabled: bool = True
    severity: str = "HIGH"
    regex_patterns: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class PolicyViolation(BaseModel):
    rule_id: str
    rule_name: str
    category: RiskCategoryEnum
    decision: PolicyDecisionEnum
    severity: str
    evidence_snippet: str
    explanation: str
    redacted_preview: Optional[str] = None


class SensitiveEntityMatch(BaseModel):
    entity_type: str  # EMAIL, CREDIT_CARD, API_KEY, SSN, PHONE, PASSWORD, JWT
    start_pos: int
    end_pos: int
    redacted_value: str
    matched_value_masked: str


class GovernanceEvaluationRequest(BaseModel):
    prompt_text: Optional[str] = None
    response_text: Optional[str] = None
    context_metadata: Dict[str, Any] = Field(default_factory=dict)
    enforce_blocking: bool = True


class GovernanceEvaluationResult(BaseModel):
    decision: PolicyDecisionEnum
    violations: List[PolicyViolation] = Field(default_factory=list)
    detected_entities: List[SensitiveEntityMatch] = Field(default_factory=list)
    sanitized_prompt: Optional[str] = None
    sanitized_response: Optional[str] = None
    risk_score: float = 0.0  # 0 to 100
    prompt_injection_detected: bool = False
    secrets_detected: bool = False
    evaluation_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SourceCodeAiRisk(BaseModel):
    file_path: str
    line_number: int
    risk_type: str
    severity: str
    evidence: str
    explanation: str
    remediation: str


class GovernanceAuditEvent(BaseModel):
    id: str
    scan_id: Optional[str] = None
    event_type: str  # "RUNTIME_EVAL", "SOURCE_INSPECTION", "POLICY_UPDATE"
    decision: PolicyDecisionEnum
    risk_categories: List[str] = Field(default_factory=list)
    violations_count: int = 0
    sanitized_input_preview: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
