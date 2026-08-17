import ast
import re
import os
import json
import asyncio
import subprocess
from typing import Dict, List, Any, Optional

async def run_semgrep_analysis(file_path: str) -> Dict:
    """
    Run static application security testing (SAST) analysis on the given file
    """
    try:
        # Try semgrep if installed
        semgrep_results = await try_semgrep(file_path)
        if semgrep_results:
            return semgrep_results

        # AST & Pattern Analysis Engine
        findings = run_ast_sast_scan(file_path)
        
        return {
            "status": "error" if any(f.get("severity") in ["CRITICAL", "HIGH"] for f in findings) else "success",
            "findings": findings,
            "engine": "ast-sast-engine",
            "analyzed_at": file_path
        }
    except Exception as e:
        return {
            "status": "error",
            "findings": [],
            "error": str(e),
            "engine": "ast-sast-engine"
        }

async def try_semgrep(file_path: str) -> Optional[Dict]:
    """Attempt running semgrep binary if installed on host system"""
    try:
        rules = {
            "rules": [
                {
                    "id": "sql-injection",
                    "pattern": "execute($SQL)",
                    "message": "Potential SQL injection vulnerability",
                    "severity": "ERROR",
                    "languages": ["python"]
                }
            ]
        }
        import tempfile
        import yaml
        rules_path = os.path.join(tempfile.gettempdir(), "semgrep_rules.yaml")
        with open(rules_path, "w", encoding="utf-8") as f:
            yaml.dump(rules, f)

        proc = await asyncio.create_subprocess_exec(
            "semgrep", "--config", rules_path, "--json", file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode == 0 and stdout:
            data = json.loads(stdout.decode('utf-8'))
            findings = parse_semgrep_results(data)
            return {
                "status": "error" if findings else "success",
                "findings": findings,
                "engine": "semgrep-native"
            }
    except Exception:
        pass
    return None

def parse_semgrep_results(semgrep_output: dict) -> List[Dict]:
    findings = []
    for result in semgrep_output.get("results", []):
        findings.append({
            "rule": result.get("check_id", "Semgrep Rule"),
            "message": result.get("extra", {}).get("message", "Security issue found"),
            "severity": result.get("extra", {}).get("severity", "HIGH").upper(),
            "line": result.get("start", {}).get("line", 1),
            "column": result.get("start", {}).get("col", 1),
            "file": result.get("path", ""),
            "taint_flow": ["Source: User input", "Sink: Executed expression"]
        })
    return findings

def run_ast_sast_scan(file_path: str) -> List[Dict]:
    """
    Advanced Python AST Static Analyzer for OWASP Top 10 Security Rules
    """
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code_content = f.read()
    except Exception:
        return []

    lines = code_content.splitlines()
    findings = []

    # Parse AST
    try:
        tree = ast.parse(code_content, filename=file_path)
        ast_visitor = SecurityASTVisitor(lines)
        ast_visitor.visit(tree)
        findings.extend(ast_visitor.findings)
    except SyntaxError as se:
        findings.append({
            "rule": "Python Syntax Error",
            "message": f"Syntax error prevents AST scan: {se.msg}",
            "severity": "LOW",
            "line": se.lineno or 1,
            "taint_flow": [f"Line {se.lineno}: Syntax Error"]
        })

    # Regex & Pattern Fallbacks
    regex_findings = run_pattern_scan(lines)
    
    # Merge findings avoiding duplicate lines
    existing_lines = {f["line"] for f in findings}
    for rf in regex_findings:
        if rf["line"] not in existing_lines:
            findings.append(rf)
            existing_lines.add(rf["line"])

    return sorted(findings, key=lambda x: x["line"])

class SecurityASTVisitor(ast.NodeVisitor):
    def __init__(self, lines: List[str]):
        self.lines = lines
        self.findings = []

    def visit_Call(self, node: ast.Call):
        func_name = self._get_func_name(node.func)
        short_func = func_name.split(".")[-1]
        
        # 1. SQL Injection check
        if short_func in ["execute", "executemany", "raw", "query"]:
            if node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, (ast.JoinedStr, ast.BinOp)):
                    self.findings.append({
                        "rule": "SQL Injection (CWE-89)",
                        "message": "Dynamic string construction detected inside SQL query execution",
                        "severity": "CRITICAL",
                        "line": node.lineno,
                        "taint_flow": [
                            f"User Input -> String Formatting at line {node.lineno}",
                            f"SQL Execution Sink: {func_name}()"
                        ]
                    })

        # 2. Command Injection check
        if func_name in ["os.system", "os.popen", "eval", "exec"]:
            self.findings.append({
                "rule": "Command Injection / Code Execution (CWE-78/95)",
                "message": f"Dangerous execution call '{func_name}' with dynamic arguments",
                "severity": "CRITICAL",
                "line": node.lineno,
                "taint_flow": [
                    f"Dynamic Argument at line {node.lineno}",
                    f"Execution Sink: {func_name}()"
                ]
            })

        if func_name in ["subprocess.Popen", "subprocess.run", "subprocess.call"]:
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                    self.findings.append({
                        "rule": "Subprocess Shell Execution (CWE-78)",
                        "message": "subprocess called with shell=True which risks command injection",
                        "severity": "HIGH",
                        "line": node.lineno,
                        "taint_flow": ["shell=True parameter flag", f"Call: {func_name}"]
                    })

        # 3. Weak Cryptography
        if func_name in ["hashlib.md5", "hashlib.sha1"]:
            self.findings.append({
                "rule": "Weak Cryptographic Hash (CWE-327)",
                "message": f"Use of weak hashing algorithm '{func_name}'",
                "severity": "MEDIUM",
                "line": node.lineno,
                "taint_flow": [f"Hash invocation: {func_name}()"]
            })

        # 4. Insecure Deserialization
        if func_name in ["pickle.loads", "pickle.load", "marshal.loads"]:
            self.findings.append({
                "rule": "Insecure Deserialization (CWE-502)",
                "message": f"Unsafe deserialization call '{func_name}' can lead to remote code execution",
                "severity": "CRITICAL",
                "line": node.lineno,
                "taint_flow": [f"Deserialization Sink: {func_name}()"]
            })

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # Hardcoded Secret Check in Variable Assignment
        for target in node.targets:
            var_name = self._get_var_name(target).lower()
            if any(k in var_name for k in ["password", "secret", "api_key", "token", "private_key"]):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    val = node.value.value
                    if len(val) > 3 and val not in ["TODO", "xxx", "CHANGE_ME", ""]:
                        self.findings.append({
                            "rule": "Hardcoded Secret (CWE-798)",
                            "message": f"Hardcoded credential or API key detected in variable '{var_name}'",
                            "severity": "HIGH",
                            "line": node.lineno,
                            "taint_flow": [f"Hardcoded literal assigned to {var_name}"]
                        })
        self.generic_visit(node)

    def _get_func_name(self, node: Any) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val_name = self._get_func_name(node.value)
            return f"{val_name}.{node.attr}" if val_name else node.attr
        return ""

    def _get_var_name(self, node: Any) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return ""

def run_pattern_scan(lines: List[str]) -> List[Dict]:
    findings = []
    
    secret_pattern = re.compile(r"""(?i)(api[_-]?key|secret[_-]?key|password|jwt[_-]?secret)\s*=\s*['"][A-Za-z0-9_\-]{6,}['"]""")
    sqli_pattern = re.compile(r"""(?i)(select|insert|update|delete)\s+.*(%s|\{\}|f['"])""")

    for idx, line in enumerate(lines, start=1):
        clean_line = line.strip()
        if clean_line.startswith("#"):
            continue

        if secret_pattern.search(clean_line):
            findings.append({
                "rule": "Hardcoded Credential Pattern",
                "message": "Potential hardcoded credential or secret key detected",
                "severity": "HIGH",
                "line": idx,
                "taint_flow": ["Regex match on sensitive key pattern"]
            })

        if sqli_pattern.search(clean_line) and ("execute" in clean_line or "query" in clean_line or "=" in clean_line):
            findings.append({
                "rule": "SQL Injection Pattern",
                "message": "SQL query containing unescaped string formatting",
                "severity": "CRITICAL",
                "line": idx,
                "taint_flow": ["Unescaped SQL query string formatting"]
            })

    return findings