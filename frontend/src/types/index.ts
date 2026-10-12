export type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

export type FindingStatus = 'OPEN' | 'IN_REVIEW' | 'CONFIRMED' | 'FALSE_POSITIVE' | 'RESOLVED';

export type ScanStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'PARTIALLY_COMPLETED' | 'FAILED' | 'CANCELLED';

export type ModuleStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'BLOCKED' | 'NOT_RUN' | 'SKIPPED';

export interface ModuleProgress {
  status: ModuleStatus;
  message?: string;
  elapsed_seconds: number;
  items_analyzed?: number;
  errors?: string[];
}

export interface LanguageStats {
  language: string;
  files_count: number;
  lines_of_code: number;
  percentage: number;
}

export interface ScanSummary {
  total_findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
  scanners_used: string[];
  languages_detected: string[];
  files_analyzed: number;
  total_lines_of_code: number;
  risk_score: number;
}

export interface Scan {
  id: string;
  project_name: string;
  input_type: 'ZIP' | 'GITHUB';
  source_identifier: string;
  branch_or_commit?: string;
  commit_hash?: string;
  workspace_path?: string;
  status: ScanStatus;
  progress_percentage: number;
  current_stage: string;
  error_message?: string;
  config: {
    sast: boolean;
    secret_scanning: boolean;
    dependency_scanning: boolean;
    dast: boolean;
    llm_governance: boolean;
    ai_code_review: boolean;
    dast_target_url?: string;
  };
  module_sast: ModuleProgress;
  module_secrets: ModuleProgress;
  module_dependencies: ModuleProgress;
  module_dast: ModuleProgress;
  module_governance: ModuleProgress;
  module_ai_review: ModuleProgress;
  languages: LanguageStats[];
  summary: ScanSummary;
  logs: string[];
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface Finding {
  id: string;
  scan_id: string;
  title: string;
  description: string;
  severity: Severity;
  category: string;
  scanner: string;
  rule_id: string;
  file_path?: string;
  line_number?: number;
  end_line?: number;
  code_snippet?: string;
  cwe_ids: string[];
  remediation_guidance?: string;
  suggested_fix?: string;
  confidence: string;
  status: FindingStatus;
  is_false_positive: boolean;
  review_notes?: string;
  created_at: string;
  updated_at: string;
}

export interface PatchSuggestion {
  id: string;
  file_path: string;
  line_start: number;
  line_end: number;
  original_code: string;
  suggested_code: string;
  diff_unified: string;
  explanation: string;
  safety_notes: string;
  status: 'PENDING' | 'APPROVE' | 'REJECT' | 'MARK_VERIFIED';
}

export interface AiReviewItem {
  id: string;
  scan_id: string;
  file_path: string;
  line_number: number;
  title: string;
  linked_finding_id?: string;
  severity: string;
  category: string;
  explanation_simple: string;
  root_cause: string;
  patch?: PatchSuggestion;
  maintainability_impact: string;
  confidence_score: number;
  status: 'PENDING' | 'APPROVE' | 'REJECT' | 'MARK_VERIFIED';
  reviewer_comment?: string;
  created_at: string;
}

export interface AiReviewSummary {
  scan_id: string;
  total_recommendations: number;
  approved_count: number;
  rejected_count: number;
  pending_count: number;
  model_used: string;
  overall_code_quality_grade: string;
  key_strengths: string[];
  top_risks: string[];
  recommendations: AiReviewItem[];
  generated_at: string;
}

export interface DastAlert {
  id: string;
  plugin_id?: string;
  alert_name: string;
  risk: 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';
  confidence: string;
  url: string;
  param?: string;
  attack_vector?: string;
  evidence?: string;
  description: string;
  solution: string;
  cwe_id?: string;
}

export interface DastEndpoint {
  url: string;
  method: string;
  status_code?: number;
  response_time_ms?: number;
  alerts_count: number;
}

export interface DastResult {
  scan_id: string;
  target_url: string;
  is_authorized: boolean;
  status: string;
  reason?: string;
  spider_endpoints_found: number;
  endpoints: DastEndpoint[];
  alerts: DastAlert[];
  total_alerts: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  info_count: number;
  scan_duration_seconds: number;
  missing_security_headers: string[];
}

export interface GovernanceViolation {
  rule_id: string;
  rule_name: string;
  category: string;
  decision: 'ALLOW' | 'WARN' | 'BLOCK';
  severity: string;
  evidence_snippet: string;
  explanation: string;
}

export interface SensitiveEntityMatch {
  entity_type: string;
  start_pos: number;
  end_pos: number;
  redacted_value: string;
  matched_value_masked: string;
}

export interface GovernanceEvalResult {
  decision: 'ALLOW' | 'WARN' | 'BLOCK';
  violations: GovernanceViolation[];
  detected_entities: SensitiveEntityMatch[];
  sanitized_prompt?: string;
  sanitized_response?: string;
  risk_score: number;
  prompt_injection_detected: boolean;
  secrets_detected: boolean;
  evaluation_time_ms: number;
  timestamp: string;
}

export interface GovernanceAuditEvent {
  id: string;
  scan_id?: string;
  event_type: string;
  decision: string;
  risk_categories: string[];
  violations_count: number;
  sanitized_input_preview?: string;
  timestamp: string;
}

export interface DashboardMetrics {
  total_scans: number;
  completed_scans: number;
  running_scans: number;
  total_vulnerabilities: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  projects_analyzed: number;
  severity_distribution: { name: string; value: number; color: string }[];
  findings_by_language: { language: string; files: number }[];
  vulnerability_trends: { scan_id: string; project: string; critical: number; high: number; medium: number; total: number }[];
  recent_scans: Scan[];
}

export interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  lines?: number;
  extension?: string;
  findings_count: number;
  severity_breakdown?: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  children?: FileNode[];
}

export interface FileItem {
  path: string;
  name: string;
  size: number;
  lines: number;
  extension: string;
  findings_count: number;
  severity_breakdown?: {
    total: number;
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
}

export interface ScanDirectoryInfo {
  status: string;
  scan_id: string;
  project_name: string;
  input_type: 'ZIP' | 'GITHUB';
  source_identifier: string;
  workspace_path: string;
  total_files: number;
  total_directories: number;
  total_size_bytes: number;
  tree: FileNode;
  files: FileItem[];
}
