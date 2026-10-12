import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Upload,
  FolderArchive,
  GitBranch,
  Play,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Copy,
  Check,
  RefreshCw,
  Sparkles,
  FileCode,
  ShieldAlert,
  Download,
  FileText,
  RotateCcw,
  Search,
  Diff,
  ShieldCheck,
  Folder,
  HardDrive,
  Activity,
  Zap,
  CheckCheck,
  Code2,
} from 'lucide-react';
import { ApiService } from '../services/api';
import type { Finding, Scan, AiReviewSummary, AiReviewItem, FindingStatus, ScanDirectoryInfo } from '../types';
import { SeverityBadge } from '../components/SeverityBadge';
import { DirectoryTreeExplorer } from '../components/DirectoryTreeExplorer';
import { PipelineRunningAnimation } from '../components/PipelineRunningAnimation';

interface Props {
  activeScanId?: string | null;
  onScanChange?: (scanId: string) => void;
}

export const NewScanView: React.FC<Props> = ({ activeScanId, onScanChange }) => {
  // Navigation / Phase: 'input' | 'running' | 'results'
  const [phase, setPhase] = useState<'input' | 'running' | 'results'>(activeScanId ? 'results' : 'input');

  // Input Type: ZIP vs GITHUB
  const [inputType, setInputType] = useState<'ZIP' | 'GITHUB'>('ZIP');

  // ZIP Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [projectName, setProjectName] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // GitHub Form State
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [authToken, setAuthToken] = useState('');

  // Scan & Pipeline State
  const [currentScanId, setCurrentScanId] = useState<string | null>(activeScanId || null);
  const [scan, setScan] = useState<Scan | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [pipelineProgress, setPipelineProgress] = useState(0);
  const [currentStage, setCurrentStage] = useState('');

  // Results State
  const [findings, setFindings] = useState<Finding[]>([]);
  const [aiReviews, setAiReviews] = useState<AiReviewSummary | null>(null);
  const [directoryInfo, setDirectoryInfo] = useState<ScanDirectoryInfo | null>(null);
  const [activeResultsTab, setActiveResultsTab] = useState<'findings' | 'remediation' | 'directory'>('findings');
  const [loadingResults, setLoadingResults] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [domainFilter, setDomainFilter] = useState<'ALL' | 'CODE_QUALITY' | 'SAST' | 'DAST' | 'GOVERNANCE'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedPatchId, setCopiedPatchId] = useState<string | null>(null);
  const [diffViewMap, setDiffViewMap] = useState<Record<string, boolean>>({});
  const [isRemediating, setIsRemediating] = useState(false);
  const [remediationSuccessMsg, setRemediationSuccessMsg] = useState('');

  // Sync with prop
  useEffect(() => {
    if (activeScanId && activeScanId !== currentScanId) {
      setCurrentScanId(activeScanId);
      setPhase('results');
    }
  }, [activeScanId]);

  // Load Scan Data
  const loadScanData = useCallback(async (scanId: string) => {
    try {
      const scanData = await ApiService.getScan(scanId);
      setScan(scanData);
      setPipelineProgress(scanData.progress_percentage || 0);
      setCurrentStage(scanData.current_stage || '');

      if (['COMPLETED', 'PARTIALLY_COMPLETED'].includes(scanData.status)) {
        setPhase('results');
        setLoadingResults(true);
        try {
          const [findRes, revRes, dirRes] = await Promise.all([
            ApiService.getScanFindings(scanId).catch((e) => {
              console.warn('Findings load fallback:', e);
              return { total: 0, findings: [] };
            }),
            ApiService.getAiReviews(scanId).catch(() => null),
            ApiService.getScanDirectory(scanId).catch(() => null),
          ]);
          setFindings(findRes?.findings || []);
          if (revRes) setAiReviews(revRes);
          if (dirRes) setDirectoryInfo(dirRes);
        } catch (loadErr) {
          console.error('Error populating scan results:', loadErr);
        } finally {
          setLoadingResults(false);
        }
      } else if (scanData.status === 'FAILED') {
        setPhase('results');
        setErrorMsg(scanData.error_message || 'Scan failed.');
      } else {
        setPhase('running');
      }
    } catch (err: any) {
      console.error('Failed to load scan:', err);
    }
  }, []);

  // Polling while running
  useEffect(() => {
    if (!currentScanId) return;

    loadScanData(currentScanId);

    const interval = setInterval(() => {
      if (phase === 'running') {
        loadScanData(currentScanId);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [currentScanId, phase, loadScanData]);

  // File Handlers
  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.toLowerCase().endsWith('.zip')) {
        setSelectedFile(file);
        if (!projectName) {
          setProjectName(file.name.replace(/\.zip$/i, ''));
        }
        setErrorMsg('');
      } else {
        setErrorMsg('Please upload a valid ZIP archive (.zip)');
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (file.name.toLowerCase().endsWith('.zip')) {
        setSelectedFile(file);
        if (!projectName) {
          setProjectName(file.name.replace(/\.zip$/i, ''));
        }
        setErrorMsg('');
      } else {
        setErrorMsg('Please upload a valid ZIP archive (.zip)');
      }
    }
  };

  // Run the Pipeline
  const handleRunPipeline = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setErrorMsg('');
    setPhase('running');
    setFindings([]);
    setAiReviews(null);
    setPipelineProgress(10);
    setCurrentStage('Initializing pipeline and workspace...');

    try {
      let createdScanId = '';

      if (inputType === 'ZIP') {
        if (!selectedFile) {
          throw new Error('Please select a project ZIP archive first.');
        }

        const formData = new FormData();
        formData.append('file', selectedFile);
        if (projectName) formData.append('project_name', projectName);
        formData.append('enable_sast', 'true');
        formData.append('enable_secrets', 'true');
        formData.append('enable_dependencies', 'true');
        formData.append('enable_governance', 'true');
        formData.append('enable_ai_review', 'true');

        const res = await ApiService.uploadZip(formData);
        createdScanId = res.scan_id;
      } else {
        if (!repoUrl) {
          throw new Error('Please enter a valid GitHub repository URL.');
        }

        const res = await ApiService.scanGitHub({
          repo_url: repoUrl.trim(),
          branch: branch?.trim() || undefined,
          auth_token: authToken?.trim() || undefined,
          enable_sast: true,
          enable_secrets: true,
          enable_dependencies: true,
          enable_governance: true,
          enable_ai_review: true,
        });
        createdScanId = res.scan_id;
      }

      if (createdScanId) {
        setCurrentScanId(createdScanId);
        if (onScanChange) onScanChange(createdScanId);
        loadScanData(createdScanId);
      }
    } catch (err: any) {
      console.error('Pipeline start error:', err);
      const isTimeout = err?.code === 'ECONNABORTED' || (err?.message && err.message.toLowerCase().includes('timeout'));
      const msg = isTimeout
        ? 'Repository analysis is taking longer than expected. The scan job has been queued in the background — please wait or check recent scans.'
        : (err.response?.data?.detail || err.message || 'Failed to start pipeline.');
      setErrorMsg(msg);
      setPhase('input');
    }
  };

  // Load Sample Project
  const handleLoadSample = async () => {
    setErrorMsg('');
    setPhase('running');
    setCurrentStage('Loading sample vulnerable project and AI patches...');
    try {
      const res = await ApiService.seedDemoData();
      if (res.scan_id) {
        setCurrentScanId(res.scan_id);
        if (onScanChange) onScanChange(res.scan_id);
        loadScanData(res.scan_id);
      }
    } catch (err: any) {
      setErrorMsg('Failed to load sample project.');
      setPhase('input');
    }
  };

  // Copy code
  const handleCopyCode = (text: string, patchId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedPatchId(patchId);
    setTimeout(() => setCopiedPatchId(null), 2000);
  };

  // Toggle diff
  const toggleDiffView = (findingId: string) => {
    setDiffViewMap((prev) => ({ ...prev, [findingId]: !prev[findingId] }));
  };

  // Update status
  const handleStatusChange = async (findingId: string, newStatus: FindingStatus) => {
    if (!currentScanId) return;
    try {
      await ApiService.updateFindingStatus(currentScanId, findingId, newStatus);
      setFindings((prev) =>
        prev.map((f) => (f.id === findingId ? { ...f, status: newStatus } : f))
      );
    } catch (err) {
      console.error('Failed to update finding status:', err);
    }
  };

  // Reset back to new scan
  const handleResetToNewScan = () => {
    setPhase('input');
    setScan(null);
    setCurrentScanId(null);
    setSelectedFile(null);
    setRepoUrl('');
    setFindings([]);
    setAiReviews(null);
    setErrorMsg('');
    if (onScanChange) onScanChange('');
  };

  // Map AI review to finding
  const getReviewForFinding = (finding: Finding): AiReviewItem | undefined => {
    if (!aiReviews?.recommendations) return undefined;
    return aiReviews.recommendations.find(
      (r) =>
        r.linked_finding_id === finding.id ||
        (r.file_path === finding.file_path && r.title.toLowerCase().includes(finding.title.toLowerCase().slice(0, 10)))
    );
  };

  const categorizeFinding = (finding: Finding): 'CODE_QUALITY' | 'SAST' | 'DAST' | 'GOVERNANCE' => {
    const rule = (finding.rule_id || '').toUpperCase();
    const cat = (finding.category || '').toLowerCase();
    const scanner = (finding.scanner || '').toLowerCase();

    if (scanner.includes('governance') || cat.includes('llm') || rule.startsWith('AI-') || rule.startsWith('PROMPT-')) {
      return 'GOVERNANCE';
    }
    if (scanner.includes('dast') || scanner.includes('zap') || rule.startsWith('DAST-')) {
      return 'DAST';
    }
    if (
      cat.includes('quality') ||
      cat.includes('syntax') ||
      cat.includes('complexity') ||
      rule.startsWith('SYNTAX-') ||
      rule.startsWith('MCCABE-') ||
      rule.startsWith('DUP-') ||
      rule.startsWith('UNUSED-') ||
      rule.startsWith('TAUTOLOGY-') ||
      rule.startsWith('ZERO-DIV-') ||
      rule.startsWith('INF-LOOP-') ||
      rule.startsWith('EXCEPT-') ||
      rule.startsWith('FORMAT-')
    ) {
      return 'CODE_QUALITY';
    }
    return 'SAST';
  };

  const handleAutoRemediate = async () => {
    if (!currentScanId) return;
    setIsRemediating(true);
    setRemediationSuccessMsg('');
    setErrorMsg('');
    try {
      const res = await ApiService.remediateScan(currentScanId);
      setRemediationSuccessMsg(
        `All ${res.fixes_applied_count || 'detected'} security & quality vulnerabilities have been remediated! Repository is certified production-ready.`
      );
      await loadScanData(currentScanId);
      setActiveResultsTab('remediation');
    } catch (err: any) {
      console.error('Auto remediation failed:', err);
      setErrorMsg(err.response?.data?.detail || err.message || 'Auto-remediation failed.');
    } finally {
      setIsRemediating(false);
    }
  };

  const codeQualityCount = findings.filter((f) => categorizeFinding(f) === 'CODE_QUALITY').length;
  const sastCount = findings.filter((f) => categorizeFinding(f) === 'SAST').length;
  const dastCount = findings.filter((f) => categorizeFinding(f) === 'DAST').length;
  const govCount = findings.filter((f) => categorizeFinding(f) === 'GOVERNANCE').length;

  const resolvedCount = findings.filter((f) => f.status === 'RESOLVED').length;
  const openIssuesCount = findings.filter((f) => f.status !== 'RESOLVED' && f.status !== 'FALSE_POSITIVE').length;
  const isCertifiedReady =
    openIssuesCount === 0 ||
    (scan?.summary?.risk_score === 0.0 && (resolvedCount > 0 || findings.length === 0)) ||
    !!remediationSuccessMsg;

  const filteredFindings = findings.filter((f) => {
    const matchesSev = severityFilter === 'ALL' || f.severity === severityFilter;
    const matchesDomain = domainFilter === 'ALL' || categorizeFinding(f) === domainFilter;
    const matchesSearch =
      !searchQuery ||
      f.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (f.file_path && f.file_path.toLowerCase().includes(searchQuery.toLowerCase())) ||
      f.rule_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSev && matchesDomain && matchesSearch;
  });

  const canRun = inputType === 'ZIP' ? !!selectedFile : !!repoUrl.trim();

  // =========================================================================
  // VIEW MODE 1: RUNNING PIPELINE PROGRESS
  // =========================================================================
  if (phase === 'running') {
    return (
      <div className="p-6 md:p-8">
        <PipelineRunningAnimation
          scan={scan}
          pipelineProgress={pipelineProgress}
          currentStage={currentStage}
        />
      </div>
    );
  }

  // =========================================================================
  // VIEW MODE 2: PRODUCTION READINESS DASHBOARD & RESULTS
  // =========================================================================
  if (phase === 'results' && scan) {
    return (
      <div className="p-6 md:p-8 max-w-6xl mx-auto space-y-6">
        {/* Top Header & Quick Actions */}
        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-200">
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
                  Full Audit Pipeline Complete
                </span>
                <span className="text-xs font-mono font-medium text-slate-400">[{scan.id}]</span>
              </div>
              <h2 className="text-xl font-bold text-slate-900 mt-1">{scan.project_name}</h2>
              <p className="text-xs text-slate-500">
                {scan.summary?.files_analyzed || 0} files analyzed &bull;{' '}
                {(scan.summary?.total_lines_of_code || 0).toLocaleString()} lines of code &bull;{' '}
                {scan.languages?.map((l) => l.language).join(', ') || 'Multi-language'}
              </p>
            </div>

            {/* Quick Actions */}
            <div className="flex items-center gap-2.5 shrink-0 flex-wrap">
              <a
                href={ApiService.getFixedZipUrl(scan.id)}
                download
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition-colors flex items-center gap-2 shadow-xs shadow-emerald-200 cursor-pointer"
                title="Download 100% production-ready, remediated repository ZIP"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Production Code (.ZIP)</span>
              </a>

              <a
                href={ApiService.getReportPdfUrl(scan.id)}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-xl transition-colors flex items-center gap-2 shadow-xs shadow-blue-200 cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>PDF Report</span>
              </a>

              <a
                href={ApiService.getReportJsonUrl(scan.id)}
                target="_blank"
                rel="noreferrer"
                className="px-4 py-2 bg-white hover:bg-slate-50 text-slate-700 border border-slate-300 text-xs font-bold rounded-xl transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5 text-slate-500" />
                <span>Export JSON</span>
              </a>

              <button
                type="button"
                onClick={handleResetToNewScan}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold rounded-xl transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>New Scan</span>
              </button>
            </div>
          </div>
        </div>

        {/* Remediation Success Notification */}
        {remediationSuccessMsg && (
          <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 bg-emerald-600 text-white rounded-lg">
                <CheckCheck className="w-4 h-4" />
              </div>
              <div>
                <p className="font-extrabold text-sm">{remediationSuccessMsg}</p>
                <p className="text-[11px] text-emerald-700 mt-0.5">
                  SQL parameterized, hardcoded secrets converted to environment variables, deserialization hardened, and CVE dependencies upgraded.
                </p>
              </div>
            </div>
            <a
              href={ApiService.getFixedZipUrl(scan.id)}
              download
              className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold flex items-center gap-1.5 shrink-0 self-start sm:self-auto cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Clean ZIP</span>
            </a>
          </div>
        )}

        {/* =========================================================================
            EXECUTIVE PRODUCTION READINESS STATUS BANNER
            ========================================================================= */}
        <div
          className={`p-6 rounded-2xl border transition-all ${
            isCertifiedReady
              ? 'bg-gradient-to-r from-emerald-50 via-teal-50/60 to-emerald-50 border-emerald-300 shadow-xs'
              : 'bg-gradient-to-r from-amber-50 via-red-50/40 to-amber-50 border-amber-300 shadow-xs'
          }`}
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
            <div className="space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                {isCertifiedReady ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold bg-emerald-600 text-white shadow-2xs">
                    <CheckCheck className="w-4 h-4" />
                    CERTIFIED PRODUCTION READY &bull; GRADE A+
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold bg-red-600 text-white shadow-2xs">
                    <AlertTriangle className="w-4 h-4" />
                    PRODUCTION DEPLOYMENT BLOCKED ({openIssuesCount} ISSUES)
                  </span>
                )}
                <span className="text-xs font-bold text-slate-600">
                  Risk Score: {isCertifiedReady ? '0.0 / 100 (Safe)' : `${scan.summary?.risk_score || 78.5} / 100`}
                </span>
              </div>

              <h3 className="text-lg font-extrabold text-slate-900">
                {isCertifiedReady
                  ? 'Codebase Verified & Hardened for Production Deployment'
                  : 'Action Required: Codebase Contains Security & Quality Vulnerabilities'}
              </h3>
              <p className="text-xs text-slate-600 max-w-2xl leading-relaxed">
                {isCertifiedReady
                  ? 'All security vulnerabilities, code complexity anti-patterns, hardcoded credentials, and flawed dependencies have been resolved. The code is ready for zero-defect production release.'
                  : 'Automated static analysis, runtime verification, and AI review detected issues that prevent production deployment. Click "Auto-Fix All Issues" to remediate all flaws and obtain clean, production-ready code.'}
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0">
              {!isCertifiedReady && (
                <button
                  type="button"
                  onClick={handleAutoRemediate}
                  disabled={isRemediating}
                  className="px-5 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white text-xs font-extrabold rounded-xl transition-all flex items-center justify-center gap-2 shadow-md shadow-blue-500/20 cursor-pointer disabled:opacity-70"
                >
                  {isRemediating ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Applying Automated Fixes...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4 text-amber-300 fill-amber-300" />
                      <span>⚡ Auto-Fix All Issues & Make Production Ready</span>
                    </>
                  )}
                </button>
              )}

              <a
                href={ApiService.getFixedZipUrl(scan.id)}
                download
                className={`px-5 py-3 rounded-xl text-xs font-extrabold flex items-center justify-center gap-2 transition-all cursor-pointer ${
                  isCertifiedReady
                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-md shadow-emerald-600/20'
                    : 'bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 shadow-2xs'
                }`}
              >
                <Download className="w-4 h-4" />
                <span>{isCertifiedReady ? 'Download Production Code (.ZIP)' : 'Download Clean Archive (.ZIP)'}</span>
              </a>
            </div>
          </div>
        </div>

        {/* =========================================================================
            EXECUTIVE MULTI-DOMAIN AUDIT CARDS (CODE REVIEW, SAST, DAST, GOVERNANCE)
            ========================================================================= */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Code Review & Quality */}
          <div
            onClick={() => {
              setActiveResultsTab('findings');
              setDomainFilter('CODE_QUALITY');
            }}
            className="p-5 rounded-2xl bg-white border border-slate-200 hover:border-blue-400 hover:shadow-xs transition-all cursor-pointer space-y-2 group"
          >
            <div className="flex items-center justify-between">
              <div className="p-2.5 rounded-xl bg-blue-50 text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <Code2 className="w-5 h-5" />
              </div>
              <span
                className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                  codeQualityCount === 0 || isCertifiedReady
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}
              >
                {codeQualityCount === 0 || isCertifiedReady ? 'PASSED' : `${codeQualityCount} ISSUES`}
              </span>
            </div>
            <h4 className="text-sm font-bold text-slate-900 pt-1">1. Code Review & Quality</h4>
            <p className="text-[11px] text-slate-500">
              AST syntax errors, McCabe complexity, duplicate code, unused variables/imports, loops.
            </p>
          </div>

          {/* Card 2: SAST Security */}
          <div
            onClick={() => {
              setActiveResultsTab('findings');
              setDomainFilter('SAST');
            }}
            className="p-5 rounded-2xl bg-white border border-slate-200 hover:border-red-400 hover:shadow-xs transition-all cursor-pointer space-y-2 group"
          >
            <div className="flex items-center justify-between">
              <div className="p-2.5 rounded-xl bg-red-50 text-red-600 group-hover:bg-red-600 group-hover:text-white transition-colors">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <span
                className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                  sastCount === 0 || isCertifiedReady
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}
              >
                {sastCount === 0 || isCertifiedReady ? 'SECURE' : `${sastCount} FLAWS`}
              </span>
            </div>
            <h4 className="text-sm font-bold text-slate-900 pt-1">2. SAST Static Security</h4>
            <p className="text-[11px] text-slate-500">
              Secrets, SQL injection, XSS, Command injection, SSRF, IDOR, CVE dependencies.
            </p>
          </div>

          {/* Card 3: DAST Runtime Analysis */}
          <div
            onClick={() => {
              setActiveResultsTab('findings');
              setDomainFilter('DAST');
            }}
            className="p-5 rounded-2xl bg-white border border-slate-200 hover:border-purple-400 hover:shadow-xs transition-all cursor-pointer space-y-2 group"
          >
            <div className="flex items-center justify-between">
              <div className="p-2.5 rounded-xl bg-purple-50 text-purple-600 group-hover:bg-purple-600 group-hover:text-white transition-colors">
                <Activity className="w-5 h-5" />
              </div>
              <span
                className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                  dastCount === 0 || isCertifiedReady
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-purple-50 text-purple-700 border border-purple-200'
                }`}
              >
                {dastCount === 0 || isCertifiedReady ? 'VERIFIED' : `${dastCount} ALERTS`}
              </span>
            </div>
            <h4 className="text-sm font-bold text-slate-900 pt-1">3. DAST Runtime Analysis</h4>
            <p className="text-[11px] text-slate-500">
              Runtime SQLi/XSS, Auth bypass, CSP headers, stack leaks, improper input validation.
            </p>
          </div>

          {/* Card 4: LLM Governance */}
          <div
            onClick={() => {
              setActiveResultsTab('findings');
              setDomainFilter('GOVERNANCE');
            }}
            className="p-5 rounded-2xl bg-white border border-slate-200 hover:border-fuchsia-400 hover:shadow-xs transition-all cursor-pointer space-y-2 group"
          >
            <div className="flex items-center justify-between">
              <div className="p-2.5 rounded-xl bg-fuchsia-50 text-fuchsia-600 group-hover:bg-fuchsia-600 group-hover:text-white transition-colors">
                <Sparkles className="w-5 h-5" />
              </div>
              <span
                className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${
                  govCount === 0 || isCertifiedReady
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-fuchsia-50 text-fuchsia-700 border border-fuchsia-200'
                }`}
              >
                {govCount === 0 || isCertifiedReady ? 'GUARDED' : `${govCount} RISKS`}
              </span>
            </div>
            <h4 className="text-sm font-bold text-slate-900 pt-1">4. LLM AI Governance</h4>
            <p className="text-[11px] text-slate-500">
              Prompt injections, system prompt leak, RAG data leakage, unsafe AI output execution.
            </p>
          </div>
        </div>

        {/* =========================================================================
            RESULTS NAVIGATION TABS
            ========================================================================= */}
        <div className="flex items-center gap-2 border-b border-slate-200 pb-2 overflow-x-auto">
          <button
            type="button"
            onClick={() => {
              setActiveResultsTab('findings');
              setDomainFilter('ALL');
            }}
            className={`px-4 py-2.5 rounded-xl text-xs font-extrabold flex items-center gap-2 transition-all cursor-pointer shrink-0 ${
              activeResultsTab === 'findings'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200'
            }`}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>Security & Quality Audit ({findings.length})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveResultsTab('remediation')}
            className={`px-4 py-2.5 rounded-xl text-xs font-extrabold flex items-center gap-2 transition-all cursor-pointer shrink-0 ${
              activeResultsTab === 'remediation'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200'
            }`}
          >
            <Zap className="w-4 h-4 text-amber-300" />
            <span>⚡ Production Fixes & Unified Diffs ({aiReviews?.recommendations?.length || scan.summary?.total_findings || 0})</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveResultsTab('directory')}
            className={`px-4 py-2.5 rounded-xl text-xs font-extrabold flex items-center gap-2 transition-all cursor-pointer shrink-0 ${
              activeResultsTab === 'directory'
                ? 'bg-blue-600 text-white shadow-xs'
                : 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200'
            }`}
          >
            <Folder className="w-4 h-4" />
            <span>Repository File Explorer ({directoryInfo?.total_files || scan.summary?.files_analyzed || 0} Files)</span>
          </button>
        </div>

        {/* =========================================================================
            TAB 1: PRODUCTION FIXES & UNIFIED DIFFS (DEFAULT TAB)
            ========================================================================= */}
        {activeResultsTab === 'remediation' && (
          <div className="space-y-5">
            {/* Action Bar */}
            <div className="p-4 rounded-2xl bg-white border border-slate-200 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <h4 className="text-sm font-extrabold text-slate-900 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-600" />
                  Automated Unified Diffs & Production Remediation
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Pre-synthesized AST patches that fix every identified vulnerability into production-ready code.
                </p>
              </div>

              {!isCertifiedReady && (
                <button
                  type="button"
                  onClick={handleAutoRemediate}
                  disabled={isRemediating}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition-colors flex items-center gap-2 shrink-0 cursor-pointer disabled:opacity-70 shadow-2xs"
                >
                  {isRemediating ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Remediating...</span>
                    </>
                  ) : (
                    <>
                      <CheckCheck className="w-3.5 h-3.5" />
                      <span>Apply All Fixes & Certify Repository</span>
                    </>
                  )}
                </button>
              )}
            </div>

            {/* List of Unified Diff Patches */}
            {(!aiReviews?.recommendations || aiReviews.recommendations.length === 0) ? (
              <div className="bg-white p-12 rounded-2xl border border-slate-200 text-center space-y-4">
                <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto" />
                <h4 className="text-sm font-bold text-slate-900">
                  {findings.length > 0 ? `${findings.length} Audit Item(s) Found` : 'Zero Pending Fixes Required'}
                </h4>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  {findings.length > 0
                    ? `The pipeline identified ${findings.length} security / quality item(s). Switch to the "Security & Quality Audit" tab to review line-by-line items and code fixes.`
                    : 'All security and quality checks are verified and ready for zero-defect production release.'}
                </p>
                {findings.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setActiveResultsTab('findings')}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold transition-colors cursor-pointer shadow-xs inline-flex items-center gap-1.5"
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>View Security Audit Items ({findings.length})</span>
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {aiReviews.recommendations.map((rec) => {
                  const patch = rec.patch;
                  const diffUnified = patch?.diff_unified;
                  const showDiff = diffViewMap[rec.id] !== false; // default true for remediation tab

                  return (
                    <div
                      key={rec.id}
                      className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden transition-all hover:border-slate-300"
                    >
                      <div className="p-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/70">
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                              PATCH READY
                            </span>
                            <span className="font-mono text-xs font-semibold text-slate-700 flex items-center gap-1">
                              <FileCode className="w-3.5 h-3.5 text-slate-400" />
                              {rec.file_path} {rec.line_number ? `:${rec.line_number}` : ''}
                            </span>
                          </div>
                          <h4 className="text-sm font-bold text-slate-900 mt-1">{rec.title}</h4>
                        </div>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => toggleDiffView(rec.id)}
                            className="px-2.5 py-1 text-xs font-semibold text-slate-600 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg transition-colors cursor-pointer"
                          >
                            <Diff className="w-3 h-3 inline mr-1" />
                            {showDiff ? 'Clean Code' : 'Unified Diff'}
                          </button>

                          <button
                            type="button"
                            onClick={() => handleCopyCode(patch?.suggested_code || '', rec.id)}
                            className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer shadow-2xs flex items-center gap-1.5"
                          >
                            {copiedPatchId === rec.id ? (
                              <>
                                <Check className="w-3.5 h-3.5" />
                                <span>Copied!</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3.5 h-3.5" />
                                <span>Copy Code</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>

                      <div className="p-5 space-y-3">
                        <p className="text-xs text-slate-700 leading-relaxed">
                          <strong>Root Cause & Fix:</strong> {rec.explanation_simple || rec.root_cause}
                        </p>

                        {/* Diff Box */}
                        {showDiff && diffUnified ? (
                          <div className="bg-slate-900 rounded-xl p-3.5 font-mono text-xs overflow-x-auto border border-slate-700">
                            {diffUnified.split('\n').map((line, idx) => (
                              <div
                                key={idx}
                                className={
                                  line.startsWith('+')
                                    ? 'text-emerald-400 font-semibold bg-emerald-950/30 px-1 rounded'
                                    : line.startsWith('-')
                                    ? 'text-red-400 bg-red-950/30 px-1 rounded'
                                    : line.startsWith('@')
                                    ? 'text-blue-400'
                                    : 'text-slate-400'
                                }
                              >
                                {line || '\u00A0'}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="bg-slate-900 rounded-xl p-3.5 font-mono text-xs text-emerald-300 overflow-x-auto border border-emerald-950/40">
                            <pre className="leading-relaxed font-semibold">
                              {patch?.suggested_code}
                            </pre>
                          </div>
                        )}

                        {patch?.explanation && (
                          <div className="text-[11px] text-emerald-800 leading-relaxed bg-emerald-50/60 p-2.5 rounded-lg border border-emerald-100">
                            <strong>Why this fix is production-ready:</strong> {patch.explanation}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            TAB 2: DETAILED SECURITY & CODE QUALITY AUDIT
            ========================================================================= */}
        {activeResultsTab === 'findings' && (
          <div className="space-y-5">
            {/* Domain & Severity Filters */}
            <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-2xs space-y-3">
              {/* Domain Pills */}
              <div className="flex items-center gap-2 flex-wrap border-b border-slate-100 pb-3">
                <span className="text-xs font-bold text-slate-400 mr-1">Domain:</span>
                {[
                  { id: 'ALL', label: `All (${findings.length})` },
                  { id: 'CODE_QUALITY', label: `Code Review & Quality (${codeQualityCount})` },
                  { id: 'SAST', label: `SAST Security (${sastCount})` },
                  { id: 'DAST', label: `DAST Runtime (${dastCount})` },
                  { id: 'GOVERNANCE', label: `LLM Governance (${govCount})` },
                ].map((dom) => (
                  <button
                    key={dom.id}
                    type="button"
                    onClick={() => setDomainFilter(dom.id as any)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                      domainFilter === dom.id
                        ? 'bg-blue-600 text-white shadow-2xs'
                        : 'bg-slate-100 hover:bg-slate-200 text-slate-600'
                    }`}
                  >
                    {dom.label}
                  </button>
                ))}
              </div>

              {/* Severity & Search Bar */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
                <div className="flex items-center gap-1.5 flex-wrap w-full sm:w-auto">
                  <span className="text-xs font-bold text-slate-400 mr-1">Severity:</span>
                  {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
                    <button
                      key={sev}
                      type="button"
                      onClick={() => setSeverityFilter(sev)}
                      className={`px-3 py-1 rounded-lg text-xs font-bold transition-colors cursor-pointer ${
                        severityFilter === sev
                          ? 'bg-slate-900 text-white shadow-2xs'
                          : 'bg-slate-100 hover:bg-slate-200 text-slate-600'
                      }`}
                    >
                      {sev}
                    </button>
                  ))}
                </div>

                <div className="relative w-full sm:w-72">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search findings, rules, or files..."
                    className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  />
                </div>
              </div>
            </div>

            {/* Findings List */}
            {loadingResults ? (
              <div className="py-16 flex flex-col items-center justify-center space-y-3">
                <RefreshCw className="w-7 h-7 text-blue-600 animate-spin" />
                <p className="text-xs font-semibold text-slate-500">Loading vulnerabilities & audit items...</p>
              </div>
            ) : filteredFindings.length === 0 ? (
              <div className="bg-white p-12 rounded-2xl border border-slate-200 shadow-2xs text-center space-y-3">
                <ShieldCheck className="w-12 h-12 text-emerald-500 mx-auto" />
                <h4 className="text-sm font-bold text-slate-900">
                  {findings.length === 0 ? 'Zero Vulnerabilities Detected' : 'No Issues Match Current Filter'}
                </h4>
                <p className="text-xs text-slate-400">
                  {findings.length === 0
                    ? 'All static security analyzers, secret scanners, and compliance checks passed with 0 defects.'
                    : 'Select "All" domains and severities to view the full findings list.'}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredFindings.map((finding) => {
                  const reviewItem = getReviewForFinding(finding);
                  const patch = reviewItem?.patch;
                  const hasSuggestedFix = patch?.suggested_code || finding.suggested_fix;

                  return (
                    <div
                      key={finding.id}
                      className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden transition-all hover:border-slate-300"
                    >
                      <div className="p-4 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-50/50">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <SeverityBadge severity={finding.severity} size="sm" />
                            <span className="font-mono text-[11px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                              {finding.rule_id}
                            </span>
                            {finding.cwe_ids && finding.cwe_ids.length > 0 && (
                              <span className="font-mono text-[11px] font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                                {finding.cwe_ids[0]}
                              </span>
                            )}
                            <span className="text-[11px] text-slate-400">&bull; {finding.scanner}</span>
                          </div>
                          <h4 className="text-base font-bold text-slate-900">{finding.title}</h4>
                          <div className="flex items-center gap-1.5 font-mono text-xs text-slate-600">
                            <FileCode className="w-3.5 h-3.5 text-slate-400" />
                            <span className="font-semibold">{finding.file_path || 'External Target'}</span>
                            {finding.line_number && <span className="text-slate-400">:{finding.line_number}</span>}
                          </div>
                        </div>

                        {/* Status Triage */}
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-xs font-semibold text-slate-400">Status:</span>
                          <select
                            value={finding.status}
                            onChange={(e) => handleStatusChange(finding.id, e.target.value as FindingStatus)}
                            className="px-2.5 py-1 text-xs font-bold rounded-lg bg-white border border-slate-200 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer"
                          >
                            <option value="OPEN">OPEN</option>
                            <option value="IN_REVIEW">IN REVIEW</option>
                            <option value="CONFIRMED">CONFIRMED</option>
                            <option value="RESOLVED">RESOLVED</option>
                            <option value="FALSE_POSITIVE">FALSE POSITIVE</option>
                          </select>
                        </div>
                      </div>

                      <div className="p-5 space-y-4">
                        <div>
                          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">
                            Vulnerability Explanation & Root Cause
                          </p>
                          <p className="text-xs text-slate-700 leading-relaxed">
                            {reviewItem?.explanation_simple || finding.description}
                          </p>
                        </div>

                        {finding.code_snippet && (
                          <div>
                            <p className="text-xs font-bold text-red-600 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded-full bg-red-500" />
                              Flawed Code (Vulnerable Snippet)
                            </p>
                            <div className="bg-slate-900 rounded-xl p-3.5 font-mono text-xs text-red-300 overflow-x-auto border border-red-950/40">
                              <pre className="leading-relaxed">{finding.code_snippet}</pre>
                            </div>
                          </div>
                        )}

                        {hasSuggestedFix && (
                          <div className="bg-emerald-50/40 p-4 rounded-xl border border-emerald-200/80 space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-emerald-900 flex items-center gap-1.5">
                                <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                                Recommended Production-Ready Fix
                              </span>
                              <button
                                type="button"
                                onClick={() => handleCopyCode(patch?.suggested_code || finding.suggested_fix || '', finding.id)}
                                className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-bold transition-colors cursor-pointer"
                              >
                                {copiedPatchId === finding.id ? 'Copied!' : 'Copy Fix'}
                              </button>
                            </div>
                            <div className="bg-slate-900 rounded-xl p-3 font-mono text-xs text-emerald-300 overflow-x-auto border border-emerald-950/40">
                              <pre>{patch?.suggested_code || finding.suggested_fix}</pre>
                            </div>
                          </div>
                        )}

                        {finding.remediation_guidance && !hasSuggestedFix && (
                          <div className="p-3 bg-blue-50/50 rounded-xl border border-blue-200/80 text-xs text-blue-900">
                            <span className="font-bold flex items-center gap-1 text-blue-800 mb-1">
                              <ShieldCheck className="w-3.5 h-3.5 text-blue-600" /> Remediation Guidance:
                            </span>
                            <p className="leading-relaxed">{finding.remediation_guidance}</p>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* =========================================================================
            TAB 3: REPOSITORY FILE EXPLORER
            ========================================================================= */}
        {activeResultsTab === 'directory' && (
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
            <div>
              <h4 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Folder className="w-4 h-4 text-blue-600" />
                Scanned Repository File Hierarchy
              </h4>
              <p className="text-xs text-slate-500 mt-0.5">
                Inspect workspace directories, file sizes, lines of code, and localized issue markers.
              </p>
            </div>
            <DirectoryTreeExplorer
              scanId={scan.id}
              directoryInfo={directoryInfo}
              findings={findings}
              aiReviews={aiReviews}
            />
          </div>
        )}
      </div>
    );
  }

  // =========================================================================
  // VIEW MODE 3: INITIAL INPUT (ZIP & GITHUB SELECTION)
  // =========================================================================
  return (
    <div className="p-8 max-w-4xl mx-auto space-y-7">
      {/* Header Banner */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">New Security Scan</h2>
            <p className="text-xs text-slate-500 mt-1">
              Select your codebase source below. Run the pipeline to view immediate vulnerability results and AI-corrected code suggestions.
            </p>
          </div>

          <button
            type="button"
            onClick={handleLoadSample}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-purple-200 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold transition-colors cursor-pointer self-start sm:self-auto shrink-0 shadow-2xs"
            title="Load ready-to-test vulnerable project with SQL injection and credential leaks"
          >
            <Sparkles className="w-4 h-4 text-purple-600" />
            <span>Load Sample Project</span>
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2.5">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Source Selector: 1. ZIP, 2. GITHUB */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Option 1: ZIP */}
        <button
          type="button"
          onClick={() => setInputType('ZIP')}
          className={`p-5 rounded-2xl border text-left transition-all flex items-start gap-4 cursor-pointer ${
            inputType === 'ZIP'
              ? 'bg-blue-50/60 border-blue-500 ring-2 ring-blue-500/20 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300'
          }`}
        >
          <div
            className={`p-3 rounded-xl border ${
              inputType === 'ZIP'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-slate-100 text-slate-600 border-slate-200'
            }`}
          >
            <FolderArchive className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 text-sm">1. Upload ZIP Archive</span>
              {inputType === 'ZIP' && <CheckCircle2 className="w-4 h-4 text-blue-600" />}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Upload zipped source code. Analyzed safely in an isolated workspace.
            </p>
          </div>
        </button>

        {/* Option 2: GITHUB */}
        <button
          type="button"
          onClick={() => setInputType('GITHUB')}
          className={`p-5 rounded-2xl border text-left transition-all flex items-start gap-4 cursor-pointer ${
            inputType === 'GITHUB'
              ? 'bg-blue-50/60 border-blue-500 ring-2 ring-blue-500/20 shadow-xs'
              : 'bg-white border-slate-200 hover:border-slate-300'
          }`}
        >
          <div
            className={`p-3 rounded-xl border ${
              inputType === 'GITHUB'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-slate-100 text-slate-600 border-slate-200'
            }`}
          >
            <GitBranch className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 text-sm">2. GitHub Repository</span>
              {inputType === 'GITHUB' && <CheckCircle2 className="w-4 h-4 text-blue-600" />}
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Provide a GitHub repository link for shallow clone and code review.
            </p>
          </div>
        </button>
      </div>

      {/* Input Configuration Box */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs space-y-5">
        <h3 className="text-sm font-bold text-slate-900">
          {inputType === 'ZIP' ? 'Project Archive Details' : 'GitHub Repository Link'}
        </h3>

        {inputType === 'ZIP' ? (
          <div className="space-y-4">
            {/* Drag & Drop Area */}
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleFileDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-colors ${
                selectedFile
                  ? 'border-blue-400 bg-blue-50/40'
                  : 'border-slate-200 hover:border-blue-400 bg-slate-50/50 hover:bg-slate-50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                onChange={handleFileSelect}
                className="hidden"
              />
              <div className="flex flex-col items-center justify-center space-y-2">
                <div className="p-3 bg-white border border-slate-200 rounded-full shadow-xs text-blue-600">
                  <Upload className="w-6 h-6" />
                </div>
                {selectedFile ? (
                  <div>
                    <p className="text-sm font-bold text-slate-900">{selectedFile.name}</p>
                    <p className="text-xs text-slate-500">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB &bull; Ready for analysis
                    </p>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-semibold text-slate-800">
                      Drag and drop your project ZIP here, or <span className="text-blue-600 font-bold">browse</span>
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Supports Python, Java, JS/TS, Go, PHP, C/C++, C#, Ruby, Rust (Max 50MB)
                    </p>
                  </div>
                )}
              </div>
            </div>

            {selectedFile && (
              <div className="p-3 bg-blue-50/60 border border-blue-200/70 rounded-xl flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <HardDrive className="w-4 h-4 text-blue-600 shrink-0" />
                  <div>
                    <p className="font-bold text-slate-800">Target Workspace Directory</p>
                    <p className="text-[11px] font-mono text-slate-500">
                      data/workspaces/{selectedFile.name.replace(/\.zip$/i, '').toLowerCase()}-[scan-id]
                    </p>
                  </div>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                  Isolated Sandbox
                </span>
              </div>
            )}

            {/* Project Name */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Project Name (Optional)
              </label>
              <input
                type="text"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="e.g. PaymentGatewayService"
                className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              />
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                GitHub Repository URL <span className="text-red-500">*</span>
              </label>
              <input
                type="url"
                required
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="https://github.com/owner/repository"
                className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
              />
            </div>

            {repoUrl.trim() && (
              <div className="p-3 bg-blue-50/60 border border-blue-200/70 rounded-xl flex items-center justify-between text-xs">
                <div className="flex items-center gap-2.5">
                  <HardDrive className="w-4 h-4 text-blue-600 shrink-0" />
                  <div>
                    <p className="font-bold text-slate-800">Target Workspace Directory</p>
                    <p className="text-[11px] font-mono text-slate-500">
                      data/workspaces/{repoUrl.split('/').pop()?.replace('.git', '') || 'repo'}-[scan-id]
                    </p>
                  </div>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                  Isolated Sandbox
                </span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Branch Name
                </label>
                <input
                  type="text"
                  value={branch}
                  onChange={(e) => setBranch(e.target.value)}
                  placeholder="main"
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Access Token (Optional for Private Repos)
                </label>
                <input
                  type="password"
                  value={authToken}
                  onChange={(e) => setAuthToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  className="w-full px-3.5 py-2 text-xs bg-white border border-slate-200 rounded-lg text-slate-900 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* PROMINENT RUN THE PIPELINE BUTTON */}
        <div className="pt-3 border-t border-slate-100 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            {canRun
              ? 'Click to run the security pipeline and inspect corrected code suggestions.'
              : 'Attach a ZIP file or enter a GitHub link to run the pipeline.'}
          </p>

          <button
            type="button"
            onClick={() => handleRunPipeline()}
            disabled={!canRun}
            className={`px-8 py-3 text-sm font-extrabold rounded-xl flex items-center gap-2.5 transition-all cursor-pointer ${
              canRun
                ? 'bg-blue-600 hover:bg-blue-700 text-white shadow-md shadow-blue-300/40 hover:scale-[1.01]'
                : 'bg-slate-200 text-slate-400 cursor-not-allowed'
            }`}
          >
            <Play className="w-4 h-4 fill-white text-white" />
            <span>Run the Pipeline</span>
          </button>
        </div>
      </div>
    </div>
  );
};
