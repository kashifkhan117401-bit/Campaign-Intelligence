import React, { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertCircle,
  ExternalLink,
  FileBarChart2,
  FlaskConical,
  Loader2,
  MessageSquare,
  Search,
  Sparkles,
  ThumbsUp,
  Trash2,
  Users,
  Youtube,
} from "lucide-react";
import { analysisApi, authApi } from "../services/api";
import type { IntegrationStatus, PaginatedComments, VideoAnalysis } from "../types";
import { DemoDataBanner, DisclaimerNote, EmptyState } from "../components/UI";
import { useToast } from "../contexts/ToastContext";
import { useDebounce } from "../hooks/useDebounce";
import { formatDate, formatNumber, getApiErrorMessage } from "../utils/format";

const SENTIMENT_COLORS = ["#10B981", "#F43F5E", "#F59E0B"];

export function YouTubeAnalyzerPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { notify } = useToast();

  const [urlInput, setUrlInput] = useState(searchParams.get("url") || "");
  const [maxComments, setMaxComments] = useState(500);
  const [useDemoFallback, setUseDemoFallback] = useState(false);
  const [integrations, setIntegrations] = useState<IntegrationStatus | null>(null);

  const [analyses, setAnalyses] = useState<VideoAnalysis[]>([]);
  const [activeAnalysis, setActiveAnalysis] = useState<VideoAnalysis | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Comments table state
  const [commentsPage, setCommentsPage] = useState<PaginatedComments | null>(null);
  const [sentimentFilter, setSentimentFilter] = useState<string>("");
  const [keywordFilter, setKeywordFilter] = useState<string>("");
  const debouncedKeyword = useDebounce(keywordFilter, 300);
  const [page, setPage] = useState(1);

  const loadList = useCallback(async () => {
    try {
      const [list, integ] = await Promise.all([analysisApi.list(), authApi.integrations()]);
      setAnalyses(list);
      setIntegrations(integ);
      if (!integ.youtube_api_configured && integ.allow_demo_mode) {
        setUseDemoFallback(true);
      }
      const requestedId = searchParams.get("analysisId");
      if (requestedId) {
        const match = list.find((a) => a.id === requestedId);
        if (match) setActiveAnalysis(match);
      } else if (list.length > 0 && !activeAnalysis) {
        setActiveAnalysis(list[0]);
      }
    } catch (err) {
      notify("error", "Could not load analyses", getApiErrorMessage(err));
    }
  }, [notify, searchParams]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void loadList();
  }, [loadList]);

  // Poll while pending/collecting/analyzing
  useEffect(() => {
    if (!activeAnalysis) return;
    if (!["pending", "collecting", "analyzing"].includes(activeAnalysis.status)) return;

    const timer = window.setInterval(async () => {
      try {
        const updated = await analysisApi.get(activeAnalysis.id);
        setActiveAnalysis(updated);
        setAnalyses((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
        if (updated.status === "completed") {
          notify("success", "Analysis complete", `Analyzed ${updated.analyzed_comments_count} comments.`);
        } else if (updated.status === "failed") {
          notify("error", "Analysis failed", updated.error_message || "See error details.");
        }
      } catch {
        // Ignore transient poll errors
      }
    }, 1800);

    return () => window.clearInterval(timer);
  }, [activeAnalysis, notify]);

  // Load comments when completed analysis or filters change
  useEffect(() => {
    if (!activeAnalysis || activeAnalysis.status !== "completed") {
      setCommentsPage(null);
      return;
    }
    let mounted = true;
    analysisApi
      .comments(activeAnalysis.id, {
        sentiment: sentimentFilter || undefined,
        keyword: debouncedKeyword || undefined,
        page,
        page_size: 20,
      })
      .then((res) => mounted && setCommentsPage(res))
      .catch(() => { });
    return () => {
      mounted = false;
    };
  }, [activeAnalysis, sentimentFilter, debouncedKeyword, page]);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;
    setSubmitting(true);
    try {
      const created = await analysisApi.start({
        youtube_url: urlInput.trim(),
        max_comments: maxComments,
        use_demo_fallback: useDemoFallback,
      });
      setActiveAnalysis(created);
      setAnalyses((prev) => [created, ...prev]);
      setSearchParams({ analysisId: created.id });
      notify("info", "Analysis started", "Collecting video metadata & public comments...");
    } catch (err) {
      notify("error", "Unable to start analysis", getApiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteAnalysis = async (id: string) => {
    try {
      await analysisApi.remove(id);
      const remaining = analyses.filter((a) => a.id !== id);
      setAnalyses(remaining);
      if (activeAnalysis?.id === id) {
        const next = remaining[0] || null;
        setActiveAnalysis(next);
        setPage(1);
        if (next) setSearchParams({ analysisId: next.id });
        else setSearchParams({});
      }
      notify("info", "Analysis deleted from history");
    } catch (err) {
      notify("error", "Delete failed", getApiErrorMessage(err));
    }
  };

  const handleClearAnalyses = async () => {
    if (!window.confirm("Delete all video analysis history? This will also remove linked PDF reports.")) return;
    try {
      await analysisApi.clearAll();
      setAnalyses([]);
      setActiveAnalysis(null);
      setCommentsPage(null);
      setSearchParams({});
      notify("info", "All analysis history cleared");
    } catch (err) {
      notify("error", "Could not clear history", getApiErrorMessage(err));
    }
  };

  const pieData = activeAnalysis
    ? [
      { name: "Positive", value: activeAnalysis.positive_pct },
      { name: "Negative", value: activeAnalysis.negative_pct },
      { name: "Neutral", value: activeAnalysis.neutral_pct },
    ]
    : [];

  const emotionData = activeAnalysis
    ? Object.entries(activeAnalysis.emotion_distribution_json || {}).map(([emotion, count]) => ({
      emotion: emotion.charAt(0).toUpperCase() + emotion.slice(1),
      count,
    }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">YouTube Sentiment Analysis Engine</h1>
        <p className="mt-1 text-sm text-slate-400">
          Collect up to 2,000 accessible public comments via YouTube Data API v3 and run batch AI sentiment, emotion,
          topic, and pain-point intelligence.
        </p>
      </div>

      {/* URL Submission Card */}
      <form onSubmit={handleAnalyze} className="tm-card p-5 space-y-4">
        <div className="grid gap-3 md:grid-cols-12">
          <div className="md:col-span-7">
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Public YouTube Video URL</label>
            <div className="relative">
              <Youtube className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-rose-400" />
              <input
                type="text"
                required
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/..."
                className="tm-input pl-9"
              />
            </div>
          </div>

          <div className="md:col-span-2">
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Max Comments</label>
            <select
              value={maxComments}
              onChange={(e) => setMaxComments(Number(e.target.value))}
              className="tm-input"
            >
              <option value={100}>Up to 100</option>
              <option value={500}>Up to 500</option>
              <option value={1000}>Up to 1,000</option>
              <option value={2000}>Up to 2,000</option>
            </select>
          </div>

          <div className="flex items-end md:col-span-3">
            <button type="submit" disabled={submitting} className="tm-btn-primary w-full py-2.5">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {submitting ? "Starting..." : "Run AI Analysis"}
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-800/80 pt-3 text-xs">
          <div className="flex items-center gap-2 text-slate-400">
            <span
              className={`h-2 w-2 rounded-full ${integrations?.youtube_api_configured ? "bg-emerald-400" : "bg-amber-400"
                }`}
            />
            <span>
              {integrations?.youtube_api_configured
                ? "YouTube Data API v3 connected (Live mode)"
                : "YOUTUBE_API_KEY not configured in .env — live fetching requires an API key"}
            </span>
          </div>

          {integrations && !integrations.youtube_api_configured && integrations.allow_demo_mode && (
            <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-amber-200">
              <input
                type="checkbox"
                checked={useDemoFallback}
                onChange={(e) => setUseDemoFallback(e.target.checked)}
                className="rounded border-amber-500 bg-slate-900 text-amber-500"
              />
              <FlaskConical className="h-3.5 w-3.5" />
              <span>Use visibly labeled Development Demo Mode</span>
            </label>
          )}
        </div>
      </form>

      {/* Saved Analyses Switcher */}
      {analyses.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Analysis History ({analyses.length})
            </span>
            <button
              type="button"
              onClick={() => void handleClearAnalyses()}
              className="inline-flex items-center gap-1 text-xs text-rose-400 hover:text-rose-300"
            >
              <Trash2 className="h-3.5 w-3.5" /> Clear History
            </button>
          </div>
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {analyses.slice(0, 12).map((a) => (
              <div
                key={a.id}
                onClick={() => {
                  setActiveAnalysis(a);
                  setPage(1);
                  setSearchParams({ analysisId: a.id });
                }}
                className={`flex shrink-0 cursor-pointer items-start gap-2 rounded-xl border px-3 py-2 text-left text-xs transition ${activeAnalysis?.id === a.id
                    ? "border-indigo-500 bg-indigo-500/15 text-white"
                    : "border-slate-800 bg-slate-900/70 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                  }`}
              >
                <div>
                  <p className="max-w-[190px] truncate font-medium">{a.video.title}</p>
                  <p className="text-[10px] text-slate-400">
                    {a.analyzed_comments_count} comments • {a.status}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    void handleDeleteAnalysis(a.id);
                  }}
                  className="rounded p-1 text-slate-500 hover:bg-rose-500/20 hover:text-rose-300"
                  aria-label="Delete analysis"
                  title="Delete analysis"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Analysis Detail */}
      {!activeAnalysis ? (
        <EmptyState
          icon={Youtube}
          title="Paste a YouTube URL to begin"
          description="Campaign Intelligence validates the URL, paginates up to 2,000 real comments, filters out prompt-injection payloads, and maps viewer sentiment, emotions, and pain points."
        />
      ) : ["pending", "collecting", "analyzing"].includes(activeAnalysis.status) ? (
        <div className="tm-card p-8 text-center">
          <Loader2 className="mx-auto h-10 w-10 animate-spin text-indigo-400" />
          <h3 className="mt-4 text-lg font-semibold text-white">{activeAnalysis.status_message}</h3>
          <p className="mt-1 text-xs text-slate-400">
            Collected {activeAnalysis.collected_comments_count} / {activeAnalysis.requested_max_comments} requested comments
          </p>
          <div className="mx-auto mt-5 h-2.5 w-full max-w-md overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 transition-all duration-500"
              style={{ width: `${activeAnalysis.progress_pct}%` }}
            />
          </div>
        </div>
      ) : activeAnalysis.status === "failed" ? (
        <div className="tm-card border-rose-500/40 p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-6 w-6 shrink-0 text-rose-400" />
            <div>
              <h3 className="text-base font-semibold text-white">Analysis Failed</h3>
              <p className="mt-1 text-sm text-rose-200">{activeAnalysis.error_message}</p>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <DemoDataBanner visible={activeAnalysis.is_demo_data} />

          {/* Video Header Card */}
          <div className="tm-card flex flex-col gap-5 p-5 lg:flex-row lg:items-center">
            <img
              src={activeAnalysis.video.thumbnail_url}
              alt={activeAnalysis.video.title}
              className="h-32 w-56 shrink-0 rounded-xl object-cover bg-slate-800"
            />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-lg font-bold text-white">{activeAnalysis.video.title}</h2>
                <a
                  href={activeAnalysis.video.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:underline"
                >
                  Open on YouTube <ExternalLink className="h-3 w-3" />
                </a>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                Channel: <span className="text-slate-200">{activeAnalysis.video.channel_title}</span> • Views:{" "}
                <span className="text-slate-200">{formatNumber(activeAnalysis.video.view_count)}</span> • Likes:{" "}
                <span className="text-slate-200">{formatNumber(activeAnalysis.video.like_count)}</span> • Collected:{" "}
                <span className="font-semibold text-indigo-300">
                  {formatNumber(activeAnalysis.collected_comments_count)} comments
                </span>
              </p>

              <div className="mt-4 flex flex-wrap gap-2.5">
                <button
                  onClick={() => navigate(`/audience?analysisId=${activeAnalysis.id}`)}
                  className="tm-btn-secondary text-xs"
                >
                  <Users className="h-3.5 w-3.5 text-cyan-400" /> Audience Intelligence
                </button>
                <button
                  onClick={() => navigate(`/content-studio?analysisId=${activeAnalysis.id}`)}
                  className="tm-btn-secondary text-xs"
                >
                  <Sparkles className="h-3.5 w-3.5 text-violet-400" /> Generate Content from Analysis
                </button>
                <button
                  onClick={() => navigate(`/reports?analysisId=${activeAnalysis.id}`)}
                  className="tm-btn-primary text-xs"
                >
                  <FileBarChart2 className="h-3.5 w-3.5" /> Export Executive PDF
                </button>
              </div>
            </div>
          </div>

          <DisclaimerNote text={activeAnalysis.ai_disclaimer} variant="info" />

          {/* Sentiment KPI Strip */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="tm-card p-4">
              <p className="text-xs text-slate-400">Comments Analyzed</p>
              <p className="mt-1 text-2xl font-bold text-white">{activeAnalysis.analyzed_comments_count}</p>
            </div>
            <div className="tm-card border-emerald-500/20 p-4">
              <p className="text-xs text-emerald-400">Positive Sentiment</p>
              <p className="mt-1 text-2xl font-bold text-emerald-300">{activeAnalysis.positive_pct}%</p>
              <p className="text-xs text-slate-400">{activeAnalysis.positive_count} comments</p>
            </div>
            <div className="tm-card border-rose-500/20 p-4">
              <p className="text-xs text-rose-400">Negative Sentiment</p>
              <p className="mt-1 text-2xl font-bold text-rose-300">{activeAnalysis.negative_pct}%</p>
              <p className="text-xs text-slate-400">{activeAnalysis.negative_count} comments</p>
            </div>
            <div className="tm-card border-amber-500/20 p-4">
              <p className="text-xs text-amber-400">Neutral Sentiment</p>
              <p className="mt-1 text-2xl font-bold text-amber-300">{activeAnalysis.neutral_pct}%</p>
              <p className="text-xs text-slate-400">{activeAnalysis.neutral_count} comments</p>
            </div>
          </div>

          {/* Charts Grid */}
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="tm-card p-5">
              <h3 className="mb-3 text-sm font-semibold text-white">Sentiment Distribution</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={55} outerRadius={88} paddingAngle={4}>
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={SENTIMENT_COLORS[i % SENTIMENT_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", borderRadius: 10 }} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="tm-card p-5">
              <h3 className="mb-3 text-sm font-semibold text-white">Emotion Distribution</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={emotionData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                    <XAxis dataKey="emotion" tick={{ fill: "#94A3B8", fontSize: 11 }} />
                    <YAxis tick={{ fill: "#94A3B8", fontSize: 11 }} />
                    <Tooltip contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", borderRadius: 10 }} />
                    <Bar dataKey="count" name="Comments" fill="#8B5CF6" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="tm-card p-5">
              <h3 className="mb-3 text-sm font-semibold text-white">Most Frequently Discussed Topics</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={activeAnalysis.topics_json.slice(0, 7)} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                    <XAxis type="number" tick={{ fill: "#94A3B8", fontSize: 11 }} />
                    <YAxis type="category" dataKey="topic" width={140} tick={{ fill: "#CBD5E1", fontSize: 11 }} />
                    <Tooltip contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", borderRadius: 10 }} />
                    <Bar dataKey="count" name="Mentions" fill="#06B6D4" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="tm-card p-5">
              <h3 className="mb-3 text-sm font-semibold text-white">Sentiment Trends Over Time</h3>
              {activeAnalysis.sentiment_trends_json.length > 1 ? (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={activeAnalysis.sentiment_trends_json}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="date" tick={{ fill: "#94A3B8", fontSize: 10 }} />
                      <YAxis tick={{ fill: "#94A3B8", fontSize: 11 }} />
                      <Tooltip contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", borderRadius: 10 }} />
                      <Legend />
                      <Line type="monotone" dataKey="positive" stroke="#10B981" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="negative" stroke="#F43F5E" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="neutral" stroke="#F59E0B" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-64 items-center justify-center text-xs text-slate-500">
                  Not enough multi-day comment timestamps to render a time-series trend.
                </div>
              )}
            </div>
          </div>

          {/* Keywords + Pain Points Ranking */}
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="tm-card p-5">
              <h3 className="mb-3 text-sm font-semibold text-white">Top Repeated Keywords</h3>
              <div className="flex flex-wrap gap-2">
                {activeAnalysis.keywords_json.slice(0, 20).map((kw) => (
                  <button
                    key={kw.keyword}
                    onClick={() => {
                      setKeywordFilter(kw.keyword);
                      setPage(1);
                    }}
                    className="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-xs text-indigo-200 hover:bg-indigo-500/20"
                  >
                    {kw.keyword} <span className="ml-1 text-indigo-400">({kw.count})</span>
                  </button>
                ))}
              </div>
            </div>

            <div className="tm-card p-5">
              <h3 className="mb-3 text-sm font-semibold text-white">Audience Pain Point Ranking</h3>
              <div className="space-y-3">
                {activeAnalysis.pain_points_json.slice(0, 6).map((p) => (
                  <div key={p.pain_point}>
                    <div className="mb-1 flex items-center justify-between text-xs">
                      <span className="font-medium text-slate-200">{p.pain_point}</span>
                      <span className="text-rose-300">
                        {p.mentions} mentions • Severity {p.severity_score}/100
                      </span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-amber-500 to-rose-500"
                        style={{ width: `${Math.min(100, p.severity_score)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Qualitative Insights Grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[
              { title: "Complaints", items: activeAnalysis.complaints_json, color: "text-rose-300" },
              { title: "Feature Requests & Suggestions", items: activeAnalysis.feature_requests_json, color: "text-cyan-300" },
              { title: "Frequently Asked Questions", items: activeAnalysis.faqs_json, color: "text-indigo-300" },
              { title: "Buying Objections", items: activeAnalysis.buying_objections_json, color: "text-amber-300" },
              { title: "Emerging Topics", items: activeAnalysis.emerging_topics_json, color: "text-violet-300" },
              { title: "Viewer Suggestions", items: activeAnalysis.suggestions_json, color: "text-emerald-300" },
            ].map((box) => (
              <div key={box.title} className="tm-card p-4">
                <h4 className={`text-xs font-semibold uppercase tracking-wider ${box.color}`}>{box.title}</h4>
                <ul className="mt-3 space-y-2 text-xs text-slate-300">
                  {box.items.length > 0 ? (
                    box.items.slice(0, 5).map((item, idx) => (
                      <li key={idx} className="rounded-lg bg-slate-900/70 p-2 leading-relaxed">
                        {item}
                      </li>
                    ))
                  ) : (
                    <li className="text-slate-500">None identified in this sample.</li>
                  )}
                </ul>
              </div>
            ))}
          </div>

          {/* Comments Explorer Table */}
          <div className="tm-card p-5">
            <div className="mb-4 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white">
                  Analyzed Comments ({commentsPage?.total ?? 0})
                </h3>
              </div>
              <div className="flex flex-wrap gap-2">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    value={keywordFilter}
                    onChange={(e) => {
                      setKeywordFilter(e.target.value);
                      setPage(1);
                    }}
                    placeholder="Filter by keyword..."
                    className="tm-input py-1.5 pl-8 text-xs sm:w-52"
                  />
                </div>
                <select
                  value={sentimentFilter}
                  onChange={(e) => {
                    setSentimentFilter(e.target.value);
                    setPage(1);
                  }}
                  className="tm-input py-1.5 text-xs sm:w-40"
                >
                  <option value="">All Sentiments</option>
                  <option value="positive">Positive</option>
                  <option value="negative">Negative</option>
                  <option value="neutral">Neutral</option>
                </select>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="pb-3 pr-4">Author</th>
                    <th className="pb-3 pr-4">Comment</th>
                    <th className="pb-3 pr-4">Sentiment</th>
                    <th className="pb-3 pr-4">Emotion</th>
                    <th className="pb-3 pr-4">Likes</th>
                    <th className="pb-3">Published</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {commentsPage?.items.map((c) => (
                    <tr key={c.id} className="hover:bg-slate-900/50">
                      <td className="py-3 pr-4 font-medium text-slate-200 whitespace-nowrap">
                        {c.author_display_name}
                      </td>
                      <td className="max-w-md py-3 pr-4 text-slate-300 leading-relaxed">{c.text}</td>
                      <td className="py-3 pr-4">
                        <span
                          className={`tm-badge ${c.sentiment === "positive"
                              ? "bg-emerald-500/15 text-emerald-300"
                              : c.sentiment === "negative"
                                ? "bg-rose-500/15 text-rose-300"
                                : "bg-amber-500/15 text-amber-300"
                            }`}
                        >
                          {c.sentiment}
                        </span>
                      </td>
                      <td className="py-3 pr-4 capitalize text-slate-300">{c.primary_emotion}</td>
                      <td className="py-3 pr-4 text-slate-300">
                        <span className="inline-flex items-center gap-1">
                          <ThumbsUp className="h-3 w-3 text-slate-500" /> {c.like_count}
                        </span>
                      </td>
                      <td className="py-3 whitespace-nowrap text-slate-400">{formatDate(c.published_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {commentsPage && commentsPage.total > commentsPage.page_size && (
              <div className="mt-4 flex items-center justify-between border-t border-slate-800 pt-3 text-xs text-slate-400">
                <span>
                  Page {commentsPage.page} of {Math.ceil(commentsPage.total / commentsPage.page_size)}
                </span>
                <div className="flex gap-2">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    className="tm-btn-secondary py-1.5 text-xs"
                  >
                    Previous
                  </button>
                  <button
                    disabled={page >= Math.ceil(commentsPage.total / commentsPage.page_size)}
                    onClick={() => setPage((p) => p + 1)}
                    className="tm-btn-secondary py-1.5 text-xs"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
