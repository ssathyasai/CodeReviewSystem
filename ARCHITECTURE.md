# System Architecture Documentation

## Hybrid Code Intelligence & Governance Platform

### Overview
The **Hybrid Code Intelligence Agent** is an enterprise-grade code review, security audit, and policy compliance system. It integrates static analysis (SAST), dynamic execution profiling (DAST), and Large Language Model (LLM) governance into a unified multi-engine pipeline backed by MongoDB and FastAPI.

---

## 🏗 High-Level Architecture Diagram

```
+-----------------------------------------------------------------------+
|                            REACT SPA FRONTEND                         |
|   (Vite + Tailwind CSS + Lucide Icons + Real-time WebSockets / REST)  |
+-----------------------------------------------------------------------+
                                    |
                                    v (HTTP REST / WS)
+-----------------------------------------------------------------------+
|                             FASTAPI BACKEND                           |
|       - Static Asset Mounting & Single-Page Application Fallback      |
|       - MongoDB Atlas / Local Database Connection Manager (db.py)     |
|       - HMAC SHA-256 Webhook Security Gatekeeper                      |
+-----------------------------------------------------------------------+
           |                        |                       |
           v                        v                       v
+--------------------+    +--------------------+    +--------------------+
| 1. SAST ENGINE     |    | 2. DAST ENGINE     |    | 3. GOVERNANCE LLM  |
| - Python AST Tree  |    | - Process Profiler |    | - Groq Llama 3.3   |
| - OWASP Top 10     |    | - Memory Leaks     |    | - Code Remediation |
| - SQLi / Secrets   |    | - CPU Spike Check  |    | - Structured JSON  |
+--------------------+    +--------------------+    +--------------------+
           \                        |                       /
            \                       |                      /
             v                      v                     v
+-----------------------------------------------------------------------+
|                             MONGODB STORAGE                           |
|   - `projects` collection: Registered codebases & auto-scan flags    |
|   - `scans` collection: Historical audit runs, findings & verdicts    |
+-----------------------------------------------------------------------+
```

---

## 📦 Database Schemas (MongoDB)

### Collection: `projects`
Stores registered codebases managed by the agent.

```json
{
  "_id": "ObjectId(...)",
  "name": "MyProjectService",
  "path": "/absolute/path/to/project",
  "auto_scan": true,
  "created_at": "2026-08-17T18:00:00.000Z",
  "updated_at": "2026-08-17T18:05:00.000Z"
}
```

### Collection: `scans`
Stores multi-engine audit records and verdicts.

```json
{
  "_id": "ObjectId(...)",
  "scan_id": "b3e94a8f-2871-460b-8d13-91b53e77f0a8",
  "timestamp": "2026-08-17T18:10:00.000Z",
  "file": "test_code.py",
  "project_name": "MyProjectService",
  "engines": {
    "sast": { "status": "error", "findings": [...] },
    "dast": { "status": "warning", "findings": [...] },
    "governance": { "status": "error", "findings": [...] }
  },
  "verdict": {
    "decision": "BLOCK",
    "severity": "CRITICAL",
    "reason": "Found 2 critical issues"
  }
}
```

---

## 🔒 Webhook Security Model
GitHub webhook push events sent to `/github/webhook` must include a valid `X-Hub-Signature-256` header. The server computes the HMAC SHA-256 digest of the raw request payload using `GITHUB_WEBHOOK_SECRET` and performs a constant-time comparison via `hmac.compare_digest`. Unsigned or invalid requests are rejected with HTTP 401 Unauthorized.
