import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { FileBarChart2, History, Megaphone, Search, Sparkles, Trash2, Upload, Youtube } from "lucide-react";
import { dashboardApi } from "../services/api";
import type { CampaignRecord } from "../types";
import { EmptyState, SkeletonCard } from "../components/UI";
import { formatDate, getApiErrorMessage } from "../utils/format";
import { useToast } from "../contexts/ToastContext";

const FILTERS = [
  { value: "", label: "All Records" },
  { value: "video_analysis", label: "Video Analyses" },
  { value: "content_generation", label: "Content Packs" },
  { value: "ads_strategy", label: "Ads Strategies" },
  { value: "pdf_report", label: "PDF Reports" },
  { value: "youtube_publish", label: "YouTube Publishing" },
];

export function CampaignHistoryPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { notify } = useToast();

  const [records, setRecords] = useState<CampaignRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");
  const [query, setQuery] = useState(searchParams.get("q") || "");

  useEffect(() => {
    setLoading(true);
    dashboardApi
      .activity(typeFilter || undefined)
      .then((res) => setRecords(res.items))
      .catch((err) => notify("error", "Could not load campaign history", getApiErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [typeFilter, notify]);

  const filtered = records.filter((r) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return r.name.toLowerCase().includes(q) || r.summary.toLowerCase().includes(q);
  });

  const openRecord = (r: CampaignRecord) => {
    if (r.record_type === "video_analysis" && r.analysis_id) navigate(`/analyzer?analysisId=${r.analysis_id}`);
    else if (r.record_type === "content_generation") navigate("/content-studio");
    else if (r.record_type === "ads_strategy") navigate("/ads-planner");
    else if (r.record_type === "pdf_report") navigate("/reports");
    else if (r.record_type === "youtube_publish") navigate("/video-studio");
  };

  const iconFor = (type: string) => {
    if (type === "video_analysis") return Youtube;
    if (type === "content_generation") return Sparkles;
    if (type === "ads_strategy") return Megaphone;
    if (type === "pdf_report") return FileBarChart2;
    return Upload;
  };

  const handleDeleteRecord = async (id: string) => {
    try {
      await dashboardApi.removeActivity(id);
      setRecords((prev) => prev.filter((r) => r.id !== id));
      notify("info", "History record deleted");
    } catch (err) {
      notify("error", "Delete failed", getApiErrorMessage(err));
    }
  };

  const handleClearRecords = async () => {
    const label = FILTERS.find((f) => f.value === typeFilter)?.label || "All Records";
    if (!window.confirm(`Delete ${label.toLowerCase()} from campaign history?`)) return;
    try {
      await dashboardApi.clearActivity(typeFilter || undefined);
      setRecords([]);
      notify("info", "Campaign history cleared");
    } catch (err) {
      notify("error", "Could not clear history", getApiErrorMessage(err));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Campaign History</h1>
          <p className="mt-1 text-sm text-slate-400">
            Complete audit trail of your YouTube analyses, generated content, ad strategies, published videos, and PDF
            reports.
          </p>
        </div>
        {records.length > 0 && (
          <button
            type="button"
            onClick={() => void handleClearRecords()}
            className="tm-btn-secondary shrink-0 text-xs text-rose-400 hover:border-rose-500/40 hover:text-rose-300"
          >
            <Trash2 className="h-3.5 w-3.5" /> Clear {typeFilter ? "Filtered" : "All"} History
          </button>
        )}
      </div>

      <div className="tm-card flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setTypeFilter(f.value)}
              className={`rounded-xl px-3 py-1.5 text-xs font-medium transition ${
                typeFilter === f.value
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="relative sm:w-64">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search history..."
            className="tm-input py-1.5 pl-8 text-xs"
          />
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} className="h-20" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={History}
          title="No matching campaign records"
          description="Your analyses, content packs, ad plans, and exports are logged automatically here."
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((rec) => {
            const Icon = iconFor(rec.record_type);
            return (
              <div
                key={rec.id}
                onClick={() => openRecord(rec)}
                className="tm-card-hover flex cursor-pointer items-center justify-between gap-4 p-4"
              >
                <div className="flex items-start gap-3.5 min-w-0">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-400">
                    <Icon className="h-5 w-5" />
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-white">{rec.name}</p>
                    <p className="mt-0.5 text-xs text-slate-400">{rec.summary}</p>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <div className="text-right">
                    <span className="tm-badge border border-emerald-500/30 bg-emerald-500/15 text-emerald-300">
                      {rec.status}
                    </span>
                    <p className="mt-1 text-[11px] text-slate-500">{formatDate(rec.created_at)}</p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      void handleDeleteRecord(rec.id);
                    }}
                    className="rounded-lg p-1.5 text-slate-500 hover:bg-rose-500/20 hover:text-rose-300"
                    aria-label="Delete history record"
                    title="Delete record"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
