export interface UserProfile {
  full_name: string;
  company_name: string;
  job_title: string;
  avatar_url: string;
  bio: string;
  niche: string;
  primary_goal: string;
  onboarding_completed: boolean;
}

export interface UserSettings {
  default_tone: string;
  default_currency: string;
  preferred_llm_model: string;
  email_notifications: boolean;
  demo_mode_enabled: boolean;
  benchmark_cpv: number;
  benchmark_cpm: number;
  benchmark_ctr: number;
}

export interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  profile: UserProfile | null;
  settings: UserSettings | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface IntegrationStatus {
  ai_configured: boolean;
  gemini_configured: boolean;
  openai_configured: boolean;
  youtube_api_configured: boolean;
  google_oauth_configured: boolean;
  ffmpeg_available: boolean;
  allow_demo_mode: boolean;
  llm_provider: string;
  llm_model: string;
}

export interface YouTubeVideoSummary {
  id: string;
  youtube_video_id: string;
  url: string;
  title: string;
  description: string;
  channel_id: string;
  channel_title: string;
  thumbnail_url: string;
  published_at: string | null;
  duration_iso: string;
  view_count: number;
  like_count: number;
  comment_count: number;
  tags_json: string[];
  comments_disabled: boolean;
  is_demo_data: boolean;
}

export interface VideoAnalysis {
  id: string;
  status: "pending" | "collecting" | "analyzing" | "completed" | "failed" | string;
  progress_pct: number;
  status_message: string;
  error_message: string | null;
  requested_max_comments: number;
  collected_comments_count: number;
  analyzed_comments_count: number;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  positive_pct: number;
  negative_pct: number;
  neutral_pct: number;
  emotion_distribution_json: Record<string, number>;
  topics_json: { topic: string; count: number; share_pct: number }[];
  keywords_json: { keyword: string; count: number }[];
  pain_points_json: { pain_point: string; mentions: number; severity_score: number }[];
  complaints_json: string[];
  feature_requests_json: string[];
  faqs_json: string[];
  buying_objections_json: string[];
  suggestions_json: string[];
  emerging_topics_json: string[];
  sentiment_trends_json: {
    date: string;
    positive: number;
    negative: number;
    neutral: number;
    total: number;
  }[];
  is_demo_data: boolean;
  ai_disclaimer: string;
  completed_at: string | null;
  created_at: string;
  video: YouTubeVideoSummary;
}

export interface CommentItem {
  id: string;
  youtube_comment_id: string;
  author_display_name: string;
  text: string;
  like_count: number;
  reply_count: number;
  published_at: string | null;
  sentiment: "positive" | "negative" | "neutral" | string;
  confidence: number;
  primary_emotion: string;
  secondary_emotions: string[];
  purchase_intent: boolean;
  is_complaint: boolean;
  is_feature_request: boolean;
  is_question: boolean;
  topics: string[];
  keywords: string[];
}

export interface PaginatedComments {
  analysis_id: string;
  total: number;
  page: number;
  page_size: number;
  ai_disclaimer: string;
  items: CommentItem[];
}

export interface AudienceInsight {
  id: string;
  analysis_id: string;
  interests_json: string[];
  expectations_json: string[];
  common_problems_json: string[];
  unanswered_questions_json: string[];
  agreement_reasons_json: string[];
  disagreement_reasons_json: string[];
  main_frustrations_json: string[];
  content_gaps_json: string[];
  product_opportunities_json: string[];
  customer_objections_json: string[];
  marketing_angles_json: string[];
  top_10_questions_json: {
    rank: number;
    question: string;
    audience_intent: string;
    suggested_video_angle: string;
  }[];
  opportunity_score: number;
  opportunity_score_breakdown_json: Record<string, any>;
  opportunity_formula_doc: string;
  is_demo_data: boolean;
  created_at: string;
}

export interface GeneratedContent {
  id: string;
  analysis_id: string | null;
  title: string;
  tone: string;
  status: string;
  topic_brief: string;
  youtube_content_json: {
    title_options: string[];
    hooks: string[];
    script: {
      introduction: string;
      main_sections: { heading: string; talking_points: string[]; script_body: string }[];
      conclusion: string;
      call_to_action: string;
    };
  };
  seo_json: {
    description: string;
    hashtags: string[];
    tags: string[];
    primary_keyword: string;
    secondary_keywords: string[];
    search_intent: string;
    title_variations: string[];
  };
  social_media_json: {
    youtube_shorts_scripts: { title: string; hook: string; body: string; cta: string }[];
    instagram_reels_captions: string[];
    facebook_post: string;
    linkedin_post: string;
    x_post: string;
  };
  content_strategy_json: {
    future_video_ideas: { title: string; angle: string; target_pain_point: string }[];
    content_calendar: { week: string; format: string; topic: string; goal: string }[];
    publishing_frequency: string;
    audience_recommendations: string[];
  };
  disclaimer: string;
  is_demo_data: boolean;
  created_at: string;
  updated_at: string;
}

export interface UploadedMedia {
  id: string;
  original_filename: string;
  mime_type: string;
  file_size_bytes: number;
  duration_seconds: number;
  width: number;
  height: number;
  aspect_ratio: string;
  frame_rate: number;
  audio_codec: string;
  audio_channels: number;
  audio_sample_rate: number;
  metadata_source: string;
  frames_json: { index: number; timestamp_seconds: number; timestamp_label: string; path: string }[];
  transcript_text: string;
  transcript_segments_json: { start: number; end: number; timestamp: string; text: string }[];
  content_analysis_json: {
    main_subject?: string;
    topics_covered?: string[];
    important_moments?: { timestamp: string; description: string }[];
    target_audience?: string;
    video_objective?: string;
    visual_notes?: string;
  };
  generated_metadata_json: {
    titles?: string[];
    description?: string;
    hashtags?: string[];
    tags?: string[];
    chapters?: { timestamp: string; title: string }[];
    thumbnail_concepts?: { concept: string; overlay_text: string }[];
    pinned_comment?: string;
    call_to_action?: string;
    category_suggestion?: { id: string; name: string };
    audience_targeting?: string[];
  };
  analysis_status: string;
  error_message: string | null;
  is_demo_data: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConnectedChannel {
  id: string;
  channel_id: string;
  channel_title: string;
  channel_thumbnail: string;
  subscriber_count: number;
  scopes: string;
  is_active: boolean;
  is_demo_connection: boolean;
  created_at: string;
}

export interface PublishingJob {
  id: string;
  media_id: string;
  channel_id: string | null;
  status: string;
  privacy_status: string;
  scheduled_publish_at: string | null;
  title: string;
  description: string;
  tags_json: string[];
  category_id: string;
  pinned_comment: string;
  upload_progress_pct: number;
  bytes_uploaded: number;
  youtube_video_id: string | null;
  youtube_video_url: string | null;
  user_confirmed: boolean;
  confirmed_at: string | null;
  error_message: string | null;
  created_at: string;
}

export interface BudgetTier {
  id?: string;
  tier: "low" | "balanced" | "aggressive" | string;
  currency: string;
  campaign_duration_days: number;
  daily_budget: number;
  total_budget: number;
  assumed_cpv: number;
  assumed_cpm: number;
  assumed_ctr: number;
  estimated_impressions: number;
  estimated_views: number;
  estimated_clicks: number;
  estimated_reach: number;
  assumptions_json: Record<string, any>;
  disclaimer: string;
}

export interface AdvertisingStrategy {
  id: string;
  analysis_id: string | null;
  media_id: string | null;
  campaign_name: string;
  video_context: string;
  target_country: string;
  target_audience: string;
  industry_niche: string;
  marketing_objective: string;
  campaign_duration_days: number;
  available_budget: number;
  currency: string;
  recommended_objective: string;
  audience_segments_json: string[];
  geographic_targeting_json: Record<string, any>;
  audience_interests_json: string[];
  campaign_type_and_format: string;
  placement_strategy_json: string[];
  suggested_daily_budget: number;
  suggested_total_budget: number;
  creative_recommendations_json: string[];
  ab_testing_ideas_json: string[];
  optimization_strategy_json: string[];
  executive_report: string;
  disclaimer: string;
  is_demo_data: boolean;
  budget_estimates: BudgetTier[];
  created_at: string;
}

export interface PDFReport {
  id: string;
  analysis_id: string;
  content_id: string | null;
  strategy_id: string | null;
  title: string;
  file_size_bytes: number;
  page_count: number;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignRecord {
  id: string;
  analysis_id: string | null;
  content_id: string | null;
  strategy_id: string | null;
  publishing_job_id: string | null;
  report_id: string | null;
  name: string;
  record_type: string;
  status: string;
  summary: string;
  metadata_json: Record<string, any>;
  created_at: string;
}

export interface DashboardOverview {
  total_videos_analyzed: number;
  total_comments_analyzed: number;
  avg_positive_sentiment: number;
  content_generated_count: number;
  reports_created_count: number;
  published_videos_count: number;
  active_ad_strategies_count: number;
  recent_analyses: {
    id: string;
    status: string;
    progress_pct: number;
    analyzed_comments_count: number;
    positive_pct: number;
    negative_pct: number;
    neutral_pct: number;
    is_demo_data: boolean;
    created_at: string;
    video_title: string;
    thumbnail_url: string;
    channel_title: string;
    youtube_video_id: string;
  }[];
  sentiment_history: {
    label: string;
    positive: number;
    negative: number;
    neutral: number;
    comments: number;
  }[];
  content_performance_mix: { category: string; count: number }[];
  integrations: {
    ai_configured: boolean;
    gemini_configured: boolean;
    openai_configured: boolean;
    youtube_api_configured: boolean;
    google_oauth_configured: boolean;
    ffmpeg_available: boolean;
    allow_demo_mode: boolean;
    llm_provider?: string;
    llm_model?: string;
  };
}
