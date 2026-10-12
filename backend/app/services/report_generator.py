import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.app.config import settings
from backend.app.models.ai_review import AiReviewSummary
from backend.app.models.dast import DastScanResult
from backend.app.models.finding import Finding
from backend.app.models.governance import SourceCodeAiRisk
from backend.app.models.report import UnifiedSecurityReport
from backend.app.models.scan import Scan

logger = logging.getLogger("codereview.report")


class ReportGenerator:
    @classmethod
    def generate_json_report(
        cls,
        scan: Scan,
        findings: List[Finding],
        dast_results: Optional[DastScanResult] = None,
        ai_review: Optional[AiReviewSummary] = None,
        gov_risks: Optional[List[SourceCodeAiRisk]] = None
    ) -> Dict[str, Any]:
        """Generates unified security report data dictionary."""
        report = UnifiedSecurityReport(
            report_id=f"rep-{scan.id}",
            scan_id=scan.id,
            project_name=scan.project_name,
            scan_metadata=scan,
            summary=scan.summary,
            findings=findings,
            dast_results=dast_results,
            ai_review=ai_review,
            governance_risks=gov_risks or [],
            compliance_matrix={
                "OWASP Top 10 2021": f"{sum(1 for f in findings if 'A0' in str(f.cwe_ids))} Issues Flagged",
                "CWE Top 25": f"{sum(1 for f in findings if any(cwe in ['CWE-89', 'CWE-78', 'CWE-79', 'CWE-502', 'CWE-22', 'CWE-798'] for cwe in f.cwe_ids))} Critical CWEs",
                "LLM Guardrails / OWASP LLM Top 10": f"{len(gov_risks or [])} AI Security Findings",
                "DAST Dynamic Vulnerabilities": f"{len(dast_results.alerts) if dast_results else 0} Dynamic Alerts"
            },
            executive_summary=(
                f"Security assessment conducted for project '{scan.project_name}' on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}. "
                f"A total of {len(findings)} security findings were identified ({scan.summary.critical} Critical, "
                f"{scan.summary.high} High, {scan.summary.medium} Medium, {scan.summary.low} Low). "
                f"Primary codebase composition includes {', '.join([l.language for l in scan.languages[:3]]) or 'Multi-language'}. "
                f"Overall security risk score: {scan.summary.risk_score:.1f}/100."
            ),
            scanner_coverage_notes=[
                "SAST static scanning completed across all detected source files.",
                "Secret scanning performed across all commits and files using Gitleaks rules.",
                "Dependency manifest audit performed against OSV database.",
                "LLM Governance analyzed prompt safety and source code AI integrations.",
                "DAST dynamic analysis executed in controlled test mode." if dast_results and dast_results.is_authorized else "DAST dynamic analysis marked as not executed / blocked for unauthorized target."
            ]
        )
        return report.model_dump()

    @classmethod
    def generate_pdf_report(
        cls,
        scan: Scan,
        findings: List[Finding],
        dast_results: Optional[DastScanResult] = None,
        ai_review: Optional[AiReviewSummary] = None,
        gov_risks: Optional[List[SourceCodeAiRisk]] = None,
        output_path: Optional[Path] = None
    ) -> Path:
        """Generates a professional executive PDF report using ReportLab."""
        pdf_filename = f"security_report_{scan.id}.pdf"
        pdf_path = output_path or (settings.REPORTS_DIR / pdf_filename)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(pdf_path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()
        
        # Custom Light Professional Styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1E3A8A")
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4B5563")
        )
        h2_style = ParagraphStyle(
            'SectionH2',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1E3A8A"),
            spaceBefore=14,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            'ReportBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1F2937")
        )
        code_style = ParagraphStyle(
            'ReportCode',
            parent=styles['Normal'],
            fontName='Courier',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#111827")
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph("AI Code Review & Security Quality Assurance System", title_style))
        story.append(Paragraph(f"Executive Security Audit Report &bull; Project: <b>{scan.project_name}</b> &bull; Scan ID: <code>{scan.id}</code>", subtitle_style))
        story.append(Paragraph(f"Generated on: {datetime.now(timezone.utc).strftime('%B %d, %Y - %H:%M:%S UTC')}", subtitle_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=14))

        # 2. Executive Summary Box
        story.append(Paragraph("Executive Summary", h2_style))
        summary_text = (
            f"An end-to-end security assessment was performed for <b>{scan.project_name}</b>. "
            f"The assessment evaluated static code security (SAST), secret exposures, dependency vulnerabilities, "
            f"dynamic application security (DAST), and LLM Governance risks. "
            f"A total of <b>{len(findings)}</b> findings were identified. "
            f"Overall Security Risk Score: <b>{scan.summary.risk_score:.1f}/100</b>."
        )
        story.append(Paragraph(summary_text, body_style))
        story.append(Spacer(1, 10))

        # 3. KPI Metrics Table
        kpi_data = [
            ["Total Findings", "Critical Severity", "High Severity", "Medium Severity", "Low / Info"],
            [
                str(len(findings)),
                str(scan.summary.critical),
                str(scan.summary.high),
                str(scan.summary.medium),
                str(scan.summary.low + scan.summary.info)
            ]
        ]
        kpi_table = Table(kpi_data, colWidths=[1.4*inch, 1.4*inch, 1.4*inch, 1.4*inch, 1.4*inch])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#374151")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor("#DC2626")),  # Critical red
            ('TEXTCOLOR', (2, 1), (2, 1), colors.HexColor("#EA580C")),  # High orange
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 12),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 14))

        # 4. Detected Languages Breakdown
        if scan.languages:
            story.append(Paragraph("Codebase Technology Stack", h2_style))
            lang_data = [["Language", "Files Count", "Lines of Code (SLOC)", "Percentage"]]
            for l in scan.languages:
                lang_data.append([l.language, str(l.files_count), f"{l.lines_of_code:,}", f"{l.percentage}%"])
            
            lang_table = Table(lang_data, colWidths=[2.2*inch, 1.5*inch, 1.8*inch, 1.5*inch])
            lang_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1E40AF")),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8.5),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ]))
            story.append(lang_table)
            story.append(Spacer(1, 14))

        # 5. Top Vulnerabilities Table
        story.append(Paragraph("Key Security Findings & Vulnerabilities", h2_style))
        if findings:
            find_data = [["Severity", "Vulnerability Title", "Scanner", "Location", "CWE"]]
            for f in findings[:20]:  # Up to top 20
                loc = f"{f.file_path or 'N/A'}:{f.line_number}" if f.line_number else (f.file_path or 'N/A')
                cwe_str = ", ".join(f.cwe_ids[:2]) if f.cwe_ids else "N/A"
                find_data.append([
                    f.severity,
                    Paragraph(f"<b>{f.title[:50]}</b>", body_style),
                    f.scanner.split()[0],
                    Paragraph(f"<code>{loc[:35]}</code>", code_style),
                    cwe_str
                ])

            find_table = Table(find_data, colWidths=[1.0*inch, 2.5*inch, 1.1*inch, 1.6*inch, 0.8*inch])
            find_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ('ALIGN', (4, 0), (4, -1), 'CENTER'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ]))
            story.append(find_table)
        else:
            story.append(Paragraph("No vulnerabilities identified during this scan.", body_style))

        story.append(Spacer(1, 14))

        # 6. DAST Dynamic Analysis Section
        if dast_results and dast_results.is_authorized:
            story.append(Paragraph("DAST Dynamic Security Analysis", h2_style))
            dast_summary = (
                f"Target URL: <code>{dast_results.target_url}</code> &bull; Status: <b>{dast_results.status}</b> &bull; "
                f"Endpoints Spidered: <b>{dast_results.spider_endpoints_found}</b> &bull; Total DAST Alerts: <b>{dast_results.total_alerts}</b>"
            )
            story.append(Paragraph(dast_summary, body_style))
            story.append(Spacer(1, 6))

        # 7. AI Code Review Recommendations Section
        if ai_review and ai_review.recommendations:
            story.append(Paragraph("AI-Assisted Remediation & Code Recommendations", h2_style))
            story.append(Paragraph(f"Overall Code Quality Grade: <b>{ai_review.overall_code_quality_grade}</b> &bull; Total AI Recommendations: <b>{ai_review.total_recommendations}</b>", body_style))
            story.append(Spacer(1, 6))
            
            for rec in ai_review.recommendations[:5]:
                rec_block = [
                    Paragraph(f"<b>Issue:</b> {rec.title} ({rec.file_path}:{rec.line_number})", body_style),
                    Paragraph(f"<b>Explanation:</b> {rec.explanation_simple}", body_style),
                ]
                if rec.patch:
                    rec_block.append(Paragraph(f"<b>Suggested Patch:</b><br/><code>{rec.patch.suggested_code.replace(chr(10), '<br/>')}</code>", code_style))
                rec_block.append(Spacer(1, 6))
                story.append(KeepTogether(rec_block))

        # Build document
        doc.build(story)
        logger.info(f"Generated PDF report at {pdf_path}")
        return pdf_path
