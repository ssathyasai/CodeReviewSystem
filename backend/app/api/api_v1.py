import asyncio
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse

from backend.app.config import settings
from backend.app.db.mongo import db
from backend.app.models.ai_review import ReviewActionEnum
from backend.app.models.finding import Finding, FindingStatusEnum
from backend.app.models.governance import (
    GovernanceEvaluationRequest,
    GovernanceEvaluationResult,
    PolicyRule,
)
from backend.app.models.scan import (
    GitHubScanRequest,
    InputTypeEnum,
    ModuleProgress,
    ModuleStatusEnum,
    Scan,
    ScanModulesConfig,
    ScanStatusEnum,
    ScanSummary,
)
from backend.app.services.archive_service import ArchiveSecurityError, ArchiveService
from backend.app.services.dast_engine import DastEngine
from backend.app.services.github_service import GitHubSecurityError, GitHubService
from backend.app.services.governance_engine import GovernanceEngine
from backend.app.services.orchestrator import ScanOrchestrator
from backend.app.services.remediation_service import RemediationService
from backend.app.services.report_generator import ReportGenerator

router = APIRouter()


# -----------------------------------------------------------------------------
# 1. Health & Dashboard Metrics
# -----------------------------------------------------------------------------
@router.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "HEALTHY",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database_connected": db.is_connected,
        "database_mode": "MongoDB" if not db.use_fallback else "LocalDocumentStore",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/metrics", tags=["Dashboard"])
async def get_dashboard_metrics():
    """Returns aggregated security metrics across all scans for the dashboard."""
    all_scans = list(db.scans.find().sort("created_at", -1))
    all_findings = list(db.findings.find())

    total_scans = len(all_scans)
    completed_scans = sum(1 for s in all_scans if s.get("status") == "COMPLETED")
    running_scans = sum(1 for s in all_scans if s.get("status") in ["RUNNING", "QUEUED"])

    crit_cnt = sum(1 for f in all_findings if f.get("severity") == "CRITICAL")
    high_cnt = sum(1 for f in all_findings if f.get("severity") == "HIGH")
    med_cnt = sum(1 for f in all_findings if f.get("severity") == "MEDIUM")
    low_cnt = sum(1 for f in all_findings if f.get("severity") == "LOW")
    info_cnt = sum(1 for f in all_findings if f.get("severity") == "INFO")

    # Severity distribution
    severity_distribution = [
        {"name": "Critical", "value": crit_cnt, "color": "#EF4444"},
        {"name": "High", "value": high_cnt, "color": "#F97316"},
        {"name": "Medium", "value": med_cnt, "color": "#EAB308"},
        {"name": "Low", "value": low_cnt, "color": "#3B82F6"},
        {"name": "Info", "value": info_cnt, "color": "#94A3B8"}
    ]

    # Findings by language
    lang_counts: Dict[str, int] = {}
    for s in all_scans:
        for l in s.get("languages", []):
            lang_name = l.get("language", "Unknown")
            lang_counts[lang_name] = lang_counts.get(lang_name, 0) + l.get("files_count", 0)

    findings_by_lang = [{"language": k, "files": v} for k, v in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:6]]

    # Vulnerability trends over recent scans
    recent_trends = []
    for s in reversed(all_scans[:7]):
        summary = s.get("summary", {})
        recent_trends.append({
            "scan_id": s.get("id", "")[:8],
            "project": s.get("project_name", "Project")[:12],
            "critical": summary.get("critical", 0),
            "high": summary.get("high", 0),
            "medium": summary.get("medium", 0),
            "total": summary.get("total_findings", 0)
        })

    return {
        "total_scans": total_scans,
        "completed_scans": completed_scans,
        "running_scans": running_scans,
        "total_vulnerabilities": len(all_findings),
        "critical_count": crit_cnt,
        "high_count": high_cnt,
        "medium_count": med_cnt,
        "low_count": low_cnt,
        "projects_analyzed": len({s.get("project_name") for s in all_scans}),
        "severity_distribution": severity_distribution,
        "findings_by_language": findings_by_lang,
        "vulnerability_trends": recent_trends,
        "recent_scans": all_scans[:5]
    }


# -----------------------------------------------------------------------------
# 2. Project Submissions & Scans
# -----------------------------------------------------------------------------
@router.post("/scans/upload", tags=["Scans"])
async def upload_and_scan_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_name: Optional[str] = Form(None),
    dast_target_url: Optional[str] = Form(None),
    enable_sast: bool = Form(True),
    enable_secrets: bool = Form(True),
    enable_dependencies: bool = Form(True),
    enable_dast: bool = Form(False),
    enable_governance: bool = Form(True),
    enable_ai_review: bool = Form(True)
):
    """Accepts project ZIP archive, performs security validation, and triggers background scan pipeline."""
    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP archive files (.zip) are accepted.")

    scan_id = f"scan-{uuid.uuid4().hex[:8]}"
    proj_title = project_name or file.filename.removesuffix(".zip").removesuffix(".ZIP")
    
    # Save uploaded file
    zip_dest = settings.UPLOADS_DIR / f"{scan_id}_{file.filename}"
    try:
        with open(zip_dest, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # Extract safely
    workspace_path = settings.WORKSPACES_DIR / scan_id
    try:
        success, msg, meta = ArchiveService.validate_and_extract_zip(zip_dest, workspace_path)
    except ArchiveSecurityError as e:
        if zip_dest.exists():
            zip_dest.unlink()
        raise HTTPException(status_code=400, detail=f"Archive validation failed: {str(e)}")

    # Create scan record in database
    config = ScanModulesConfig(
        sast=enable_sast,
        secret_scanning=enable_secrets,
        dependency_scanning=enable_dependencies,
        dast=enable_dast,
        llm_governance=enable_governance,
        ai_code_review=enable_ai_review,
        dast_target_url=dast_target_url
    )

    scan = Scan(
        id=scan_id,
        project_name=proj_title,
        input_type=InputTypeEnum.ZIP,
        source_identifier=file.filename,
        workspace_path=str(workspace_path),
        config=config,
        status=ScanStatusEnum.QUEUED,
        current_stage="Queued for analysis..."
    )

    db.scans.insert_one(scan.model_dump())

    # Trigger background pipeline
    background_tasks.add_task(ScanOrchestrator.run_analysis_pipeline, scan_id, workspace_path)

    return {
        "status": "SUCCESS",
        "message": "Project ZIP accepted and scan initiated successfully.",
        "scan_id": scan_id,
        "project_name": proj_title,
        "metadata": meta
    }


@router.post("/scans/github", tags=["Scans"])
async def scan_github_repository(
    request: GitHubScanRequest,
    background_tasks: BackgroundTasks
):
    """Clones GitHub repository using shallow clone, validates URL safety, and starts scan pipeline."""
    valid, err_or_url = GitHubService.validate_repo_url(request.repo_url)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Invalid GitHub repository URL: {err_or_url}")

    scan_id = f"scan-{uuid.uuid4().hex[:8]}"
    repo_name = request.repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    workspace_path = settings.WORKSPACES_DIR / scan_id

    # Create scan record in database
    config = ScanModulesConfig(
        sast=request.enable_sast,
        secret_scanning=request.enable_secrets,
        dependency_scanning=request.enable_dependencies,
        dast=request.enable_dast,
        llm_governance=request.enable_governance,
        ai_code_review=request.enable_ai_review,
        dast_target_url=request.dast_target_url
    )

    scan = Scan(
        id=scan_id,
        project_name=repo_name,
        input_type=InputTypeEnum.GITHUB,
        source_identifier=request.repo_url,
        branch_or_commit=request.branch or request.commit or "default",
        workspace_path=str(workspace_path),
        config=config,
        status=ScanStatusEnum.QUEUED,
        current_stage="Cloning GitHub repository..."
    )

    db.scans.insert_one(scan.model_dump())

    async def _async_clone_and_start():
        try:
            clone_info = GitHubService.clone_repository(
                repo_url=request.repo_url,
                target_dir=workspace_path,
                branch=request.branch,
                commit=request.commit,
                auth_token=request.auth_token
            )
            db.scans.update_one({"id": scan_id}, {"$set": {"commit_hash": clone_info.get("commit_sha")}})
            await ScanOrchestrator.run_analysis_pipeline(scan_id, workspace_path)
        except GitHubSecurityError as e:
            db.scans.update_one({"id": scan_id}, {"$set": {
                "status": ScanStatusEnum.FAILED.value,
                "current_stage": f"GitHub checkout failed: {str(e)}",
                "error_message": str(e)
            }})
        except Exception as e:
            db.scans.update_one({"id": scan_id}, {"$set": {
                "status": ScanStatusEnum.FAILED.value,
                "current_stage": f"Scan failed: {str(e)}",
                "error_message": str(e)
            }})

    background_tasks.add_task(_async_clone_and_start)

    return {
        "status": "SUCCESS",
        "message": "GitHub repository scan job queued.",
        "scan_id": scan_id,
        "repo_url": request.repo_url,
        "project_name": repo_name
    }


@router.get("/scans", tags=["Scans"])
async def list_scans(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """Lists recent scans with status and findings summary."""
    query = {}
    if status:
        query["status"] = status.upper()

    cursor = db.scans.find(query).sort("created_at", -1).skip(skip).limit(limit)
    scans = list(cursor)
    return {"total": db.scans.count_documents(query), "scans": scans}


@router.get("/scans/{scan_id}", tags=["Scans"])
async def get_scan_details(scan_id: str):
    """Retrieves full status, progress percentage, stage, and module state of a scan."""
    scan = db.scans.find_one({"id": scan_id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return scan


@router.post("/scans/{scan_id}/cancel", tags=["Scans"])
async def cancel_scan(scan_id: str):
    """Cancels a currently queued or running scan."""
    scan = db.scans.find_one({"id": scan_id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    ScanOrchestrator.cancel_scan(scan_id)
    return {"status": "SUCCESS", "message": f"Scan {scan_id} cancellation requested."}


@router.get("/scans/{scan_id}/directory", tags=["Scans"])
async def get_scan_directory(scan_id: str):
    """
    Returns the workspace directory structure, file hierarchy, file metadata,
    and associated finding counts for the uploaded or cloned project.
    """
    scan = db.scans.find_one({"id": scan_id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")

    workspace_str = scan.get("workspace_path")
    workspace_path = Path(workspace_str) if workspace_str else None

    # Fetch findings to annotate files with issue counts
    findings = list(db.findings.find({"scan_id": scan_id}))
    file_findings_map: Dict[str, Dict[str, Any]] = {}
    for f in findings:
        fpath = (f.get("file_path") or "").replace("\\", "/").lstrip("/")
        if fpath:
            if fpath not in file_findings_map:
                file_findings_map[fpath] = {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0}
            file_findings_map[fpath]["total"] += 1
            sev = (f.get("severity") or "LOW").lower()
            if sev in file_findings_map[fpath]:
                file_findings_map[fpath][sev] += 1

    files_list = []
    tree = {
        "name": scan.get("project_name") or "root",
        "path": "",
        "type": "directory",
        "children": [],
        "findings_count": len(findings)
    }

    def insert_into_tree(root_node: Dict[str, Any], rel_parts: List[str], file_info: Dict[str, Any]):
        curr = root_node
        curr_path = ""
        for part in rel_parts[:-1]:
            curr_path = f"{curr_path}/{part}" if curr_path else part
            found = next((c for c in curr["children"] if c["name"] == part and c["type"] == "directory"), None)
            if not found:
                found = {
                    "name": part,
                    "path": curr_path,
                    "type": "directory",
                    "children": [],
                    "findings_count": 0
                }
                curr["children"].append(found)
            found["findings_count"] += file_info.get("findings_count", 0)
            curr = found

        curr["children"].append({
            "name": rel_parts[-1],
            "path": file_info["path"],
            "type": "file",
            "size": file_info.get("size", 0),
            "lines": file_info.get("lines", 0),
            "extension": file_info.get("extension", ""),
            "findings_count": file_info.get("findings_count", 0),
            "severity_breakdown": file_info.get("severity_breakdown", {})
        })

    # 1. Walk workspace if on disk
    if workspace_path and workspace_path.exists():
        excluded_dirs = {".git", ".svn", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            for file_name in files:
                full_path = Path(root) / file_name
                try:
                    rel_p = str(full_path.relative_to(workspace_path)).replace("\\", "/")
                    size_b = full_path.stat().st_size
                    ext = full_path.suffix.lower()

                    lines_cnt = 0
                    if size_b < 500000:
                        try:
                            with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                                lines_cnt = sum(1 for _ in fp)
                        except Exception:
                            pass

                    f_findings = file_findings_map.get(rel_p, {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0})
                    file_info = {
                        "path": rel_p,
                        "name": file_name,
                        "size": size_b,
                        "lines": lines_cnt,
                        "extension": ext,
                        "findings_count": f_findings["total"],
                        "severity_breakdown": f_findings
                    }
                    files_list.append(file_info)
                    insert_into_tree(tree, rel_p.split("/"), file_info)
                except Exception:
                    pass

    # 2. If workspace empty or demo data, populate from findings
    if not files_list and file_findings_map:
        for fpath, fstats in file_findings_map.items():
            parts = fpath.split("/")
            ext = "." + parts[-1].split(".")[-1] if "." in parts[-1] else ""
            file_info = {
                "path": fpath,
                "name": parts[-1],
                "size": 1500,
                "lines": 45,
                "extension": ext,
                "findings_count": fstats["total"],
                "severity_breakdown": fstats
            }
            files_list.append(file_info)
            insert_into_tree(tree, parts, file_info)

    def sort_tree(node: Dict[str, Any]):
        if "children" in node:
            node["children"].sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))
            for child in node["children"]:
                if child["type"] == "directory":
                    sort_tree(child)

    sort_tree(tree)

    total_dirs = max(1, len(set("/".join(f["path"].split("/")[:-1]) for f in files_list if "/" in f["path"])))
    total_size = sum(f.get("size", 0) for f in files_list)

    return {
        "status": "SUCCESS",
        "scan_id": scan_id,
        "project_name": scan.get("project_name"),
        "input_type": scan.get("input_type"),
        "source_identifier": scan.get("source_identifier"),
        "workspace_path": str(workspace_path) if workspace_path else "",
        "total_files": len(files_list),
        "total_directories": max(1, total_dirs),
        "total_size_bytes": total_size,
        "tree": tree,
        "files": files_list
    }


@router.get("/scans/{scan_id}/files/content", tags=["Scans"])
async def get_scan_file_content(scan_id: str, file_path: str = Query(...)):
    """Retrieves safe file content from the scan workspace for preview."""
    scan = db.scans.find_one({"id": scan_id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")

    workspace_str = scan.get("workspace_path")
    if not workspace_str:
        raise HTTPException(status_code=404, detail="Workspace not available.")

    workspace_path = Path(workspace_str).resolve()
    target_file = (workspace_path / file_path.lstrip("/\\")).resolve()

    try:
        target_file.relative_to(workspace_path)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path traversal detected.")

    if not target_file.exists() or not target_file.is_file():
        raise HTTPException(status_code=404, detail=f"File '{file_path}' not found in workspace.")

    if target_file.stat().st_size > 200000:
        return {"file_path": file_path, "truncated": True, "content": "File is too large for inline preview."}

    try:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        return {"file_path": file_path, "content": content, "lines": len(content.splitlines())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


# -----------------------------------------------------------------------------
# 3. Findings Management
# -----------------------------------------------------------------------------
@router.get("/scans/{scan_id}/findings", tags=["Findings"])
async def get_scan_findings(
    scan_id: str,
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    scanner: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """Returns normalized security findings for a scan with full filtering support."""
    query: Dict[str, Any] = {"scan_id": scan_id}
    
    if severity:
        query["severity"] = severity.upper()
    if category:
        query["category"] = category
    if scanner:
        query["scanner"] = {"$regex": scanner, "$options": "i"}
    if status:
        query["status"] = status.upper()
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
            {"file_path": {"$regex": search, "$options": "i"}},
            {"rule_id": {"$regex": search, "$options": "i"}}
        ]

    findings = list(db.findings.find(query).sort("severity", 1))
    return {
        "scan_id": scan_id,
        "total": len(findings),
        "findings": findings
    }


@router.get("/findings", tags=["Findings"])
async def get_all_findings(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    """Global findings query across all scanned projects."""
    query: Dict[str, Any] = {}
    if severity:
        query["severity"] = severity.upper()
    if status:
        query["status"] = status.upper()
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"file_path": {"$regex": search, "$options": "i"}}
        ]
    findings = list(db.findings.find(query).sort("created_at", -1).limit(limit))
    return {"total": len(findings), "findings": findings}


@router.post("/scans/{scan_id}/findings/{finding_id}/status", tags=["Findings"])
async def update_finding_status(
    scan_id: str,
    finding_id: str,
    new_status: FindingStatusEnum = Form(...),
    notes: Optional[str] = Form(None)
):
    """Updates status of a finding (e.g. FALSE_POSITIVE, CONFIRMED, RESOLVED)."""
    update_data: Dict[str, Any] = {
        "status": new_status.value,
        "is_false_positive": (new_status == FindingStatusEnum.FALSE_POSITIVE),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if notes:
        update_data["review_notes"] = notes

    res = db.findings.update_one({"id": finding_id, "scan_id": scan_id}, {"$set": update_data})
    if res.modified_count == 0:
        raise HTTPException(status_code=404, detail="Finding not found.")
    return {"status": "SUCCESS", "message": f"Finding status updated to {new_status.value}"}


# -----------------------------------------------------------------------------
# 4. AI Code Review & Remediation
# -----------------------------------------------------------------------------
@router.get("/scans/{scan_id}/reviews", tags=["AI Code Review"])
async def get_ai_reviews(scan_id: str):
    """Retrieves AI-generated code review recommendations and patch diffs."""
    review_doc = db.ai_reviews.find_one({"scan_id": scan_id})
    if not review_doc:
        raise HTTPException(status_code=404, detail="AI review not found for this scan.")
    return review_doc


@router.post("/scans/{scan_id}/reviews/{recommendation_id}/action", tags=["AI Code Review"])
async def apply_review_action(
    scan_id: str,
    recommendation_id: str,
    action: ReviewActionEnum = Form(...),
    comment: Optional[str] = Form(None)
):
    """Allows developer to approve, reject, or mark verified for an AI suggested patch."""
    review_doc = db.ai_reviews.find_one({"scan_id": scan_id})
    if not review_doc:
        raise HTTPException(status_code=404, detail="AI review not found.")

    recs = review_doc.get("recommendations", [])
    updated = False
    for r in recs:
        if r.get("id") == recommendation_id:
            r["status"] = action.value
            r["reviewer_comment"] = comment
            if "patch" in r and r["patch"]:
                r["patch"]["status"] = action.value
            updated = True
            break

    if not updated:
        raise HTTPException(status_code=404, detail="Recommendation not found.")

    # Recompute summary counts
    app_cnt = sum(1 for r in recs if r.get("status") == ReviewActionEnum.APPROVE.value)
    rej_cnt = sum(1 for r in recs if r.get("status") == ReviewActionEnum.REJECT.value)
    pend_cnt = sum(1 for r in recs if r.get("status") == ReviewActionEnum.PENDING.value)

    db.ai_reviews.update_one(
        {"scan_id": scan_id},
        {"$set": {
            "recommendations": recs,
            "approved_count": app_cnt,
            "rejected_count": rej_cnt,
            "pending_count": pend_cnt
        }}
    )
    return {"status": "SUCCESS", "message": f"Review action '{action.value}' recorded."}


# -----------------------------------------------------------------------------
# 4.1 Automated Remediation & Production-Ready Code Export
# -----------------------------------------------------------------------------
@router.post("/scans/{scan_id}/remediate", tags=["Remediation"])
async def remediate_scan_code(scan_id: str):
    """
    Executes automated end-to-end remediations across the scanned codebase:
    - Patches SQL injections into parameterized queries
    - Eliminates hardcoded secrets into secure environment variables
    - Removes deserialization vulnerabilities (pickle -> json)
    - Fixes XSS sinks and missing input validations
    - Resolves mutable defaults and syntax/complexity bugs
    - Upgrades vulnerable dependencies
    - Packages 100% production-ready clean repository
    """
    res = RemediationService.apply_all_fixes(scan_id)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "Remediation failed"))
    return res


@router.get("/scans/{scan_id}/download-fixed", tags=["Remediation"])
async def download_production_ready_zip(scan_id: str):
    """Downloads the cleanly remediated, production-ready code archive."""
    scan = db.scans.find_one({"id": scan_id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")

    clean_zip = settings.REPORTS_DIR / f"{scan_id}_production_ready.zip"
    if not clean_zip.exists():
        workspace_str = scan.get("workspace_path")
        if not workspace_str:
            raise HTTPException(status_code=404, detail="Workspace directory unavailable.")
        workspace_path = Path(workspace_str)
        if not workspace_path.exists():
            raise HTTPException(status_code=404, detail="Workspace files not found on disk.")
        RemediationService.apply_all_fixes(scan_id)

    if not clean_zip.exists():
        raise HTTPException(status_code=500, detail="Failed to package production-ready archive.")

    proj_name = (scan.get("project_name") or "codebase").replace(" ", "_")
    return FileResponse(
        str(clean_zip),
        media_type="application/zip",
        filename=f"{proj_name}_production_ready.zip"
    )


# -----------------------------------------------------------------------------
# 5. DAST Dynamic Analysis
# -----------------------------------------------------------------------------
@router.post("/scans/{scan_id}/dast", tags=["DAST"])
async def trigger_dast_scan(
    scan_id: str,
    target_url: str = Form(...),
    background_tasks: BackgroundTasks = None
):
    """Configures and runs an authorized DAST scan against target URL."""
    valid, msg = DastEngine.validate_target_safety(target_url)
    if not valid:
        raise HTTPException(status_code=400, detail=f"DAST Target Rejected: {msg}")

    dast_res = await DastEngine.run_dast_scan(target_url, scan_id)
    dast_findings = DastEngine.convert_dast_alerts_to_findings(dast_res, scan_id)
    if dast_findings:
        db.findings.insert_many([f.dict() for f in dast_findings])

    return dast_res.dict()


@router.get("/scans/{scan_id}/dast", tags=["DAST"])
async def get_scan_dast_results(scan_id: str):
    """Retrieves DAST analysis results, alerts, and endpoint security tree."""
    scan = db.scans.find_one({"id": scan_id})
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")

    target = scan.get("config", {}).get("dast_target_url")
    if not target:
        return {"status": "NOT_RUN", "message": "No DAST target configured for this scan."}

    # Fetch DAST alerts from findings collection
    dast_findings = list(db.findings.find({"scan_id": scan_id, "scanner": "OWASP ZAP / DAST Engine"}))
    return {
        "target_url": target,
        "status": scan.get("module_dast", {}).get("status", "NOT_RUN"),
        "alerts_count": len(dast_findings),
        "findings": dast_findings
    }


# -----------------------------------------------------------------------------
# 6. LLM Governance
# -----------------------------------------------------------------------------
@router.post("/governance/evaluate", response_model=GovernanceEvaluationResult, tags=["LLM Governance"])
async def evaluate_governance(request: GovernanceEvaluationRequest):
    """Real-time policy evaluation endpoint: checks prompt injection, entity redaction, and policy enforcement."""
    result = GovernanceEngine.evaluate_text(request)
    return result


@router.get("/governance/policies", tags=["LLM Governance"])
async def list_governance_policies():
    """Returns configured LLM Governance guardrail policies."""
    policies = list(db.governance_policies.find())
    if not policies:
        # Return default initialized rules
        from backend.app.services.governance_engine import PROMPT_INJECTION_PATTERNS
        return [{"id": p["id"], "name": p["name"], "category": p["category"].value, "severity": p["severity"], "action": p["action"].value, "is_enabled": True} for p in PROMPT_INJECTION_PATTERNS]
    return policies


@router.get("/governance/events", tags=["LLM Governance"])
async def list_governance_audit_events(limit: int = Query(50, ge=1, le=200)):
    """Returns immutable governance audit logs and decision trail."""
    events = list(db.governance_events.find().sort("timestamp", -1).limit(limit))
    return {"total": len(events), "events": events}


# -----------------------------------------------------------------------------
# 7. Unified Reports (JSON & PDF)
# -----------------------------------------------------------------------------
@router.get("/scans/{scan_id}/report", tags=["Reports"])
async def get_scan_report(
    scan_id: str,
    format: str = Query("json", pattern="^(json|pdf)$")
):
    """Generates and downloads Unified Security Report in JSON or PDF format."""
    scan_doc = db.scans.find_one({"id": scan_id})
    if not scan_doc:
        raise HTTPException(status_code=404, detail="Scan not found.")

    findings = [Finding(**f) for f in db.findings.find({"scan_id": scan_id})]
    ai_rev_doc = db.ai_reviews.find_one({"scan_id": scan_id})
    ai_review = None
    if ai_rev_doc:
        try:
            from backend.app.models.ai_review import AiReviewSummary
            ai_review = AiReviewSummary(**ai_rev_doc)
        except Exception:
            pass

    scan_obj = Scan(**scan_doc)

    if format == "pdf":
        pdf_path = settings.REPORTS_DIR / f"security_report_{scan_id}.pdf"
        if not pdf_path.exists():
            pdf_path = ReportGenerator.generate_pdf_report(scan_obj, findings, None, ai_review, None)
        return FileResponse(
            str(pdf_path),
            media_type="application/pdf",
            filename=f"Security_Report_{scan_obj.project_name}_{scan_id}.pdf"
        )
    else:
        report_data = ReportGenerator.generate_json_report(scan_obj, findings, None, ai_review, None)
        return report_data


# -----------------------------------------------------------------------------
# 8. Demo Seed Data for Immediate Interactive Demonstration
# -----------------------------------------------------------------------------
@router.post("/demo/seed", tags=["System"])
async def seed_demo_data():
    """Seeds realistic sample projects, vulnerability findings, and scans for demonstration."""
    from backend.app.models.finding import FindingCategoryEnum, ScannerTypeEnum, SeverityEnum
    
    demo_scan_id = "scan-demo-banking-api"
    
    # Check if already exists
    if db.scans.find_one({"id": demo_scan_id}):
        return {"status": "SUCCESS", "message": "Demo data already loaded.", "scan_id": demo_scan_id}

    # Create demo scan
    demo_scan = {
        "id": demo_scan_id,
        "project_name": "FinTech-Payment-Gateway",
        "input_type": "GITHUB",
        "source_identifier": "https://github.com/fintech-corp/payment-gateway-service",
        "branch_or_commit": "main",
        "commit_hash": "a8f3b9c41d7e2f50a6b7c8d9e0f123456789abcd",
        "workspace_path": str(settings.WORKSPACES_DIR / demo_scan_id),
        "status": "COMPLETED",
        "progress_percentage": 100,
        "current_stage": "Analysis completed successfully.",
        "config": {
            "sast": True,
            "secret_scanning": True,
            "dependency_scanning": True,
            "dast": True,
            "llm_governance": True,
            "ai_code_review": True,
            "dast_target_url": "https://demo-banking.internal.app"
        },
        "module_sast": {"status": "COMPLETED", "message": "Analyzed 42 files across Python & TypeScript", "elapsed_seconds": 3.8},
        "module_secrets": {"status": "COMPLETED", "message": "Found 2 hardcoded secrets", "elapsed_seconds": 1.2},
        "module_dependencies": {"status": "COMPLETED", "message": "Found 3 vulnerable packages", "elapsed_seconds": 0.9},
        "module_dast": {"status": "COMPLETED", "message": "Spidered 8 endpoints, 3 dynamic alerts", "elapsed_seconds": 4.1},
        "module_governance": {"status": "COMPLETED", "message": "Found 2 prompt injection risks", "elapsed_seconds": 1.5},
        "module_ai_review": {"status": "COMPLETED", "message": "Generated 6 patch suggestions", "elapsed_seconds": 2.4},
        "languages": [
            {"language": "Python", "files_count": 28, "lines_of_code": 4350, "percentage": 64.2},
            {"language": "TypeScript", "files_count": 12, "lines_of_code": 1820, "percentage": 26.8},
            {"language": "JSON / Manifest", "files_count": 4, "lines_of_code": 320, "percentage": 4.7},
            {"language": "YAML Config", "files_count": 3, "lines_of_code": 290, "percentage": 4.3}
        ],
        "summary": {
            "total_findings": 8,
            "critical": 3,
            "high": 3,
            "medium": 2,
            "low": 0,
            "info": 0,
            "scanners_used": [
                "Bandit (Python SAST)",
                "Semgrep AST Rules",
                "Gitleaks Secret Scanner",
                "OSV Dependency Scanner",
                "LLM Governance Guardrails",
                "OWASP ZAP / DAST Engine"
            ],
            "languages_detected": ["Python", "TypeScript", "JSON / Manifest", "YAML Config"],
            "files_analyzed": 47,
            "total_lines_of_code": 6780,
            "risk_score": 92.5
        },
        "logs": [
            "[14:00:00] Scan pipeline initialized for FinTech-Payment-Gateway.",
            "[14:00:01] Cloned repository from GitHub (commit: a8f3b9c).",
            "[14:00:02] Language detection complete. Primary: Python (64.2%).",
            "[14:00:04] SAST & Secret Scanner identified 5 vulnerabilities.",
            "[14:00:05] LLM Governance identified prompt injection risk in chatbot handler.",
            "[14:00:07] DAST analysis spidered 8 endpoints.",
            "[14:00:09] AI Code Review generated 6 patch recommendations.",
            "[14:00:10] Unified PDF and JSON security report generated."
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    db.scans.insert_one(demo_scan)

    # Demo Findings
    demo_findings = [
        {
            "id": "find-demo-001",
            "scan_id": demo_scan_id,
            "title": "SQL Injection in User Transaction Query",
            "description": "Raw SQL query constructed using f-string parameter interpolation allows arbitrary SQL command execution and authentication bypass.",
            "severity": "CRITICAL",
            "category": "Injection (SQL/Command/LDAP)",
            "scanner": "Semgrep AST Rules",
            "rule_id": "PY-SQLI-FORMAT",
            "file_path": "services/payment_service.py",
            "line_number": 48,
            "code_snippet": "cursor.execute(f\"SELECT * FROM transactions WHERE account_id = '{account_id}' AND status = 'ACTIVE'\")",
            "cwe_ids": ["CWE-89"],
            "remediation_guidance": "Use parameterized queries with database placeholder tuples: cursor.execute('SELECT * FROM transactions WHERE account_id = %s', (account_id,))",
            "confidence": "HIGH",
            "status": "OPEN",
            "is_false_positive": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "find-demo-002",
            "scan_id": demo_scan_id,
            "title": "AWS Access Key ID Exposed in Config",
            "description": "Hardcoded production AWS Access Key ID found in cleartext repository configuration.",
            "severity": "CRITICAL",
            "category": "Sensitive Data & Secret Exposure",
            "scanner": "Gitleaks Secret Scanner",
            "rule_id": "GITLEAKS-AWS-KEY",
            "file_path": "config/aws_client.py",
            "line_number": 12,
            "code_snippet": "AWS_ACCESS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'",
            "cwe_ids": ["CWE-798", "CWE-312"],
            "remediation_guidance": "Revoke AWS IAM key immediately and inject credentials via AWS Secrets Manager or environment variables.",
            "confidence": "HIGH",
            "status": "OPEN",
            "is_false_positive": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "find-demo-003",
            "scan_id": demo_scan_id,
            "title": "Unchecked Execution of LLM-Generated Output",
            "description": "Executing AI model output directly with eval() creates a critical Remote Code Execution vulnerability.",
            "severity": "CRITICAL",
            "category": "LLM & AI Integration Security",
            "scanner": "LLM Governance Guardrails",
            "rule_id": "AI-UNSAFE-CODE-EXEC",
            "file_path": "ai/assistant_agent.py",
            "line_number": 89,
            "code_snippet": "result = eval(model_output['calculator_code'])",
            "cwe_ids": ["CWE-94", "CWE-20"],
            "remediation_guidance": "Do not evaluate raw code generated by LLM models. Parse output into structured AST tokens or run in a restricted sandbox.",
            "confidence": "HIGH",
            "status": "OPEN",
            "is_false_positive": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "find-demo-004",
            "scan_id": demo_scan_id,
            "title": "OS Command Injection in Network Utility",
            "description": "Passing unvalidated user hostname parameter to `os.system` allows arbitrary shell command execution.",
            "severity": "HIGH",
            "category": "Injection (SQL/Command/LDAP)",
            "scanner": "Bandit (Python SAST)",
            "rule_id": "BANDIT-B605",
            "file_path": "utils/diagnostics.py",
            "line_number": 34,
            "code_snippet": "os.system(f'ping -c 1 {host_ip}')",
            "cwe_ids": ["CWE-78"],
            "remediation_guidance": "Use subprocess.run(['ping', '-c', '1', host_ip], shell=False) with strict IP address validation.",
            "confidence": "HIGH",
            "status": "OPEN",
            "is_false_positive": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "find-demo-005",
            "scan_id": demo_scan_id,
            "title": "Vulnerable Dependency: PyYAML Insecure Deserialization",
            "description": "Package pyyaml==5.3.1 contains known Arbitrary Code Execution vulnerability (CVE-2020-14343).",
            "severity": "HIGH",
            "category": "Vulnerable Dependency",
            "scanner": "OSV Dependency Scanner",
            "rule_id": "CVE-2020-14343",
            "file_path": "requirements.txt",
            "line_number": 18,
            "code_snippet": "pyyaml==5.3.1",
            "cwe_ids": ["CWE-502", "CWE-1395"],
            "remediation_guidance": "Upgrade pyyaml to version >=6.0 in requirements.txt.",
            "confidence": "HIGH",
            "status": "OPEN",
            "is_false_positive": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "find-demo-006",
            "scan_id": demo_scan_id,
            "title": "DAST: Missing Content-Security-Policy (CSP)",
            "description": "Target server response headers do not include Content-Security-Policy, leaving client vulnerable to XSS.",
            "severity": "MEDIUM",
            "category": "Security Misconfiguration",
            "scanner": "OWASP ZAP / DAST Engine",
            "rule_id": "DAST-HDR-10038",
            "file_path": "https://demo-banking.internal.app",
            "line_number": None,
            "code_snippet": "HTTP/1.1 200 OK\nServer: nginx\nContent-Type: text/html",
            "cwe_ids": ["CWE-693"],
            "remediation_guidance": "Configure web server to return 'Content-Security-Policy: default-src \\'self\\'; script-src \\'self\\'' header.",
            "confidence": "HIGH",
            "status": "OPEN",
            "is_false_positive": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    db.findings.insert_many(demo_findings)

    # Demo AI Reviews
    demo_ai_review = {
        "scan_id": demo_scan_id,
        "total_recommendations": 3,
        "approved_count": 0,
        "rejected_count": 0,
        "pending_count": 3,
        "model_used": "Security-Specialized AI Engine",
        "overall_code_quality_grade": "C+",
        "key_strengths": [
            "Good separation of business logic in service classes.",
            "Explicit Pydantic data validation on incoming request schemas."
        ],
        "top_risks": [
            "SQL Injection in payment service query string.",
            "Unchecked eval() of LLM generated output in assistant agent."
        ],
        "recommendations": [
            {
                "id": "rev-demo-01",
                "scan_id": demo_scan_id,
                "file_path": "services/payment_service.py",
                "line_number": 48,
                "title": "Parameterized SQL Query Remediation",
                "linked_finding_id": "find-demo-001",
                "severity": "CRITICAL",
                "category": "Injection (SQL/Command/LDAP)",
                "explanation_simple": "Directly concatenating account_id into SQL string allows malicious SQL injection payloads.",
                "root_cause": "F-string SQL query construction without parameterized driver queries.",
                "patch": {
                    "id": "patch-demo-01",
                    "file_path": "services/payment_service.py",
                    "line_start": 48,
                    "line_end": 48,
                    "original_code": "cursor.execute(f\"SELECT * FROM transactions WHERE account_id = '{account_id}' AND status = 'ACTIVE'\")",
                    "suggested_code": "cursor.execute(\"SELECT * FROM transactions WHERE account_id = %s AND status = %s\", (account_id, 'ACTIVE'))",
                    "diff_unified": "- cursor.execute(f\"SELECT * FROM transactions WHERE account_id = '{account_id}' AND status = 'ACTIVE'\")\n+ cursor.execute(\"SELECT * FROM transactions WHERE account_id = %s AND status = %s\", (account_id, 'ACTIVE'))",
                    "explanation": "Replaces string formatting with safe DB-API parameter placeholders (%s).",
                    "safety_notes": "Tested against PostgreSQL and MySQL adapters.",
                    "status": "PENDING"
                },
                "maintainability_impact": "High: Prevents database compromise and standardizes SQL querying.",
                "confidence_score": 0.99,
                "status": "PENDING"
            },
            {
                "id": "rev-demo-02",
                "scan_id": demo_scan_id,
                "file_path": "config/aws_client.py",
                "line_number": 12,
                "title": "Environment Variable Secret Management",
                "linked_finding_id": "find-demo-002",
                "severity": "CRITICAL",
                "category": "Sensitive Data & Secret Exposure",
                "explanation_simple": "Cleartext AWS access key in source code exposes cloud infrastructure to credential theft.",
                "root_cause": "Hardcoded credential string in repository.",
                "patch": {
                    "id": "patch-demo-02",
                    "file_path": "config/aws_client.py",
                    "line_start": 12,
                    "line_end": 12,
                    "original_code": "AWS_ACCESS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'",
                    "suggested_code": "AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')\nif not AWS_ACCESS_KEY_ID:\n    raise ValueError('AWS_ACCESS_KEY_ID environment variable is missing.')",
                    "diff_unified": "- AWS_ACCESS_KEY_ID = 'AKIAIOSFODNN7EXAMPLE'\n+ AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')\n+ if not AWS_ACCESS_KEY_ID:\n+     raise ValueError('AWS_ACCESS_KEY_ID environment variable is missing.')",
                    "explanation": "Loads AWS credentials from secure environment variables.",
                    "safety_notes": "Add .env to .gitignore to avoid pushing secrets.",
                    "status": "PENDING"
                },
                "maintainability_impact": "High: Meets 12-factor application security requirements.",
                "confidence_score": 0.98,
                "status": "PENDING"
            }
        ]
    }
    db.ai_reviews.insert_one(demo_ai_review)

    return {"status": "SUCCESS", "message": "Demo data seeded successfully.", "scan_id": demo_scan_id}


# -----------------------------------------------------------------------------
# 12. Settings & AI Engine Configuration
# -----------------------------------------------------------------------------
class SystemSettingsUpdate(BaseModel):
    ai_provider: Optional[str] = None
    groq_api_key: Optional[str] = None
    groq_model: Optional[str] = None
    ollama_url: Optional[str] = None
    ollama_model: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    max_upload_size_mb: Optional[int] = None
    dast_allow_local_targets: Optional[bool] = None


@router.get("/settings", tags=["Settings"])
async def get_system_settings():
    return {
        "ai_provider": settings.AI_PROVIDER,
        "groq_configured": bool(settings.GROQ_API_KEY),
        "groq_model": settings.GROQ_MODEL,
        "ollama_url": settings.OLLAMA_URL,
        "ollama_model": settings.OLLAMA_MODEL,
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "openai_model": settings.OPENAI_MODEL,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "dast_allow_local_targets": settings.DAST_ALLOW_LOCAL_TARGETS,
    }


@router.post("/settings", tags=["Settings"])
async def update_system_settings(payload: SystemSettingsUpdate):
    if payload.ai_provider is not None:
        settings.AI_PROVIDER = payload.ai_provider.lower()
    if payload.groq_api_key is not None and payload.groq_api_key.strip():
        settings.GROQ_API_KEY = payload.groq_api_key.strip()
    if payload.groq_model is not None and payload.groq_model.strip():
        settings.GROQ_MODEL = payload.groq_model.strip()
    if payload.ollama_url is not None and payload.ollama_url.strip():
        settings.OLLAMA_URL = payload.ollama_url.strip()
    if payload.ollama_model is not None and payload.ollama_model.strip():
        settings.OLLAMA_MODEL = payload.ollama_model.strip()
    if payload.openai_api_key is not None and payload.openai_api_key.strip():
        settings.OPENAI_API_KEY = payload.openai_api_key.strip()
    if payload.gemini_api_key is not None and payload.gemini_api_key.strip():
        settings.GEMINI_API_KEY = payload.gemini_api_key.strip()
    if payload.max_upload_size_mb is not None:
        settings.MAX_UPLOAD_SIZE_MB = payload.max_upload_size_mb
    if payload.dast_allow_local_targets is not None:
        settings.DAST_ALLOW_LOCAL_TARGETS = payload.dast_allow_local_targets

    return {
        "status": "SUCCESS",
        "message": "Settings updated successfully.",
        "current_ai_provider": settings.AI_PROVIDER,
        "current_model": settings.GROQ_MODEL if settings.AI_PROVIDER == "groq" else (settings.OLLAMA_MODEL if settings.AI_PROVIDER == "ollama" else settings.AI_PROVIDER)
    }

