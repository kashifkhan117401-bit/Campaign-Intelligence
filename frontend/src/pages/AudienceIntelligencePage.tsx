import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Compass,
  HelpCircle,
  Lightbulb,
  Sparkles,
  Target,
  Trash2,
  Users,
} from "lucide-react";
import { analysisApi } from "../services/api";
import type { AudienceInsight, VideoAnalysis } from "../types";
import { DemoDataBanner, DisclaimerNote, EmptyState, SkeletonCard } from "../components/UI";
import { useToast } from "../contexts/ToastContext";
import { getApiErrorMessage } from "../utils/format";

export function AudienceIntelligencePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { notify } = useToast();

  const [analyses, setAnalyses] = useState<VideoAnalysis[]>([]);
  const [selectedId, setSelectedId] = useState<string>(searchParams.get("analysisId") || "");
  const [insight, setInsight] = useState<AudienceInsight | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    analysisApi
      .list()
      .then((list) => {
        const completed = list.filter((a) => a.status === "completed");
        setAnalyses(completed);
        const target = searchParams.get("analysisId") || completed[0]?.id || "";
        setSelectedId(target);
      })
      .catch((err) => notify("error", "Could not load analyses", getApiErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [notify, searchParams]);

  useEffect(() => {
    if (!selectedId) {
      setInsight(null);
      return;
    }
    let mounted = true;
    setLoading(true);
    analysisApi
      .insights(selectedId)
      .then((res) => mounted && setInsight(res))
      .catch((err) => notify("error", "Could not load audience insights", getApiErrorMessage(err)))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, [selectedId, notify]);

  if (loading && !insight) {
    return (
      <div className="space-y-4">
        <SkeletonCard className="h-28" />
        <div className="grid gap-4 md:grid-cols-2">
          <SkeletonCard className="h-56" />
          <SkeletonCard className="h-56" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Audience Intelligence</h1>
          <p className="mt-1 text-sm text-slate-400">
            Deep buyer psychology, content gaps, objections, marketing angles, and top 10 questions to answer next.
          </p>
        </div>

        {analyses.length > 0 && (
          <div className="flex items-center gap-2">
            <select
              value={selectedId}
              onChange={(e) => {
                setSelectedId(e.target.value);
                setSearchParams({ analysisId: e.target.value });
              }}
              className="tm-input sm:w-80"
            >
              {analyses.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.video.title.slice(0, 55)} ({a.analyzed_comments_count} comments)
                </option>
              ))}
            </select>
            {selectedId && (
              <button
                type="button"
                onClick={async () => {
                  if (!window.confirm("Delete this analysis and its audience intelligence report?")) return;
                  try {
                    await analysisApi.remove(selectedId);
                    const remaining = analyses.filter((a) => a.id !== selectedId);
                    setAnalyses(remaining);
                    const nextId = remaining[0]?.id || "";
                    setSelectedId(nextId);
                    if (nextId) setSearchParams({ analysisId: nextId });
                    else setSearchParams({});
                    notify("info", "Analysis deleted from history");
                  } catch (err) {
                    notify("error", "Delete failed", getApiErrorMessage(err));
                  }
                }}
                className="tm-btn-secondary shrink-0 px-3 py-2 text-xs text-rose-400 hover:border-rose-500/40 hover:text-rose-300"
                title="Delete selected analysis"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        )}
      </div>

      {!insight ? (
        <EmptyState
          icon={Users}
          title="No Audience Intelligence Available"
          description="Complete a YouTube video analysis first to unlock deep audience interests, objections, content gaps, and the transparent Audience Opportunity Score."
          action={
            <button onClick={() => navigate("/analyzer")} className="tm-btn-primary">
              Analyze a YouTube Video
            </button>
          }
        />
      ) : (
        <div className="space-y-6">
          <DemoDataBanner visible={insight.is_demo_data} />

          {/* Opportunity Score Card with Transparent Formula */}
          <div className="tm-card border-indigo-500/30 bg-gradient-to-br from-[#0F1830] to-[#13112B] p-6">
            <div className="grid gap-6 lg:grid-cols-12">
              <div className="flex flex-col items-center justify-center rounded-2xl border border-indigo-500/30 bg-[#0A1020] p-6 text-center lg:col-span-4">
                <p className="text-xs font-semibold uppercase tracking-widest text-indigo-400">
                  Audience Opportunity Score
                </p>
                <p className="mt-2 bg-gradient-to-r from-indigo-400 via-violet-400 to-cyan-400 bg-clip-text text-5xl font-extrabold text-transparent">
                  {insight.opportunity_score}
                  <span className="text-xl text-slate-500">/100</span>
                </p>
                <p className="mt-2 text-[11px] text-slate-400">
                  Internal prioritization heuristic (not an externally validated benchmark)
                </p>
                <button
                  onClick={() => navigate(`/content-studio?analysisId=${insight.analysis_id}`)}
                  className="tm-btn-primary mt-4 w-full text-xs"
                >
                  <Sparkles className="h-3.5 w-3.5" /> Turn into Content Pack
                </button>
              </div>

              <div className="space-y-4 lg:col-span-8">
                <h3 className="text-sm font-semibold text-white">Transparent Scoring Breakdown</h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  {[
                    { key: "engagement_demand", label: "Engagement Demand (25%)", color: "from-indigo-500 to-cyan-500" },
                    { key: "unmet_need_intensity", label: "Unmet Need Intensity (25%)", color: "from-amber-500 to-rose-500" },
                    { key: "commercial_signal", label: "Commercial Signal (25%)", color: "from-violet-500 to-fuchsia-500" },
                    { key: "sentiment_leverage", label: "Sentiment Leverage (25%)", color: "from-emerald-500 to-teal-500" },
                  ].map((m) => {
                    const val = Number(insight.opportunity_score_breakdown_json?.[m.key] ?? 0);
                    return (
                      <div key={m.key} className="rounded-xl border border-slate-800 bg-[#0A1020] p-3">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-300">{m.label}</span>
                          <span className="font-bold text-white">{val}/100</span>
                        </div>
                        <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-800">
                          <div className={`h-full rounded-full bg-gradient-to-r ${m.color}`} style={{ width: `${Math.min(100, val)}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
                <DisclaimerNote text={insight.opportunity_formula_doc} variant="info" />
              </div>
            </div>
          </div>

          {/* Insight Cards Grid */}
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {[
              { title: "Audience Interests", icon: Compass, items: insight.interests_json, accent: "text-cyan-400" },
              { title: "Audience Expectations", icon: Target, items: insight.expectations_json, accent: "text-indigo-400" },
              { title: "Common Problems", icon: HelpCircle, items: insight.common_problems_json, accent: "text-rose-400" },
              { title: "Main Frustrations", icon: HelpCircle, items: insight.main_frustrations_json, accent: "text-amber-400" },
              { title: "Content Gaps", icon: Lightbulb, items: insight.content_gaps_json, accent: "text-violet-400" },
              { title: "Product / Service Opportunities", icon: Sparkles, items: insight.product_opportunities_json, accent: "text-emerald-400" },
              { title: "Why People Agree", icon: Users, items: insight.agreement_reasons_json, accent: "text-emerald-300" },
              { title: "Why People Disagree / Objections", icon: Users, items: [...insight.disagreement_reasons_json, ...insight.customer_objections_json].slice(0, 6), accent: "text-rose-300" },
              { title: "Suggested Marketing Angles", icon: Target, items: insight.marketing_angles_json, accent: "text-indigo-300" },
            ].map((card) => {
              const Icon = card.icon;
              return (
                <div key={card.title} className="tm-card p-5">
                  <div className="flex items-center gap-2">
                    <Icon className={`h-4 w-4 ${card.accent}`} />
                    <h3 className="text-sm font-semibold text-white">{card.title}</h3>
                  </div>
                  <ul className="mt-3 space-y-2 text-xs text-slate-300">
                    {card.items.length > 0 ? (
                      card.items.map((txt, i) => (
                        <li key={i} className="rounded-lg bg-slate-900/70 p-2.5 leading-relaxed">
                          {txt}
                        </li>
                      ))
                    ) : (
                      <li className="text-slate-500">No items detected.</li>
                    )}
                  </ul>
                </div>
              );
            })}
          </div>

          {/* Top 10 Questions to Answer in Future Videos */}
          <div className="tm-card p-5">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-white">Top 10 Questions to Answer in Future Videos</h3>
                <p className="text-xs text-slate-400">
                  Prioritized directly from audience inquiries and recurring discussion gaps.
                </p>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="pb-3 pr-3">#</th>
                    <th className="pb-3 pr-4">Audience Question</th>
                    <th className="pb-3 pr-4">Intent</th>
                    <th className="pb-3">Suggested Video Angle</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {insight.top_10_questions_json.map((q) => (
                    <tr key={q.rank} className="hover:bg-slate-900/40">
                      <td className="py-3 pr-3 font-bold text-indigo-400">{q.rank}</td>
                      <td className="py-3 pr-4 font-medium text-white">{q.question}</td>
                      <td className="py-3 pr-4">
                        <span className="tm-badge border border-slate-700 bg-slate-800 text-slate-200">
                          {q.audience_intent}
                        </span>
                      </td>
                      <td className="py-3 text-slate-300">{q.suggested_video_angle}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
