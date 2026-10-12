from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DastRiskLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class DastAlert(BaseModel):
    id: str
    plugin_id: Optional[str] = None
    alert_name: str
    risk: DastRiskLevel
    confidence: str
    url: str
    param: Optional[str] = None
    attack_vector: Optional[str] = None
    evidence: Optional[str] = None
    description: str
    solution: str
    cwe_id: Optional[str] = None
    wasc_id: Optional[str] = None
    reference: Optional[str] = None


class DastEndpoint(BaseModel):
    url: str
    method: str = "GET"
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None
    alerts_count: int = 0


class DastScanResult(BaseModel):
    scan_id: str
    target_url: str
    is_authorized: bool = False
    authorization_method: str = "Pre-configured Dev / Whitelisted Domain"
    status: str = "COMPLETED"  # COMPLETED, BLOCKED, FAILED, NOT_RUN
    reason: Optional[str] = None
    spider_endpoints_found: int = 0
    endpoints: List[DastEndpoint] = Field(default_factory=list)
    alerts: List[DastAlert] = Field(default_factory=list)
    total_alerts: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    scan_duration_seconds: float = 0.0
    headers_analyzed: Dict[str, str] = Field(default_factory=dict)
    missing_security_headers: List[str] = Field(default_factory=list)
    ssl_tls_info: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
