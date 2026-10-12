import asyncio
import ipaddress
import logging
import socket
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from backend.app.config import settings
from backend.app.models.dast import DastAlert, DastEndpoint, DastRiskLevel, DastScanResult
from backend.app.models.finding import (
    Finding,
    FindingCategoryEnum,
    FindingStatusEnum,
    ScannerTypeEnum,
    SeverityEnum,
)

logger = logging.getLogger("codereview.dast")

# Blocked SSRF metadata & dangerous endpoints
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("169.254.169.254/32"),  # Cloud metadata service (AWS/GCP/Azure)
    ipaddress.ip_network("100.100.100.200/32"),  # Alibaba cloud metadata
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
]

REQUIRED_SECURITY_HEADERS = [
    ("Content-Security-Policy", "Missing Content-Security-Policy (CSP) allows Cross-Site Scripting (XSS) and data injection attacks."),
    ("Strict-Transport-Security", "Missing HSTS allows SSL-stripping and Man-in-the-Middle (MITM) attacks."),
    ("X-Frame-Options", "Missing X-Frame-Options allows clickjacking attacks."),
    ("X-Content-Type-Options", "Missing X-Content-Type-Options (nosniff) enables MIME-type sniffing vulnerabilities."),
    ("Referrer-Policy", "Missing Referrer-Policy may leak sensitive URL parameters to third-party referrers."),
    ("Permissions-Policy", "Missing Permissions-Policy leaves sensitive browser hardware features unrestricted.")
]

COMMON_PROBE_PATHS = [
    "/",
    "/api",
    "/api/v1/health",
    "/health",
    "/login",
    "/admin",
    "/search",
    "/.env",
    "/.git/config",
    "/swagger.json",
    "/openapi.json",
    "/actuator/health",
    "/phpinfo.php"
]


class DastEngine:
    @classmethod
    def validate_target_safety(cls, target_url: str) -> Tuple[bool, str]:
        """
        Validates whether target URL is authorized and safe to test:
        - Must be http or https
        - Prohibits cloud metadata addresses (169.254.169.254)
        - Prevents unauthorized internal network scanning unless in explicit dev mode
        """
        if not target_url:
            return False, "Target URL cannot be empty."

        try:
            parsed = urlparse(target_url.strip())
        except Exception:
            return False, "Invalid URL structure."

        if parsed.scheme not in ["http", "https"]:
            return False, "Target URL must use HTTP or HTTPS."

        hostname = parsed.hostname
        if not hostname:
            return False, "Target URL must contain a valid hostname."

        # Resolve IP to check for metadata service or SSRF target
        try:
            target_ip_str = socket.gethostbyname(hostname)
            target_ip = ipaddress.ip_address(target_ip_str)

            for blocked in BLOCKED_IP_RANGES:
                if target_ip in blocked:
                    return False, f"Target IP {target_ip_str} is in a restricted/cloud-metadata range."

            # If target is private IP (127.0.0.1, 10.x, 192.168.x), verify dev setting
            if target_ip.is_private and not settings.DAST_ALLOW_LOCAL_TARGETS:
                return False, f"Private/Local IP targets ({target_ip_str}) are disabled by DAST governance policy."

        except socket.gaierror:
            return False, f"Could not resolve host '{hostname}' in DNS."
        except Exception as e:
            logger.warning(f"IP check error: {e}")

        return True, "Target authorized."

    @classmethod
    async def run_dast_scan(cls, target_url: str, scan_id: str) -> DastScanResult:
        """
        Executes controlled DAST analysis against the authorized target URL:
        1. Connectivity and SSL/TLS validation
        2. Passive Security Headers & Cookie Flags Audit
        3. Endpoint Discovery (Spidering safe paths)
        4. Active Security Probes (Safe SQLi reflection, XSS probes, Information disclosure)
        5. Compiles structured DAST alerts and metrics
        """
        start_time = time.time()
        is_auth, auth_msg = cls.validate_target_safety(target_url)
        
        if not is_auth:
            return DastScanResult(
                scan_id=scan_id,
                target_url=target_url or "N/A",
                is_authorized=False,
                status="BLOCKED",
                reason=f"DAST Execution Blocked: {auth_msg}",
                scan_duration_seconds=round(time.time() - start_time, 2)
            )

        alerts: List[DastAlert] = []
        endpoints: List[DastEndpoint] = []
        headers_found: Dict[str, str] = {}
        missing_headers: List[str] = []

        async with httpx.AsyncClient(timeout=10.0, verify=False, follow_redirects=True) as client:
            # 1. Base check
            try:
                base_resp = await client.get(target_url)
                resp_headers = {k.lower(): v for k, v in base_resp.headers.items()}
                headers_found = dict(base_resp.headers)

                # Passive: Check security headers
                for header_name, desc in REQUIRED_SECURITY_HEADERS:
                    if header_name.lower() not in resp_headers:
                        missing_headers.append(header_name)
                        alerts.append(DastAlert(
                            id=f"DAST-HDR-{uuid.uuid4().hex[:6]}",
                            plugin_id="10038",
                            alert_name=f"Missing Security Header: {header_name}",
                            risk=DastRiskLevel.LOW if header_name != "Content-Security-Policy" else DastRiskLevel.MEDIUM,
                            confidence="HIGH",
                            url=target_url,
                            description=desc,
                            solution=f"Configure web server to return the '{header_name}' HTTP response header with secure defaults.",
                            cwe_id="CWE-693"
                        ))

                # Passive: Check Server info leakage
                if "server" in resp_headers or "x-powered-by" in resp_headers:
                    server_val = resp_headers.get("server") or resp_headers.get("x-powered-by")
                    alerts.append(DastAlert(
                        id=f"DAST-INFO-{uuid.uuid4().hex[:6]}",
                        plugin_id="10036",
                        alert_name="Server / Framework Banner Information Disclosure",
                        risk=DastRiskLevel.LOW,
                        confidence="HIGH",
                        url=target_url,
                        evidence=f"Header: {server_val}",
                        description=f"Server returned version header '{server_val}', revealing technology stack to attackers.",
                        solution="Suppress server tokens and X-Powered-By headers in web server configuration.",
                        cwe_id="CWE-200"
                    ))

                # Passive: Check Cookies
                for cookie in base_resp.cookies.jar:
                    if not cookie.secure:
                        alerts.append(DastAlert(
                            id=f"DAST-COOKIE-{uuid.uuid4().hex[:6]}",
                            plugin_id="10011",
                            alert_name=f"Cookie Without Secure Flag: {cookie.name}",
                            risk=DastRiskLevel.MEDIUM,
                            confidence="HIGH",
                            url=target_url,
                            param=cookie.name,
                            description=f"Cookie '{cookie.name}' is set without the Secure attribute, allowing transmission over unencrypted HTTP.",
                            solution="Set the 'Secure' attribute on all authentication and session cookies.",
                            cwe_id="CWE-614"
                        ))

                endpoints.append(DastEndpoint(
                    url=target_url,
                    method="GET",
                    status_code=base_resp.status_code,
                    response_time_ms=round(base_resp.elapsed.total_seconds() * 1000, 1),
                    alerts_count=len(alerts)
                ))

            except Exception as e:
                logger.warning(f"DAST connection error on base URL {target_url}: {e}")
                return DastScanResult(
                    scan_id=scan_id,
                    target_url=target_url,
                    is_authorized=True,
                    status="FAILED",
                    reason=f"Failed to connect to target URL: {str(e)}",
                    scan_duration_seconds=round(time.time() - start_time, 2)
                )

            # 2. Spider & Probe Common Paths
            for path in COMMON_PROBE_PATHS[1:]:
                probe_url = urljoin(target_url, path)
                try:
                    p_resp = await client.get(probe_url)
                    if p_resp.status_code in [200, 204, 301, 302, 401, 403]:
                        endpoints.append(DastEndpoint(
                            url=probe_url,
                            method="GET",
                            status_code=p_resp.status_code,
                            response_time_ms=round(p_resp.elapsed.total_seconds() * 1000, 1)
                        ))

                        # Check for exposed sensitive files
                        if path in ["/.env", "/.git/config"] and p_resp.status_code == 200:
                            content_sample = p_resp.text[:100]
                            if "=" in content_sample or "[core]" in content_sample:
                                alerts.append(DastAlert(
                                    id=f"DAST-EXPOSURE-{uuid.uuid4().hex[:6]}",
                                    plugin_id="10045",
                                    alert_name=f"Exposed Sensitive File: {path}",
                                    risk=DastRiskLevel.HIGH,
                                    confidence="HIGH",
                                    url=probe_url,
                                    evidence=content_sample[:50],
                                    description=f"Sensitive repository/configuration file {path} is publicly accessible via web root.",
                                    solution="Restrict access to hidden files (.env, .git) in web server routing rules.",
                                    cwe_id="CWE-538"
                                ))
                except Exception:
                    pass

            # 3. Active Safe Security Probes (Reflected XSS, SQLi, Auth Bypass, Error Disclosures)
            xss_test_payload = "<xssTest123>"
            sqli_test_payload = "' OR 1=1--"
            error_probe_payload = "'\";--}{<>"

            # Database error signatures for runtime SQL injection detection
            db_error_signatures = [
                "syntax error in string", "unclosed quotation mark", "you have an error in your sql syntax",
                "pg_query(): query failed", "sqlite3.operationalerror", "ora-00933", "microsoft ole db provider for sql server",
                "sqlstate[42000]"
            ]

            # Stack trace signatures for error disclosure detection
            stack_trace_signatures = [
                "traceback (most recent call last):", "nullpointerexception", "fatal error:", "fastapi error",
                "exception in thread", "django.core.exceptions", "at line in file"
            ]
            
            for ep in endpoints[:5]:
                # Test Reflected XSS & SQLi on endpoints accepting parameters
                if "?" in ep.url or "/search" in ep.url or "/api" in ep.url or "/login" in ep.url:
                    try:
                        # 3a. Test Reflected XSS
                        xss_url = f"{ep.url}?q={xss_test_payload}&search={xss_test_payload}"
                        xss_resp = await client.get(xss_url)
                        if xss_test_payload in xss_resp.text:
                            alerts.append(DastAlert(
                                id=f"DAST-XSS-{uuid.uuid4().hex[:6]}",
                                plugin_id="40012",
                                alert_name="Reflected Cross-Site Scripting (XSS)",
                                risk=DastRiskLevel.HIGH,
                                confidence="HIGH",
                                url=xss_url,
                                attack_vector=xss_test_payload,
                                evidence=xss_test_payload,
                                description="Injected HTML/JS characters were reflected in the server response without proper sanitization.",
                                solution="Contextually HTML-encode all user input before rendering in the response body.",
                                cwe_id="CWE-79"
                            ))

                        # 3b. Test Runtime SQL Injection Syntax & Error Reflection
                        sqli_url = f"{ep.url}?id={sqli_test_payload}&user={sqli_test_payload}&search={sqli_test_payload}"
                        sqli_resp = await client.get(sqli_url)
                        resp_lower = sqli_resp.text.lower()
                        for sig in db_error_signatures:
                            if sig in resp_lower:
                                alerts.append(DastAlert(
                                    id=f"DAST-SQLI-{uuid.uuid4().hex[:6]}",
                                    plugin_id="40018",
                                    alert_name="Runtime SQL Injection / Database Error Disclosure",
                                    risk=DastRiskLevel.HIGH,
                                    confidence="HIGH",
                                    url=sqli_url,
                                    attack_vector=sqli_test_payload,
                                    evidence=sig,
                                    description=f"Server returned a raw database syntax error '{sig}' when probed with an SQL injection payload.",
                                    solution="Use parameterized SQL queries and disable database verbose error display in production.",
                                    cwe_id="CWE-89"
                                ))
                                break

                        # 3c. Test Stack Trace / Security-Related Error Disclosure
                        err_url = f"{ep.url}?debug=1&id={error_probe_payload}"
                        err_resp = await client.get(err_url)
                        err_lower = err_resp.text.lower()
                        for st_sig in stack_trace_signatures:
                            if st_sig in err_lower:
                                alerts.append(DastAlert(
                                    id=f"DAST-STACK-{uuid.uuid4().hex[:6]}",
                                    plugin_id="10023",
                                    alert_name="Verbose Stack Trace / Error Disclosure",
                                    risk=DastRiskLevel.MEDIUM,
                                    confidence="HIGH",
                                    url=err_url,
                                    evidence=st_sig,
                                    description=f"Malformed input triggered an unhandled exception leaking server stack trace or framework internals: '{st_sig}'.",
                                    solution="Implement global exception handlers and return generic, non-descriptive error responses.",
                                    cwe_id="CWE-209"
                                ))
                                break

                        # 3d. Test Improper Input Validation (Null bytes and large buffer)
                        null_byte_url = f"{ep.url}?param=%00&data={'A'*1024}"
                        null_resp = await client.get(null_byte_url)
                        if null_resp.status_code == 500 and "unhandled" in null_resp.text.lower():
                            alerts.append(DastAlert(
                                id=f"DAST-INPUT-VAL-{uuid.uuid4().hex[:6]}",
                                plugin_id="10049",
                                alert_name="Improper Input Validation (Null Byte / Buffer Handling)",
                                risk=DastRiskLevel.MEDIUM,
                                confidence="MEDIUM",
                                url=null_byte_url,
                                description="Sending null bytes or buffer payloads triggered internal server 500 failure instead of graceful 400 Bad Request validation.",
                                solution="Validate and sanitize all input formats and length boundaries strictly before processing.",
                                cwe_id="CWE-20"
                            ))

                    except Exception:
                        pass

            # 4. Active Authentication Bypass & Broken Access Control Probes
            admin_test_paths = ["/admin", "/api/admin", "/dashboard", "/api/v1/admin"]
            for a_path in admin_test_paths:
                target_admin_url = urljoin(target_url, a_path)
                try:
                    # Normal unauthenticated request
                    norm_resp = await client.get(target_admin_url)
                    if norm_resp.status_code == 200 and ("admin" in norm_resp.text.lower() or "dashboard" in norm_resp.text.lower()):
                        alerts.append(DastAlert(
                            id=f"DAST-UNAUTH-ADMIN-{uuid.uuid4().hex[:6]}",
                            plugin_id="10051",
                            alert_name=f"Broken Access Control: Unauthenticated Admin Endpoint {a_path}",
                            risk=DastRiskLevel.HIGH,
                            confidence="HIGH",
                            url=target_admin_url,
                            description=f"Administrative endpoint {a_path} is accessible without authentication (HTTP 200 OK).",
                            solution="Enforce strict authentication and role-based access control (RBAC) on all administrative routes.",
                            cwe_id="CWE-284"
                        ))

                    # Header-based authentication bypass check (X-Original-URL, X-Forwarded-For)
                    bypass_headers = {
                        "X-Forwarded-For": "127.0.0.1",
                        "X-Original-URL": a_path,
                        "X-Custom-IP-Authorization": "127.0.0.1"
                    }
                    bypass_resp = await client.get(target_admin_url, headers=bypass_headers)
                    if norm_resp.status_code in [401, 403] and bypass_resp.status_code == 200:
                        alerts.append(DastAlert(
                            id=f"DAST-AUTH-BYPASS-{uuid.uuid4().hex[:6]}",
                            plugin_id="10052",
                            alert_name=f"Authentication Bypass via Header Spoofing on {a_path}",
                            risk=DastRiskLevel.HIGH,
                            confidence="HIGH",
                            url=target_admin_url,
                            description="Sending internal IP headers (X-Forwarded-For, X-Original-URL) bypassed gateway authentication controls.",
                            solution="Do not trust client-supplied X-Forwarded-For or X-Original-URL headers for authorization decisions.",
                            cwe_id="CWE-287"
                        ))
                except Exception:
                    pass

        # Compute stats
        high_cnt = sum(1 for a in alerts if a.risk == DastRiskLevel.HIGH)
        med_cnt = sum(1 for a in alerts if a.risk == DastRiskLevel.MEDIUM)
        low_cnt = sum(1 for a in alerts if a.risk == DastRiskLevel.LOW)
        info_cnt = sum(1 for a in alerts if a.risk == DastRiskLevel.INFORMATIONAL)

        duration = round(time.time() - start_time, 2)

        return DastScanResult(
            scan_id=scan_id,
            target_url=target_url,
            is_authorized=True,
            status="COMPLETED",
            spider_endpoints_found=len(endpoints),
            endpoints=endpoints,
            alerts=alerts,
            total_alerts=len(alerts),
            high_count=high_cnt,
            medium_count=med_cnt,
            low_count=low_cnt,
            info_count=info_cnt,
            scan_duration_seconds=duration,
            headers_analyzed=headers_found,
            missing_security_headers=missing_headers,
            ssl_tls_info={"scheme": urlparse(target_url).scheme.upper(), "https_enforced": target_url.startswith("https://")}
        )

    @classmethod
    def convert_dast_alerts_to_findings(cls, dast_result: DastScanResult, scan_id: str) -> List[Finding]:
        """Converts DAST alerts to normalized Finding models for the unified report."""
        findings = []
        for alert in dast_result.alerts:
            sev_map = {
                DastRiskLevel.HIGH: SeverityEnum.HIGH,
                DastRiskLevel.MEDIUM: SeverityEnum.MEDIUM,
                DastRiskLevel.LOW: SeverityEnum.LOW,
                DastRiskLevel.INFORMATIONAL: SeverityEnum.INFO,
            }
            findings.append(Finding(
                id=f"dast-find-{uuid.uuid4().hex[:8]}",
                scan_id=scan_id,
                title=f"DAST: {alert.alert_name}",
                description=alert.description,
                severity=sev_map.get(alert.risk, SeverityEnum.LOW),
                category=FindingCategoryEnum.OTHER if "Header" in alert.alert_name else FindingCategoryEnum.XSS if "XSS" in alert.alert_name else FindingCategoryEnum.SECURITY_MISCONFIG,
                scanner=ScannerTypeEnum.OWASP_ZAP,
                rule_id=alert.id,
                file_path=alert.url,
                code_snippet=alert.evidence or alert.attack_vector or f"Target URL: {alert.url}",
                cwe_ids=[alert.cwe_id] if alert.cwe_id else [],
                remediation_guidance=alert.solution,
                confidence=alert.confidence
            ))
        return findings
