import sys
import os

# Add backend directory to python path
backend_dir = os.path.dirname(__file__)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Body, Request, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import uuid
from datetime import datetime
import tempfile
import shutil
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

# Initialize FastAPI App
app = FastAPI(
    title="Hybrid Code Intelligence Agent",
    description="Enterprise Code Review, SAST, DAST, and LLM Governance Platform",
    version="2.0.0"
)

# CORS Configuration
cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
origins = [o.strip() for o in cors_origins_raw.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Import (MongoDB Atlas / Local PyMongo)
from db import (
    init_db,
    save_scan as db_save_scan,
    get_scans as db_get_scans,
    get_scan_by_id as db_get_scan_by_id,
    create_user,
    get_user_by_username,
    verify_password
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on app startup"""
    init_db()

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Engine Imports
from engines.sast_engine import run_semgrep_analysis
from engines.governance_engine_api import run_governance_check, run_governance_check_with_context
from engines.dast_engine import run_runtime_analysis
from github_integration import github_integration

# ==================== Core Endpoints ====================

@app.get("/api/health")
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Hybrid Code Intelligence Agent",
        "database": "MongoDB",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/llm/status")
async def llm_status():
    """Check LLM Groq configuration and health status"""
    from engines.governance_engine_api import init_groq_client, call_groq_api
    
    groq_key = os.getenv("GROQ_API_KEY")
    status = {
        "llm_provider": "groq",
        "groq_api_key_configured": bool(groq_key),
        "groq_client_initialized": False,
        "groq_working": False,
        "error": None
    }
    
    try:
        if init_groq_client():
            status["groq_client_initialized"] = True
            try:
                response_text = call_groq_api("Say 'test successful' in exactly 2 words only.")
                if response_text:
                    status["groq_working"] = True
                    status["test_response"] = response_text
                else:
                    status["error"] = "No response from Groq API"
            except Exception as e:
                status["error"] = f"Groq API call error: {str(e)}"
        else:
            status["error"] = "GROQ_API_KEY not configured in .env"
    except Exception as e:
        status["error"] = f"Groq initialization exception: {str(e)}"
    
    return status

# ==================== User Authentication Endpoints ====================

@app.post("/auth/register")
async def register_user(payload: dict = Body(...)):
    """Register a new user account"""
    username = payload.get("username")
    email = payload.get("email")
    password = payload.get("password")
    
    if not username or not email or not password:
        return JSONResponse(status_code=400, content={"error": "Username, email, and password are required"})
        
    result = create_user(username, email, password)
    if result.get("status") == "error":
        return JSONResponse(status_code=400, content={"error": result.get("message")})
        
    return {"status": "success", "user": result.get("user")}

@app.post("/auth/login")
async def login_user(payload: dict = Body(...)):
    """Authenticate user login"""
    username = payload.get("username", "").strip().lower()
    password = payload.get("password", "")
    
    user = get_user_by_username(username)
    if not user or not verify_password(password, user.get("password_hash", "")):
        return JSONResponse(status_code=401, content={"error": "Invalid username or password"})
        
    user_data = {
        "username": user["username"],
        "email": user["email"],
        "created_at": user.get("created_at")
    }
    return {"status": "success", "user": user_data, "token": f"user_token_{user['username']}"}

# ==================== Scan History Endpoints ====================

@app.get("/scans")
async def list_scans(limit: int = Query(50, ge=1, le=200), username: Optional[str] = None):
    """Get scan history records from MongoDB (filtered by user if specified)"""
    scans = db_get_scans(limit=limit, username=username)
    return {"scans": scans, "count": len(scans)}

@app.get("/scans/{scan_id}")
async def get_scan_details(scan_id: str):
    """Get detailed report for a specific scan ID"""
    scan = db_get_scan_by_id(scan_id)
    if scan:
        return scan
    return JSONResponse(status_code=404, content={"error": f"Scan ID '{scan_id}' not found"})

# ==================== Scanning & Analysis ====================

@app.post("/scan")
async def scan_code(file: UploadFile = File(...), username: Optional[str] = Form(None)):
    """Trigger parallel SAST, DAST, and LLM Governance analysis on uploaded file"""
    try:
        content = await file.read()
        file_content = content.decode("utf-8", errors="ignore")
        
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        scan_id = str(uuid.uuid4())
        results = {
            "scan_id": scan_id,
            "timestamp": datetime.now().isoformat(),
            "file": file.filename,
            "engines": {}
        }
        
        sast_task = asyncio.create_task(run_semgrep_analysis(temp_file_path))
        governance_task = asyncio.create_task(run_governance_check(temp_file_path))
        dast_task = asyncio.create_task(run_runtime_analysis(temp_file_path))
        
        sast_results, governance_results, dast_results = await asyncio.gather(
            sast_task, governance_task, dast_task
        )
        
        results["engines"]["sast"] = sast_results
        results["engines"]["governance"] = governance_results
        results["engines"]["dast"] = dast_results
        
        results["verdict"] = calculate_verdict(results)
        
        # Save scan to MongoDB scan history
        db_save_scan(results)
        
        # Broadcast live scan update via WebSockets
        await manager.broadcast({
            "type": "scan_complete",
            "data": results
        })
        
        shutil.rmtree(temp_dir, ignore_errors=True)
        return JSONResponse(content=results)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/deploy/scan")
async def deploy_scan(request: dict = Body(...)):
    """Scan entire project directory for production deployment safety"""
    project_name = request.get("project_name")
    project_path = request.get("project_path")
    
    if not project_path or not os.path.exists(project_path):
        return JSONResponse(status_code=404, content={"error": "Project path not found"})
    
    python_files = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'venv', '.venv', 'dist']]
        for f in files:
            if f.endswith('.py'):
                python_files.append(os.path.join(root, f))
    
    project_context = build_project_context(python_files)
    results = []
    critical_count = 0
    warning_count = 0
    clean_count = 0
    
    for file_path in python_files:
        file_context = get_file_context(file_path, project_context)
        file_result = await scan_file_with_context(file_path, file_context)
        
        has_critical = any(f.get('severity') == 'CRITICAL' for f in file_result.get('findings', []))
        has_warnings = any(f.get('severity') in ['HIGH', 'MEDIUM'] for f in file_result.get('findings', []))
        
        if has_critical:
            critical_count += 1
        elif has_warnings:
            warning_count += 1
        else:
            clean_count += 1
        
        results.append({
            "filename": os.path.basename(file_path),
            "path": file_path,
            "has_critical": has_critical,
            "has_warnings": has_warnings,
            "issues": len(file_result.get('findings', []))
        })
    
    can_deploy = (critical_count == 0)
    scan_id = str(uuid.uuid4())
    
    deploy_summary = {
        "scan_id": scan_id,
        "project_name": project_name,
        "timestamp": datetime.now().isoformat(),
        "can_deploy": can_deploy,
        "total_files": len(python_files),
        "clean_files": clean_count,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "files": results
    }
    
    db_save_scan(deploy_summary)
    return deploy_summary

# ==================== GitHub Integration ====================

@app.post("/github/scan-repo")
async def scan_github_repo(request: dict = Body(...)):
    """Clone and audit any GitHub repository URL directly"""
    repo_url = request.get("repo_url")
    branch = request.get("branch", "main")
    username = request.get("username")
    
    if not repo_url:
        return JSONResponse(status_code=400, content={"error": "Repository URL ('repo_url') is required"})
    
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    clone_path = await github_integration.clone_repository(repo_url, branch)
    if not clone_path and branch != "master":
        # Fallback to master branch if main branch cloning fails
        branch = "master"
        clone_path = await github_integration.clone_repository(repo_url, branch)
    
    if not clone_path:
        return JSONResponse(status_code=400, content={"error": f"Failed to clone repository from URL: {repo_url}"})
    
    try:
        results = await github_integration.analyze_repository(
            clone_path,
            changed_files=[],
            repo_name=repo_name,
            branch=branch
        )
        scan_id = str(uuid.uuid4())
        results["scan_id"] = scan_id
        results["timestamp"] = datetime.now().isoformat()
        if username:
            results["username"] = username.strip().lower()
        
        # Store in MongoDB scan history
        db_save_scan(results)
        return results
    finally:
        github_integration.cleanup_repository(clone_path)

@app.post("/github/webhook")
async def github_webhook(request: Request):
    """Secure GitHub Webhook Receiver with mandatory HMAC SHA-256 Signature Verification"""
    try:
        raw_body = await request.body()
        signature = request.headers.get("X-Hub-Signature-256", "")
        
        # Verify HMAC Signature
        if not github_integration.verify_signature(raw_body, signature):
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized: Invalid or missing X-Hub-Signature-256 header"}
            )
        
        payload = json.loads(raw_body.decode('utf-8'))
        event_type = payload.get('ref', '').startswith('refs/heads/')
        
        if not event_type:
            return JSONResponse(status_code=400, content={"error": "Only push events are supported"})
        
        results = await github_integration.handle_push_event(payload)
        
        # Save scan report
        scan_id = str(uuid.uuid4())
        results["scan_id"] = scan_id
        results["scan_type"] = "github_webhook"
        results["is_webhook"] = True
        results["timestamp"] = datetime.now().isoformat()
        db_save_scan(results)
        
        await manager.broadcast({
            "type": "github_analysis_complete",
            "data": results
        })
        
        return JSONResponse(content=results)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/github/simulate-push")
async def simulate_github_push(request: dict = Body(...)):
    """Simulate receiving a GitHub push webhook event for testing and previewing code review UI"""
    repo_name = request.get("repo_name", "ssathyasai/CodeReviewSystem")
    branch = request.get("branch", "main")
    pusher = request.get("pusher", "alex-developer")
    
    scan_id = str(uuid.uuid4())
    simulated_results = {
        "scan_id": scan_id,
        "scan_type": "github_webhook",
        "is_webhook": True,
        "timestamp": datetime.now().isoformat(),
        "repository": repo_name,
        "branch": branch,
        "files_analyzed": 2,
        "status": "warning",
        "can_deploy": False,
        "message": "Found 1 high severity issue. Security review required.",
        "metadata": {
            "repository": repo_name,
            "branch": branch,
            "pusher": pusher,
            "commit_count": 1,
            "changed_files": ["backend/payment_gateway.py", "backend/main.py"]
        },
        "summary": {
            "total_issues": 2,
            "critical_issues": 0,
            "high_issues": 1,
            "medium_issues": 1,
            "low_issues": 0
        },
        "files": [
            {
                "path": "backend/payment_gateway.py",
                "status": "analyzed",
                "findings_count": 2,
                "summary": {"critical": 0, "high": 1, "medium": 1, "low": 0},
                "engines": {
                    "sast": {
                        "status": "warning",
                        "findings": [
                            {
                                "line": 42,
                                "issue": "Hardcoded secret key or sensitive token detected in payment headers",
                                "severity": "HIGH",
                                "rule_id": "python.lang.security.hardcoded-token",
                                "recommendation": "Use environment variables `os.getenv('PAYMENT_API_KEY')` instead of hardcoded strings."
                            }
                        ]
                    },
                    "governance": {
                        "status": "warning",
                        "findings": [
                            {
                                "line": 58,
                                "issue": "OWASP A02: Cryptographic Failure - Weak MD5 algorithm used for signature check",
                                "severity": "MEDIUM",
                                "rule_id": "gov.owasp.a02",
                                "recommendation": "Upgrade hash algorithm to SHA-256 (e.g. hashlib.sha256)."
                            }
                        ]
                    },
                    "dast": {"status": "clean", "findings": []}
                }
            }
        ]
    }
    
    db_save_scan(simulated_results)
    
    await manager.broadcast({
        "type": "github_analysis_complete",
        "data": simulated_results
    })
    
    return JSONResponse(content=simulated_results)

@app.get("/github/status")
async def github_status():
    """Check GitHub Webhook Integration configuration"""
    has_secret = bool(os.getenv("GITHUB_WEBHOOK_SECRET"))
    git_available = False
    try:
        res = subprocess.run(['git', '--version'], capture_output=True, timeout=5)
        git_available = (res.returncode == 0)
    except Exception:
        pass
    
    return {
        "configured": True,
        "webhook_secret_set": has_secret,
        "git_available": git_available,
        "webhook_url": "/github/webhook"
    }

# ==================== WebSocket ====================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"status": "received", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ==================== Code Fix / Remediation ====================

@app.post("/add-suggestion-comment")
async def add_suggestion_comment(file: UploadFile = File(...), line: int = None, suggestion: str = None):
    """Add AI suggestion as comment above specified line"""
    if not line or not suggestion:
        return {"status": "error", "message": "Missing line number or suggestion"}
    
    try:
        content = await file.read()
        lines = content.decode("utf-8").split('\n')
        
        if 0 < line <= len(lines):
            target_line = lines[line - 1]
            indent = len(target_line) - len(target_line.lstrip())
            comment = ' ' * indent + f"# AI Suggestion: {suggestion}"
            lines.insert(line - 1, comment)
            
            return {
                "status": "success",
                "message": f"Suggestion added at line {line}",
                "updated_content": '\n'.join(lines)
            }
        return {"status": "error", "message": f"Line {line} out of range"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/apply-fix")
async def apply_fix(file: UploadFile = File(...), line: int = None, new_code: str = None):
    """Apply inline auto-remediation fix to uploaded code content"""
    try:
        content = await file.read()
        lines = content.decode("utf-8").split('\n')
        
        if line and new_code and 0 < line <= len(lines):
            original = lines[line - 1]
            indent = len(original) - len(original.lstrip())
            lines[line - 1] = ' ' * indent + new_code.strip()
            
            return {
                "status": "success",
                "message": f"Applied fix to line {line}",
                "updated_content": '\n'.join(lines)
            }
        return {"status": "error", "message": "Invalid line number or missing new code"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

# ==================== Helper Functions ====================

def calculate_verdict(results: dict) -> dict:
    critical_count = 0
    high_count = 0
    for engine_name, engine_data in results.get("engines", {}).items():
        if engine_data.get("status") == "error":
            critical_count += 1
        elif engine_data.get("status") == "warning":
            high_count += 1
    
    if critical_count > 0:
        return {"decision": "BLOCK", "severity": "CRITICAL", "reason": f"Found {critical_count} critical issues"}
    elif high_count > 0:
        return {"decision": "WARN", "severity": "HIGH", "reason": f"Found {high_count} warnings"}
    else:
        return {"decision": "APPROVE", "severity": "NONE", "reason": "All security checks passed"}

def build_project_context(python_files: List[str]) -> Dict:
    context = {}
    for file_path in python_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            imports = [line.strip() for line in content.split('\n') if line.strip().startswith(('import ', 'from '))]
            context[file_path] = {"imports": imports, "content": content}
        except Exception:
            pass
    return context

def get_file_context(file_path: str, project_context: Dict) -> str:
    file_info = project_context.get(file_path, {})
    imports = file_info.get("imports", [])
    return f"File: {os.path.basename(file_path)}\nImports: {', '.join(imports) if imports else 'None'}\n"

async def scan_file_with_context(file_path: str, context: str):
    try:
        return await run_governance_check_with_context(file_path, context)
    except Exception:
        return await run_governance_check(file_path)

# ==================== Static SPA Frontend Mounting ====================

frontend_dist_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(frontend_dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist_path, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_spa(full_path: str):
        """Serve React SPA static index.html for all non-API paths"""
        file_target = os.path.join(frontend_dist_path, full_path)
        if os.path.exists(file_target) and os.path.isfile(file_target):
            return FileResponse(file_target)
        index_html = os.path.join(frontend_dist_path, "index.html")
        if os.path.exists(index_html):
            return FileResponse(index_html)
        return JSONResponse(status_code=404, content={"error": "Static asset not found"})

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)