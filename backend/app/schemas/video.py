"""Video upload studio and YouTube OAuth publishing schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class VideoAnalyzeRequest(BaseModel):
    video_id: str
    custom_notes: str = Field(default="", max_length=1500)


class GenerateMetadataRequest(BaseModel):
    tone: str = Field(default="Professional", max_length=40)
    target_keywords: List[str] = Field(default_factory=list)


class UploadedMediaResponse(BaseModel):
    id: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    duration_seconds: float
    width: int
    height: int
    aspect_ratio: str
    frame_rate: float
    audio_codec: str
    audio_channels: int
    audio_sample_rate: int
    metadata_source: str
    frames_json: List[Dict[str, Any]] = []
    transcript_text: str
    transcript_segments_json: List[Dict[str, Any]] = []
    content_analysis_json: Dict[str, Any] = {}
    generated_metadata_json: Dict[str, Any] = {}
    analysis_status: str
    error_message: Optional[str] = None
    is_demo_data: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConnectedChannelResponse(BaseModel):
    id: str
    channel_id: str
    channel_title: str
    channel_thumbnail: str
    subscriber_count: int
    scopes: str
    is_active: bool
    is_demo_connection: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class YouTubePublishRequest(BaseModel):
    media_id: str
    channel_id: Optional[str] = None
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(default="", max_length=5000)
    tags: List[str] = Field(default_factory=list)
    category_id: str = Field(default="22", max_length=20)
    privacy_status: Literal["private", "unlisted", "public"] = "private"
    publish_action: Literal["draft", "upload", "schedule"] = "draft"
    scheduled_publish_at: Optional[datetime] = None
    pinned_comment: str = Field(default="", max_length=2000)
    user_confirmed: bool = Field(
        default=False,
        description="Must be explicitly true before any live YouTube upload or public publish.",
    )


class RescheduleJobRequest(BaseModel):
    scheduled_publish_at: datetime


class PublishingJobResponse(BaseModel):
    id: str
    media_id: str
    channel_id: Optional[str] = None
    status: str
    privacy_status: str
    scheduled_publish_at: Optional[datetime] = None
    title: str
    description: str
    tags_json: List[str] = []
    category_id: str
    pinned_comment: str
    upload_progress_pct: int
    bytes_uploaded: int
    youtube_video_id: Optional[str] = None
    youtube_video_url: Optional[str] = None
    user_confirmed: bool
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    api_response_json: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
