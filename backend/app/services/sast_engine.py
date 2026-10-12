import ast
import json
import logging
import os
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.models.finding import (
    Finding,
    FindingCategoryEnum,
    FindingStatusEnum,
    ScannerTypeEnum,
    SeverityEnum,
)

logger = logging.getLogger("codereview.sast")

# Known secret scanning regexes (Gitleaks standard patterns)
SECRET_PATTERNS = [
    {
        "id": "GITLEAKS-AWS-KEY",
        "title": "AWS Access Key ID Detected",
        "regex": r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.SENSITIVE_DATA,
        "cwe": ["CWE-798", "CWE-312"],
        "description": "Hardcoded AWS Access Key ID exposed in source code.",
        "remediation": "Revoke the AWS access key immediately in AWS IAM and load secrets securely from AWS Secrets Manager or environment variables."
    },
    {
        "id": "GITLEAKS-AWS-SECRET",
        "title": "AWS Secret Access Key Pattern",
        "regex": r"(?i)aws_secret_access_key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.SENSITIVE_DATA,
        "cwe": ["CWE-798"],
        "description": "Hardcoded AWS Secret Access Key identified.",
        "remediation": "Store AWS Secret Access Keys in secure parameter stores and rotate compromised credentials."
    },
    {
        "id": "GITLEAKS-GITHUB-PAT",
        "title": "GitHub Personal Access Token Detected",
        "regex": r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82}",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.SENSITIVE_DATA,
        "cwe": ["CWE-798", "CWE-200"],
        "description": "GitHub Personal Access Token (PAT) found in cleartext.",
        "remediation": "Revoke the GitHub token at github.com/settings/tokens and store access credentials in GitHub Actions Secrets or a secrets manager."
    },
    {
        "id": "GITLEAKS-PRIVATE-KEY",
        "title": "Private RSA/EC/OpenSSH Cryptographic Key",
        "regex": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.SENSITIVE_DATA,
        "cwe": ["CWE-312", "CWE-321"],
        "description": "Unencrypted private cryptographic key file or inline string discovered.",
        "remediation": "Remove private keys from repository history. Use PKI key vaults and hardware security modules (HSM)."
    },
    {
        "id": "GITLEAKS-JWT-TOKEN",
        "title": "Hardcoded JSON Web Token (JWT)",
        "regex": r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.SENSITIVE_DATA,
        "cwe": ["CWE-798"],
        "description": "Hardcoded JWT token embedded in code.",
        "remediation": "Never hardcode JWT tokens. Generate tokens dynamically during user authentication sessions."
    },
    {
        "id": "GITLEAKS-GENERIC-API-KEY",
        "title": "Hardcoded Generic API Key / Secret Token",
        "regex": r"(?i)(?:api_key|apikey|secret_key|auth_token|client_secret|access_token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,64}['\"]",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.SENSITIVE_DATA,
        "cwe": ["CWE-798"],
        "description": "API Key or authentication token stored directly in code.",
        "remediation": "Move all API keys to environment variables (.env) or KMS services."
    },
    {
        "id": "GITLEAKS-STRIPE-KEY",
        "title": "Stripe Live/Test Secret API Key",
        "regex": r"sk_live_[0-9a-zA-Z]{24}|rk_live_[0-9a-zA-Z]{24}",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.SENSITIVE_DATA,
        "cwe": ["CWE-798"],
        "description": "Stripe production secret key exposed.",
        "remediation": "Immediately roll the Stripe API key from Stripe Dashboard and update secret configs."
    },
    {
        "id": "GITLEAKS-OPENAI-KEY",
        "title": "OpenAI / AI Service Secret API Key",
        "regex": r"sk-[a-zA-Z0-9]{20,48}|sk-proj-[a-zA-Z0-9_-]{40,120}",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.AI_SECURITY,
        "cwe": ["CWE-798"],
        "description": "OpenAI API secret key discovered in source code.",
        "remediation": "Revoke key on platform.openai.com/api-keys and use backend environment variables."
    }
]

# Multi-language static rules (Semgrep / AST level patterns)
MULTI_LANG_RULES = [
    # Python Security Rules
    {
        "id": "PY-SQLI-FORMAT",
        "title": "SQL Injection via String Formatting / F-strings",
        "extensions": [".py"],
        "regex": r"(?:(?:execute|raw|cursor\.execute)\s*\(\s*(?:f['\"].*?\{|\".*?%|\'.*?%|f\"\"\".*?\{|f\'\'\'.*?\{)|(?:query|sql|stmt|statement)\s*=\s*f['\"].*?(?:SELECT|INSERT|UPDATE|DELETE|WHERE|FROM)\b)",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.INJECTION,
        "cwe": ["CWE-89"],
        "description": "Executing raw SQL query constructed with string formatting or f-strings allows arbitrary SQL command execution.",
        "remediation": "Use parameterized queries or ORM queries. Example: `cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))`"
    },
    {
        "id": "PY-CMD-INJECTION",
        "title": "Command Injection in OS / Subprocess Execution",
        "extensions": [".py"],
        "regex": r"(?:os\.system|os\.popen|subprocess\.call|subprocess\.Popen|subprocess\.run)\s*\(\s*(?:f['\"].*?\{|.*?\+.*?|shell\s*=\s*True)",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.INJECTION,
        "cwe": ["CWE-78"],
        "description": "Passing user-controlled input or `shell=True` to system command execution allows remote arbitrary code execution.",
        "remediation": "Use `subprocess.run(['command', arg1, arg2], shell=False)` with a structured list of arguments instead of a raw shell string."
    },
    {
        "id": "PY-INSECURE-DESERIALIZATION",
        "title": "Insecure Deserialization (pickle / marshal / yaml.load)",
        "extensions": [".py"],
        "regex": r"(?:pickle\.loads?|marshal\.loads?|_pickle\.loads?|yaml\.load\s*\([^,)]*\))",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.INSECURE_DESERIALIZATION,
        "cwe": ["CWE-502"],
        "description": "Deserializing untrusted data with pickle or unloader yaml can trigger arbitrary code execution via Python object instantiations.",
        "remediation": "Use safe serialization formats such as JSON (`json.loads`) or safe YAML (`yaml.safe_load`)."
    },
    {
        "id": "PY-WEAK-HASH",
        "title": "Use of Broken / Weak Cryptographic Hash (MD5 / SHA1)",
        "extensions": [".py"],
        "regex": r"hashlib\.(?:md5|sha1)\s*\(",
        "severity": SeverityEnum.MEDIUM,
        "category": FindingCategoryEnum.WEAK_CRYPTO,
        "cwe": ["CWE-327", "CWE-328"],
        "description": "MD5 and SHA-1 algorithms are vulnerable to collision attacks and must not be used for security-sensitive purposes.",
        "remediation": "Use SHA-256 (`hashlib.sha256()`) or for passwords use `bcrypt` / `argon2`."
    },
    {
        "id": "PY-DEBUG-ENABLED",
        "title": "Production Debug Mode Enabled (Flask/Django)",
        "extensions": [".py"],
        "regex": r"(?:app\.run\(.*debug\s*=\s*True|DEBUG\s*=\s*True)",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.SECURITY_MISCONFIG,
        "cwe": ["CWE-489", "CWE-215"],
        "description": "Running web applications with debug mode enabled leaks stack traces, environment variables, and enables interactive debug shells.",
        "remediation": "Disable debug mode in production: `DEBUG = False` or control via `os.getenv('DEBUG', 'false').lower() == 'true'`."
    },
    {
        "id": "PY-PATH-TRAVERSAL",
        "title": "Arbitrary File Read / Path Traversal",
        "extensions": [".py"],
        "regex": r"open\s*\(\s*(?:f['\"].*?\{|os\.path\.join\([^)]*request|path\s*\+)",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.ACCESS_CONTROL,
        "cwe": ["CWE-22"],
        "description": "Opening file paths derived from user inputs without canonicalization checks enables unauthorized file access (e.g. `../../etc/passwd`).",
        "remediation": "Validate paths using `os.path.abspath` and verify `target_path.startswith(safe_base_dir)`."
    },

    # JavaScript / TypeScript Rules
    {
        "id": "JS-DOM-XSS",
        "title": "Cross-Site Scripting (XSS) via innerHTML / eval",
        "extensions": [".js", ".jsx", ".ts", ".tsx"],
        "regex": r"(?:\.innerHTML\s*=|dangerouslySetInnerHTML|eval\s*\(|new\s+Function\s*\(|document\.write\s*\()",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.XSS,
        "cwe": ["CWE-79"],
        "description": "Directly assigning unsanitized dynamic content to `innerHTML` or `eval` enables client-side Cross-Site Scripting (XSS).",
        "remediation": "Use `textContent`, DOMPurify sanitization, or framework-safe JSX bindings."
    },
    {
        "id": "JS-SQLI-CONCAT",
        "title": "Node.js SQL Injection via String Concatenation",
        "extensions": [".js", ".ts"],
        "regex": r"(?:db\.query|client\.query|sequelize\.query|connection\.query)\s*\(\s*(?:`SELECT.*?\$|`INSERT.*?\$|`UPDATE.*?\$|\"SELECT.*?\s*\+|\'SELECT.*?\s*\+)",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.INJECTION,
        "cwe": ["CWE-89"],
        "description": "Constructing SQL statements through string concatenation or template literals exposes database to SQL injection.",
        "remediation": "Use parameterized queries. E.g.: `db.query('SELECT * FROM users WHERE id = $1', [userId])`."
    },
    {
        "id": "JS-COMMAND-EXEC",
        "title": "Command Injection in child_process.exec",
        "extensions": [".js", ".ts"],
        "regex": r"(?:child_process\.exec|exec\s*\(\s*`|execSync\s*\(\s*`)",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.INJECTION,
        "cwe": ["CWE-78"],
        "description": "Executing shell commands directly using `child_process.exec` allows arbitrary command execution if input contains shell metacharacters.",
        "remediation": "Use `child_process.execFile` or `spawn` without shell invocation."
    },
    {
        "id": "JS-INSECURE-TLS",
        "title": "Disabled TLS/SSL Certificate Verification",
        "extensions": [".js", ".ts"],
        "regex": r"rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0['\"]?",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.SECURITY_MISCONFIG,
        "cwe": ["CWE-295"],
        "description": "Disabling TLS certificate validation allows Man-in-the-Middle (MITM) attacks and credential theft.",
        "remediation": "Keep `rejectUnauthorized: true` and install trusted root CA certificates."
    },

    # Java Security Rules
    {
        "id": "JAVA-SQLI-CONCAT",
        "title": "Java SQL Injection via Statement Concatenation",
        "extensions": [".java"],
        "regex": r"(?:createStatement\s*\(\)\.executeQuery|prepareStatement\s*\(\s*['\"].*?\+)",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.INJECTION,
        "cwe": ["CWE-89"],
        "description": "Dynamically concatenating input into SQL statements in JDBC.",
        "remediation": "Use `PreparedStatement` with placeholder parameters (`?`) and `pstmt.setString(1, val)`."
    },
    {
        "id": "JAVA-COMMAND-EXEC",
        "title": "Java Process / Runtime Command Execution",
        "extensions": [".java"],
        "regex": r"Runtime\.getRuntime\(\)\.exec\s*\(|ProcessBuilder\s*\(",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.INJECTION,
        "cwe": ["CWE-78"],
        "description": "Direct command execution through Runtime or ProcessBuilder.",
        "remediation": "Sanitize arguments rigorously and avoid executing OS commands directly."
    },
    {
        "id": "JAVA-XXE-INJECTION",
        "title": "XML External Entity (XXE) Vulnerability",
        "extensions": [".java"],
        "regex": r"DocumentBuilderFactory\.newInstance\(\)|SAXParserFactory\.newInstance\(\)",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.INJECTION,
        "cwe": ["CWE-611"],
        "description": "XML parser instantiated without explicitly disabling DTDs or external general entities.",
        "remediation": "Set `factory.setFeature('http://apache.org/xml/features/disallow-doctype-decl', true)`."
    },

    # C / C++ Rules
    {
        "id": "CPP-BUFFER-OVERFLOW",
        "title": "Unsafe C/C++ Buffer Operations (strcpy/strcat/gets/sprintf)",
        "extensions": [".c", ".cpp", ".cc", ".h", ".hpp"],
        "regex": r"\b(?:strcpy|strcat|gets|sprintf|vsprintf)\s*\(",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.OTHER,
        "cwe": ["CWE-120", "CWE-676"],
        "description": "Using unsafe C memory functions without bounds checking causes stack buffer overflow and remote code execution.",
        "remediation": "Replace with bounded functions: `strncpy`, `strncat`, `snprintf`, or modern C++ `std::string`."
    },

    # PHP Rules
    {
        "id": "PHP-CODE-EVAL",
        "title": "PHP Arbitrary Code Evaluation / RCE",
        "extensions": [".php"],
        "regex": r"\b(?:eval|assert|passthru|system|shell_exec|exec)\s*\(\s*\$_(?:GET|POST|REQUEST|COOKIE)",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.INJECTION,
        "cwe": ["CWE-94", "CWE-78"],
        "description": "Passing user input directly to PHP execution functions leads to Remote Code Execution.",
        "remediation": "Never pass untrusted user variables into `eval()` or system execution functions."
    },

    # Go Rules
    {
        "id": "GO-SQLI-FORMAT",
        "title": "Go SQL Injection via fmt.Sprintf",
        "extensions": [".go"],
        "regex": r"(?:db\.Query|db\.Exec)\s*\(\s*fmt\.Sprintf\s*\(",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.INJECTION,
        "cwe": ["CWE-89"],
        "description": "Constructing SQL queries using `fmt.Sprintf` in Go leads to SQL injection.",
        "remediation": "Use database driver query parameters: `db.Query('SELECT * FROM users WHERE id = $1', id)`."
    },

    # SSRF & Access Control Rules
    {
        "id": "SEC-SSRF-UNVALIDATED",
        "title": "Server-Side Request Forgery (SSRF) via User URL",
        "extensions": [".py", ".js", ".ts"],
        "regex": r"(?:requests\.(?:get|post|put|delete)|httpx\.(?:get|post)|urllib\.request\.urlopen|axios\.(?:get|post)|fetch)\s*\(\s*(?:request\.(?:args|GET|POST|params|query|data)|req\.(?:query|body|params)|url_param|user_url)",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.SSRF,
        "cwe": ["CWE-918"],
        "description": "Making outbound HTTP requests using untrusted user-supplied URLs without IP range or domain validation causes Server-Side Request Forgery (SSRF).",
        "remediation": "Validate target URLs against a strict domain whitelist and reject private IP ranges (127.0.0.1, 10.x, 169.254.169.254)."
    },
    {
        "id": "SEC-IDOR-QUERY",
        "title": "Broken Access Control / Insecure Direct Object Reference (IDOR)",
        "extensions": [".py", ".js", ".ts"],
        "regex": r"(?:(?:objects\.get|find_one|findById|findByPk)\s*\(\s*(?:id|pk)\s*=\s*(?:request\.|req\.(?:params|query))\b|(?:WHERE|where:)\s*\{?\s*(?:id|_id)\s*[:=]\s*(?:req\.|request\.))",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.ACCESS_CONTROL,
        "cwe": ["CWE-639", "CWE-284"],
        "description": "Fetching database entity directly by client-supplied ID without verifying ownership or tenant permissions leads to Broken Access Control (IDOR).",
        "remediation": "Always verify that the requesting user (`request.user.id`) is authorized to access or modify the target object."
    },
    {
        "id": "SEC-WEAK-RNG-AUTH",
        "title": "Weak Cryptographic PRNG Used for Security Tokens",
        "extensions": [".py", ".js", ".ts"],
        "regex": r"(?:(?:token|secret|session|auth|password|key|otp)\w*\s*[:=]\s*(?:random\.random|random\.randint|Math\.random)|(?:random\.random\(\)|random\.randint\(|Math\.random\(\)).*?(?:token|secret|session|auth|password|key|otp))",
        "severity": SeverityEnum.HIGH,
        "category": FindingCategoryEnum.WEAK_CRYPTO,
        "cwe": ["CWE-330", "CWE-338"],
        "description": "Using standard pseudo-random number generator (PRNG) for cryptographic tokens, passwords, or session IDs creates predictable values.",
        "remediation": "Use cryptographically secure random sources: Python `secrets.token_hex()` or Node.js `crypto.randomBytes()`."
    },
    {
        "id": "SEC-DEFAULT-CREDENTIALS",
        "title": "Hardcoded Default / Weak Administrative Credentials",
        "extensions": [".py", ".js", ".ts", ".json", ".yaml", ".yml"],
        "regex": r"(?i)(?:password|passwd|pwd|admin_pass)\s*[:=]\s*['\"](?:admin|password123|root|123456|toor|default)['\"]",
        "severity": SeverityEnum.CRITICAL,
        "category": FindingCategoryEnum.BROKEN_AUTH,
        "cwe": ["CWE-798", "CWE-1392"],
        "description": "Default or hardcoded administrative credentials identified in source code or configuration files.",
        "remediation": "Never use default credentials. Force unique password generation and load from environment variables."
    },
    {
        "id": "SEC-INSECURE-CORS",
        "title": "Insecure CORS Policy with Allow-Credentials",
        "extensions": [".py", ".js", ".ts"],
        "regex": r"(?:allow_origins\s*=\s*\[\s*['\"]\*['\"]\s*\]\s*,\s*allow_credentials\s*=\s*True|cors\(.*origin:\s*['\"].?\*['\"].*credentials:\s*true)",
        "severity": SeverityEnum.MEDIUM,
        "category": FindingCategoryEnum.SECURITY_MISCONFIG,
        "cwe": ["CWE-942"],
        "description": "Permissive CORS configuration allowing wildcard origin combined with credentials exposes cross-origin authentication data.",
        "remediation": "Specify an explicit list of trusted frontend origins when `credentials=True`."
    }
]

# Vulnerable dependencies database (OSV-Scanner equivalent rules)
VULNERABLE_PACKAGES_DB = [
    {"eco": "npm", "pkg": "lodash", "vuln_below": "4.17.21", "cve": "CVE-2021-23337", "sev": SeverityEnum.HIGH, "title": "Command Injection in lodash.template"},
    {"eco": "npm", "pkg": "axios", "vuln_below": "1.7.4", "cve": "CVE-2024-39338", "sev": SeverityEnum.HIGH, "title": "Axios Server-Side Request Forgery (SSRF)"},
    {"eco": "npm", "pkg": "jsonwebtoken", "vuln_below": "9.0.0", "cve": "CVE-2022-23529", "sev": SeverityEnum.HIGH, "title": "Insecure Key Verification in jsonwebtoken"},
    {"eco": "npm", "pkg": "express", "vuln_below": "4.19.2", "cve": "CVE-2024-29041", "sev": SeverityEnum.MEDIUM, "title": "Open Redirect in Express Router"},
    {"eco": "pip", "pkg": "requests", "vuln_below": "2.31.0", "cve": "CVE-2023-32681", "sev": SeverityEnum.MEDIUM, "title": "Proxy-Authorization Header Leak in Requests"},
    {"eco": "pip", "pkg": "flask", "vuln_below": "2.2.5", "cve": "CVE-2023-30861", "sev": SeverityEnum.HIGH, "title": "High Resource Consumption / Cookie Tampering in Flask"},
    {"eco": "pip", "pkg": "django", "vuln_below": "4.2.14", "cve": "CVE-2024-38875", "sev": SeverityEnum.CRITICAL, "title": "Denial-of-Service / URL Bypass in Django"},
    {"eco": "pip", "pkg": "urllib3", "vuln_below": "2.0.7", "cve": "CVE-2023-45803", "sev": SeverityEnum.HIGH, "title": "Request Body Stripping Bypass in urllib3"},
    {"eco": "pip", "pkg": "pyyaml", "vuln_below": "5.4", "cve": "CVE-2020-14343", "sev": SeverityEnum.CRITICAL, "title": "Arbitrary Code Execution in PyYAML FullLoader"},
]


class SastEngine:
    @classmethod
    def run_sast(cls, workspace_path: Path, scan_id: str) -> List[Finding]:
        """
        Runs comprehensive static analysis across all files:
        1. Bandit (Python AST)
        2. Gitleaks secret scanning
        3. Multi-language AST / pattern scanning
        4. Dependency vulnerability scanning
        5. Normalization & Deduplication
        """
        findings: List[Finding] = []

        # 1. Run Python Bandit
        bandit_findings = cls._run_bandit(workspace_path, scan_id)
        findings.extend(bandit_findings)

        # 2. Run Gitleaks Secret Scanner
        secret_findings = cls._run_secret_scanner(workspace_path, scan_id)
        findings.extend(secret_findings)

        # 3. Run Multi-language AST/Pattern Analysis
        pattern_findings = cls._run_pattern_rules(workspace_path, scan_id)
        findings.extend(pattern_findings)

        # 4. Run Dependency Analysis
        dep_findings = cls._run_dependency_scanner(workspace_path, scan_id)
        findings.extend(dep_findings)

        # 5. Run Code Quality, AST Linting & Complexity Analysis
        quality_findings = cls._run_code_quality_and_lint(workspace_path, scan_id)
        findings.extend(quality_findings)

        # Deduplicate findings
        deduped = cls._deduplicate(findings)
        return deduped

    @classmethod
    def _run_bandit(cls, workspace_path: Path, scan_id: str) -> List[Finding]:
        findings = []
        try:
            cmd = ["python", "-m", "bandit", "-r", str(workspace_path), "-f", "json", "-q"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.stdout:
                data = json.loads(res.stdout)
                for item in data.get("results", []):
                    sev_map = {
                        "HIGH": SeverityEnum.HIGH,
                        "MEDIUM": SeverityEnum.MEDIUM,
                        "LOW": SeverityEnum.LOW
                    }
                    sev = sev_map.get(item.get("issue_severity", "").upper(), SeverityEnum.MEDIUM)
                    
                    # Convert absolute path to relative
                    raw_file = item.get("filename", "")
                    rel_file = str(Path(raw_file).relative_to(workspace_path)) if raw_file.startswith(str(workspace_path)) else raw_file

                    findings.append(Finding(
                        id=f"find-{uuid.uuid4().hex[:8]}",
                        scan_id=scan_id,
                        title=f"Bandit: {item.get('issue_text', 'Security Issue')}",
                        description=f"{item.get('issue_text')} (Test ID: {item.get('test_id')}, {item.get('test_name')})",
                        severity=sev,
                        category=FindingCategoryEnum.SECURITY_MISCONFIG,
                        scanner=ScannerTypeEnum.BANDIT,
                        rule_id=f"BANDIT-{item.get('test_id')}",
                        file_path=rel_file,
                        line_number=item.get("line_number"),
                        end_line=item.get("line_range", [None])[-1] if item.get("line_range") else None,
                        code_snippet=item.get("code", "").strip(),
                        cwe_ids=[f"CWE-{item.get('issue_cwe', {}).get('id', 'N/A')}"] if item.get("issue_cwe") else [],
                        remediation_guidance=f"Review reference at {item.get('more_info')}" if item.get('more_info') else "Apply Python secure coding best practices.",
                        confidence=item.get("issue_confidence", "HIGH")
                    ))
        except Exception as e:
            logger.warning(f"Bandit scan skipped or failed: {e}")
        return findings

    @classmethod
    def _run_secret_scanner(cls, workspace_path: Path, scan_id: str) -> List[Finding]:
        findings = []
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "__pycache__", "dist"]]
            for file in files:
                file_path = Path(root) / file
                rel_path = str(file_path.relative_to(workspace_path))
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except Exception:
                    continue

                for line_idx, line in enumerate(lines, start=1):
                    for pat in SECRET_PATTERNS:
                        match = re.search(pat["regex"], line)
                        if match:
                            snippet = line.strip()
                            # Mask matched secret in snippet
                            matched_text = match.group(0)
                            masked_snippet = snippet.replace(matched_text, matched_text[:4] + "*" * (len(matched_text) - 8) + matched_text[-4:] if len(matched_text) > 8 else "***REDACTED***")
                            
                            findings.append(Finding(
                                id=f"find-{uuid.uuid4().hex[:8]}",
                                scan_id=scan_id,
                                title=pat["title"],
                                description=pat["description"],
                                severity=pat["severity"],
                                category=pat["category"],
                                scanner=ScannerTypeEnum.GITLEAKS,
                                rule_id=pat["id"],
                                file_path=rel_path,
                                line_number=line_idx,
                                code_snippet=masked_snippet,
                                cwe_ids=pat["cwe"],
                                remediation_guidance=pat["remediation"],
                                confidence="HIGH"
                            ))
        return findings

    @classmethod
    def _run_pattern_rules(cls, workspace_path: Path, scan_id: str) -> List[Finding]:
        findings = []
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"]]
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                rel_path = str(file_path.relative_to(workspace_path))

                applicable_rules = [r for r in MULTI_LANG_RULES if ext in r["extensions"]]
                if not applicable_rules:
                    continue

                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                except Exception:
                    continue

                for line_idx, line in enumerate(lines, start=1):
                    for rule in applicable_rules:
                        if re.search(rule["regex"], line):
                            # Extract 3-line context
                            start_ctx = max(0, line_idx - 2)
                            end_ctx = min(len(lines), line_idx + 1)
                            snippet = "".join(lines[start_ctx:end_ctx]).strip()

                            findings.append(Finding(
                                id=f"find-{uuid.uuid4().hex[:8]}",
                                scan_id=scan_id,
                                title=rule["title"],
                                description=rule["description"],
                                severity=rule["severity"],
                                category=rule["category"],
                                scanner=ScannerTypeEnum.SEMGREP,
                                rule_id=rule["id"],
                                file_path=rel_path,
                                line_number=line_idx,
                                code_snippet=snippet,
                                cwe_ids=rule["cwe"],
                                remediation_guidance=rule["remediation"],
                                confidence="HIGH"
                            ))
        return findings

    @classmethod
    def _run_dependency_scanner(cls, workspace_path: Path, scan_id: str) -> List[Finding]:
        findings = []
        # Check requirements.txt
        req_file = workspace_path / "requirements.txt"
        if req_file.exists():
            try:
                with open(req_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, start=1):
                        line_clean = line.strip().split("#")[0].strip()
                        if "==" in line_clean:
                            pkg_name, version = line_clean.split("==", 1)
                            pkg_name = pkg_name.strip().lower()
                            version = version.strip()

                            for vuln in VULNERABLE_PACKAGES_DB:
                                if vuln["eco"] == "pip" and vuln["pkg"] == pkg_name:
                                    findings.append(Finding(
                                        id=f"find-{uuid.uuid4().hex[:8]}",
                                        scan_id=scan_id,
                                        title=f"Vulnerable Dependency: {pkg_name} ({vuln['cve']})",
                                        description=f"Package {pkg_name}=={version} is affected by {vuln['title']}.",
                                        severity=vuln["sev"],
                                        category=FindingCategoryEnum.VULNERABLE_DEPENDENCY,
                                        scanner=ScannerTypeEnum.DEPENDENCY,
                                        rule_id=vuln["cve"],
                                        file_path="requirements.txt",
                                        line_number=line_idx,
                                        code_snippet=line.strip(),
                                        cwe_ids=["CWE-1395", "CWE-1104"],
                                        remediation_guidance=f"Upgrade {pkg_name} to version >={vuln['vuln_below']}.",
                                        confidence="HIGH"
                                    ))
            except Exception as e:
                logger.warning(f"Requirements parsing error: {e}")

        # Check package.json
        pkg_json = workspace_path / "package.json"
        if pkg_json.exists():
            try:
                with open(pkg_json, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    for pkg_name, ver_str in all_deps.items():
                        clean_ver = re.sub(r"[^\d\.]", "", ver_str)
                        for vuln in VULNERABLE_PACKAGES_DB:
                            if vuln["eco"] == "npm" and vuln["pkg"] == pkg_name.lower():
                                findings.append(Finding(
                                    id=f"find-{uuid.uuid4().hex[:8]}",
                                    scan_id=scan_id,
                                    title=f"Vulnerable NPM Dependency: {pkg_name} ({vuln['cve']})",
                                    description=f"Dependency '{pkg_name}' version {ver_str} matches known vulnerability: {vuln['title']}.",
                                    severity=vuln["sev"],
                                    category=FindingCategoryEnum.VULNERABLE_DEPENDENCY,
                                    scanner=ScannerTypeEnum.DEPENDENCY,
                                    rule_id=vuln["cve"],
                                    file_path="package.json",
                                    code_snippet=f'"{pkg_name}": "{ver_str}"',
                                    cwe_ids=["CWE-1395", "CWE-1104"],
                                    remediation_guidance=f"Update '{pkg_name}' to version >={vuln['vuln_below']} in package.json and run npm install.",
                                    confidence="HIGH"
                                ))
            except Exception as e:
                logger.warning(f"package.json parsing error: {e}")

        return findings

    @classmethod
    def _run_code_quality_and_lint(cls, workspace_path: Path, scan_id: str) -> List[Finding]:
        """
        Executes AST-level code quality, linting, complexity and maintainability analysis:
        1. Syntax Error validation (Python ast.parse, JSON parse)
        2. McCabe Cyclomatic Complexity per function (>10 flagged)
        3. Duplicate Code / Copy-Paste block detection (6+ line blocks)
        4. Unused imports & Unused local variables
        5. Logical errors (tautological conditions, mutating list while iterating, mutable defaults)
        6. Runtime errors (zero division, bare except, unclosed resource leaks)
        7. Inefficient patterns (string concatenation in loops)
        8. Coding standard violations (excessive function length, excessive parameters)
        """
        findings: List[Finding] = []
        code_chunks: Dict[str, Tuple[str, int, str]] = {}
        dup_count = 0

        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "venv", ".venv", "__pycache__", "dist", ".pytest_cache"]]
            for file in files:
                file_path = Path(root) / file
                rel_path = str(file_path.relative_to(workspace_path))
                ext = file_path.suffix.lower()

                # Read raw content
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        raw_lines = content.splitlines()
                except Exception:
                    continue

                # -------------------------------------------------------------
                # A. Duplicate Code Detection (Rolling 6-line window across code files)
                # -------------------------------------------------------------
                if ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".c", ".cpp"]:
                    clean_lines = []
                    for idx, line in enumerate(raw_lines, start=1):
                        trimmed = line.strip()
                        if trimmed and not trimmed.startswith(("#", "//", "/*", "*")):
                            clean_lines.append((idx, trimmed))

                    if len(clean_lines) >= 6 and dup_count < 10:
                        for i in range(len(clean_lines) - 5):
                            chunk_text = " ".join(l[1] for l in clean_lines[i:i + 6])
                            if len(chunk_text) > 60:
                                chunk_hash = f"{len(chunk_text)}:{chunk_text[:80]}"
                                if chunk_hash in code_chunks:
                                    orig_file, orig_line, orig_snippet = code_chunks[chunk_hash]
                                    if orig_file != rel_path or abs(clean_lines[i][0] - orig_line) > 12:
                                        dup_count += 1
                                        findings.append(Finding(
                                            id=f"find-dup-{uuid.uuid4().hex[:8]}",
                                            scan_id=scan_id,
                                            title="Duplicate Code Block Detected",
                                            description=f"Identical code block of 6+ statements detected (also found at {orig_file}:{orig_line}). Violates the DRY (Don't Repeat Yourself) principle.",
                                            severity=SeverityEnum.LOW,
                                            category=FindingCategoryEnum.CODE_QUALITY,
                                            scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                            rule_id="CODE-DUPLICATE-BLOCK",
                                            file_path=rel_path,
                                            line_number=clean_lines[i][0],
                                            code_snippet="\n".join(raw_lines[max(0, clean_lines[i][0] - 1):clean_lines[i][0] + 5]),
                                            cwe_ids=["CWE-1041"],
                                            remediation_guidance=f"Extract duplicated logic into a shared reusable utility function in {orig_file} or a common helper module.",
                                            confidence="HIGH"
                                        ))
                                        break
                                else:
                                    code_chunks[chunk_hash] = (rel_path, clean_lines[i][0], chunk_text)

                # -------------------------------------------------------------
                # B. JSON Syntax Error Validation
                # -------------------------------------------------------------
                if ext == ".json":
                    try:
                        json.loads(content)
                    except json.JSONDecodeError as je:
                        findings.append(Finding(
                            id=f"find-syntax-{uuid.uuid4().hex[:8]}",
                            scan_id=scan_id,
                            title=f"JSON Syntax Error: {je.msg}",
                            description=f"Malformed JSON syntax on line {je.lineno}, column {je.colno}: {je.msg}.",
                            severity=SeverityEnum.CRITICAL,
                            category=FindingCategoryEnum.CODE_QUALITY,
                            scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                            rule_id="CODE-SYNTAX-JSON",
                            file_path=rel_path,
                            line_number=je.lineno,
                            code_snippet=raw_lines[je.lineno - 1] if je.lineno <= len(raw_lines) else "",
                            cwe_ids=["CWE-754"],
                            remediation_guidance="Correct invalid JSON characters, trailing commas, or quotation marks.",
                            confidence="HIGH"
                        ))
                    continue

                # -------------------------------------------------------------
                # C. Python AST Deep Code Quality, Errors & Complexity Checks
                # -------------------------------------------------------------
                if ext == ".py":
                    try:
                        tree = ast.parse(content, filename=rel_path)
                    except SyntaxError as se:
                        # 1. Syntax Error
                        findings.append(Finding(
                            id=f"find-syntax-{uuid.uuid4().hex[:8]}",
                            scan_id=scan_id,
                            title=f"Python Syntax Error: {se.msg}",
                            description=f"SyntaxError prevented module compilation on line {se.lineno}: {se.msg}.",
                            severity=SeverityEnum.CRITICAL,
                            category=FindingCategoryEnum.CODE_QUALITY,
                            scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                            rule_id="CODE-SYNTAX-ERROR",
                            file_path=rel_path,
                            line_number=se.lineno or 1,
                            code_snippet=se.text.strip() if se.text else (raw_lines[se.lineno - 1] if se.lineno and se.lineno <= len(raw_lines) else ""),
                            cwe_ids=["CWE-754"],
                            remediation_guidance="Resolve indentation error, missing colon, or invalid Python syntax.",
                            confidence="HIGH"
                        ))
                        continue

                    # Collect imported names vs loaded names for Unused Imports
                    imported_names = {}
                    loaded_names = set()

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imported_names[alias.asname or alias.name] = (node.lineno, alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            for alias in node.names:
                                imported_names[alias.asname or alias.name] = (node.lineno, alias.name)
                        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                            loaded_names.add(node.id)

                    # 2. Unused Imports (skip __init__.py which commonly exposes package APIs)
                    if not file_path.name.startswith("__init__"):
                        for imp_alias, (imp_line, orig_name) in imported_names.items():
                            if imp_alias not in loaded_names and imp_alias != "*":
                                findings.append(Finding(
                                    id=f"find-imp-{uuid.uuid4().hex[:8]}",
                                    scan_id=scan_id,
                                    title=f"Unused Import: '{imp_alias}'",
                                    description=f"Module or symbol '{orig_name}' is imported on line {imp_line} but never referenced.",
                                    severity=SeverityEnum.LOW,
                                    category=FindingCategoryEnum.CODE_QUALITY,
                                    scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                    rule_id="CODE-UNUSED-IMPORT",
                                    file_path=rel_path,
                                    line_number=imp_line,
                                    code_snippet=raw_lines[imp_line - 1] if imp_line <= len(raw_lines) else f"import {orig_name}",
                                    cwe_ids=["CWE-561"],
                                    remediation_guidance=f"Remove unused import '{imp_alias}' to improve performance and code clarity.",
                                    confidence="HIGH"
                                ))

                    # Traverse Function Definitions
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            fn_line = node.lineno
                            fn_end = getattr(node, "end_lineno", fn_line)
                            fn_length = fn_end - fn_line + 1

                            # 3. Excessive Function Length (Coding standard)
                            if fn_length > 65:
                                findings.append(Finding(
                                    id=f"find-len-{uuid.uuid4().hex[:8]}",
                                    scan_id=scan_id,
                                    title=f"Function Exceeds Length Threshold: '{node.name}' ({fn_length} lines)",
                                    description=f"Function '{node.name}' spans {fn_length} lines (threshold: 65), violating Single Responsibility and maintainability guidelines.",
                                    severity=SeverityEnum.LOW,
                                    category=FindingCategoryEnum.CODE_QUALITY,
                                    scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                    rule_id="CODE-LONG-FUNCTION",
                                    file_path=rel_path,
                                    line_number=fn_line,
                                    code_snippet=raw_lines[fn_line - 1] if fn_line <= len(raw_lines) else "",
                                    cwe_ids=["CWE-1047"],
                                    remediation_guidance="Decompose this large function into modular helper functions with distinct responsibilities.",
                                    confidence="HIGH"
                                ))

                            # 4. Excessive Parameters (Clean Code violation)
                            param_count = len(node.args.args)
                            if param_count > 6:
                                findings.append(Finding(
                                    id=f"find-params-{uuid.uuid4().hex[:8]}",
                                    scan_id=scan_id,
                                    title=f"Too Many Parameters in Function: '{node.name}' ({param_count} params)",
                                    description=f"Function '{node.name}' accepts {param_count} parameters (threshold: 6), indicating poor parameter abstraction.",
                                    severity=SeverityEnum.LOW,
                                    category=FindingCategoryEnum.CODE_QUALITY,
                                    scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                    rule_id="CODE-TOO-MANY-PARAMS",
                                    file_path=rel_path,
                                    line_number=fn_line,
                                    code_snippet=raw_lines[fn_line - 1] if fn_line <= len(raw_lines) else "",
                                    cwe_ids=["CWE-1047"],
                                    remediation_guidance="Refactor parameters into a Pydantic schema, dataclass, or configuration object.",
                                    confidence="HIGH"
                                ))

                            # 5. Mutable Default Arguments (Logical bug / State pollution)
                            for default in node.args.defaults:
                                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                                    findings.append(Finding(
                                        id=f"find-mut-{uuid.uuid4().hex[:8]}",
                                        scan_id=scan_id,
                                        title=f"Mutable Default Argument in '{node.name}'",
                                        description=f"Function '{node.name}' uses a mutable default argument (list/dict/set), which retains state across function invocations.",
                                        severity=SeverityEnum.MEDIUM,
                                        category=FindingCategoryEnum.CODE_QUALITY,
                                        scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                        rule_id="CODE-MUTABLE-DEFAULT",
                                        file_path=rel_path,
                                        line_number=fn_line,
                                        code_snippet=raw_lines[fn_line - 1] if fn_line <= len(raw_lines) else "",
                                        cwe_ids=["CWE-665"],
                                        remediation_guidance="Use `None` as the default argument and initialize dynamically: `if arg is None: arg = []`.",
                                        confidence="HIGH"
                                    ))

                            # 6. McCabe Cyclomatic Complexity Analyzer
                            complexity = 1
                            for child in ast.walk(node):
                                if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler, ast.With, ast.Assert)):
                                    complexity += 1
                                elif isinstance(child, ast.BoolOp):
                                    complexity += len(child.values) - 1

                            if complexity > 10:
                                findings.append(Finding(
                                    id=f"find-cpx-{uuid.uuid4().hex[:8]}",
                                    scan_id=scan_id,
                                    title=f"High Cyclomatic Complexity in '{node.name}' (Score: {complexity})",
                                    description=f"Function '{node.name}' has a McCabe complexity of {complexity} (threshold: 10), indicating high branching complexity, severe bug risk, and low testability.",
                                    severity=SeverityEnum.HIGH if complexity >= 15 else SeverityEnum.MEDIUM,
                                    category=FindingCategoryEnum.CODE_QUALITY,
                                    scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                    rule_id="CODE-HIGH-COMPLEXITY",
                                    file_path=rel_path,
                                    line_number=fn_line,
                                    code_snippet=raw_lines[fn_line - 1] if fn_line <= len(raw_lines) else "",
                                    cwe_ids=["CWE-1047"],
                                    remediation_guidance="Simplify branching logic, replace deep nested if-else ladders with polymorphism or lookup tables.",
                                    confidence="HIGH"
                                ))

                            # 7. Unused Local Variables in Functions
                            fn_assigned = {}
                            fn_loaded = set()
                            arg_names = {a.arg for a in node.args.args}
                            for fn_child in ast.walk(node):
                                if isinstance(fn_child, ast.Name):
                                    if isinstance(fn_child.ctx, ast.Store):
                                        fn_assigned[fn_child.id] = fn_child.lineno
                                    elif isinstance(fn_child.ctx, ast.Load):
                                        fn_loaded.add(fn_child.id)

                            for var_name, var_line in fn_assigned.items():
                                if var_name not in fn_loaded and var_name not in arg_names and not var_name.startswith("_"):
                                    findings.append(Finding(
                                        id=f"find-var-{uuid.uuid4().hex[:8]}",
                                        scan_id=scan_id,
                                        title=f"Unused Local Variable: '{var_name}' in '{node.name}'",
                                        description=f"Variable '{var_name}' is assigned on line {var_line} in function '{node.name}' but never used.",
                                        severity=SeverityEnum.LOW,
                                        category=FindingCategoryEnum.CODE_QUALITY,
                                        scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                        rule_id="CODE-UNUSED-VARIABLE",
                                        file_path=rel_path,
                                        line_number=var_line,
                                        code_snippet=raw_lines[var_line - 1] if var_line <= len(raw_lines) else "",
                                        cwe_ids=["CWE-561"],
                                        remediation_guidance=f"Remove variable '{var_name}' or prefix with an underscore `_{var_name}` if intentionally discarded.",
                                        confidence="HIGH"
                                    ))

                        # 8. Division by Zero (Runtime Crash)
                        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                                findings.append(Finding(
                                    id=f"find-zero-{uuid.uuid4().hex[:8]}",
                                    scan_id=scan_id,
                                    title="ZeroDivisionError: Explicit Division or Modulo by Zero",
                                    description=f"Expression on line {node.lineno} divides directly by zero, causing guaranteed runtime crash (`ZeroDivisionError`).",
                                    severity=SeverityEnum.CRITICAL,
                                    category=FindingCategoryEnum.CODE_QUALITY,
                                    scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                    rule_id="CODE-ZERO-DIVISION",
                                    file_path=rel_path,
                                    line_number=node.lineno,
                                    code_snippet=raw_lines[node.lineno - 1] if node.lineno <= len(raw_lines) else "",
                                    cwe_ids=["CWE-369"],
                                    remediation_guidance="Check denominator before division or guard with non-zero validation.",
                                    confidence="HIGH"
                                ))

                        # 9. Tautological / Redundant Comparison (Logical flaw)
                        if isinstance(node, ast.Compare) and len(node.comparators) == 1:
                            if isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                                left_dump = ast.dump(node.left)
                                right_dump = ast.dump(node.comparators[0])
                                if left_dump == right_dump:
                                    findings.append(Finding(
                                        id=f"find-taut-{uuid.uuid4().hex[:8]}",
                                        scan_id=scan_id,
                                        title="Tautological Comparison: Variable Compared to Itself",
                                        description=f"Comparison on line {node.lineno} compares identical expressions (`x == x`), resulting in a constant boolean value.",
                                        severity=SeverityEnum.MEDIUM,
                                        category=FindingCategoryEnum.CODE_QUALITY,
                                        scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                        rule_id="CODE-TAUTOLOGICAL-CONDITION",
                                        file_path=rel_path,
                                        line_number=node.lineno,
                                        code_snippet=raw_lines[node.lineno - 1] if node.lineno <= len(raw_lines) else "",
                                        cwe_ids=["CWE-571", "CWE-570"],
                                        remediation_guidance="Verify intended variable in comparison to eliminate redundant condition.",
                                        confidence="HIGH"
                                    ))

                        # 10. Infinite Loop Detection (Loop condition True without break/return)
                        if isinstance(node, ast.While):
                            is_const_true = (isinstance(node.test, ast.Constant) and node.test.value is True) or (isinstance(node.test, ast.Name) and node.test.id == "True")
                            if is_const_true:
                                has_exit = any(isinstance(c, (ast.Break, ast.Return, ast.Raise)) for c in ast.walk(node))
                                if not has_exit:
                                    findings.append(Finding(
                                        id=f"find-inf-{uuid.uuid4().hex[:8]}",
                                        scan_id=scan_id,
                                        title="Infinite Loop Without Termination Condition",
                                        description=f"While loop on line {node.lineno} has condition `while True:` but contains no `break`, `return`, or `raise` statements, causing execution lockup.",
                                        severity=SeverityEnum.HIGH,
                                        category=FindingCategoryEnum.CODE_QUALITY,
                                        scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                        rule_id="CODE-INFINITE-LOOP",
                                        file_path=rel_path,
                                        line_number=node.lineno,
                                        code_snippet=raw_lines[node.lineno - 1] if node.lineno <= len(raw_lines) else "while True:",
                                        cwe_ids=["CWE-835"],
                                        remediation_guidance="Add a termination condition or include a `break` statement inside the loop body.",
                                        confidence="HIGH"
                                    ))

                        # 11. Bare Except Clause (Poor error handling)
                        if isinstance(node, ast.ExceptHandler):
                            if node.type is None or (isinstance(node.type, ast.Name) and node.type.id in ["BaseException"]):
                                findings.append(Finding(
                                    id=f"find-bare-{uuid.uuid4().hex[:8]}",
                                    scan_id=scan_id,
                                    title="Bare / Overly Broad Exception Handler",
                                    description=f"Except clause on line {node.lineno} catches all exceptions indiscriminately, suppressing critical errors and system interrupts.",
                                    severity=SeverityEnum.MEDIUM,
                                    category=FindingCategoryEnum.CODE_QUALITY,
                                    scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                    rule_id="CODE-BARE-EXCEPT",
                                    file_path=rel_path,
                                    line_number=node.lineno,
                                    code_snippet=raw_lines[node.lineno - 1] if node.lineno <= len(raw_lines) else "except:",
                                    cwe_ids=["CWE-391"],
                                    remediation_guidance="Catch specific exception types (e.g. `except (ValueError, KeyError):`) and log tracebacks.",
                                    confidence="HIGH"
                                ))

                        # 12. Inefficient String Concatenation in Loops
                        if isinstance(node, (ast.For, ast.While)):
                            for loop_child in ast.walk(node):
                                if isinstance(loop_child, ast.AugAssign) and isinstance(loop_child.op, ast.Add):
                                    if isinstance(loop_child.target, ast.Name) and any(w in loop_child.target.id.lower() for w in ["str", "text", "msg", "out", "html"]):
                                        findings.append(Finding(
                                            id=f"find-eff-{uuid.uuid4().hex[:8]}",
                                            scan_id=scan_id,
                                            title="Inefficient String Concatenation Inside Loop",
                                            description=f"In-place string concatenation (`+=`) on line {loop_child.lineno} inside a loop has O(N^2) memory reallocation complexity.",
                                            severity=SeverityEnum.LOW,
                                            category=FindingCategoryEnum.CODE_QUALITY,
                                            scanner=ScannerTypeEnum.CODE_QUALITY_LINTER,
                                            rule_id="CODE-INEFFICIENT-STR-CONCAT",
                                            file_path=rel_path,
                                            line_number=loop_child.lineno,
                                            code_snippet=raw_lines[loop_child.lineno - 1] if loop_child.lineno <= len(raw_lines) else "",
                                            cwe_ids=["CWE-400"],
                                            remediation_guidance="Append items to a list and join at the end: `''.join(chunks)`.",
                                            confidence="HIGH"
                                        ))
                                        break

        return findings

    @classmethod
    def _deduplicate(cls, findings: List[Finding]) -> List[Finding]:
        seen = set()
        deduped = []
        for f in findings:
            key = (f.file_path, f.line_number, f.rule_id)
            if key not in seen:
                seen.add(key)
                deduped.append(f)
        return deduped
