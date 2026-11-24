import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Download, FileBarChart2, FileText, Loader2, RefreshCw, Sparkles, Trash2 } from "lucide-react";
import { adsApi, analysisApi, contentApi, reportsApi } from "../services/api";
import type { AdvertisingStrategy, GeneratedContent, PDFReport, VideoAnalysis } from "../types";
import { EmptyState } from "../components/UI";
import { useToast } from "../contexts/ToastContext";
import { formatBytes, formatDate, getApiErrorMessage } from "../utils/format";

export function ReportsPage() {
  const [searchParams] = useSearchParams();
  const { notify } = useToast();

  const [analyses, setAnalyses] = useState<VideoAnalysis[]>([]);
  const [contents, setContents] = useState<GeneratedContent[]>([]);
  const [strategies, setStrategies] = useState<AdvertisingStrategy[]>([]);
  const [reports, setReports] = useState<PDFReport[]>([]);

  const [analysisId, setAnalysisId] = useState(searchParams.get("analysisId") || "");
  const [contentId, setContentId] = useState("");
  const [strategyId, setStrategyId] = useState("");
  const [customTitle, setCustomTitle] = useState("");
  const [generating, setGenerating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([analysisApi.list(), contentApi.list(), adsApi.history(), reportsApi.list()])
      .then(([aList, cList, sList, rList]) => {
        const done = aList.filter((a) => a.status === "completed");
        setAnalyses(done);
        setContents(cList);
        setStrategies(sList);
        setReports(rList);
        if (!analysisId && done.length > 0) setAnalysisId(done[0].id);
      })
      .catch((err) => notify("error", "Could not load reports", getApiErrorMessage(err)));
  }, [notify]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!analysisId) {
      notify("error", "Select an analysis", "Choose a completed YouTube analysis to generate a PDF report.");
      return;
    }
    setGenerating(true);
    try {
      const rep = await reportsApi.generate({
        analysis_id: analysisId,
        content_id: contentId || null,
        strategy_id: strategyId || null,
        title: customTitle.trim() || undefined,
      });
      setReports((prev) => [rep, ...prev]);
      setCustomTitle("");
      notify("success", "Executive PDF generated", `${rep.page_count} pages ready for download.`);
    } catch (err) {
      notify("error", "Report generation failed", getApiErrorMessage(err));
    } finally {
      setGenerating(false);
    }
  };

  const handleDownload = async (report: PDFReport) => {
    setBusyId(report.id);
    try {
      const blob = await reportsApi.downloadBlob(report.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Campaign_Intelligence_Report_v${report.version}_${report.id.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      notify("error", "Download failed", getApiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const handleRegenerate = async (report: PDFReport) => {
    setBusyId(report.id);
    try {
      const updated = await reportsApi.regenerate(report.id);
      setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      notify("success", "Report regenerated", `Updated to version v${updated.version}.`);
    } catch (err) {
      notify("error", "Regeneration failed", getApiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const handleDeleteReport = async (report: PDFReport) => {
    setBusyId(report.id);
    try {
      await reportsApi.remove(report.id);
      setReports((prev) => prev.filter((r) => r.id !== report.id));
      notify("info", "Report deleted");
    } catch (err) {
      notify("error", "Delete failed", getApiErrorMessage(err));
    } finally {
      setBusyId(null);
    }
  };

  const handleClearReports = async () => {
    if (!window.confirm("Delete all generated PDF reports?")) return;
    try {
      await reportsApi.clearAll();
      setReports([]);
      notify("info", "All PDF reports cleared");
    } catch (err) {
      notify("error", "Clear failed", getApiErrorMessage(err));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Professional PDF Reports</h1>
          <p className="mt-1 text-sm text-slate-400">
            Export polished 18-section ReportLab PDF reports with vector sentiment & emotion charts, audience
            intelligence, SEO content packs, YouTube advertising strategies, and full methodology disclosures.
          </p>
        </div>
        {reports.length > 0 && (
          <button
            type="button"
            onClick={() => void handleClearReports()}
            className="tm-btn-secondary shrink-0 text-xs text-rose-400 hover:border-rose-500/40 hover:text-rose-300"
          >
            <Trash2 className="h-3.5 w-3.5" /> Clear All Reports
          </button>
        )}
      </div>

      {/* Report Builder */}
      <form onSubmit={handleGenerate} className="tm-card p-5 space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Video Analysis (Required)</label>
            <select value={analysisId} onChange={(e) => setAnalysisId(e.target.value)} className="tm-input" required>
              <option value="">— Select completed analysis —</option>
              {analyses.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.video.title.slice(0, 50)} ({a.analyzed_comments_count} comments)
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Attach Content Pack (Optional)</label>
            <select value={contentId} onChange={(e) => setContentId(e.target.value)} className="tm-input">
              <option value="">Auto-attach latest linked content</option>
              {contents.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title.slice(0, 50)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Attach Ads Strategy (Optional)</label>
            <select value={strategyId} onChange={(e) => setStrategyId(e.target.value)} className="tm-input">
              <option value="">Auto-attach latest linked strategy</option>
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.campaign_name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            value={customTitle}
            onChange={(e) => setCustomTitle(e.target.value)}
            placeholder="Optional custom cover page report title..."
            className="tm-input flex-1"
          />
          <button type="submit" disabled={generating || !analysisId} className="tm-btn-primary shrink-0">
            {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            {generating ? "Building PDF..." : "Generate 18-Section PDF"}
          </button>
        </div>
      </form>

      {/* Reports List */}
      {reports.length === 0 ? (
        <EmptyState
          icon={FileBarChart2}
          title="No PDF reports generated yet"
          description="Select a completed YouTube analysis above to generate a client-ready multi-page PDF intelligence report."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {reports.map((rep) => (
            <div key={rep.id} className="tm-card-hover flex flex-col justify-between gap-4 p-5">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-indigo-500/30 bg-indigo-500/10 text-indigo-400">
                  <FileText className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="truncate text-sm font-semibold text-white">{rep.title}</h3>
                    <span className="tm-badge bg-slate-800 text-indigo-300">v{rep.version}</span>
                  </div>
                  <p className="mt-1 text-xs text-slate-400">
                    {rep.page_count} pages • {formatBytes(rep.file_size_bytes)} • Updated {formatDate(rep.updated_at)}
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 border-t border-slate-800/80 pt-3">
                <button
                  onClick={() => void handleDeleteReport(rep)}
                  disabled={busyId === rep.id}
                  className="tm-btn-secondary py-1.5 text-xs text-rose-400 hover:border-rose-500/40 hover:text-rose-300"
                  title="Delete report"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Delete
                </button>
                <button
                  onClick={() => void handleRegenerate(rep)}
                  disabled={busyId === rep.id}
                  className="tm-btn-secondary py-1.5 text-xs"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${busyId === rep.id ? "animate-spin" : ""}`} />
                  Regenerate
                </button>
                <button
                  onClick={() => void handleDownload(rep)}
                  disabled={busyId === rep.id}
                  className="tm-btn-primary py-1.5 text-xs"
                >
                  <Download className="h-3.5 w-3.5" />
                  Download PDF
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
