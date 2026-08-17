import asyncio
import ast
import json
import os
import shutil
import subprocess
from typing import Dict, List, Optional
import aiohttp
import re

# Configuration for LLM providers
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()  # "ollama" or "groq"

# Ollama configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-70b-8192")  # Groq's most capable model

# Analysis configuration
MAX_ANALYSIS_TIME = 120  # seconds
CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence for findings

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
        syntax_findings = check_syntax(code_content, lang)

        findings = syntax_findings.copy()

        if LLM_PROVIDER == 'ollama':
            findings += await analyze_with_ollama(code_content, guidelines, file_path)
        elif LLM_PROVIDER == 'groq':
            from engines.governance_engine_api import analyze_with_groq
            findings += await analyze_with_groq(code_content, guidelines, file_path)
        else:
            findings += simulate_governance_check(code_content, guidelines)

        # Deduplicate exact rule/line messages to avoid double count
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
        syntax_findings = check_syntax(code_content, lang)

        findings = syntax_findings.copy()

        if LLM_PROVIDER == 'ollama':
            findings += await analyze_with_context(code_content, guidelines, context, lang)
        elif LLM_PROVIDER == 'groq':
            from engines.governance_engine_api import analyze_with_context as analyze_with_context_groq
            findings += await analyze_with_context_groq(code_content, guidelines, context, lang)
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


def detect_language_from_code(code: str, file_path: Optional[str] = None) -> str:
    """Basic language detection from file extension + keywords"""
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
    # Heuristics
    if 'def ' in code or 'import ' in code or 'print(' in code:
        return 'python'
    if 'function ' in code or 'console.log' in code or 'var ' in code:
        return 'javascript'
    if 'public class' in code or 'System.out.println' in code:
        return 'java'

    return 'unknown'


def _get_undefined_names_python(tree: ast.AST) -> List[Dict]:
    findings = []
    builtin_names = set(dir(__builtins__))

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
                if name in builtin_names:
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
                # attribute assignments (obj.attr) are not tracked as variable names
                pass
            return names

    visitor = ScopeVisitor()
    visitor.visit(tree)

    for name, lineno, _ in visitor.undefined:
        findings.append({
            'rule': 'Undefined Variable',
            'line': lineno,
            'severity': 'HIGH',
            'message': f'Undefined variable: {name}',
            'suggestion': f'Declare or pass `{name}` before use',
            'oldCode': '',
            'newCode': '',
            'confidence': 0.85
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
        # CLI not installed for this language, fallback to LLM or simulate
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
                'suggestion': 'Fix the Python syntax error shown',
                'oldCode': e.text.strip() if e.text else '',
                'newCode': '',
                'confidence': 0.99
            })
    else:
        findings.extend(_shell_syntax_check(code, language))

    return findings


async def analyze_with_context(code: str, guidelines: str, context: str, language: str) -> List[Dict]:
    """
    Analyze code with cross-file context using Ollama
    """
    try:
        prompt = f"""You are a robust, language-aware code governance and security reviewer.\n\nLANGUAGE: {language}\n\nCONTEXT INFORMATION:\n{context}\n\nGUIDELINES:\n{guidelines}\n\nCODE TO ANALYZE:\n```{language}\n{code}\n```\n\nTasks:\n1. Identify all syntax errors and their exact location.\n2. Identify undefined and uninitialized symbols.\n3. Identify security issues: hardcoded secret, injection, unsafe I/O, path traversal.\n4. Identify policy violations: hardcoded financial constants, missing sanitization.\n5. Provide exact oldCode and newCode for code fixes (if possible).\n6. Provide short, actionable suggestion for each finding.\n\nEvery line may generate multiple findings. Do NOT combine separate issues into one.\n\nResponse format (JSON array):\n[\n  {{\n    "rule": "Issue type",\n    "line": 10,\n    "severity": "CRITICAL",\n    "message": "Description",\n    "suggestion": "How to fix",\n    "oldCode": "actual code line",\n    "newCode": "fixed code",\n    "confidence": 0.0\n  }}\n]\n\nOutput only valid JSON array without markdown code fences."""

        response_text = await call_ollama(prompt)
        
        # Parse JSON from response
        response_text = extract_json(response_text)
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

def read_guidelines() -> str:
    """
    Read organizational guidelines
    """
    default_guidelines = """
# Organizational Code Guidelines

## Financial Policies
1. Never hardcode discount rates, prices, or financial calculations
2. All financial constants must be retrieved from ConfigService
3. Discount rates must support A/B testing and regional variations

## Security Policies
1. All user input must be sanitized before database operations
2. No hardcoded credentials or API keys
3. Sensitive data must be encrypted at rest

## Performance Policies
1. Database queries must use connection pooling
2. Large datasets must be paginated
3. Memory-intensive operations must have cleanup handlers

## Code Quality
1. All public APIs must have OpenAPI documentation
2. Error messages must not expose internal details
3. Logging must follow structured format
"""
    
    guidelines_path = "guidelines.md"
    
    try:
        if os.path.exists(guidelines_path):
            with open(guidelines_path, 'r') as f:
                return f.read()
    except:
        pass
    
    return default_guidelines


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

async def call_ollama(prompt: str, system_prompt: str = "Respond only with valid JSON. Always provide exact code snippets, never descriptions.") -> str:
    """
    Call Ollama API for LLM inference
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                        "num_predict": 4000
                    }
                },
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    response_text = result.get("response", "")
                    lang = detect_language_from_code(prompt)
                    write_debug_log("ollama", prompt, response_text, lang)
                    return response_text
                else:
                    error_text = await response.text()
                    raise Exception(f"Ollama API error: {response.status} - {error_text}")
    except Exception as e:
        print(f"Ollama API call failed: {e}")
        raise

def extract_json(text: str) -> str:
    """
    Extract JSON from response text (handles markdown code blocks)
    """
    text = text.strip()
    
    # Remove markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    
    # Find JSON array or object
    if text.startswith('['):
        end = text.rfind(']')
        if end != -1:
            text = text[:end+1]
    elif text.startswith('{'):
        end = text.rfind('}')
        if end != -1:
            text = text[:end+1]
    
    return text

async def analyze_with_ollama(code: str, guidelines: str, file_path: str) -> List[Dict]:
    """
    Use Ollama local LLM - provide actual code snippets, not descriptions
    """
    try:
        requirements = ""
        req_path = "requirements_spec.md"
        if os.path.exists(req_path):
            with open(req_path, 'r') as f:
                requirements = f.read()
        
        prompt = f"""You are an expert code governance AI. Analyze code in a language-aware manner and provide fixes with ACTUAL CODE SNIPPETS.\n\nLANGUAGE: {detect_language_from_code(code, file_path)}\n\nCRITICAL RULES:\n1. oldCode: MUST be the EXACT code line from the file (not a description)\n2. newCode: MUST be the EXACT replacement code (not a description)\n3. suggestion: Human-readable explanation (this is separate)\n4. Do NOT detect os.getenv(), ConfigService.get(), or SecureVault as hardcoded (if language is Python)\n5. Only flag ACTUAL hardcoded values like "password123" or 0.20\n\nGUIDELINES:\n{guidelines}\n\nCODE:\n```{detect_language_from_code(code, file_path)}\n{code}\n```\n\nResponse format (JSON array):
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

        response_text = await call_ollama(prompt)
        response_text = extract_json(response_text)
        
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
        print(f"Ollama analysis error: {e}")
        return simulate_governance_check(code, guidelines)

def simulate_governance_check(code: str, guidelines: str) -> List[Dict]:
    """
    Simulate governance check - detect REAL issues only
    """
    findings = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Skip empty lines and comments
        if not line_stripped or line_stripped.startswith('#'):
            continue
        
        # Hardcoded credentials - but NOT if using os.getenv, SecureVault, etc.
        if any(kw in line.lower() for kw in ['password', 'api_key', 'secret', 'token']) and '=' in line:
            # Check if it's actually hardcoded (has quotes with value)
            if ('"' in line or "'" in line) and not any(safe in line for safe in ['getenv', 'SecureVault', 'config.get', 'os.environ']):
                # Extract the actual assignment
                if '=' in line:
                    var_name = line.split('=')[0].strip()
                    old_value = line.split('=')[1].strip()
                    findings.append({
                        "rule": "Hardcoded Credentials",
                        "line": i + 1,
                        "severity": "CRITICAL",
                        "message": "Credentials hardcoded in source code",
                        "suggestion": "Use environment variables or secure vault for credentials",
                        "oldCode": line_stripped,
                        "newCode": f"{var_name} = os.getenv('{var_name}')",
                        "canAutoFix": True
                    })
        
        # Hardcoded discount/price - but NOT if using ConfigService
        elif any(kw in line.lower() for kw in ['discount', 'price', 'rate']) and '=' in line:
            if any(char.isdigit() for char in line) and '0.' in line and 'ConfigService' not in line:
                var_name = line.split('=')[0].strip()
                findings.append({
                    "rule": "Hardcoded Configuration",
                    "line": i + 1,
                    "severity": "HIGH",
                    "message": "Financial constant hardcoded - violates policy",
                    "suggestion": "Use ConfigService to retrieve dynamic values",
                    "oldCode": line_stripped,
                    "newCode": f"{var_name} = ConfigService.get('{var_name.lower()}')",
                    "canAutoFix": True
                })
        
        # SQL injection - string formatting in queries
        elif ('execute' in line.lower() or 'query' in line.lower()):
            if ('f"' in line or "f'" in line or '+' in line) and ('SELECT' in line or 'INSERT' in line or 'UPDATE' in line or 'DELETE' in line):
                findings.append({
                    "rule": "SQL Injection",
                    "line": i + 1,
                    "severity": "CRITICAL",
                    "message": "SQL query vulnerable to injection",
                    "suggestion": "Use parameterized queries instead of string formatting",
                    "oldCode": line_stripped,
                    "newCode": 'cursor.execute("SELECT * FROM table WHERE id = ?", (user_input,))',
                    "canAutoFix": True
                })
        
        # Division without zero check
        elif '/' in line and '//' not in line and '/*' not in line:
            if '=' in line and not any(check in line for check in ['if', '!= 0', '> 0']):
                var_name = line.split('=')[0].strip()
                expr = line.split('=')[1].strip()
                # Extract divisor
                parts = expr.split('/')
                if len(parts) == 2:
                    divisor = parts[1].strip()
                    findings.append({
                        "rule": "Division by Zero Risk",
                        "line": i + 1,
                        "severity": "HIGH",
                        "message": "Potential division by zero - add safety check",
                        "suggestion": "Add validation to prevent division by zero",
                        "oldCode": line_stripped,
                        "newCode": f"{var_name} = {expr} if {divisor} != 0 else 0",
                        "canAutoFix": True
                    })
    
    return findings