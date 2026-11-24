"""Advertising strategy and budget planning schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

MarketingObjective = Literal[
    "Brand awareness",
    "Reach",
    "Video views",
    "Website traffic",
    "Lead generation",
    "Product promotion",
    "Conversions",
]


class AdsStrategyRequest(BaseModel):
    campaign_name: str = Field(..., min_length=2, max_length=200)
    analysis_id: Optional[str] = None
    media_id: Optional[str] = None
    video_context: str = Field(..., min_length=10, max_length=3000)
    target_country: str = Field(..., min_length=2, max_length=100)
    target_audience: str = Field(..., min_length=3, max_length=300)
    industry_niche: str = Field(..., min_length=2, max_length=150)
    marketing_objective: MarketingObjective
    campaign_duration_days: int = Field(..., ge=3, le=365)
    available_budget: float = Field(..., gt=10, le=10_000_000)
    currency: str = Field(default="USD", min_length=3, max_length=10)
    custom_cpv: Optional[float] = Field(default=None, gt=0.001, le=5.0)
    custom_cpm: Optional[float] = Field(default=None, gt=0.5, le=200.0)
    custom_ctr: Optional[float] = Field(default=None, gt=0.001, le=0.3)


class BudgetEstimateRequest(BaseModel):
    available_budget: float = Field(..., gt=10, le=10_000_000)
    campaign_duration_days: int = Field(..., ge=3, le=365)
    currency: str = Field(default="USD", min_length=3, max_length=10)
    target_country: str = Field(default="United States", max_length=100)
    industry_niche: str = Field(default="Technology & SaaS", max_length=150)
    marketing_objective: MarketingObjective = "Video views"
    custom_cpv: Optional[float] = Field(default=None, gt=0.001, le=5.0)
    custom_cpm: Optional[float] = Field(default=None, gt=0.5, le=200.0)
    custom_ctr: Optional[float] = Field(default=None, gt=0.001, le=0.3)


class BudgetTierEstimate(BaseModel):
    id: Optional[str] = None
    tier: str
    currency: str
    campaign_duration_days: int
    daily_budget: float
    total_budget: float
    assumed_cpv: float
    assumed_cpm: float
    assumed_ctr: float
    estimated_impressions: int
    estimated_views: int
    estimated_clicks: int
    estimated_reach: int
    assumptions_json: Dict[str, Any] = {}
    disclaimer: str

    model_config = {"from_attributes": True}


class BudgetEstimateResponse(BaseModel):
    currency: str
    campaign_duration_days: int
    formula_note: str
    is_illustrative_estimate: bool = True
    disclaimer: str
    tiers: List[BudgetTierEstimate]


class AdvertisingStrategyResponse(BaseModel):
    id: str
    analysis_id: Optional[str] = None
    media_id: Optional[str] = None
    campaign_name: str
    video_context: str
    target_country: str
    target_audience: str
    industry_niche: str
    marketing_objective: str
    campaign_duration_days: int
    available_budget: float
    currency: str
    recommended_objective: str
    audience_segments_json: List[str] = []
    geographic_targeting_json: Dict[str, Any] = {}
    audience_interests_json: List[str] = []
    campaign_type_and_format: str
    placement_strategy_json: List[str] = []
    suggested_daily_budget: float
    suggested_total_budget: float
    creative_recommendations_json: List[str] = []
    ab_testing_ideas_json: List[str] = []
    optimization_strategy_json: List[str] = []
    executive_report: str
    disclaimer: str
    is_demo_data: bool
    budget_estimates: List[BudgetTierEstimate] = []
    created_at: datetime

    model_config = {"from_attributes": True}
