import asyncio
import logging
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.config import settings
from backend.app.db.mongo import db
from backend.app.models.finding import Finding, SeverityEnum
from backend.app.models.scan import (
    LanguageStats,
    ModuleProgress,
    ModuleStatusEnum,
    Scan,
    ScanStatusEnum,
    ScanSummary,
)
from backend.app.services.ai_review_engine import AiReviewEngine
from backend.app.services.dast_engine import DastEngine
from backend.app.services.governance_engine import GovernanceEngine
from backend.app.services.language_detector import LanguageDetector
from backend.app.services.report_generator import ReportGenerator
from backend.app.services.sast_engine import SastEngine

logger = logging.getLogger("codereview.orchestrator")


class ScanOrchestrator:
    _cancelled_scans = set()

    @classmethod
    def cancel_scan(cls, scan_id: str) -> bool:
        cls._cancelled_scans.add(scan_id)
        db.scans.update_one(
            {"id": scan_id},
            {"$set": {
                "status": ScanStatusEnum.CANCELLED.value,
                "current_stage": "Scan cancelled by user",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        return True

    @classmethod
    async def run_analysis_pipeline(cls, scan_id: str, workspace_path: Path):
        """
        Main end-to-end background orchestration pipeline.
        Executes all configured modules, tracks progress, and saves findings.
        """
        scan_doc = db.scans.find_one({"id": scan_id})
        if not scan_doc:
            logger.error(f"Scan {scan_id} not found in database.")
            return

        start_time = time.time()
        logger.info(f"Starting analysis pipeline for scan {scan_id} at {workspace_path}")

        try:
            # Update Status to RUNNING
            cls._update_scan(scan_id, {
                "status": ScanStatusEnum.RUNNING.value,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "progress_percentage": 5,
                "current_stage": "Detecting programming languages and project structure...",
                "logs": [f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Scan pipeline initialized."]
            })

            if scan_id in cls._cancelled_scans:
                return

            # -------------------------------------------------------------
            # STAGE 1: Multi-Language & Manifest Detection
            # -------------------------------------------------------------
            languages, lang_meta = LanguageDetector.analyze_workspace(workspace_path)
            cls._log(scan_id, f"Language detection complete. Primary: {lang_meta.get('primary_language', 'N/A')}, Files: {lang_meta.get('total_analyzed_files', 0)}, SLOC: {lang_meta.get('total_lines_of_code', 0)}")

            cls._update_scan(scan_id, {
                "languages": [l.dict() for l in languages],
                "progress_percentage": 15,
                "current_stage": "Executing SAST, Secret, and Dependency Analysis...",
            })

            all_findings: List[Finding] = []

            # -------------------------------------------------------------
            # STAGE 2: SAST, Secret Scanning & Dependency Audits
            # -------------------------------------------------------------
            sast_start = time.time()
            cls._update_module_status(scan_id, "module_sast", ModuleStatusEnum.RUNNING, "Running Static Code Analyzers...")
            cls._update_module_status(scan_id, "module_secrets", ModuleStatusEnum.RUNNING, "Scanning for credentials and secrets...")
            cls._update_module_status(scan_id, "module_dependencies", ModuleStatusEnum.RUNNING, "Auditing dependency manifests...")

            sast_findings = SastEngine.run_sast(workspace_path, scan_id)
            all_findings.extend(sast_findings)

            sast_elapsed = round(time.time() - sast_start, 2)
            cls._update_module_status(scan_id, "module_sast", ModuleStatusEnum.COMPLETED, f"Found {len([f for f in sast_findings if f.scanner != 'Gitleaks Secret Scanner'])} issues", sast_elapsed)
            cls._update_module_status(scan_id, "module_secrets", ModuleStatusEnum.COMPLETED, f"Found {len([f for f in sast_findings if f.scanner == 'Gitleaks Secret Scanner'])} secrets", sast_elapsed)
            cls._update_module_status(scan_id, "module_dependencies", ModuleStatusEnum.COMPLETED, f"Audited dependencies", sast_elapsed)

            cls._log(scan_id, f"SAST complete. Found {len(sast_findings)} total static findings in {sast_elapsed}s.")
            cls._update_scan(scan_id, {"progress_percentage": 45, "current_stage": "Running LLM Governance inspections..."})

            if scan_id in cls._cancelled_scans:
                return

            # -------------------------------------------------------------
            # STAGE 3: LLM Governance Source Code Inspection
            # -------------------------------------------------------------
            gov_start = time.time()
            cls._update_module_status(scan_id, "module_governance", ModuleStatusEnum.RUNNING, "Inspecting AI integrations and prompt security...")
            gov_risks, gov_findings = GovernanceEngine.inspect_source_code_ai_risks(workspace_path, scan_id)
            all_findings.extend(gov_findings)

            gov_elapsed = round(time.time() - gov_start, 2)
            cls._update_module_status(scan_id, "module_governance", ModuleStatusEnum.COMPLETED, f"Found {len(gov_risks)} AI risks", gov_elapsed)
            cls._log(scan_id, f"LLM Governance inspection complete in {gov_elapsed}s.")

            cls._update_scan(scan_id, {"progress_percentage": 65, "current_stage": "Generating AI Code Reviews and patches..."})

            if scan_id in cls._cancelled_scans:
                return

            # -------------------------------------------------------------
            # STAGE 4: AI Code Review & Remediation Suggestions
            # -------------------------------------------------------------
            ai_start = time.time()
            cls._update_module_status(scan_id, "module_ai_review", ModuleStatusEnum.RUNNING, "Generating code explanations & suggested patches...")
            ai_review = await AiReviewEngine.generate_code_reviews(workspace_path, all_findings, scan_id)
            
            # Save AI review to DB
            db.ai_reviews.insert_one(ai_review.dict())
            ai_elapsed = round(time.time() - ai_start, 2)
            cls._update_module_status(scan_id, "module_ai_review", ModuleStatusEnum.COMPLETED, f"Generated {ai_review.total_recommendations} patch suggestions", ai_elapsed)
            cls._log(scan_id, f"AI Code Review complete. Grade: {ai_review.overall_code_quality_grade}.")

            cls._update_scan(scan_id, {"progress_percentage": 80, "current_stage": "Evaluating DAST Dynamic Application Security..."})

            if scan_id in cls._cancelled_scans:
                return

            # -------------------------------------------------------------
            # STAGE 5: DAST Dynamic Analysis
            # -------------------------------------------------------------
            dast_target = scan_doc.get("config", {}).get("dast_target_url")
            enable_dast = scan_doc.get("config", {}).get("dast", False)
            dast_result = None

            if enable_dast and dast_target:
                cls._update_module_status(scan_id, "module_dast", ModuleStatusEnum.RUNNING, f"Probing {dast_target}...")
                cls._log(scan_id, f"Starting DAST dynamic scan on target {dast_target}")
                dast_result = await DastEngine.run_dast_scan(dast_target, scan_id)
                
                if dast_result.status == "COMPLETED":
                    dast_findings = DastEngine.convert_dast_alerts_to_findings(dast_result, scan_id)
                    all_findings.extend(dast_findings)
                    cls._update_module_status(scan_id, "module_dast", ModuleStatusEnum.COMPLETED, f"Spidered {dast_result.spider_endpoints_found} endpoints, {dast_result.total_alerts} alerts", dast_result.scan_duration_seconds)
                elif dast_result.status == "BLOCKED":
                    cls._update_module_status(scan_id, "module_dast", ModuleStatusEnum.BLOCKED, dast_result.reason or "Target blocked by security policy", dast_result.scan_duration_seconds)
                else:
                    cls._update_module_status(scan_id, "module_dast", ModuleStatusEnum.FAILED, dast_result.reason or "DAST probe failed", dast_result.scan_duration_seconds)
            else:
                cls._update_module_status(scan_id, "module_dast", ModuleStatusEnum.NOT_RUN, "No authorized DAST target URL specified.")

            cls._update_scan(scan_id, {"progress_percentage": 90, "current_stage": "Persisting findings and generating reports..."})

            # -------------------------------------------------------------
            # STAGE 6: Persist Findings and Calculate Metrics
            # -------------------------------------------------------------
            if all_findings:
                finding_dicts = [f.dict() for f in all_findings]
                db.findings.insert_many(finding_dicts)

            # Calculate Severity & Risk Metrics
            crit_cnt = sum(1 for f in all_findings if f.severity == SeverityEnum.CRITICAL.value)
            high_cnt = sum(1 for f in all_findings if f.severity == SeverityEnum.HIGH.value)
            med_cnt = sum(1 for f in all_findings if f.severity == SeverityEnum.MEDIUM.value)
            low_cnt = sum(1 for f in all_findings if f.severity == SeverityEnum.LOW.value)
            info_cnt = sum(1 for f in all_findings if f.severity == SeverityEnum.INFO.value)

            # Score formula: 0 (safe) to 100 (hazardous)
            risk_score = min(100.0, (crit_cnt * 25.0) + (high_cnt * 10.0) + (med_cnt * 4.0) + (low_cnt * 1.0))

            summary = ScanSummary(
                total_findings=len(all_findings),
                critical=crit_cnt,
                high=high_cnt,
                medium=med_cnt,
                low=low_cnt,
                info=info_cnt,
                scanners_used=list({f.scanner for f in all_findings}),
                languages_detected=[l.language for l in languages],
                files_analyzed=lang_meta.get("total_analyzed_files", 0),
                total_lines_of_code=lang_meta.get("total_lines_of_code", 0),
                risk_score=round(risk_score, 1)
            )

            # -------------------------------------------------------------
            # STAGE 7: Generate Unified Reports (JSON & PDF)
            # -------------------------------------------------------------
            current_scan_obj = Scan(**{**scan_doc, "summary": summary, "languages": languages, "status": ScanStatusEnum.COMPLETED.value})
            ReportGenerator.generate_pdf_report(current_scan_obj, all_findings, dast_result, ai_review, gov_risks)

            # Finalize Scan Record
            total_duration = round(time.time() - start_time, 2)
            cls._update_scan(scan_id, {
                "status": ScanStatusEnum.COMPLETED.value,
                "progress_percentage": 100,
                "current_stage": "Analysis completed successfully.",
                "summary": summary.model_dump(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            })
            cls._log(scan_id, f"Pipeline completed successfully in {total_duration}s. Total findings: {len(all_findings)}.")

        except Exception as e:
            logger.exception(f"Error executing scan pipeline for {scan_id}: {e}")
            cls._update_scan(scan_id, {
                "status": ScanStatusEnum.FAILED.value,
                "current_stage": "Scan failed due to an internal error.",
                "error_message": str(e),
                "completed_at": datetime.now(timezone.utc).isoformat()
            })
            cls._log(scan_id, f"Scan failed: {str(e)}")

    @classmethod
    def _update_scan(cls, scan_id: str, fields: Dict[str, Any]):
        db.scans.update_one({"id": scan_id}, {"$set": fields})

    @classmethod
    def _update_module_status(cls, scan_id: str, module_name: str, status: ModuleStatusEnum, message: str = "", elapsed: float = 0.0):
        db.scans.update_one(
            {"id": scan_id},
            {"$set": {
                f"{module_name}.status": status.value,
                f"{module_name}.message": message,
                f"{module_name}.elapsed_seconds": elapsed
            }}
        )

    @classmethod
    def _log(cls, scan_id: str, message: str):
        timestamp_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
        db.scans.update_one(
            {"id": scan_id},
            {"$push": {"logs": f"[{timestamp_str}] {message}"}}
        )
