import React, { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Calculator, Loader2, Megaphone, Sparkles, Trash2 } from "lucide-react";
import { adsApi, analysisApi } from "../services/api";
import type { AdvertisingStrategy, BudgetTier, VideoAnalysis } from "../types";
import { CopyButton, DisclaimerNote, EmptyState } from "../components/UI";
import { useToast } from "../contexts/ToastContext";
import { formatCurrency, formatNumber, getApiErrorMessage } from "../utils/format";

const OBJECTIVES = [
  "Brand awareness",
  "Reach",
  "Video views",
  "Website traffic",
  "Lead generation",
  "Product promotion",
  "Conversions",
] as const;

export function AdsPlannerPage() {
  const { notify } = useToast();

  const [analyses, setAnalyses] = useState<VideoAnalysis[]>([]);
  const [history, setHistory] = useState<AdvertisingStrategy[]>([]);
  const [active, setActive] = useState<AdvertisingStrategy | null>(null);
  const [previewTiers, setPreviewTiers] = useState<BudgetTier[]>([]);
  const [formulaNote, setFormulaNote] = useState("");
  const [disclaimer, setDisclaimer] = useState("");

  // Form state
  const [campaignName, setCampaignName] = useState("YouTube Growth Launch");
  const [analysisId, setAnalysisId] = useState("");
  const [videoContext, setVideoContext] = useState("");
  const [targetCountry, setTargetCountry] = useState("United States");
  const [targetAudience, setTargetAudience] = useState("SaaS founders, creators, and growth marketers aged 24-48");
  const [industryNiche, setIndustryNiche] = useState("B2B SaaS & Creator Economy");
  const [objective, setObjective] = useState<string>("Video views");
  const [durationDays, setDurationDays] = useState(30);
  const [budget, setBudget] = useState(1500);
  const [currency, setCurrency] = useState("USD");
  const [customCpv, setCustomCpv] = useState<string>("");

  const [calculating, setCalculating] = useState(false);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    Promise.all([analysisApi.list(), adsApi.history()])
      .then(([aList, hList]) => {
        setAnalyses(aList.filter((a) => a.status === "completed"));
        setHistory(hList);
        if (hList.length > 0) setActive(hList[0]);
      })
      .catch((err) => notify("error", "Could not load Ads Planner", getApiErrorMessage(err)));
  }, [notify]);

  const handleCalculatePreview = async () => {
    setCalculating(true);
    try {
      const res = await adsApi.estimateBudget({
        available_budget: budget,
        campaign_duration_days: durationDays,
        currency,
        target_country: targetCountry,
        industry_niche: industryNiche,
        marketing_objective: objective,
        custom_cpv: customCpv ? Number(customCpv) : undefined,
      });
      setPreviewTiers(res.tiers);
      setFormulaNote(res.formula_note);
      setDisclaimer(res.disclaimer);
    } catch (err) {
      notify("error", "Budget calculation failed", getApiErrorMessage(err));
    } finally {
      setCalculating(false);
    }
  };

  const handleGenerateStrategy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!videoContext.trim() || videoContext.trim().length < 10) {
      notify("error", "Video context required", "Describe the video content (at least 10 characters).");
      return;
    }
    setGenerating(true);
    try {
      const created = await adsApi.createStrategy({
        campaign_name: campaignName.trim(),
        analysis_id: analysisId || null,
        video_context: videoContext.trim(),
        target_country: targetCountry.trim(),
        target_audience: targetAudience.trim(),
        industry_niche: industryNiche.trim(),
        marketing_objective: objective,
        campaign_duration_days: durationDays,
        available_budget: budget,
        currency,
        custom_cpv: customCpv ? Number(customCpv) : undefined,
      });
      setHistory((prev) => [created, ...prev]);
      setActive(created);
      setPreviewTiers(created.budget_estimates || []);
      notify("success", "Advertising strategy created", "Full targeting, creatives, A/B tests & 3 budget tiers ready.");
    } catch (err) {
      notify("error", "Strategy generation failed", getApiErrorMessage(err));
    } finally {
      setGenerating(false);
    }
  };

  const displayTiers = active?.budget_estimates?.length ? active.budget_estimates : previewTiers;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">AI Advertising Strategy & Budget Planner</h1>
        <p className="mt-1 text-sm text-slate-400">
          Build YouTube Ads campaign recommendations with transparent Low, Balanced, and Aggressive budget scenarios.
        </p>
      </div>

      {/* Strategy Form */}
      <form onSubmit={handleGenerateStrategy} className="tm-card p-5 space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Campaign Name</label>
            <input
              type="text"
              required
              value={campaignName}
              onChange={(e) => setCampaignName(e.target.value)}
              className="tm-input"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Marketing Objective</label>
            <select value={objective} onChange={(e) => setObjective(e.target.value)} className="tm-input">
              {OBJECTIVES.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Link Video Analysis (Optional)</label>
            <select
              value={analysisId}
              onChange={(e) => {
                setAnalysisId(e.target.value);
                const found = analyses.find((a) => a.id === e.target.value);
                if (found && !videoContext) {
                  setVideoContext(`YouTube video "${found.video.title}" by ${found.video.channel_title}`);
                }
              }}
              className="tm-input"
            >
              <option value="">— None —</option>
              {analyses.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.video.title.slice(0, 48)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-300">Video Content & Offer Context</label>
          <textarea
            rows={2}
            required
            value={videoContext}
            onChange={(e) => setVideoContext(e.target.value)}
            placeholder="Describe the video angle, product/service being promoted, and desired viewer action..."
            className="tm-input text-xs"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Target Country</label>
            <input type="text" required value={targetCountry} onChange={(e) => setTargetCountry(e.target.value)} className="tm-input" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Industry / Niche</label>
            <input type="text" required value={industryNiche} onChange={(e) => setIndustryNiche(e.target.value)} className="tm-input" />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Available Budget</label>
            <input
              type="number"
              min={20}
              step={10}
              required
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className="tm-input"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Duration (Days)</label>
            <input
              type="number"
              min={3}
              max={365}
              required
              value={durationDays}
              onChange={(e) => setDurationDays(Number(e.target.value))}
              className="tm-input"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Currency & Optional CPV</label>
            <div className="flex gap-2">
              <select value={currency} onChange={(e) => setCurrency(e.target.value)} className="tm-input w-24">
                {["USD", "EUR", "GBP", "CAD", "AUD", "AED", "INR", "PKR"].map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              <input
                type="number"
                step="0.005"
                min="0.005"
                placeholder="CPV"
                value={customCpv}
                onChange={(e) => setCustomCpv(e.target.value)}
                className="tm-input"
                title="Optional custom assumed Cost Per View"
              />
            </div>
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-slate-300">Target Audience</label>
          <input type="text" required value={targetAudience} onChange={(e) => setTargetAudience(e.target.value)} className="tm-input" />
        </div>

        <div className="flex flex-wrap justify-end gap-2.5">
          <button type="button" onClick={handleCalculatePreview} disabled={calculating} className="tm-btn-secondary">
            {calculating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Calculator className="h-4 w-4 text-cyan-400" />}
            Preview Budget Tiers
          </button>
          <button type="submit" disabled={generating} className="tm-btn-primary">
            {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Generate Full AI Ads Strategy
          </button>
        </div>
      </form>

      {/* 3-Tier Budget Calculator */}
      {displayTiers.length > 0 && (
        <div className="space-y-4">
          <DisclaimerNote
            text={
              active?.disclaimer ||
              disclaimer ||
              "Illustrative estimates derived from configurable benchmark assumptions (Estimated Views = Campaign Budget / Assumed CPV). Not live Google Ads forecasts."
            }
            variant="warning"
          />
          {formulaNote && <p className="text-xs font-mono text-indigo-300">{formulaNote}</p>}

          <div className="grid gap-4 md:grid-cols-3">
            {displayTiers.map((t) => (
              <div
                key={t.tier}
                className={`tm-card p-5 ${
                  t.tier === "balanced" ? "border-indigo-500/50 bg-indigo-500/5 shadow-glow" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-300">
                    {t.tier} Strategy
                  </span>
                  <span className="tm-badge bg-slate-800 text-slate-300">Illustrative Estimate</span>
                </div>
                <p className="mt-2 text-2xl font-extrabold text-white">
                  {formatCurrency(t.total_budget, t.currency)}
                </p>
                <p className="text-xs text-slate-400">
                  {formatCurrency(t.daily_budget, t.currency)} / day × {t.campaign_duration_days} days
                </p>

                <div className="mt-4 space-y-2 border-t border-slate-800 pt-3 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Est. Views (Budget ÷ CPV)</span>
                    <span className="font-semibold text-emerald-300">{formatNumber(t.estimated_views)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Est. Impressions</span>
                    <span className="font-semibold text-white">{formatNumber(t.estimated_impressions)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Est. Reach</span>
                    <span className="font-semibold text-cyan-300">{formatNumber(t.estimated_reach)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Est. Clicks</span>
                    <span className="font-semibold text-violet-300">{formatNumber(t.estimated_clicks)}</span>
                  </div>
                  <div className="flex justify-between border-t border-slate-800/70 pt-2 text-[11px] text-slate-400">
                    <span>Assumed CPV / CPM / CTR</span>
                    <span>
                      {t.assumed_cpv} / {t.assumed_cpm} / {(t.assumed_ctr * 100).toFixed(2)}%
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="tm-card p-5">
            <h3 className="mb-3 text-sm font-semibold text-white">Illustrative Views & Reach by Budget Tier</h3>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={displayTiers}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                  <XAxis dataKey="tier" tick={{ fill: "#CBD5E1", fontSize: 12 }} />
                  <YAxis tick={{ fill: "#94A3B8", fontSize: 11 }} />
                  <Tooltip contentStyle={{ backgroundColor: "#0F172A", borderColor: "#334155", borderRadius: 10 }} />
                  <Bar dataKey="estimated_views" name="Est. Views" fill="#6366F1" radius={[6, 6, 0, 0]} />
                  <Bar dataKey="estimated_reach" name="Est. Reach" fill="#06B6D4" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Full Strategy Report + History */}
      <div className="grid gap-6 lg:grid-cols-12">
        <div className="space-y-2.5 lg:col-span-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Saved Strategies ({history.length})
            </h3>
            {history.length > 0 && (
              <button
                type="button"
                onClick={async () => {
                  if (!window.confirm("Delete all saved advertising strategies?")) return;
                  try {
                    await adsApi.clearAll();
                    setHistory([]);
                    setActive(null);
                    notify("info", "All strategies cleared");
                  } catch (err) {
                    notify("error", "Clear failed", getApiErrorMessage(err));
                  }
                }}
                className="inline-flex items-center gap-1 text-[11px] text-rose-400 hover:text-rose-300"
              >
                <Trash2 className="h-3 w-3" /> Clear All
              </button>
            )}
          </div>
          {history.map((s) => (
            <div
              key={s.id}
              onClick={() => setActive(s)}
              className={`cursor-pointer rounded-xl border p-3 text-xs transition ${
                active?.id === s.id
                  ? "border-indigo-500 bg-indigo-500/15"
                  : "border-slate-800 bg-slate-900/70 hover:border-slate-700"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="font-semibold text-white">{s.campaign_name}</p>
                <button
                  onClick={async (e) => {
                    e.stopPropagation();
                    await adsApi.remove(s.id);
                    const rest = history.filter((h) => h.id !== s.id);
                    setHistory(rest);
                    if (active?.id === s.id) setActive(rest[0] || null);
                    notify("info", "Strategy removed");
                  }}
                  className="text-slate-500 hover:text-rose-400"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <p className="mt-1 text-[10px] text-slate-400">
                {s.marketing_objective} • {formatCurrency(s.available_budget, s.currency)}
              </p>
            </div>
          ))}
        </div>

        <div className="lg:col-span-9">
          {!active ? (
            <EmptyState
              icon={Megaphone}
              title="Generate your YouTube Advertising Blueprint"
              description="Configure your target market, niche, objective, and budget above to receive campaign formats, targeting segments, creative A/B tests, and an executive report."
            />
          ) : (
            <div className="tm-card p-6 space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <h2 className="text-lg font-bold text-white">{active.campaign_name}</h2>
                  <p className="text-xs text-slate-400">
                    {active.recommended_objective} • {active.target_country} • {active.campaign_duration_days} days
                  </p>
                </div>
                <CopyButton text={active.executive_report} label="Copy Executive Report" />
              </div>

              <div className="rounded-xl border border-slate-800 bg-[#090F1E] p-4">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                  Executive Advertising Recommendation Report
                </h4>
                <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-slate-200">
                  {active.executive_report}
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                {[
                  { title: "Suggested Audience Segments", items: active.audience_segments_json },
                  { title: "Relevant Audience Interests", items: active.audience_interests_json },
                  { title: "Placement Strategy", items: active.placement_strategy_json },
                  { title: "Creative Recommendations", items: active.creative_recommendations_json },
                  { title: "A/B Testing Ideas", items: active.ab_testing_ideas_json },
                  { title: "Optimization Strategy", items: active.optimization_strategy_json },
                ].map((blk) => (
                  <div key={blk.title} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-cyan-400">{blk.title}</h4>
                    <ul className="mt-2.5 space-y-1.5 text-xs text-slate-300">
                      {blk.items.map((it, i) => (
                        <li key={i} className="leading-relaxed">
                          • {it}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
