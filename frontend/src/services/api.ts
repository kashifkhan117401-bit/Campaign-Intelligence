import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import type {
  AdvertisingStrategy,
  AudienceInsight,
  BudgetTier,
  CampaignRecord,
  ConnectedChannel,
  DashboardOverview,
  GeneratedContent,
  IntegrationStatus,
  PaginatedComments,
  PDFReport,
  PublishingJob,
  TokenResponse,
  UploadedMedia,
  User,
  UserProfile,
  UserSettings,
  VideoAnalysis,
} from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

const ACCESS_KEY = "tubemind_access_token";
const REFRESH_KEY = "tubemind_refresh_token";

export function getStoredTokens() {
  return {
    accessToken: localStorage.getItem(ACCESS_KEY),
    refreshToken: localStorage.getItem(REFRESH_KEY),
  };
}

export function setStoredTokens(access: string, refresh: string) {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearStoredTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const { accessToken } = getStoredTokens();
  if (accessToken && config.headers) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = [];

function processQueue(error: unknown, token: string | null = null) {
  failedQueue.forEach((p) => {
    if (error) p.reject(error);
    else if (token) p.resolve(token);
  });
  failedQueue = [];
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && original && !original._retry && !original.url?.includes("/auth/")) {
      const { refreshToken } = getStoredTokens();
      if (!refreshToken) {
        clearStoredTokens();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (newToken: string) => {
              if (original.headers) original.headers.Authorization = `Bearer ${newToken}`;
              resolve(api(original));
            },
            reject,
          });
        });
      }

      original._retry = true;
      isRefreshing = true;

      try {
        const resp = await axios.post<TokenResponse>(`${API_BASE}/auth/refresh`, {
          refresh_token: refreshToken,
        });
        setStoredTokens(resp.data.access_token, resp.data.refresh_token);
        processQueue(null, resp.data.access_token);
        if (original.headers) original.headers.Authorization = `Bearer ${resp.data.access_token}`;
        return api(original);
      } catch (refreshErr) {
        processQueue(refreshErr, null);
        clearStoredTokens();
        window.location.href = "/login";
        return Promise.reject(refreshErr);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

// --- Auth & Profile ---
export const authApi = {
  captcha: () =>
    api
      .get<{ captcha_token: string; image_data_url: string; expires_in: number }>("/auth/captcha")
      .then((r) => r.data),
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    company_name?: string;
    captcha_token?: string;
    captcha_answer?: string;
    accepted_terms?: boolean;
  }) => api.post<TokenResponse>("/auth/register", payload).then((r) => r.data),
  login: (payload: {
    email: string;
    password: string;
    captcha_token?: string;
    captcha_answer?: string;
  }) => api.post<TokenResponse>("/auth/login", payload).then((r) => r.data),
  logout: (refresh_token?: string | null) =>
    api.post("/auth/logout", { refresh_token }).then((r) => r.data),
  me: () => api.get<User>("/auth/me").then((r) => r.data),
  updateProfile: (payload: Partial<UserProfile>) =>
    api.put<UserProfile>("/auth/profile", payload).then((r) => r.data),
  updateSettings: (payload: Partial<UserSettings>) =>
    api.put<UserSettings>("/auth/settings", payload).then((r) => r.data),
  integrations: () => api.get<IntegrationStatus>("/auth/integrations").then((r) => r.data),
  changePassword: (current_password: string, new_password: string) =>
    api.post<{ message: string }>("/auth/password/change", { current_password, new_password }).then((r) => r.data),
  exportPrivacyData: () => api.get<Record<string, unknown>>("/auth/privacy/export").then((r) => r.data),
  deleteAccount: (password: string, confirm_text: string) =>
    api.delete("/auth/account", { data: { password, confirm_text } }),
  requestPasswordReset: (email: string) =>
    api.post<{ message: string; dev_reset_token?: string }>("/auth/password-reset/request", { email }).then((r) => r.data),
  confirmPasswordReset: (token: string, new_password: string) =>
    api.post<{ message: string }>("/auth/password-reset/confirm", { token, new_password }).then((r) => r.data),
};

// --- YouTube Analysis ---
export const analysisApi = {
  start: (payload: { youtube_url: string; max_comments: number; use_demo_fallback: boolean }) =>
    api.post<VideoAnalysis>("/analyze", payload).then((r) => r.data),
  list: () => api.get<VideoAnalysis[]>("/analyze").then((r) => r.data),
  get: (analysisId: string) => api.get<VideoAnalysis>(`/analyze/${analysisId}`).then((r) => r.data),
  comments: (
    analysisId: string,
    params: { sentiment?: string; emotion?: string; keyword?: string; page?: number; page_size?: number }
  ) => api.get<PaginatedComments>(`/analyze/${analysisId}/comments`, { params }).then((r) => r.data),
  insights: (analysisId: string) =>
    api.get<AudienceInsight>(`/analyze/${analysisId}/insights`).then((r) => r.data),
  remove: (analysisId: string) => api.delete(`/analyze/${analysisId}`),
  clearAll: () => api.delete("/analyze"),
};

// --- AI Content Studio ---
export const contentApi = {
  generate: (payload: {
    analysis_id?: string | null;
    topic_brief?: string;
    tone: string;
    target_audience?: string;
    custom_instructions?: string;
  }) => api.post<GeneratedContent>("/content/generate", payload).then((r) => r.data),
  list: () => api.get<GeneratedContent[]>("/content").then((r) => r.data),
  update: (id: string, payload: Partial<GeneratedContent>) =>
    api.put<GeneratedContent>(`/content/${id}`, payload).then((r) => r.data),
  remove: (id: string) => api.delete(`/content/${id}`),
  clearAll: () => api.delete("/content"),
};

// --- Video Studio & YouTube Publishing ---
export const videoApi = {
  upload: (file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append("file", file);
    return api
      .post<UploadedMedia>("/videos/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (evt) => {
          if (evt.total && onProgress) {
            onProgress(Math.round((evt.loaded / evt.total) * 100));
          }
        },
      })
      .then((r) => r.data);
  },
  list: () => api.get<UploadedMedia[]>("/videos").then((r) => r.data),
  get: (videoId: string) => api.get<UploadedMedia>(`/videos/${videoId}`).then((r) => r.data),
  removeVideo: (videoId: string) => api.delete(`/videos/${videoId}`),
  clearVideos: () => api.delete("/videos"),
  analyze: (video_id: string, custom_notes = "") =>
    api.post<UploadedMedia>("/videos/analyze", { video_id, custom_notes }).then((r) => r.data),
  generateMetadata: (videoId: string, tone: string, target_keywords: string[] = []) =>
    api
      .post<UploadedMedia>(`/videos/${videoId}/generate-metadata`, { tone, target_keywords })
      .then((r) => r.data),
  connectYouTube: () =>
    api
      .get<{ configured: boolean; authorization_url: string | null; message: string; required_scopes?: string[] }>(
        "/youtube/connect"
      )
      .then((r) => r.data),
  channels: () => api.get<ConnectedChannel[]>("/youtube/channels").then((r) => r.data),
  disconnectChannel: (id: string) => api.delete(`/youtube/channels/${id}`),
  publish: (payload: {
    media_id: string;
    channel_id?: string | null;
    title: string;
    description: string;
    tags: string[];
    category_id: string;
    privacy_status: "private" | "unlisted" | "public";
    publish_action: "draft" | "upload" | "schedule";
    scheduled_publish_at?: string | null;
    pinned_comment: string;
    user_confirmed: boolean;
  }) => api.post<PublishingJob>("/youtube/publish", payload).then((r) => r.data),
  jobs: () => api.get<PublishingJob[]>("/youtube/jobs").then((r) => r.data),
  jobStatus: (jobId: string) =>
    api.get<PublishingJob>(`/youtube/publishing-status/${jobId}`).then((r) => r.data),
  rescheduleJob: (jobId: string, scheduled_publish_at: string) =>
    api.patch<PublishingJob>(`/youtube/jobs/${jobId}/schedule`, { scheduled_publish_at }).then((r) => r.data),
  cancelJob: (jobId: string) => api.delete(`/youtube/jobs/${jobId}`),
  clearJobs: () => api.delete("/youtube/jobs"),
};

// --- Ads Strategy ---
export const adsApi = {
  estimateBudget: (payload: {
    available_budget: number;
    campaign_duration_days: number;
    currency: string;
    target_country: string;
    industry_niche: string;
    marketing_objective: string;
    custom_cpv?: number;
    custom_cpm?: number;
    custom_ctr?: number;
  }) =>
    api
      .post<{
        currency: string;
        campaign_duration_days: number;
        formula_note: string;
        is_illustrative_estimate: boolean;
        disclaimer: string;
        tiers: BudgetTier[];
      }>("/ads/budget-estimate", payload)
      .then((r) => r.data),
  createStrategy: (payload: {
    campaign_name: string;
    analysis_id?: string | null;
    media_id?: string | null;
    video_context: string;
    target_country: string;
    target_audience: string;
    industry_niche: string;
    marketing_objective: string;
    campaign_duration_days: number;
    available_budget: number;
    currency: string;
    custom_cpv?: number;
    custom_cpm?: number;
    custom_ctr?: number;
  }) => api.post<AdvertisingStrategy>("/ads/strategy", payload).then((r) => r.data),
  history: () => api.get<AdvertisingStrategy[]>("/ads/history").then((r) => r.data),
  remove: (id: string) => api.delete(`/ads/history/${id}`),
  clearAll: () => api.delete("/ads/history"),
};

// --- Reports ---
export const reportsApi = {
  generate: (payload: {
    analysis_id: string;
    content_id?: string | null;
    strategy_id?: string | null;
    title?: string;
  }) => api.post<PDFReport>("/reports/generate", payload).then((r) => r.data),
  list: () => api.get<PDFReport[]>("/reports").then((r) => r.data),
  regenerate: (reportId: string) =>
    api.post<PDFReport>(`/reports/${reportId}/regenerate`).then((r) => r.data),
  downloadBlob: (reportId: string) =>
    api.get<Blob>(`/reports/${reportId}/download`, { responseType: "blob" }).then((r) => r.data),
  remove: (reportId: string) => api.delete(`/reports/${reportId}`),
  clearAll: () => api.delete("/reports"),
};

// --- Dashboard ---
export const dashboardApi = {
  overview: () => api.get<DashboardOverview>("/dashboard/overview").then((r) => r.data),
  activity: (record_type?: string) =>
    api
      .get<{ items: CampaignRecord[]; total: number }>("/dashboard/activity", {
        params: record_type ? { record_type } : undefined,
      })
      .then((r) => r.data),
  removeActivity: (recordId: string) => api.delete(`/dashboard/activity/${recordId}`),
  clearActivity: (record_type?: string) =>
    api.delete("/dashboard/activity", {
      params: record_type ? { record_type } : undefined,
    }),
};
