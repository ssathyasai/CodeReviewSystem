from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class InputTypeEnum(str, Enum):
    ZIP = "ZIP"
    GITHUB = "GITHUB"


class ScanStatusEnum(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ModuleStatusEnum(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT_RUN"
    SKIPPED = "SKIPPED"


class ModuleProgress(BaseModel):
    status: ModuleStatusEnum = ModuleStatusEnum.QUEUED
    message: Optional[str] = None
    elapsed_seconds: float = 0.0
    items_analyzed: int = 0
    errors: List[str] = Field(default_factory=list)


class ScanModulesConfig(BaseModel):
    sast: bool = True
    secret_scanning: bool = True
    dependency_scanning: bool = True
    dast: bool = False
    llm_governance: bool = True
    ai_code_review: bool = True
    dast_target_url: Optional[str] = None


class LanguageStats(BaseModel):
    language: str
    files_count: int
    lines_of_code: int
    percentage: float


class ScanSummary(BaseModel):
    total_findings: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    scanners_used: List[str] = Field(default_factory=list)
    languages_detected: List[str] = Field(default_factory=list)
    files_analyzed: int = 0
    total_lines_of_code: int = 0
    risk_score: float = 0.0  # 0 to 100 security risk score


class Scan(BaseModel):
    id: str = Field(..., description="Unique scan ID (e.g. scan-abc123)")
    scan_id: Optional[str] = None
    project_name: str
    input_type: InputTypeEnum
    
    # Source metadata
    source_identifier: str  # Zip filename or Github repo URL
    branch_or_commit: Optional[str] = None
    commit_hash: Optional[str] = None
    workspace_path: Optional[str] = None
    
    # Configuration
    config: ScanModulesConfig = Field(default_factory=ScanModulesConfig)
    
    # Overall Status & Progress
    status: ScanStatusEnum = ScanStatusEnum.QUEUED
    progress_percentage: int = 0
    current_stage: str = "Initialized"
    error_message: Optional[str] = None
    
    # Module States
    module_sast: ModuleProgress = Field(default_factory=ModuleProgress)
    module_secrets: ModuleProgress = Field(default_factory=ModuleProgress)
    module_dependencies: ModuleProgress = Field(default_factory=ModuleProgress)
    module_dast: ModuleProgress = Field(default_factory=ModuleProgress)
    module_governance: ModuleProgress = Field(default_factory=ModuleProgress)
    module_ai_review: ModuleProgress = Field(default_factory=ModuleProgress)
    
    # Analysis Metrics
    languages: List[LanguageStats] = Field(default_factory=list)
    summary: ScanSummary = Field(default_factory=ScanSummary)
    
    # Logs & Timeline
    logs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.scan_id:
            self.scan_id = self.id

    model_config = ConfigDict(use_enum_values=True)


class GitHubScanRequest(BaseModel):
    repo_url: str
    branch: Optional[str] = None
    commit: Optional[str] = None
    auth_token: Optional[str] = None
    dast_target_url: Optional[str] = None
    enable_sast: bool = True
    enable_secrets: bool = True
    enable_dependencies: bool = True
    enable_dast: bool = False
    enable_governance: bool = True
    enable_ai_review: bool = True


class ScanFilterParams(BaseModel):
    severity: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = None
    scanner: Optional[str] = None
    status: Optional[str] = None
    search: Optional[str] = None
