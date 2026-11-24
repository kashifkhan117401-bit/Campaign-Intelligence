"""YouTube analysis, comments, and audience intelligence schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    youtube_url: str = Field(..., min_length=10, max_length=500)
    max_comments: int = Field(default=500, ge=10, le=2000)
    use_demo_fallback: bool = Field(
        default=False,
        description="Explicitly permit clearly labeled demo data when YouTube/AI API keys are unconfigured.",
    )


class YouTubeVideoSummary(BaseModel):
    id: str
    youtube_video_id: str
    url: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    thumbnail_url: str
    published_at: Optional[datetime] = None
    duration_iso: str
    view_count: int
    like_count: int
    comment_count: int
    tags_json: List[str] = []
    comments_disabled: bool
    is_demo_data: bool

    model_config = {"from_attributes": True}


class VideoAnalysisResponse(BaseModel):
    id: str
    status: str
    progress_pct: int
    status_message: str
    error_message: Optional[str] = None
    requested_max_comments: int
    collected_comments_count: int
    analyzed_comments_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_pct: float
    negative_pct: float
    neutral_pct: float
    emotion_distribution_json: Dict[str, int] = {}
    topics_json: List[Dict[str, Any]] = []
    keywords_json: List[Dict[str, Any]] = []
    pain_points_json: List[Dict[str, Any]] = []
    complaints_json: List[str] = []
    feature_requests_json: List[str] = []
    faqs_json: List[str] = []
    buying_objections_json: List[str] = []
    suggestions_json: List[str] = []
    emerging_topics_json: List[str] = []
    sentiment_trends_json: List[Dict[str, Any]] = []
    is_demo_data: bool
    ai_disclaimer: str
    completed_at: Optional[datetime] = None
    created_at: datetime
    video: YouTubeVideoSummary

    model_config = {"from_attributes": True}


class CommentItemResponse(BaseModel):
    id: str
    youtube_comment_id: str
    author_display_name: str
    text: str
    like_count: int
    reply_count: int
    published_at: Optional[datetime] = None
    sentiment: str
    confidence: float
    primary_emotion: str
    secondary_emotions: List[str] = []
    purchase_intent: bool
    is_complaint: bool
    is_feature_request: bool
    is_question: bool
    topics: List[str] = []
    keywords: List[str] = []


class PaginatedCommentsResponse(BaseModel):
    analysis_id: str
    total: int
    page: int
    page_size: int
    ai_disclaimer: str
    items: List[CommentItemResponse]


class AudienceInsightResponse(BaseModel):
    id: str
    analysis_id: str
    interests_json: List[str] = []
    expectations_json: List[str] = []
    common_problems_json: List[str] = []
    unanswered_questions_json: List[str] = []
    agreement_reasons_json: List[str] = []
    disagreement_reasons_json: List[str] = []
    main_frustrations_json: List[str] = []
    content_gaps_json: List[str] = []
    product_opportunities_json: List[str] = []
    customer_objections_json: List[str] = []
    marketing_angles_json: List[str] = []
    top_10_questions_json: List[Dict[str, Any]] = []
    opportunity_score: float
    opportunity_score_breakdown_json: Dict[str, Any] = {}
    opportunity_formula_doc: str
    is_demo_data: bool
    created_at: datetime

    model_config = {"from_attributes": True}
