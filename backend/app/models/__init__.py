"""Export all SQLAlchemy models so Alembic & metadata creation discover them."""
from app.models.ads import AdvertisingStrategy, BudgetEstimate
from app.models.analysis import (
    AudienceInsight,
    Comment,
    CommentSentimentResult,
    VideoAnalysis,
    YouTubeVideo,
)
from app.models.content import GeneratedContent, PublishingJob, UploadedMedia
from app.models.reporting import APIUsageLog, CampaignRecord, PDFReport
from app.models.user import (
    ConnectedYouTubeChannel,
    RefreshToken,
    User,
    UserProfile,
    UserSettings,
)

__all__ = [
    "User",
    "UserProfile",
    "RefreshToken",
    "UserSettings",
    "ConnectedYouTubeChannel",
    "YouTubeVideo",
    "VideoAnalysis",
    "Comment",
    "CommentSentimentResult",
    "AudienceInsight",
    "GeneratedContent",
    "UploadedMedia",
    "PublishingJob",
    "AdvertisingStrategy",
    "BudgetEstimate",
    "PDFReport",
    "CampaignRecord",
    "APIUsageLog",
]
