# TubeMind AI — REST API Reference

Interactive OpenAPI / Swagger UI is served live at `GET /docs` and `GET /redoc`.
All protected routes require `Authorization: Bearer <access_token>`.

## Authentication
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Register a new user, create default profile & settings, return JWT pair |
| `POST` | `/api/auth/login` | Authenticate email + password, return JWT access & refresh tokens |
| `POST` | `/api/auth/refresh` | Rotate refresh token and issue a fresh JWT pair |
| `POST` | `/api/auth/logout` | Revoke active refresh token(s) |
| `POST` | `/api/auth/password-reset/request` | Generate time-limited password reset token |
| `POST` | `/api/auth/password-reset/confirm` | Confirm password reset token and update password |
| `GET` | `/api/auth/me` | Fetch authenticated user, profile, and workspace settings |
| `PUT` | `/api/auth/profile` | Update profile fields and onboarding status |
| `PUT` | `/api/auth/settings` | Update tone, currency, and advertising benchmark defaults |
| `GET` | `/api/auth/integrations` | Check server configuration state for Gemini/OpenAI, YouTube API, OAuth, and FFmpeg |

## YouTube Sentiment Analysis & Audience Intelligence
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/analyze` | Validate YouTube URL and enqueue background comment collection (up to 2,000) & batch AI analysis |
| `GET` | `/api/analyze` | List current user's video analyses |
| `GET` | `/api/analyze/{analysis_id}` | Poll progress or retrieve completed sentiment, emotions, topics, keywords & pain points |
| `GET` | `/api/analyze/{analysis_id}/comments` | Paginated comments table with `sentiment`, `emotion`, and `keyword` filters |
| `GET` | `/api/analyze/{analysis_id}/insights` | Retrieve Audience Intelligence report, Top 10 Questions, and transparent Opportunity Score |

## AI Content Studio
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/content/generate` | Generate full YouTube script, SEO pack, social media suite & 4-week calendar |
| `GET` | `/api/content` | List saved content packs |
| `GET` | `/api/content/{content_id}` | Get single content pack |
| `PUT` | `/api/content/{content_id}` | Edit and save content draft |
| `DELETE` | `/api/content/{content_id}` | Delete content pack |

## Video Upload Studio & YouTube Publishing
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/videos/upload` | Upload video file (MIME + header validation, FFprobe metadata extraction) |
| `GET` | `/api/videos` | List uploaded videos |
| `POST` | `/api/videos/analyze` | Sample keyframes (FFmpeg), transcribe audio (Gemini/Whisper), analyze video topics & moments |
| `GET` | `/api/videos/{video_id}` | Get uploaded media details |
| `POST` | `/api/videos/{video_id}/generate-metadata` | Generate 5 titles, description, chapters, tags, hashtags & thumbnail concepts |
| `GET` | `/api/youtube/connect` | Get Google OAuth 2.0 consent URL or clear missing-configuration guidance |
| `GET` | `/api/youtube/callback` | Exchange OAuth code, encrypt tokens with Fernet, and store channel |
| `GET` | `/api/youtube/channels` | List connected YouTube channels |
| `DELETE` | `/api/youtube/channels/{channel_id}` | Disconnect channel |
| `POST` | `/api/youtube/publish` | Save draft or enqueue explicitly confirmed YouTube Data API resumable upload |
| `GET` | `/api/youtube/jobs` | List user's publishing jobs |
| `GET` | `/api/youtube/publishing-status/{job_id}` | Check real-time upload progress and verified YouTube video URL |

## Advertising Strategy & Budget Planner
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/ads/budget-estimate` | Calculate illustrative Low, Balanced & Aggressive tiers (`Views = Budget / CPV`) |
| `POST` | `/api/ads/strategy` | Generate & store 12-part YouTube Ads strategy + 3 budget tiers |
| `GET` | `/api/ads/history` | List saved advertising strategies |
| `DELETE` | `/api/ads/history/{strategy_id}` | Delete an advertising strategy |

## PDF Reports & Dashboard
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/reports/generate` | Build 18-section ReportLab PDF combining analysis, insights, content & ads |
| `GET` | `/api/reports` | List generated PDF reports |
| `GET` | `/api/reports/{report_id}/download` | Stream downloadable PDF file |
| `POST` | `/api/reports/{report_id}/regenerate` | Regenerate report with incremented version |
| `GET` | `/api/dashboard/overview` | Aggregated KPIs, recent analyses, sentiment history & content mix |
| `GET` | `/api/dashboard/activity` | Filterable campaign history log |
