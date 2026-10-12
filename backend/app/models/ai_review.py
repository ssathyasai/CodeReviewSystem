from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReviewActionEnum(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    MARK_VERIFIED = "MARK_VERIFIED"
    PENDING = "PENDING"


class PatchSuggestion(BaseModel):
    id: str
    file_path: str
    line_start: int
    line_end: int
    original_code: str
    suggested_code: str
    diff_unified: str
    explanation: str
    safety_notes: str
    status: ReviewActionEnum = ReviewActionEnum.PENDING


class AiReviewItem(BaseModel):
    id: str
    scan_id: str
    file_path: str
    line_number: int
    title: str
    linked_finding_id: Optional[str] = None
    severity: str
    category: str
    explanation_simple: str
    root_cause: str
    patch: Optional[PatchSuggestion] = None
    maintainability_impact: str
    confidence_score: float = 0.95
    status: ReviewActionEnum = ReviewActionEnum.PENDING
    reviewer_comment: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AiReviewSummary(BaseModel):
    scan_id: str
    total_recommendations: int = 0
    approved_count: int = 0
    rejected_count: int = 0
    pending_count: int = 0
    model_used: str = "Local Security-Specialized Review Engine"
    overall_code_quality_grade: str = "B+"
    key_strengths: List[str] = Field(default_factory=list)
    top_risks: List[str] = Field(default_factory=list)
    recommendations: List[AiReviewItem] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
