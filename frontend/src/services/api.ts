import axios from 'axios';
import type {
  DashboardMetrics,
  Finding,
  FindingStatus,
  GovernanceAuditEvent,
  GovernanceEvalResult,
  Scan,
  AiReviewSummary,
  ScanDirectoryInfo,
} from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

const api = axios.create({
  baseURL: API_BASE_URL ? `${API_BASE_URL}/api` : '/api',
  timeout: 300000, // 5 minutes to prevent premature aborts on repository scans and remediations
});

export const ApiService = {
  // System Health & Metrics
  async getHealth() {
    const res = await api.get('/health');
    return res.data;
  },

  async getMetrics(): Promise<DashboardMetrics> {
    const res = await api.get('/metrics');
    return res.data;
  },

  // Scans
  async listScans(status?: string, limit: number = 50): Promise<{ total: number; scans: Scan[] }> {
    const res = await api.get('/scans', { params: { status, limit } });
    return res.data;
  },

  async getScan(scanId: string): Promise<Scan> {
    const res = await api.get(`/scans/${scanId}`);
    return res.data;
  },

  async getScanDirectory(scanId: string): Promise<ScanDirectoryInfo> {
    const res = await api.get(`/scans/${scanId}/directory`);
    return res.data;
  },

  async getScanFileContent(scanId: string, filePath: string): Promise<{ file_path: string; content?: string; lines?: number; truncated?: boolean }> {
    const res = await api.get(`/scans/${scanId}/files/content`, { params: { file_path: filePath } });
    return res.data;
  },

  async uploadZip(formData: FormData) {
    const res = await api.post('/scans/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async scanGitHub(data: {
    repo_url: string;
    branch?: string;
    commit?: string;
    auth_token?: string;
    dast_target_url?: string;
    enable_sast?: boolean;
    enable_secrets?: boolean;
    enable_dependencies?: boolean;
    enable_dast?: boolean;
    enable_governance?: boolean;
    enable_ai_review?: boolean;
  }) {
    const res = await api.post('/scans/github', data);
    return res.data;
  },

  async cancelScan(scanId: string) {
    const res = await api.post(`/scans/${scanId}/cancel`);
    return res.data;
  },

  // Findings
  async getScanFindings(
    scanId: string,
    filters?: { severity?: string; category?: string; scanner?: string; status?: string; search?: string }
  ): Promise<{ scan_id: string; total: number; findings: Finding[] }> {
    const res = await api.get(`/scans/${scanId}/findings`, { params: filters });
    return res.data;
  },

  async getAllFindings(filters?: { severity?: string; status?: string; search?: string; limit?: number }): Promise<{ total: number; findings: Finding[] }> {
    const res = await api.get('/findings', { params: filters });
    return res.data;
  },

  async updateFindingStatus(scanId: string, findingId: string, newStatus: FindingStatus, notes?: string) {
    const form = new FormData();
    form.append('new_status', newStatus);
    if (notes) form.append('notes', notes);
    const res = await api.post(`/scans/${scanId}/findings/${findingId}/status`, form);
    return res.data;
  },

  // AI Code Reviews
  async getAiReviews(scanId: string): Promise<AiReviewSummary> {
    const res = await api.get(`/scans/${scanId}/reviews`);
    return res.data;
  },

  async applyReviewAction(scanId: string, recId: string, action: string, comment?: string) {
    const form = new FormData();
    form.append('action', action);
    if (comment) form.append('comment', comment);
    const res = await api.post(`/scans/${scanId}/reviews/${recId}/action`, form);
    return res.data;
  },

  // DAST
  async getDastResults(scanId: string) {
    const res = await api.get(`/scans/${scanId}/dast`);
    return res.data;
  },

  async triggerDast(scanId: string, targetUrl: string) {
    const form = new FormData();
    form.append('target_url', targetUrl);
    const res = await api.post(`/scans/${scanId}/dast`, form);
    return res.data;
  },

  // LLM Governance
  async evaluateGovernance(promptText?: string, responseText?: string, enforceBlocking: boolean = true): Promise<GovernanceEvalResult> {
    const res = await api.post('/governance/evaluate', {
      prompt_text: promptText,
      response_text: responseText,
      enforce_blocking: enforceBlocking,
    });
    return res.data;
  },

  async listGovernancePolicies() {
    const res = await api.get('/governance/policies');
    return res.data;
  },

  async listGovernanceAuditEvents(): Promise<{ total: number; events: GovernanceAuditEvent[] }> {
    const res = await api.get('/governance/events');
    return res.data;
  },

  // Reports
  getReportPdfUrl(scanId: string) {
    return `${API_BASE_URL}/api/scans/${scanId}/report?format=pdf`;
  },

  getReportJsonUrl(scanId: string) {
    return `${API_BASE_URL}/api/scans/${scanId}/report?format=json`;
  },

  async getReportJson(scanId: string) {
    const res = await api.get(`/scans/${scanId}/report`, { params: { format: 'json' } });
    return res.data;
  },

  // Production Remediation
  async remediateScan(scanId: string): Promise<{ success: boolean; fixes_applied_count: number; files_modified: string[]; quality_grade: string; risk_score: number; download_url: string }> {
    const res = await api.post(`/scans/${scanId}/remediate`);
    return res.data;
  },

  getFixedZipUrl(scanId: string) {
    return `${API_BASE_URL}/api/scans/${scanId}/download-fixed`;
  },

  // Demo seed
  async seedDemoData() {
    const res = await api.post('/demo/seed');
    return res.data;
  },

  // System Settings
  async getSettings() {
    const res = await api.get('/settings');
    return res.data;
  },

  async updateSettings(settingsData: any) {
    const res = await api.post('/settings', settingsData);
    return res.data;
  },
};

