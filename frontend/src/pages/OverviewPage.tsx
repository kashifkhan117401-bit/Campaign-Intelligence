import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowUpRight,
  CheckCircle2,
  Clock,
  FileBarChart2,
  Film,
  Megaphone,
  MessageSquareText,
  Sparkles,
  TrendingUp,
  Upload,
  Youtube,
} from "lucide-react";
import { dashboardApi } from "../services/api";
import type { CampaignRecord, DashboardOverview } from "../types";
import { EmptyState, SkeletonCard, StatCard } from "../components/UI";
import { formatDate, formatNumber, getApiErrorMessage } from "../utils/format";
import { useToast } from "../contexts/ToastContext";

export function OverviewPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [activity, setActivity] = useState<CampaignRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const { notify } = useToast();

  useEffect(() => {
    let active = true;
    Promise.all([dashboardApi.overview(), dashboardApi.activity()])
      .then(([ov, act]) => {
        if (!active) return;
        setOverview(ov);
        setActivity(act.items.slice(0, 8));
      })
      .catch((err) => notify("error", "Failed to load dashboard", getApiErrorMessage(err)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [notify]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <SkeletonCard className="h-72" />
          <SkeletonCard className="h-72" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header & Quick Actions */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Intelligence Overview</h1>
          <p className="mt-1 text-sm text-slate-400">
            Real-time YouTube audience sentiment, content automation, and campaign performance.
          </p>
        </div>
        <div className="flex flex-wrap gap-2.5">
          <button onClick={() => navigate("/analyzer")} className="tm-btn-primary">
            <Youtube className="h-4 w-4" />
            Analyze Video
          </button>
          <button onClick={() => navigate("/content-studio")} className="tm-btn-secondary">
            <Sparkles className="h-4 w-4 text-violet-400" />
            Generate Content
          </button>
          <button onClick={() => navigate("/video-studio")} className="tm-btn-secondary">
            <Upload className="h-4 w-4 text-cyan-400" />
            Upload Video
          </button>
        </div>
      </div>

      {/* KPI Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Videos Analyzed"
          value={formatNumber(overview?.total_videos_analyzed)}
          subtext="Public YouTube videos processed"
          icon={Youtube}
          accent="indigo"
        />
        <StatCard
          label="Comments Analyzed"
          value={formatNumber(overview?.total_comments_analyzed)}
          subtext="Real collected audience comments"
          icon={MessageSquareText}
          accent="cyan"
        />
        <StatCard
          label="Avg Positive Sentiment"
          value={`${overview?.avg_positive_sentiment ?? 0}%`}
          subtext="Across completed AI analyses"
          icon={TrendingUp}
          accent="emerald"
        />
        <StatCard
          label="Content Packs Generated"
          value={formatNumber(overview?.content_generated_count)}
          subtext="Scripts, SEO packs & Shorts"
          icon={Sparkles}
          accent="violet"
        />
        <StatCard
          label="PDF Reports Created"
          value={formatNumber(overview?.reports_created_count)}
          subtext="18-section executive exports"
          icon={FileBarChart2}
          accent="amber"
        />
        <StatCard
          label="Published / Scheduled"
          value={formatNumber(overview?.published_videos_count)}
          subtext={`${overview?.active_ad_strategies_count ?? 0} YouTube Ads strategies saved`}
          icon={Film}
          accent="rose"
        />
      </div>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="tm-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">Sentiment Across Analyzed Videos</h2>
              <p className="text-xs text-slate-400">Positive vs. Negative vs. Neutral share (%)</p>
            </div>
          </div>
          {overview && overview.sentiment_history.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={overview.sentiment_history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                  <XAxis dataKey="label" tick={{ fill: "#94A3B8", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#94A3B8", fontSize: 11 }} unit="%" />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", borderRadius: 12 }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="positive" name="Positive %" fill="#10B981" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="neutral" name="Neutral %" fill="#F59E0B" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="negative" name="Negative %" fill="#F43F5E" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex h-64 flex-col items-center justify-center text-center text-xs text-slate-400">
              <p>Run your first YouTube analysis to visualize sentiment trends here.</p>
              <button onClick={() => navigate("/analyzer")} className="tm-btn-secondary mt-3 text-xs">
                Open YouTube Analyzer
              </button>
            </div>
          )}
        </div>

        <div className="tm-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-white">Workspace Output Breakdown</h2>
              <p className="text-xs text-slate-400">Assets created across Campaign Intelligence modules</p>
            </div>
            <button onClick={() => navigate("/ads-planner")} className="text-xs font-medium text-indigo-400 hover:text-indigo-300">
              Plan Ads Strategy →
            </button>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={overview?.content_performance_mix || []} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                <XAxis type="number" allowDecimals={false} tick={{ fill: "#94A3B8", fontSize: 11 }} />
                <YAxis type="category" dataKey="category" width={115} tick={{ fill: "#CBD5E1", fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", borderRadius: 12 }} />
                <Bar dataKey="count" name="Total Items" fill="#6366F1" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Analyses + Recent Activity */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="tm-card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Recent YouTube Analyses</h2>
            <button
              onClick={() => navigate("/analyzer")}
              className="inline-flex items-center gap-1 text-xs font-medium text-indigo-400 hover:text-indigo-300"
            >
              New Analysis <ArrowUpRight className="h-3.5 w-3.5" />
            </button>
          </div>

          {overview && overview.recent_analyses.length > 0 ? (
            <div className="space-y-3">
              {overview.recent_analyses.map((item) => (
                <div
                  key={item.id}
                  onClick={() => navigate(`/analyzer?analysisId=${item.id}`)}
                  className="flex cursor-pointer flex-col gap-3 rounded-xl border border-slate-800/80 bg-[#0A1120] p-3 hover:border-indigo-500/40 transition sm:flex-row sm:items-center"
                >
                  <img
                    src={item.thumbnail_url || "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg"}
                    alt={item.video_title}
                    className="h-16 w-28 shrink-0 rounded-lg object-cover bg-slate-800"
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="truncate text-sm font-semibold text-white">{item.video_title}</p>
                      {item.is_demo_data && (
                        <span className="tm-badge bg-amber-500/15 text-amber-300 border border-amber-500/30">
                          Demo
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 text-xs text-slate-400">
                      {item.channel_title || "YouTube"} • {formatNumber(item.analyzed_comments_count)} comments •{" "}
                      {formatDate(item.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {item.status === "completed" ? (
                      <span className="tm-badge border border-emerald-500/30 bg-emerald-500/15 text-emerald-300">
                        <CheckCircle2 className="h-3.5 w-3.5" /> {item.positive_pct}% Pos
                      </span>
                    ) : (
                      <span className="tm-badge border border-indigo-500/30 bg-indigo-500/15 text-indigo-300">
                        <Clock className="h-3.5 w-3.5" /> {item.status} ({item.progress_pct}%)
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Youtube}
              title="No video analyses yet"
              description="Paste any public YouTube video URL in the YouTube Analyzer to collect up to 2,000 comments and unlock AI insights."
              action={
                <button onClick={() => navigate("/analyzer")} className="tm-btn-primary">
                  Start First Analysis
                </button>
              }
            />
          )}
        </div>

        <div className="tm-card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Recent Activity</h2>
            <button onClick={() => navigate("/history")} className="text-xs font-medium text-indigo-400 hover:text-indigo-300">
              View All
            </button>
          </div>
          {activity.length > 0 ? (
            <div className="space-y-3">
              {activity.map((rec) => (
                <div key={rec.id} className="rounded-xl border border-slate-800/70 bg-[#0A1120] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-slate-100 line-clamp-1">{rec.name}</span>
                    <span className="shrink-0 text-[10px] text-slate-500">{formatDate(rec.created_at)}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400 line-clamp-2">{rec.summary}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-10 text-center text-xs text-slate-500">
              <Megaphone className="mx-auto mb-2 h-6 w-6 text-slate-600" />
              Actions across analyses, content studio, ads, and PDF exports appear here.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
