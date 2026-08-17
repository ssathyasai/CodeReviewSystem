import asyncio
import ast
import json
import os
import shutil
import subprocess
from typing import Dict, List

import requests

# Groq API configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = os.getenv("GROQ_URL", "https://api.groq.com/openai/v1/chat/completions")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def write_debug_log(provider: str, prompt: str, response: str, language: str = "unknown"):
    """
    Write LLM inputs and outputs to debug log file for analysis
    """
    try:
        from datetime import datetime
        debug_file = os.path.join(os.path.dirname(__file__), "..", "debugger.txt")
        timestamp = datetime.now().isoformat()
        
        with open(debug_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"TIMESTAMP: {timestamp}\n")
            f.write(f"PROVIDER: {provider}\n")
            f.write(f"LANGUAGE: {language}\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"--- PROMPT SENT ---\n{prompt}\n\n")
            f.write(f"--- RAW RESPONSE ---\n{response}\n\n")
    except Exception as e:
        print(f"Failed to write debug log: {e}")


def detect_language_from_code(code: str, file_path: str = None) -> str:
    if file_path:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.py']:
            return 'python'
        if ext in ['.js', '.jsx']:
            return 'javascript'
        if ext in ['.ts', '.tsx']:
            return 'typescript'
        if ext in ['.java']:
            return 'java'
        if ext in ['.cs']:
            return 'csharp'
    if 'def ' in code or 'import ' in code:
        return 'python'
    if 'function ' in code or 'console.log' in code:
        return 'javascript'
    if 'public class' in code:
        return 'java'
    return 'unknown'


def _get_undefined_names_python(tree: ast.AST) -> List[Dict]:
    findings = []
    builtin_names = set(dir(__builtins__))
    common_globals = {"self", "cls", "app", "request", "conn", "cursor", "config", "ConfigService", "SecureVault", "os", "sys", "json", "datetime", "sqlite3", "pymongo", "pytest"}

    class ScopeVisitor(ast.NodeVisitor):
        def __init__(self):
            self.scopes = [set()]
            self.undefined = []

        def current_scope(self):
            return self.scopes[-1]

        def add_name(self, name: str):
            self.current_scope().add(name)

        def visit_Import(self, node: ast.Import):
            for alias in node.names:
                self.add_name(alias.asname or alias.name.split('.', 1)[0])

        def visit_ImportFrom(self, node: ast.ImportFrom):
            for alias in node.names:
                self.add_name(alias.asname or alias.name)

        def visit_FunctionDef(self, node: ast.FunctionDef):
            self.add_name(node.name)
            local = set()
            local.update(arg.arg for arg in node.args.args)
            local.update(arg.arg for arg in node.args.kwonlyargs)
            if node.args.vararg:
                local.add(node.args.vararg.arg)
            if node.args.kwarg:
                local.add(node.args.kwarg.arg)
            self.scopes.append(local)
            self.generic_visit(node)
            self.scopes.pop()

        def visit_ClassDef(self, node: ast.ClassDef):
            self.add_name(node.name)
            self.scopes.append(set())
            self.generic_visit(node)
            self.scopes.pop()

        def visit_Assign(self, node: ast.Assign):
            for target in node.targets:
                for name in self._extract_names(target):
                    self.add_name(name)
            self.generic_visit(node)

        def visit_AugAssign(self, node: ast.AugAssign):
            for name in self._extract_names(node.target):
                self.add_name(name)
            self.generic_visit(node)

        def visit_For(self, node: ast.For):
            for name in self._extract_names(node.target):
                self.add_name(name)
            self.generic_visit(node)

        def visit_With(self, node: ast.With):
            for item in node.items:
                if item.optional_vars is not None:
                    for name in self._extract_names(item.optional_vars):
                        self.add_name(name)
            self.generic_visit(node)

        def visit_Name(self, node: ast.Name):
            if isinstance(node.ctx, ast.Load):
                name = node.id
                if name in builtin_names or name in common_globals:
                    return
                if any(name in scope for scope in reversed(self.scopes)):
                    return
                self.undefined.append((name, node.lineno, node.col_offset))

        def _extract_names(self, node):
            names = []
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, (ast.Tuple, ast.List)):
                for elt in node.elts:
                    names.extend(self._extract_names(elt))
            elif isinstance(node, ast.Attribute):
                pass
            return names

    visitor = ScopeVisitor()
    visitor.visit(tree)

    seen = set()
    for name, lineno, _ in visitor.undefined:
        if name not in seen and len(name) > 1:
            seen.add(name)
            findings.append({
                'rule': 'Undefined Variable (CWE-457)',
                'line': lineno,
                'severity': 'MEDIUM',
                'message': f'Variable `{name}` is referenced before definition in current scope',
                'suggestion': f'Define or import `{name}` before referencing it',
                'oldCode': f'reference to {name}',
                'newCode': f'{name} = None',
                'confidence': 0.7
            })

    return findings


def _shell_syntax_check(code: str, language: str) -> List[Dict]:
    findings = []
    temp_file = None
    temp_dir = None
    try:
        import tempfile
        temp_dir = tempfile.mkdtemp()
        extension_map = {
            'javascript': '.js',
            'typescript': '.ts',
            'java': '.java',
            'cpp': '.cpp',
            'go': '.go',
            'terraform': '.tf'
        }
        temp_ext = extension_map.get(language, '.txt')
        temp_file = os.path.join(temp_dir, 'source' + temp_ext)

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(code)

        if language == 'javascript':
            cmd = ['node', '--check', temp_file]
        elif language == 'typescript':
            cmd = ['tsc', '--noEmit', temp_file]
        elif language == 'java':
            cmd = ['javac', temp_file]
        elif language == 'cpp':
            cmd = ['g++', '-fsyntax-only', temp_file]
        elif language == 'go':
            cmd = ['go', 'vet', temp_file]
        elif language == 'terraform':
            cmd = ['terraform', 'validate', temp_dir]
        else:
            return findings

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or 'Syntax check failed'
            findings.append({
                'rule': 'Syntax Error',
                'line': 0,
                'severity': 'HIGH',
                'message': f'{language} syntax issue: {message}',
                'suggestion': 'Fix syntax errors in source code',
                'oldCode': '',
                'newCode': '',
                'confidence': 0.9
            })
    except FileNotFoundError:
        pass
    except Exception as e:
        findings.append({
            'rule': 'Syntax Check Error',
            'line': 0,
            'severity': 'MEDIUM',
            'message': f'Unable to run {language} syntax checker: {e}',
            'suggestion': 'Install required tools or rely on LLM analysis',
            'oldCode': '',
            'newCode': '',
            'confidence': 0.6
        })
    finally:
        try:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    return findings


def check_syntax(code: str, language: str) -> List[Dict]:
    findings = []
    if language == 'python':
        try:
            tree = ast.parse(code)
            findings.extend(_get_undefined_names_python(tree))
        except SyntaxError as e:
            findings.append({
                'rule': 'Syntax Error',
                'line': getattr(e, 'lineno', 0) or 0,
                'severity': 'HIGH',
                'message': f'Python syntax error: {e.msg}',
                'suggestion': 'Fix Python syntax error',
                'oldCode': e.text.strip() if e.text else '',
                'newCode': '',
                'confidence': 0.99
            })
    else:
        findings.extend(_shell_syntax_check(code, language))
    return findings


def init_groq_client():
    """Validate Groq API key and return True if we can proceed."""
    # Clear proxy environment variables that might interfere with requests
    for proxy_var in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "all_proxy", "ALL_PROXY"]:
        os.environ.pop(proxy_var, None)

    api_key = os.getenv("GROQ_API_KEY")
    if api_key and api_key.startswith("gsk_"):
        return True

    print("Groq initialization error: GROQ_API_KEY not set or invalid")
    return False

async def run_governance_check(file_path: str) -> Dict:
    """
    Run LLM-powered governance check - ALWAYS reads fresh file
    """
    try:
        # CRITICAL: Read fresh file content every time
        with open(file_path, 'r') as f:
            code_content = f.read()

        guidelines = read_guidelines()

        lang = detect_language_from_code(code_content, file_path)
        findings = check_syntax(code_content, lang)

        groq_client = init_groq_client()
        if groq_client:
            findings += await analyze_with_groq(code_content, guidelines, file_path)
        else:
            findings += simulate_governance_check(code_content, guidelines)

        unique = []
        seen = set()
        for f in findings:
            key = (f.get('rule'), f.get('line'), f.get('message'))
            if key not in seen:
                seen.add(key)
                unique.append(f)
        findings = unique

        # Categorize each finding
        for finding in findings:
            categorize_fix(finding, code_content)

        return {
            "status": "error" if findings else "success",
            "findings": findings,
            "engine": "governance-llm"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "findings": [],
            "error": str(e),
            "engine": "governance"
        }

async def run_governance_check_with_context(file_path: str, context: str) -> Dict:
    """
    Run governance check with cross-file context awareness
    """
    try:
        with open(file_path, 'r') as f:
            code_content = f.read()

        guidelines = read_guidelines()

        lang = detect_language_from_code(code_content, file_path)
        findings = check_syntax(code_content, lang)

        groq_client = init_groq_client()
        if groq_client:
            findings += await analyze_with_context(code_content, guidelines, context, lang)
        else:
            findings += simulate_governance_check(code_content, guidelines)

        unique = []
        seen = set()
        for f in findings:
            key = (f.get('rule'), f.get('line'), f.get('message'))
            if key not in seen:
                seen.add(key)
                unique.append(f)
        findings = unique

        for finding in findings:
            categorize_fix(finding, code_content)

        return {
            "status": "error" if findings else "success",
            "findings": findings,
            "engine": "governance-llm-context"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "findings": [],
            "error": str(e),
            "engine": "governance"
        }

async def analyze_with_context(code: str, guidelines: str, context: str, language: str) -> List[Dict]:
    """
    Analyze code with cross-file context
    """
    try:
        prompt = f"""You are an expert code governance AI with cross-file context awareness.\n\nLANGUAGE: {language}\n\nCONTEXT INFORMATION:\n{context}\n\nGUIDELINES:\n{guidelines}\n\nCODE TO ANALYZE:\n```{language}\n{code}\n```\n\nUse the context to understand:\n- What classes/methods are imported\n- Whether imported items exist and their signatures\n- Cross-file dependencies\n\nOnly flag REAL issues with actual code snippets.\n\nResponse format (JSON array):\n["
  {{
    "rule": "Issue type",
    "line": 10,
    "severity": "CRITICAL",
    "message": "Description",
    "suggestion": "How to fix",
    "oldCode": "actual code line",
    "newCode": "fixed code"
  }}
]"""

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Respond only with valid JSON. Provide exact code snippets."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=4000
        )
        
        response_text = chat_completion.choices[0].message.content.strip()
        write_debug_log("groq", prompt, response_text, language)
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        findings = json.loads(response_text)
        
        for finding in findings:
            finding['canAutoFix'] = True
            if not finding.get('oldCode') or len(finding.get('oldCode', '')) > 200:
                line_num = finding.get('line', 1)
                lines = code.split('\n')
                if 0 < line_num <= len(lines):
                    finding['oldCode'] = lines[line_num - 1].strip()
        
        return findings if isinstance(findings, list) else []
        
    except Exception as e:
        print(f"Context analysis error: {e}")
        return simulate_governance_check(code, guidelines)
    """
    Run LLM-powered governance check - ALWAYS reads fresh file
    """
    try:
        # CRITICAL: Read fresh file content every time
        with open(file_path, 'r') as f:
            code_content = f.read()

        guidelines = read_guidelines()
        lang = detect_language_from_code(code_content, file_path)
        findings = check_syntax(code_content, lang)

        groq_client = init_groq_client()
        if groq_client:
            findings += await analyze_with_groq(code_content, guidelines, file_path)
        else:
            findings += simulate_governance_check(code_content, guidelines)

        unique = []
        seen = set()
        for f in findings:
            key = (f.get('rule'), f.get('line'), f.get('message'))
            if key not in seen:
                seen.add(key)
                unique.append(f)
        findings = unique

        # Categorize each finding
        for finding in findings:
            categorize_fix(finding, code_content)

        return {
            "status": "error" if findings else "success",
            "findings": findings,
            "engine": "governance-llm"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "findings": [],
            "error": str(e),
            "engine": "governance"
        }

def read_guidelines() -> str:
    """
    Read organizational guidelines
    """
    default_guidelines = """
Organizational Code Guidelines


SYNTAX AND CODE CORRECTNESS

Every line of code must be syntactically valid Python. A line that cannot be parsed by the Python interpreter is a blocking issue regardless of what else it does or does not do.

The following are always invalid and must be flagged as Syntax Errors:

first determine what is the language of by analysing the code and then check the syntax according to the determined language check the syntax very strictly every path all possible syntax errors.
also if a line is wrong syntactically dont leave it only with sybtax check but also check against below guidelines 

A single line may simultaneously violate the syntax rules and one or more other policies. Every violation on that line must be reported as a separate finding. Do not collapse multiple violations into one. Examples:

- DISCOUNT_RATE = 10% is a Syntax Error because 10% is not valid Python, and it is also a Hardcoded Configuration violation because a financial constant is being assigned directly. Two findings must be produced for this one line.
- name==1234::" is a Syntax Error because == is not assignment, :: is invalid, and the string is unterminated. It may also be a Hardcoded Credentials violation if the variable name suggests it holds sensitive data. Every applicable violation must be reported.
- DATABASE_PASSWORD = "super_secret_123" is syntactically valid Python, but it is a Hardcoded Credentials violation. One finding for the credential issue.

When analyzing code, do not stop after finding the first issue on a line or the first issue in a file. Continue scanning every remaining line independently. Every issue must be reported.


SECURITY POLICIES

Credentials and Secrets

Never hardcode passwords, API keys, tokens, secrets, or private keys as string literals in source code. All credentials must be loaded at runtime using os.getenv(), os.environ, a secrets manager, or a secure vault. Any variable whose name contains password, passwd, pwd, api_key, apikey, secret, token, auth, credential, or private_key and is assigned a plain string literal is a critical violation.

Bad: DATABASE_PASSWORD = "super_secret_123"
Good: DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")

Bad: API_KEY = "sk-abc123"
Good: API_KEY = os.getenv("API_KEY")

.env files must never be committed to version control. Any credential that has ever been committed to a repository must be rotated immediately.

Input Sanitisation

All user-supplied input must be validated and sanitised before use in database queries, file paths, shell commands, or HTML output. Use parameterised queries exclusively. Never build SQL queries using f-strings, % formatting, .format(), or string concatenation. Validate data type, length, format, and allowed character set at the earliest entry point.

Bad: cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
Good: cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

Data Protection

Sensitive data including PII, payment information, and health data must be encrypted at rest and in transit. Sensitive fields must never appear in logs. Mask or redact them before writing. Use HTTPS for all external communication. Never transmit secrets in URL query parameters.

Error Handling and Information Exposure

Error messages shown to end users must never contain stack traces, internal paths, database names, or credential hints. Full error details must be logged server-side only with appropriate access controls on log storage.


FINANCIAL AND CONFIGURATION POLICIES

No Hardcoded Financial Constants

Discount rates, prices, fees, tax rates, commissions, and markups must never be hardcoded as numeric literals, percentage literals, or percentage strings. Any variable whose name contains discount, price, rate, fee, tax, commission, or markup and is assigned a literal value is a violation. All financial constants must be retrieved from ConfigService to support A/B testing, regional variations, and runtime updates without redeployment.

Bad: DISCOUNT_RATE = 0.10
Bad: DISCOUNT_RATE = 10%
Bad: TAX_RATE = "18%"
Good: DISCOUNT_RATE = ConfigService.get("discount_rate")
Good: TAX_RATE = ConfigService.get("tax_rate")

Arithmetic Safety

Division operations must include a zero-check guard before execution. Financial calculations must use Decimal, not float, to avoid floating-point rounding errors.

Bad: return total / count
Good: return Decimal(total) / Decimal(count) if count != 0 else Decimal(0)

Configuration Management

Environment-specific values such as timeouts, limits, feature flags, and service URLs must come from configuration and must not be hardcoded. Configuration keys must follow snake_case naming and be documented in a central config registry.


CODE QUALITY POLICIES

API Documentation

Every public-facing API endpoint must have an OpenAPI or Swagger docstring or schema definition. Documentation must include the method, path, request body schema, response schema, and all possible error codes.

Structured Logging

Use a structured logging library such as structlog or python-json-logger. Bare print() statements are not permitted in production code. Every log entry must include a timestamp, log level, service name, and a correlation or request ID where available. Log level must be controlled via environment configuration and must not be hardcoded.

Type Annotations

All function signatures must include type annotations for parameters and return values. Use Optional[T] for values that may be None. Avoid unannotated None returns.

Dead Code

Commented-out code blocks must be removed before merging. Version control history serves as the record. Unreachable code must be removed.


PERFORMANCE POLICIES

Database Access

All database connections must use a connection pool. Never open a new connection per request. Queries on large tables must filter on indexed columns. Avoid SELECT star — always specify only the columns required.

Pagination

Any endpoint or function returning a collection must support pagination. Default page size must be explicitly capped to prevent unbounded memory usage.

Resource Cleanup

File handles, database cursors, and network connections must be closed explicitly or managed with with statements. Memory-intensive operations must release resources promptly and must not hold them for the lifetime of the process.

Caching

Expensive or frequently repeated external calls must be cached where the data is stable. All cache entries must carry an explicit TTL. Indefinite caching is not permitted.


DEPENDENCY AND SUPPLY CHAIN POLICIES

All third-party packages must be pinned to an exact version in requirements.txt or pyproject.toml. Dependencies must be checked for known CVEs before being added using pip-audit or safety. Unused imports must be removed.


SEVERITY REFERENCE

CRITICAL means an immediate security or data-integrity risk such as hardcoded credentials or SQL injection. It blocks deployment.

HIGH means a significant risk or policy violation such as a syntax error, division by zero, or a hardcoded financial constant. It blocks deployment.

MEDIUM means a code quality or best-practice violation. It must be fixed before the next release.

LOW means a minor style or documentation gap. It may be fixed at discretion.
"""
    
    guidelines_path = "guidelines.md"
    
    try:
        if os.path.exists(guidelines_path):
            with open(guidelines_path, 'r') as f:
                return f.read()
    except:
        pass
    
    return default_guidelines

def call_groq_api(prompt: str) -> str:
    """Call Groq API via HTTP to avoid groq client constructor issues."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured")

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Respond only with valid JSON. Always provide exact code snippets, never descriptions."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 4000
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(GROQ_URL, json=payload, headers=headers, timeout=120)
    response.raise_for_status()
    data = response.json()

    if not data or 'choices' not in data or len(data['choices']) == 0:
        raise RuntimeError("Invalid response from Groq API")

    message = data['choices'][0].get('message') or {}
    content = message.get('content') or data['choices'][0].get('text')
    if content is None:
        raise RuntimeError("Groq response missing content")

    return content.strip()


def categorize_fix(finding: dict, code_content: str):
    """
    ALL issues should be auto-fixable - system reads guidelines for context
    """
    # Everything is auto-fixable if we have a newCode suggestion
    if finding.get('newCode'):
        finding['canAutoFix'] = True
    else:
        # If no newCode provided, still mark as fixable but note it
        finding['canAutoFix'] = True
        if not finding.get('suggestion'):
            finding['suggestion'] = 'Review code and apply recommended changes'

async def analyze_with_groq(code: str, guidelines: str, file_path: str) -> List[Dict]:
    """
    Use Groq API - provide actual code snippets, not descriptions
    """
    try:
        requirements = ""
        req_path = "requirements_spec.md"
        if os.path.exists(req_path):
            with open(req_path, 'r') as f:
                requirements = f.read()
        
        prompt = f"""You are an expert code governance AI. Analyze code in a language-aware manner and provide fixes with ACTUAL CODE SNIPPETS.\n\nLANGUAGE: {detect_language_from_code(code, file_path)}\n\nCRITICAL RULES:\n1. oldCode: MUST be the EXACT code line from the file (not a description)\n2. newCode: MUST be the EXACT replacement code (not a description)\n3. suggestion: Human-readable explanation (this is separate)\n4. Do NOT detect os.getenv(), ConfigService.get(), or SecureVault as hardcoded unless language is Python\n5. Only flag ACTUAL hardcoded values like \"password123\" or 0.20\n\nGUIDELINES:\n{guidelines}\n\nCODE:\n```{detect_language_from_code(code, file_path)}\n{code}\n```\n\nResponse format (JSON array):"
[
  {{
    "rule": "Hardcoded Credentials",
    "line": 10,
    "severity": "CRITICAL",
    "message": "Password hardcoded instead of using environment variable",
    "suggestion": "Use os.getenv() to retrieve password from environment",
    "oldCode": "DATABASE_PASSWORD = \\"super_secret_123\\"",
    "newCode": "DATABASE_PASSWORD = os.getenv(\\"DATABASE_PASSWORD\\")"
  }}
]

WRONG (do not do this):
- oldCode: "Credentials hardcoded in source code" ❌
- newCode: "Use environment variables" ❌

CORRECT:
- oldCode: "API_KEY = \\"sk-12345\\"" ✅
- newCode: "API_KEY = os.getenv(\\"API_KEY\\")" ✅

DO NOT FLAG THESE AS ISSUES:
- os.getenv("PASSWORD") ← Already safe ✅
- ConfigService.get() ← Already safe ✅
- SecureVault.get() ← Already safe ✅

Only return issues for ACTUAL problems in the code."""

        response_text = call_groq_api(prompt)
        lang = detect_language_from_code(code, file_path)
        write_debug_log("groq", prompt, response_text, lang)

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        findings = json.loads(response_text)
        
        for finding in findings:
            finding['canAutoFix'] = True
            # Ensure we have oldCode and newCode, not descriptions
            if not finding.get('oldCode') or len(finding.get('oldCode', '')) > 200:
                # Fallback: extract from file
                line_num = finding.get('line', 1)
                lines = code.split('\n')
                if 0 < line_num <= len(lines):
                    finding['oldCode'] = lines[line_num - 1].strip()
        
        return findings if isinstance(findings, list) else []
        
    except Exception as e:
        print(f"Groq API error: {e}")
        return simulate_governance_check(code, guidelines)

def simulate_governance_check(code: str, guidelines: str) -> List[Dict]:
    """
    Simulate governance check - detect OWASP Top 10 vulnerabilities & corporate policies
    """
    findings = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip empty lines and comments
        if not line_stripped or line_stripped.startswith('#'):
            continue
        
        # 1. Hardcoded credentials (passwords, keys, tokens)
        if any(kw in line.lower() for kw in ['password', 'passwd', 'api_key', 'apikey', 'secret', 'token', 'auth_key', 'private_key']) and '=' in line:
            if ('"' in line or "'" in line) and not any(safe in line for safe in ['getenv', 'SecureVault', 'config.get', 'os.environ', 'ConfigService']):
                var_name = line.split('=')[0].strip()
                findings.append({
                    "rule": "Hardcoded Credentials (CWE-798)",
                    "line": i + 1,
                    "severity": "CRITICAL",
                    "message": f"Credential '{var_name}' hardcoded in source code literal",
                    "suggestion": f"Retrieve '{var_name}' dynamically from environment using os.getenv()",
                    "oldCode": line_stripped,
                    "newCode": f"{var_name} = os.getenv('{var_name.upper()}')",
                    "canAutoFix": True
                })
        
        # 2. Hardcoded Financial Constants (discounts, prices, rates, taxes)
        elif any(kw in line.lower() for kw in ['discount', 'price', 'rate', 'fee', 'tax', 'markup', 'commission']) and '=' in line:
            if any(char.isdigit() for char in line) and not any(safe in line for safe in ['ConfigService', 'os.getenv', 'getenv']):
                var_name = line.split('=')[0].strip()
                findings.append({
                    "rule": "Hardcoded Financial Constant",
                    "line": i + 1,
                    "severity": "HIGH",
                    "message": f"Financial constant '{var_name}' hardcoded as literal - violates policy",
                    "suggestion": "Retrieve financial rates dynamically via ConfigService",
                    "oldCode": line_stripped,
                    "newCode": f"{var_name} = ConfigService.get('{var_name.lower()}')",
                    "canAutoFix": True
                })
        
        # 3. SQL Injection (dynamic string query execution)
        elif any(kw in line.lower() for kw in ['execute', 'executemany', 'query', 'raw_query', 'run_sql']) and ('(' in line):
            if any(fmt in line for fmt in ['f"', "f'", '%', '.format', '+']) or not ('?' in line or '%s' in line):
                findings.append({
                    "rule": "SQL Injection Risk (CWE-89)",
                    "line": i + 1,
                    "severity": "CRITICAL",
                    "message": "Potential SQL injection vulnerability via dynamic query construction",
                    "suggestion": "Use parameterized queries with placeholder bindings",
                    "oldCode": line_stripped,
                    "newCode": 'cursor.execute("SELECT * FROM table WHERE id = ?", (user_input,))',
                    "canAutoFix": True
                })

        # 4. Command Injection / Dangerous Code Execution
        elif any(cmd in line for cmd in ['os.system', 'os.popen', 'eval(', 'exec(']) or ('subprocess' in line and 'shell=True' in line):
            findings.append({
                "rule": "Command Injection Risk (CWE-78/95)",
                "line": i + 1,
                "severity": "CRITICAL",
                "message": "Dangerous command or code execution invocation",
                "suggestion": "Avoid shell execution or use strict subprocess argument lists",
                "oldCode": line_stripped,
                "newCode": "# TODO: Refactor to safe subprocess call without shell=True",
                "canAutoFix": True
            })

        # 5. Weak Cryptography
        elif any(crypto in line.lower() for crypto in ['hashlib.md5', 'hashlib.sha1', 'md5(', 'sha1(']):
            findings.append({
                "rule": "Weak Cryptographic Algorithm (CWE-327)",
                "line": i + 1,
                "severity": "MEDIUM",
                "message": "Use of weak cryptographic hashing algorithm (MD5/SHA1)",
                "suggestion": "Upgrade to SHA-256 or bcrypt/argon2 for password hashing",
                "oldCode": line_stripped,
                "newCode": "hashlib.sha256(data.encode()).hexdigest()",
                "canAutoFix": True
            })

        # 6. Insecure Deserialization
        elif any(deser in line for deser in ['pickle.loads', 'pickle.load', 'marshal.loads']):
            findings.append({
                "rule": "Insecure Deserialization (CWE-502)",
                "line": i + 1,
                "severity": "CRITICAL",
                "message": "Untrusted object deserialization can cause remote code execution",
                "suggestion": "Use safe JSON serialization instead of pickle",
                "oldCode": line_stripped,
                "newCode": "json.loads(payload)",
                "canAutoFix": True
            })
        
        # 7. Division without zero check
        elif '/' in line and '//' not in line and '/*' not in line and '=' in line:
            if not any(check in line for check in ['if', '!= 0', '> 0', 'Decimal']):
                var_name = line.split('=')[0].strip()
                expr = line.split('=')[1].strip()
                parts = expr.split('/')
                if len(parts) == 2:
                    divisor = parts[1].strip()
                    findings.append({
                        "rule": "Division by Zero Risk (CWE-369)",
                        "line": i + 1,
                        "severity": "HIGH",
                        "message": "Potential division by zero - missing zero check guard",
                        "suggestion": "Add validation guard before performing division",
                        "oldCode": line_stripped,
                        "newCode": f"{var_name} = {expr} if {divisor} != 0 else 0",
                        "canAutoFix": True
                    })
    
    return findings