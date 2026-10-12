import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.db.mongo import db
from backend.app.models.finding import (
    Finding,
    FindingCategoryEnum,
    FindingStatusEnum,
    ScannerTypeEnum,
    SeverityEnum,
)
from backend.app.models.governance import (
    GovernanceAuditEvent,
    GovernanceEvaluationRequest,
    GovernanceEvaluationResult,
    PolicyDecisionEnum,
    PolicyRule,
    PolicyViolation,
    RiskCategoryEnum,
    SensitiveEntityMatch,
    SourceCodeAiRisk,
)

# Standard Prompt Injection & Jailbreak Heuristics
PROMPT_INJECTION_PATTERNS = [
    {
        "id": "GOV-INJ-001",
        "name": "System Instruction Override / Ignore Previous",
        "category": RiskCategoryEnum.PROMPT_INJECTION,
        "regex": r"(?i)(?:ignore\s+all\s+(?:previous|prior)\s+instructions|disregard\s+(?:all\s+)?previous\s+rules|forget\s+your\s+instructions|override\s+system\s+prompt)",
        "severity": "CRITICAL",
        "action": PolicyDecisionEnum.BLOCK,
        "explanation": "Attempted to override system instructions and safety constraints."
    },
    {
        "id": "GOV-INJ-002",
        "name": "DAN / Jailbreak Persona Mode Activation",
        "category": RiskCategoryEnum.PROMPT_INJECTION,
        "regex": r"(?i)(?:you\s+are\s+now\s+in\s+DAN\s+mode|do\s+anything\s+now|developer\s+mode\s+enabled|unrestricted\s+mode|act\s+as\s+an\s+unfiltered|jailbreak\s+mode)",
        "severity": "CRITICAL",
        "action": PolicyDecisionEnum.BLOCK,
        "explanation": "Detected jailbreak persona pattern attempting to disable AI guardrails."
    },
    {
        "id": "GOV-INJ-003",
        "name": "Special Control Token Injection",
        "category": RiskCategoryEnum.SYSTEM_OVERRIDE,
        "regex": r"(?:<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|\[SYSTEM_MESSAGE\]|###\s*Instruction:)",
        "severity": "HIGH",
        "action": PolicyDecisionEnum.BLOCK,
        "explanation": "Injected special LLM prompt delimiter tokens to manipulate chat structure."
    },
    {
        "id": "GOV-INJ-004",
        "name": "Unsafe Tool / Shell Execution Request via Prompt",
        "category": RiskCategoryEnum.UNSAFE_TOOL_USE,
        "regex": r"(?i)(?:run\s+command\s*:\s*rm\s+-rf|curl\s+https?://|wget\s+https?://|eval\(|exec\()",
        "severity": "HIGH",
        "action": PolicyDecisionEnum.BLOCK,
        "explanation": "Prompt contains direct attempt to execute untrusted system commands or download external binaries."
    },
    {
        "id": "GOV-INJ-005",
        "name": "Indirect Prompt Injection via Hidden Markdown / HTML Comment",
        "category": RiskCategoryEnum.INDIRECT_PROMPT_INJECTION,
        "regex": r"(?i)(?:<!--\s*.*?(?:ignore|override|disregard|system|instruction).*?-->|\[\/\/\]:\s*#\s*\(.*?(?:ignore|instruction|jailbreak).*?\))",
        "severity": "CRITICAL",
        "action": PolicyDecisionEnum.BLOCK,
        "explanation": "Hidden HTML/Markdown comment containing indirect prompt injection instructions embedded in untrusted document."
    },
    {
        "id": "GOV-INJ-006",
        "name": "System Prompt Exfiltration / Leakage Probe",
        "category": RiskCategoryEnum.SYSTEM_PROMPT_EXFILTRATION,
        "regex": r"(?i)(?:repeat\s+(?:all\s+)?(?:the\s+)?text\s+above|print\s+(?:your\s+)?(?:system\s+prompt|initial\s+prompt)|what\s+(?:is|were)\s+your\s+(?:system\s+instructions|initial\s+instructions)|show\s+me\s+your\s+(?:system\s+prompt|rules)|output\s+(?:your\s+)?initialization\s+message|verbatim\s+system\s+instructions)",
        "severity": "HIGH",
        "action": PolicyDecisionEnum.BLOCK,
        "explanation": "Attempted to exfiltrate and expose confidential system prompts or internal agent instructions."
    },
    {
        "id": "GOV-INJ-007",
        "name": "RAG Cross-Tenant Data Leakage / Isolation Failure",
        "category": RiskCategoryEnum.RAG_DATA_LEAKAGE,
        "regex": r"(?i)(?:\[CONFIDENTIAL_INTERNAL\]|\[RESTRICTED_ACCESS\]|\[TENANT_[A-Za-z0-9_]+\]|classified_project_data)",
        "severity": "HIGH",
        "action": PolicyDecisionEnum.WARN,
        "explanation": "Prompt or retrieved RAG context contains multi-tenant classification tags from a segregated partition."
    },
    {
        "id": "GOV-INJ-008",
        "name": "Excessive AI Tool Permissions / Privilege Escalation",
        "category": RiskCategoryEnum.UNSAFE_TOOL_USE,
        "regex": r"(?i)(?:bypass\s+permissions|grant\s+root|sudo\s+access|execute\s+as\s+admin|disable\s+safety\s+checks)",
        "severity": "HIGH",
        "action": PolicyDecisionEnum.BLOCK,
        "explanation": "Detected attempt to manipulate AI tool permissions or escalate execution privileges."
    }
]

# Sensitive Data Entity Regexes (Presidio-equivalent)
SENSITIVE_ENTITY_PATTERNS = [
    {
        "type": "EMAIL",
        "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "redact": "[REDACTED_EMAIL]"
    },
    {
        "type": "CREDIT_CARD",
        "regex": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",
        "redact": "[REDACTED_CREDIT_CARD]"
    },
    {
        "type": "SSN",
        "regex": r"\b\d{3}-\d{2}-\d{4}\b",
        "redact": "[REDACTED_SSN]"
    },
    {
        "type": "API_KEY",
        "regex": r"\b(?:sk-[a-zA-Z0-9]{20,50}|ghp_[a-zA-Z0-9]{36}|AKIA[A-Z0-9]{16})\b",
        "redact": "[REDACTED_SECRET_KEY]"
    },
    {
        "type": "PHONE",
        "regex": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "redact": "[REDACTED_PHONE]"
    }
]

# Source-code AI Integration Risk Patterns
SOURCE_AI_PATTERNS = [
    {
        "id": "AI-RAW-PROMPT-CONCAT",
        "title": "Unsanitized User Input in LLM Prompt Template",
        "regex": r"(?:f['\"].*?(?:prompt|input|query|user_msg).*?\{|messages\.append\(\s*\{['\"]role['\"]\s*:\s*['\"]user['\"]\s*,\s*['\"]content['\"]\s*:\s*(?:user_input|req\.|request\.)\b)",
        "severity": SeverityEnum.HIGH,
        "risk_type": "Direct Prompt Injection Risk",
        "explanation": "Directly concatenating untrusted user input into LLM system or user prompts without validation allows prompt injection.",
        "remediation": "Validate input with LLM Governance guardrails, sanitize input delimiters, and enforce structured JSON schemas."
    },
    {
        "id": "AI-EXPOSED-KEY",
        "title": "Hardcoded AI Model Provider API Key",
        "regex": r"(?:openai\.api_key\s*=\s*['\"]sk-|anthropic\.api_key\s*=\s*['\"]sk-ant|genai\.configure\(api_key=['\"])",
        "severity": SeverityEnum.CRITICAL,
        "risk_type": "Credential Compromise",
        "explanation": "Hardcoded AI API key found in code. Anyone with access to the codebase can make billable or unauthorized API calls.",
        "remediation": "Load API keys from environment variables (`os.getenv('OPENAI_API_KEY')`)."
    },
    {
        "id": "AI-UNSAFE-CODE-EXEC",
        "title": "Unchecked Execution of LLM-Generated Code",
        "regex": r"(?:eval|exec)\s*\(\s*(?:response|completion|result|model_out|ai_res)",
        "severity": SeverityEnum.CRITICAL,
        "risk_type": "Arbitrary Code Execution",
        "explanation": "Executing LLM output directly with eval() or exec() creates a catastrophic Remote Code Execution vulnerability.",
        "remediation": "Never evaluate untrusted LLM output directly. Execute in an isolated sandbox or parse safe data structures."
    },
    {
        "id": "AI-MISSING-OUTPUT-VALIDATION",
        "title": "Missing Guardrails / Structured Output Validation",
        "regex": r"client\.chat\.completions\.create\([^)]*response_format\s*=\s*None",
        "severity": SeverityEnum.MEDIUM,
        "risk_type": "Output Poisoning / Schema Inconsistency",
        "explanation": "Calling LLM API without structured output constraints or post-generation governance validation.",
        "remediation": "Use Pydantic structured outputs or run LLM Governance post-processing before rendering."
    },
    {
        "id": "AI-RAG-LEAKAGE",
        "title": "RAG Retrieval Missing Tenant Isolation Filter",
        "regex": r"(?:similarity_search|similarity_search_by_vector|query)\s*\([^)]*(?:without\s+filter|filter\s*=\s*None|\bquery\s*=\s*user_query\s*\))",
        "severity": SeverityEnum.HIGH,
        "risk_type": "RAG Cross-Tenant Data Leakage",
        "explanation": "Querying vector embeddings without tenant or user authorization filters causes cross-tenant knowledge retrieval leakage.",
        "remediation": "Always pass tenant namespace metadata in vector searches: `filter={'tenant_id': current_user.tenant_id}`."
    },
    {
        "id": "AI-UNAUTHORIZED-MODEL",
        "title": "Unsanitized Client-Controlled Model Selection",
        "regex": r"(?:model\s*=\s*request\.(?:args|data|json)|model\s*=\s*req\.(?:body|query)|client\.models\.get\(request\.)",
        "severity": SeverityEnum.HIGH,
        "risk_type": "Unauthorized Model Access",
        "explanation": "Allowing client input to dictate the backend model name enables unauthorized model usage or denial of service.",
        "remediation": "Restrict model selection to a strictly validated server-side whitelist."
    },
    {
        "id": "AI-EXCESSIVE-TOOL-PERMS",
        "title": "Excessive AI Agent Tool Permissions (Shell/OS Execution)",
        "regex": r"(?:ShellTool\(|TerminalTool\(|BashProcess\(|PythonAstREPLTool\(|SystemExecuteTool\()",
        "severity": SeverityEnum.CRITICAL,
        "risk_type": "Excessive AI Tool Permissions",
        "explanation": "Binding unrestricted OS shell, terminal, or REPL tools to an AI agent allows remote agent takeover and server compromise.",
        "remediation": "Enforce principle of least privilege. Grant AI agents only read-only, sandboxed APIs with human-in-the-loop approvals."
    }
]


class GovernanceEngine:
    @classmethod
    def evaluate_text(cls, req: GovernanceEvaluationRequest, scan_id: Optional[str] = None) -> GovernanceEvaluationResult:
        """
        Performs real-time LLM Governance evaluation:
        1. Checks for prompt injection & system instruction overrides
        2. Detects and redacts sensitive PII & secrets
        3. Enforces Allow / Warn / Block decisions
        4. Logs audit event to database
        """
        start_t = time.time()
        combined_text = f"{req.prompt_text or ''} {req.response_text or ''}".strip()
        
        violations: List[PolicyViolation] = []
        detected_entities: List[SensitiveEntityMatch] = []
        
        decision = PolicyDecisionEnum.ALLOW
        has_prompt_injection = False
        has_secrets = False
        risk_score = 0.0

        # 1. Prompt Injection Checks
        if req.prompt_text:
            for rule in PROMPT_INJECTION_PATTERNS:
                match = re.search(rule["regex"], req.prompt_text)
                if match:
                    has_prompt_injection = True
                    decision = PolicyDecisionEnum.BLOCK if req.enforce_blocking else PolicyDecisionEnum.WARN
                    risk_score = max(risk_score, 85.0 if rule["severity"] == "HIGH" else 98.0)
                    
                    violations.append(PolicyViolation(
                        rule_id=rule["id"],
                        rule_name=rule["name"],
                        category=rule["category"],
                        decision=decision,
                        severity=rule["severity"],
                        evidence_snippet=match.group(0),
                        explanation=rule["explanation"]
                    ))

        # 2. Sensitive Data & PII Detection
        sanitized_prompt = req.prompt_text
        sanitized_response = req.response_text

        for entity_rule in SENSITIVE_ENTITY_PATTERNS:
            # Check prompt
            if sanitized_prompt:
                for match in re.finditer(entity_rule["regex"], sanitized_prompt):
                    has_secrets = True
                    val = match.group(0)
                    masked = val[:2] + "*" * (len(val) - 4) + val[-2:] if len(val) > 4 else "***"
                    detected_entities.append(SensitiveEntityMatch(
                        entity_type=entity_rule["type"],
                        start_pos=match.start(),
                        end_pos=match.end(),
                        redacted_value=entity_rule["redact"],
                        matched_value_masked=masked
                    ))
                    if decision != PolicyDecisionEnum.BLOCK:
                        decision = PolicyDecisionEnum.WARN
                    risk_score = max(risk_score, 65.0)

                sanitized_prompt = re.sub(entity_rule["regex"], entity_rule["redact"], sanitized_prompt)

            # Check response
            if sanitized_response:
                for match in re.finditer(entity_rule["regex"], sanitized_response):
                    has_secrets = True
                    val = match.group(0)
                    masked = val[:2] + "*" * (len(val) - 4) + val[-2:] if len(val) > 4 else "***"
                    detected_entities.append(SensitiveEntityMatch(
                        entity_type=entity_rule["type"],
                        start_pos=match.start(),
                        end_pos=match.end(),
                        redacted_value=entity_rule["redact"],
                        matched_value_masked=masked
                    ))
                    if decision != PolicyDecisionEnum.BLOCK:
                        decision = PolicyDecisionEnum.WARN
                    risk_score = max(risk_score, 65.0)

                sanitized_response = re.sub(entity_rule["regex"], entity_rule["redact"], sanitized_response)

        # Record audit event
        audit_event = GovernanceAuditEvent(
            id=f"gov-evt-{uuid.uuid4().hex[:8]}",
            scan_id=scan_id,
            event_type="RUNTIME_EVAL",
            decision=decision,
            risk_categories=list({v.category.value for v in violations} | ({RiskCategoryEnum.PII_SENSITIVE_DATA.value} if has_secrets else set())),
            violations_count=len(violations),
            sanitized_input_preview=(sanitized_prompt or "")[:120]
        )
        try:
            db.governance_events.insert_one(audit_event.model_dump())
        except Exception:
            pass

        eval_ms = round((time.time() - start_t) * 1000, 2)

        return GovernanceEvaluationResult(
            decision=decision,
            violations=violations,
            detected_entities=detected_entities,
            sanitized_prompt=sanitized_prompt,
            sanitized_response=sanitized_response,
            risk_score=risk_score,
            prompt_injection_detected=has_prompt_injection,
            secrets_detected=has_secrets,
            evaluation_time_ms=eval_ms
        )

    @classmethod
    def inspect_source_code_ai_risks(cls, workspace_path: Path, scan_id: str) -> Tuple[List[SourceCodeAiRisk], List[Finding]]:
        """
        Scans project source code to identify AI/LLM integration vulnerabilities:
        - Unsanitized prompt construction
        - Exposed model API keys
        - Insecure code execution on LLM outputs
        - Missing output guardrails
        """
        risks: List[SourceCodeAiRisk] = []
        findings: List[Finding] = []

        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "__pycache__", "dist"]]
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                if ext not in [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go"]:
                    continue

                rel_path = str(file_path.relative_to(workspace_path))
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except Exception:
                    continue

                for line_idx, line in enumerate(lines, start=1):
                    for pat in SOURCE_AI_PATTERNS:
                        if re.search(pat["regex"], line):
                            snippet = line.strip()
                            risk_item = SourceCodeAiRisk(
                                file_path=rel_path,
                                line_number=line_idx,
                                risk_type=pat["risk_type"],
                                severity=pat["severity"].value,
                                evidence=snippet,
                                explanation=pat["explanation"],
                                remediation=pat["remediation"]
                            )
                            risks.append(risk_item)

                            # Also add to normalized Findings
                            findings.append(Finding(
                                id=f"gov-find-{uuid.uuid4().hex[:8]}",
                                scan_id=scan_id,
                                title=f"LLM Governance: {pat['title']}",
                                description=pat["explanation"],
                                severity=pat["severity"],
                                category=FindingCategoryEnum.AI_SECURITY,
                                scanner=ScannerTypeEnum.LLM_GOVERNANCE,
                                rule_id=pat["id"],
                                file_path=rel_path,
                                line_number=line_idx,
                                code_snippet=snippet,
                                cwe_ids=["CWE-20", "CWE-94"],
                                remediation_guidance=pat["remediation"],
                                confidence="HIGH"
                            ))

        return risks, findings

    @classmethod
    def sanitize_code_for_ai(cls, code_content: str) -> str:
        """Sanitizes code by redacting sensitive secrets before sending to external LLMs."""
        sanitized = code_content
        for entity in SENSITIVE_ENTITY_PATTERNS:
            sanitized = re.sub(entity["regex"], entity["redact"], sanitized)
        return sanitized
