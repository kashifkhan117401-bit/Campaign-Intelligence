"""PDF reports, campaign history, and dashboard overview schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    analysis_id: str
    content_id: Optional[str] = None
    strategy_id: Optional[str] = None
    title: Optional[str] = Field(default=None, max_length=255)


class PDFReportResponse(BaseModel):
    id: str
    analysis_id: str
    content_id: Optional[str] = None
    strategy_id: Optional[str] = None
    title: str
    file_size_bytes: int
    page_count: int
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CampaignRecordResponse(BaseModel):
    id: str
    analysis_id: Optional[str] = None
    content_id: Optional[str] = None
    strategy_id: Optional[str] = None
    publishing_job_id: Optional[str] = None
    report_id: Optional[str] = None
    name: str
    record_type: str
    status: str
    summary: str
    metadata_json: Dict[str, Any] = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardOverviewResponse(BaseModel):
    total_videos_analyzed: int
    total_comments_analyzed: int
    avg_positive_sentiment: float
    content_generated_count: int
    reports_created_count: int
    published_videos_count: int
    active_ad_strategies_count: int
    recent_analyses: List[Dict[str, Any]]
    sentiment_history: List[Dict[str, Any]]
    content_performance_mix: List[Dict[str, Any]]
    integrations: Dict[str, Any]


class DashboardActivityResponse(BaseModel):
    items: List[CampaignRecordResponse]
    total: int
