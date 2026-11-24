"""AI Content Studio Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

ToneOption = Literal[
    "Professional",
    "Educational",
    "Conversational",
    "Persuasive",
    "Entertaining",
]


class ContentGenerateRequest(BaseModel):
    analysis_id: Optional[str] = None
    topic_brief: str = Field(default="", max_length=2000)
    tone: ToneOption = "Professional"
    target_audience: str = Field(default="", max_length=300)
    custom_instructions: str = Field(default="", max_length=1000)


class ContentUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=255)
    tone: Optional[ToneOption] = None
    status: Optional[Literal["draft", "saved", "archived"]] = None
    youtube_content_json: Optional[Dict[str, Any]] = None
    seo_json: Optional[Dict[str, Any]] = None
    social_media_json: Optional[Dict[str, Any]] = None
    content_strategy_json: Optional[Dict[str, Any]] = None


class GeneratedContentResponse(BaseModel):
    id: str
    analysis_id: Optional[str] = None
    title: str
    tone: str
    status: str
    topic_brief: str
    youtube_content_json: Dict[str, Any]
    seo_json: Dict[str, Any]
    social_media_json: Dict[str, Any]
    content_strategy_json: Dict[str, Any]
    disclaimer: str
    is_demo_data: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
