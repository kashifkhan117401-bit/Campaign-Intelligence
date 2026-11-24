import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Calendar,
  Download,
  FileText,
  Hash,
  Loader2,
  RefreshCw,
  Save,
  Share2,
  Sparkles,
  Trash2,
} from "lucide-react";
import { analysisApi, contentApi } from "../services/api";
import type { GeneratedContent, VideoAnalysis } from "../types";
import { CopyButton, DemoDataBanner, DisclaimerNote, EmptyState } from "../components/UI";
import { useToast } from "../contexts/ToastContext";
import { formatDate, getApiErrorMessage } from "../utils/format";

const TONES = ["Professional", "Educational", "Conversational", "Persuasive", "Entertaining"] as const;
type TabKey = "youtube" | "seo" | "social" | "strategy";

export function ContentStudioPage() {
  const [searchParams] = useSearchParams();
  const { notify } = useToast();

  const [analyses, setAnalyses] = useState<VideoAnalysis[]>([]);
  const [items, setItems] = useState<GeneratedContent[]>([]);
  const [active, setActive] = useState<GeneratedContent | null>(null);
  const [tab, setTab] = useState<TabKey>("youtube");

  // Generator form
  const [analysisId, setAnalysisId] = useState<string>(searchParams.get("analysisId") || "");
  const [topicBrief, setTopicBrief] = useState("");
  const [tone, setTone] = useState<string>("Professional");
  const [targetAudience, setTargetAudience] = useState("");
  const [customInstructions, setCustomInstructions] = useState("");
  const [generating, setGenerating] = useState(false);

  // Editable draft fields
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editIntro, setEditIntro] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([analysisApi.list(), contentApi.list()])
      .then(([aList, cList]) => {
        setAnalyses(aList.filter((a) => a.status === "completed"));
        setItems(cList);
        if (cList.length > 0) selectItem(cList[0]);
      })
      .catch((err) => notify("error", "Could not load studio data", getApiErrorMessage(err)));
  }, [notify]);

  const selectItem = (item: GeneratedContent) => {
    setActive(item);
    setEditTitle(item.title);
    setEditDescription(item.seo_json?.description || "");
    setEditIntro(item.youtube_content_json?.script?.introduction || "");
  };

  const handleGenerate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!analysisId && !topicBrief.trim()) {
      notify("error", "Input required", "Select an analyzed video or enter a topic brief.");
      return;
    }
    setGenerating(true);
    try {
      const created = await contentApi.generate({
        analysis_id: analysisId || null,
        topic_brief: topicBrief.trim(),
        tone,
        target_audience: targetAudience.trim(),
        custom_instructions: customInstructions.trim(),
      });
      setItems((prev) => [created, ...prev]);
      selectItem(created);
      notify("success", "Content suite generated", "Full script, SEO pack, social posts & calendar ready.");
    } catch (err) {
      notify("error", "Generation failed", getApiErrorMessage(err));
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!active) return;
    setSaving(true);
    try {
      const updated = await contentApi.update(active.id, {
        title: editTitle,
        status: "saved",
        seo_json: { ...active.seo_json, description: editDescription },
        youtube_content_json: {
          ...active.youtube_content_json,
          script: { ...active.youtube_content_json.script, introduction: editIntro },
        },
      });
      setItems((prev) => prev.map((it) => (it.id === updated.id ? updated : it)));
      selectItem(updated);
      notify("success", "Draft saved", "Your edits are saved to the database.");
    } catch (err) {
      notify("error", "Save failed", getApiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await contentApi.remove(id);
      const remaining = items.filter((it) => it.id !== id);
      setItems(remaining);
      if (active?.id === id) {
        if (remaining.length > 0) selectItem(remaining[0]);
        else setActive(null);
      }
      notify("info", "Content pack deleted");
    } catch (err) {
      notify("error", "Delete failed", getApiErrorMessage(err));
    }
  };

  const handleExportMarkdown = () => {
    if (!active) return;
    const md = [
      `# ${active.title}`,
      `Tone: ${active.tone} | Created: ${active.created_at}`,
      "",
      "## Title Options",
      ...(active.youtube_content_json.title_options || []).map((t, i) => `${i + 1}. ${t}`),
      "",
      "## Hooks",
      ...(active.youtube_content_json.hooks || []).map((h, i) => `${i + 1}. ${h}`),
      "",
      "## Script Introduction",
      editIntro,
      "",
      "## Main Sections",
      ...(active.youtube_content_json.script?.main_sections || []).map(
        (s) => `### ${s.heading}\n${s.script_body}`
      ),
      "",
      "## Conclusion & Call to Action",
      active.youtube_content_json.script?.conclusion || "",
      active.youtube_content_json.script?.call_to_action || "",
      "",
      "## SEO Description",
      editDescription,
      "",
      "## Hashtags",
      (active.seo_json.hashtags || []).join(" "),
      "",
      `> ${active.disclaimer}`,
    ].join("\n");

    const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `campaign_intelligence_content_${active.id.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">AI Content Generation Studio</h1>
        <p className="mt-1 text-sm text-slate-400">
          Turn real YouTube sentiment & audience questions into full video scripts, SEO packages, Shorts, social posts,
          and a 4-week content calendar.
        </p>
      </div>

      {/* Generator Form */}
      <form onSubmit={handleGenerate} className="tm-card p-5 space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">
              Source Video Analysis (Recommended)
            </label>
            <select value={analysisId} onChange={(e) => setAnalysisId(e.target.value)} className="tm-input">
              <option value="">— Standalone Topic Brief —</option>
              {analyses.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.video.title.slice(0, 50)} ({a.analyzed_comments_count} comments)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Tone of Voice</label>
            <select value={tone} onChange={(e) => setTone(e.target.value)} className="tm-input">
              {TONES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Target Audience</label>
            <input
              type="text"
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
              placeholder="e.g., B2B SaaS founders, solo creators"
              className="tm-input"
            />
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">
              Topic Brief / Focus Angle {analysisId ? "(Optional)" : "(Required)"}
            </label>
            <input
              type="text"
              value={topicBrief}
              onChange={(e) => setTopicBrief(e.target.value)}
              placeholder="e.g., Answering viewer pricing objections & Windows setup steps"
              className="tm-input"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Custom Instructions</label>
            <input
              type="text"
              value={customInstructions}
              onChange={(e) => setCustomInstructions(e.target.value)}
              placeholder="e.g., Include a lead-magnet checklist CTA"
              className="tm-input"
            />
          </div>
        </div>

        <div className="flex justify-end">
          <button type="submit" disabled={generating} className="tm-btn-primary">
            {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {generating ? "Generating Content Suite..." : "Generate Complete Content Suite"}
          </button>
        </div>
      </form>

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Saved Drafts Sidebar */}
        <div className="space-y-2.5 lg:col-span-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Saved Content Packs ({items.length})
            </h3>
            {items.length > 0 && (
              <button
                type="button"
                onClick={async () => {
                  if (!window.confirm("Delete all saved content packs?")) return;
                  try {
                    await contentApi.clearAll();
                    setItems([]);
                    setActive(null);
                    notify("info", "All content packs cleared");
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
          {items.length === 0 ? (
            <div className="tm-card p-4 text-xs text-slate-500">No content drafts yet.</div>
          ) : (
            <div className="space-y-2">
              {items.map((it) => (
                <div
                  key={it.id}
                  onClick={() => selectItem(it)}
                  className={`cursor-pointer rounded-xl border p-3 transition ${
                    active?.id === it.id
                      ? "border-indigo-500 bg-indigo-500/15"
                      : "border-slate-800 bg-slate-900/70 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-semibold text-white line-clamp-2">{it.title}</p>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDelete(it.id);
                      }}
                      className="rounded p-1 text-slate-500 hover:bg-rose-500/20 hover:text-rose-300"
                      aria-label="Delete content pack"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <p className="mt-1 text-[10px] text-slate-400">
                    {it.tone} • {it.status} • {formatDate(it.created_at)}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Active Content Editor */}
        <div className="lg:col-span-9">
          {!active ? (
            <EmptyState
              icon={Sparkles}
              title="Ready to craft your next YouTube hit"
              description="Link a completed YouTube analysis or enter a brief above to generate 5 titles, 3 hooks, a full structured script, 15-25 hashtags, social posts, and 10 future video ideas."
            />
          ) : (
            <div className="space-y-4">
              <DemoDataBanner visible={active.is_demo_data} />

              <div className="tm-card p-5 space-y-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="tm-input font-semibold text-base sm:max-w-lg"
                  />
                  <div className="flex flex-wrap gap-2">
                    <button onClick={() => void handleGenerate()} disabled={generating} className="tm-btn-secondary text-xs">
                      <RefreshCw className="h-3.5 w-3.5" /> Regenerate
                    </button>
                    <button onClick={handleSave} disabled={saving} className="tm-btn-primary text-xs">
                      <Save className="h-3.5 w-3.5" /> {saving ? "Saving..." : "Save Draft"}
                    </button>
                    <button onClick={handleExportMarkdown} className="tm-btn-secondary text-xs">
                      <Download className="h-3.5 w-3.5" /> Export .md
                    </button>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
                  {[
                    { id: "youtube", label: "YouTube Script & Hooks", icon: FileText },
                    { id: "seo", label: "SEO, Tags & Hashtags", icon: Hash },
                    { id: "social", label: "Social & Shorts", icon: Share2 },
                    { id: "strategy", label: "10 Ideas & Calendar", icon: Calendar },
                  ].map((t) => {
                    const Icon = t.icon;
                    return (
                      <button
                        key={t.id}
                        onClick={() => setTab(t.id as TabKey)}
                        className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-medium transition ${
                          tab === t.id
                            ? "bg-indigo-600 text-white"
                            : "bg-slate-900 text-slate-400 hover:bg-slate-800 hover:text-white"
                        }`}
                      >
                        <Icon className="h-3.5 w-3.5" />
                        {t.label}
                      </button>
                    );
                  })}
                </div>

                <DisclaimerNote text={active.disclaimer} />

                {/* TAB: YouTube Video Content */}
                {tab === "youtube" && (
                  <div className="space-y-5">
                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                          5 Video Title Options
                        </h4>
                        <CopyButton text={(active.youtube_content_json.title_options || []).join("\n")} />
                      </div>
                      <div className="space-y-2">
                        {(active.youtube_content_json.title_options || []).map((t, i) => (
                          <div key={i} className="flex items-center justify-between gap-3 rounded-xl bg-slate-900/70 p-3 text-xs text-slate-100">
                            <span>
                              <strong className="mr-2 text-indigo-400">#{i + 1}</strong>
                              {t}
                            </span>
                            <CopyButton text={t} label="Copy" />
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-violet-400">
                        3 Attention-Grabbing Hooks
                      </h4>
                      <div className="space-y-2">
                        {(active.youtube_content_json.hooks || []).map((h, i) => (
                          <div key={i} className="flex items-start justify-between gap-3 rounded-xl border border-slate-800 bg-[#090F1E] p-3.5 text-xs text-slate-200 leading-relaxed">
                            <span>{h}</span>
                            <CopyButton text={h} />
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-cyan-400">
                          Script Introduction (Editable)
                        </h4>
                        <CopyButton text={editIntro} />
                      </div>
                      <textarea
                        rows={4}
                        value={editIntro}
                        onChange={(e) => setEditIntro(e.target.value)}
                        className="tm-input text-xs leading-relaxed"
                      />
                    </div>

                    <div className="space-y-3">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                        Main Content Sections
                      </h4>
                      {(active.youtube_content_json.script?.main_sections || []).map((sec, idx) => (
                        <div key={idx} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-2">
                          <div className="flex items-center justify-between">
                            <h5 className="text-sm font-semibold text-white">{sec.heading}</h5>
                            <CopyButton text={`${sec.heading}\n\n${sec.script_body}`} />
                          </div>
                          <ul className="list-disc pl-5 text-xs text-slate-400 space-y-1">
                            {(sec.talking_points || []).map((pt, pIdx) => (
                              <li key={pIdx}>{pt}</li>
                            ))}
                          </ul>
                          <p className="text-xs leading-relaxed text-slate-200">{sec.script_body}</p>
                        </div>
                      ))}
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                        <div className="mb-2 flex items-center justify-between">
                          <h5 className="text-xs font-semibold uppercase text-slate-300">Conclusion</h5>
                          <CopyButton text={active.youtube_content_json.script?.conclusion || ""} />
                        </div>
                        <p className="text-xs leading-relaxed text-slate-300">
                          {active.youtube_content_json.script?.conclusion}
                        </p>
                      </div>
                      <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/5 p-4">
                        <div className="mb-2 flex items-center justify-between">
                          <h5 className="text-xs font-semibold uppercase text-indigo-300">Call to Action</h5>
                          <CopyButton text={active.youtube_content_json.script?.call_to_action || ""} />
                        </div>
                        <p className="text-xs leading-relaxed text-slate-200">
                          {active.youtube_content_json.script?.call_to_action}
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB: SEO */}
                {tab === "seo" && (
                  <div className="space-y-5">
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-xl bg-slate-900/70 p-4">
                        <p className="text-xs text-slate-400">Primary Keyword</p>
                        <p className="mt-1 text-base font-bold text-indigo-300">{active.seo_json.primary_keyword}</p>
                      </div>
                      <div className="rounded-xl bg-slate-900/70 p-4">
                        <p className="text-xs text-slate-400">Search Intent</p>
                        <p className="mt-1 text-xs text-slate-200">{active.seo_json.search_intent}</p>
                      </div>
                    </div>

                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-indigo-400">
                          SEO-Optimized Description (Editable)
                        </h4>
                        <CopyButton text={editDescription} />
                      </div>
                      <textarea
                        rows={7}
                        value={editDescription}
                        onChange={(e) => setEditDescription(e.target.value)}
                        className="tm-input font-mono text-xs leading-relaxed"
                      />
                    </div>

                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-violet-400">
                          Hashtags ({(active.seo_json.hashtags || []).length})
                        </h4>
                        <CopyButton text={(active.seo_json.hashtags || []).join(" ")} />
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {(active.seo_json.hashtags || []).map((h, i) => (
                          <span key={i} className="rounded-lg border border-violet-500/30 bg-violet-500/10 px-2.5 py-1 text-xs text-violet-200">
                            {h}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-cyan-400">YouTube Tags</h4>
                        <CopyButton text={(active.seo_json.tags || []).join(", ")} />
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {(active.seo_json.tags || []).map((t, i) => (
                          <span key={i} className="rounded-md bg-slate-800 px-2.5 py-1 text-xs text-slate-300">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* TAB: Social Media */}
                {tab === "social" && (
                  <div className="space-y-4">
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-rose-400">
                      YouTube Shorts Scripts
                    </h4>
                    <div className="grid gap-4 md:grid-cols-2">
                      {(active.social_media_json.youtube_shorts_scripts || []).map((sh, i) => (
                        <div key={i} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4 space-y-2 text-xs">
                          <div className="flex items-center justify-between">
                            <p className="font-semibold text-white">{sh.title}</p>
                            <CopyButton text={`${sh.hook}\n${sh.body}\n${sh.cta}`} />
                          </div>
                          <p className="text-indigo-300"><strong>Hook:</strong> {sh.hook}</p>
                          <p className="text-slate-300">{sh.body}</p>
                          <p className="text-emerald-300"><strong>CTA:</strong> {sh.cta}</p>
                        </div>
                      ))}
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      {[
                        { label: "LinkedIn Post", text: active.social_media_json.linkedin_post },
                        { label: "X / Twitter Post", text: active.social_media_json.x_post },
                        { label: "Facebook Post", text: active.social_media_json.facebook_post },
                        { label: "Instagram Reels Caption", text: (active.social_media_json.instagram_reels_captions || []).join("\n\n") },
                      ].map((p) => (
                        <div key={p.label} className="rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                          <div className="mb-2 flex items-center justify-between">
                            <h5 className="text-xs font-semibold text-white">{p.label}</h5>
                            <CopyButton text={p.text || ""} />
                          </div>
                          <p className="whitespace-pre-wrap text-xs leading-relaxed text-slate-300">{p.text}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* TAB: Content Strategy */}
                {tab === "strategy" && (
                  <div className="space-y-5">
                    <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4 text-xs">
                      <span className="font-semibold text-indigo-300">Suggested Publishing Cadence: </span>
                      <span className="text-slate-200">{active.content_strategy_json.publishing_frequency}</span>
                    </div>

                    <div>
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-cyan-400">
                        4-Week Content Calendar
                      </h4>
                      <div className="grid gap-3 md:grid-cols-2">
                        {(active.content_strategy_json.content_calendar || []).map((w, i) => (
                          <div key={i} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3.5 text-xs">
                            <p className="font-bold text-indigo-400">{w.week} — {w.format}</p>
                            <p className="mt-1 font-medium text-white">{w.topic}</p>
                            <p className="mt-1 text-slate-400">{w.goal}</p>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-violet-400">
                        10 Future Video Ideas
                      </h4>
                      <div className="space-y-2">
                        {(active.content_strategy_json.future_video_ideas || []).map((idea, i) => (
                          <div key={i} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-xs">
                            <p className="font-semibold text-white">
                              <span className="mr-2 text-indigo-400">#{i + 1}</span>
                              {idea.title}
                            </p>
                            <p className="mt-1 text-slate-400">
                              Angle: {idea.angle} • Targets: {idea.target_pain_point}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
