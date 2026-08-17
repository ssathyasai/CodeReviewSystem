import asyncio
import subprocess
import psutil
import time
import tempfile
import os
import sys
import ast
from typing import Dict, List

async def run_runtime_analysis(file_path: str) -> Dict:
    """
    Dynamic Application Security Testing (DAST) & Dynamic Runtime Analysis Engine.
    Monitors process execution metrics, resource utilization, exceptions, and runtime risks.
    """
    try:
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "findings": [],
                "error": f"File not found: {file_path}",
                "engine": "dast-engine"
            }

        # 1. Pre-execution AST safety inspection
        static_anomalies = analyze_code_structure(file_path)

        # 2. Execution wrapper
        wrapper_code = f"""
import sys
import time

try:
    with open(r'''{file_path}''', 'r', encoding='utf-8') as f:
        code_content = f.read()
    exec(compile(code_content, r'''{file_path}''', 'exec'), {{'__name__': '__main__'}})
except Exception as e:
    print(f"[DAST Runtime Error] {{type(e).__name__}}: {{e}}", file=sys.stderr)
    sys.exit(1)
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            wrapper_path = f.name
            f.write(wrapper_code)

        findings = list(static_anomalies)

        try:
            # Launch isolated process
            process = await asyncio.create_subprocess_exec(
                sys.executable, wrapper_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Monitor process resource metrics
            metrics = await monitor_process(process.pid, timeout=3.0)

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=4.0)
            
            # Check stderr for runtime exceptions
            if stderr:
                err_text = stderr.decode('utf-8', errors='ignore')
                if "Runtime Error" in err_text or "Exception" in err_text:
                    findings.append({
                        "issue": "Runtime Unhandled Exception",
                        "severity": "HIGH",
                        "details": f"Script failed at runtime: {err_text.strip()[:150]}",
                        "cpuPeak": "N/A"
                    })

            # Resource metrics analysis
            if metrics:
                metric_findings = analyze_metrics(metrics)
                findings.extend(metric_findings)

        except asyncio.TimeoutError:
            try:
                process.kill()
            except Exception:
                pass
            findings.append({
                "issue": "Execution Timeout / Infinite Loop",
                "severity": "HIGH",
                "details": "Execution exceeded time threshold (possible infinite loop or blocking call)",
                "cpuPeak": "> 90%"
            })
        finally:
            try:
                os.unlink(wrapper_path)
            except Exception:
                pass

        return {
            "status": "warning" if findings else "success",
            "findings": findings,
            "engine": "dast-dynamic-engine"
        }

    except Exception as e:
        return {
            "status": "error",
            "findings": [],
            "error": str(e),
            "engine": "dast-dynamic-engine"
        }

def analyze_code_structure(file_path: str) -> List[Dict]:
    """Inspect AST for potential runtime risks (infinite loops, unclosed handles, global mutations)"""
    anomalies = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()

        tree = ast.parse(code)
        for node in ast.walk(tree):
            # Check while True loop without break
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    has_break = any(isinstance(child, ast.Break) for child in ast.walk(node))
                    if not has_break:
                        anomalies.append({
                            "issue": "Potential Infinite Loop (while True)",
                            "severity": "HIGH",
                            "details": f"Unbounded loop detected at line {node.lineno} without break statement",
                            "cpuPeak": "High Risk"
                        })
            # Global memory accumulation check
            if isinstance(node, ast.Global):
                anomalies.append({
                    "issue": "Global State Mutation",
                    "severity": "LOW",
                    "details": f"Global variable reference '{', '.join(node.names)}' at line {node.lineno}",
                    "cpuPeak": "Normal"
                })
    except Exception:
        pass
    return anomalies

async def monitor_process(pid: int, timeout: float = 3.0) -> List[Dict]:
    metrics = []
    start_time = time.time()
    try:
        process = psutil.Process(pid)
        while time.time() - start_time < timeout:
            try:
                cpu_percent = process.cpu_percent(interval=0.1)
                mem_info = process.memory_info()
                metrics.append({
                    "cpu_percent": cpu_percent,
                    "memory_mb": mem_info.rss / (1024 * 1024)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
    except Exception:
        pass
    return metrics

def analyze_metrics(metrics: List[Dict]) -> List[Dict]:
    findings = []
    if not metrics:
        return findings

    cpu_values = [m["cpu_percent"] for m in metrics]
    max_cpu = max(cpu_values) if cpu_values else 0.0

    mem_values = [m["memory_mb"] for m in metrics]
    mem_delta = mem_values[-1] - mem_values[0] if len(mem_values) > 1 else 0.0

    if max_cpu > 85.0:
        findings.append({
            "issue": "High Dynamic CPU Spike",
            "severity": "MEDIUM",
            "details": f"Process CPU spiked at {max_cpu:.1f}% during dynamic execution",
            "cpuPeak": f"{max_cpu:.1f}%"
        })

    if mem_delta > 30.0:
        findings.append({
            "issue": "Dynamic Memory Surge / Leak",
            "severity": "MEDIUM",
            "details": f"Subprocess RAM allocated increased by {mem_delta:.1f} MB during execution",
            "cpuPeak": f"{max_cpu:.1f}%"
        })

    return findings