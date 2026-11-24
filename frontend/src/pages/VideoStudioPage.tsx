import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  CalendarClock,
  CheckCircle2,
  Clock,
  Film,
  Link2,
  Loader2,
  ShieldAlert,
  Sparkles,
  Trash2,
  UploadCloud,
  Wand2,
  Youtube,
} from "lucide-react";
import { videoApi } from "../services/api";
import type { ConnectedChannel, PublishingJob, UploadedMedia } from "../types";
import { CopyButton, DisclaimerNote, EmptyState } from "../components/UI";
import { useToast } from "../contexts/ToastContext";
import { formatBytes, formatDuration, getApiErrorMessage } from "../utils/format";

function toLocalDateTimeInput(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function parseUtcDate(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const hasTz = /[zZ]$|[+-]\d{2}:\d{2}$/.test(iso);
  const d = new Date(hasTz ? iso : `${iso}Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatCountdown(target: Date | null, nowMs: number): string {
  if (!target) return "";
  const diffSec = Math.floor((target.getTime() - nowMs) / 1000);
  if (diffSec <= 0) return "Starting upload...";
  const days = Math.floor(diffSec / 86400);
  const hrs = Math.floor((diffSec % 86400) / 3600);
  const mins = Math.floor((diffSec % 3600) / 60);
  const secs = diffSec % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  if (days > 0) return `${days}d ${hrs}h ${pad(mins)}m ${pad(secs)}s`;
  if (hrs > 0) return `${hrs}h ${pad(mins)}m ${pad(secs)}s`;
  return `${pad(mins)}m ${pad(secs)}s`;
}

export function VideoStudioPage() {
  const [searchParams] = useSearchParams();
  const { notify } = useToast();

  const [mediaList, setMediaList] = useState<UploadedMedia[]>([]);
  const [activeMedia, setActiveMedia] = useState<UploadedMedia | null>(null);
  const [channels, setChannels] = useState<ConnectedChannel[]>([]);
  const [jobs, setJobs] = useState<PublishingJob[]>([]);

  const [uploading, setUploading] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [generatingMeta, setGeneratingMeta] = useState(false);
  const [customNotes, setCustomNotes] = useState("");
  const [oauthNotice, setOauthNotice] = useState<string | null>(null);

  // Editable Publish Preview State
  const [pubTitle, setPubTitle] = useState("");
  const [pubDescription, setPubDescription] = useState("");
  const [pubTags, setPubTags] = useState("");
  const [pubCategoryId, setPubCategoryId] = useState("27");
  const [pubPinned, setPubPinned] = useState("");
  const [pubPrivacy, setPubPrivacy] = useState<"private" | "unlisted" | "public">("private");
  const [pubAction, setPubAction] = useState<"draft" | "upload" | "schedule">("draft");
  const [scheduledAt, setScheduledAt] = useState(() => toLocalDateTimeInput(new Date(Date.now() + 15 * 60 * 1000)));
  const [selectedChannelId, setSelectedChannelId] = useState("");
  const [userConfirmed, setUserConfirmed] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [nowMs, setNowMs] = useState(() => Date.now());
  const [editingJobId, setEditingJobId] = useState<string | null>(null);
  const [editingScheduleVal, setEditingScheduleVal] = useState("");
  const [updatingJobId, setUpdatingJobId] = useState<string | null>(null);

  const hydratePreview = (m: UploadedMedia) => {
    setActiveMedia(m);
    const meta = m.generated_metadata_json || {};
    setPubTitle(meta.titles?.[0] || m.original_filename.replace(/\.[^.]+$/, ""));
    setPubDescription(meta.description || "");
    setPubTags((meta.tags || []).join(", "));
    setPubCategoryId(meta.category_suggestion?.id || "27");
    setPubPinned(meta.pinned_comment || "");
    setUserConfirmed(false);
  };

  const refreshAll = async () => {
    try {
      const [vids, chs, jbs] = await Promise.all([videoApi.list(), videoApi.channels(), videoApi.jobs()]);
      setMediaList(vids);
      setChannels(chs);
      setJobs(jbs);
      if (chs.length > 0 && !selectedChannelId) setSelectedChannelId(chs[0].id);
      if (vids.length > 0 && !activeMedia) hydratePreview(vids[0]);
    } catch (err) {
      notify("error", "Could not load Video Studio", getApiErrorMessage(err));
    }
  };

  useEffect(() => {
    void refreshAll();
    if (searchParams.get("oauth_connected") === "true") {
      notify("success", "YouTube channel connected", "Your Google OAuth 2.0 tokens are encrypted and stored.");
    } else if (searchParams.get("oauth_error")) {
      const errCode = searchParams.get("oauth_error");
      const errDetail = searchParams.get("oauth_detail");
      const msg = errDetail ? `${errCode}: ${errDetail}` : `Google returned: ${errCode}`;
      setOauthNotice(`YouTube OAuth failed — ${msg}`);
      notify("error", "OAuth failed", msg);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const hasActiveJobs = jobs.some((j) =>
    ["scheduled_upload", "queued", "uploading"].includes(j.status)
  );

  // Live 1-second clock for countdown timers
  useEffect(() => {
    if (!hasActiveJobs && pubAction !== "schedule") return;
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [hasActiveJobs, pubAction]);

  // Poll job statuses automatically while scheduled uploads or active uploads are pending
  useEffect(() => {
    if (!hasActiveJobs) return;
    const poller = window.setInterval(async () => {
      try {
        const latest = await videoApi.jobs();
        setJobs(latest);
      } catch {
        // Ignore transient poll errors
      }
    }, 4000);
    return () => window.clearInterval(poller);
  }, [hasActiveJobs]);

  const applyQuickScheduleOffset = (minutesFromNow: number) => {
    const target = new Date(Date.now() + minutesFromNow * 60 * 1000);
    setScheduledAt(toLocalDateTimeInput(target));
  };

  const applyTomorrowNineAm = () => {
    const target = new Date();
    target.setDate(target.getDate() + 1);
    target.setHours(9, 0, 0, 0);
    setScheduledAt(toLocalDateTimeInput(target));
  };

  const handleRescheduleJob = async (jobId: string) => {
    if (!editingScheduleVal) return;
    const targetDate = new Date(editingScheduleVal);
    if (Number.isNaN(targetDate.getTime()) || targetDate.getTime() <= Date.now()) {
      notify("error", "Invalid time", "Please choose a future date and time.");
      return;
    }
    setUpdatingJobId(jobId);
    try {
      const updated = await videoApi.rescheduleJob(jobId, targetDate.toISOString());
      setJobs((prev) => prev.map((j) => (j.id === updated.id ? updated : j)));
      setEditingJobId(null);
      notify("success", "Upload time updated", `Auto-upload rescheduled for ${targetDate.toLocaleString()}.`);
    } catch (err) {
      notify("error", "Could not update schedule", getApiErrorMessage(err));
    } finally {
      setUpdatingJobId(null);
    }
  };

  const handleCancelJob = async (jobId: string) => {
    setUpdatingJobId(jobId);
    try {
      await videoApi.cancelJob(jobId);
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
      notify("info", "Job removed from history");
    } catch (err) {
      notify("error", "Could not delete job", getApiErrorMessage(err));
    } finally {
      setUpdatingJobId(null);
    }
  };

  const handleClearJobs = async () => {
    if (!window.confirm("Delete all publishing jobs history (active uploads will be kept)?")) return;
    try {
      await videoApi.clearJobs();
      setJobs((prev) => prev.filter((j) => j.status === "uploading"));
      notify("info", "Publishing history cleared");
    } catch (err) {
      notify("error", "Could not clear publishing history", getApiErrorMessage(err));
    }
  };

  const handleDeleteMedia = async (mediaId: string) => {
    try {
      await videoApi.removeVideo(mediaId);
      const remaining = mediaList.filter((m) => m.id !== mediaId);
      setMediaList(remaining);
      setJobs((prev) => prev.filter((j) => j.media_id !== mediaId));
      if (activeMedia?.id === mediaId) {
        if (remaining.length > 0) hydratePreview(remaining[0]);
        else setActiveMedia(null);
      }
      notify("info", "Uploaded video deleted");
    } catch (err) {
      notify("error", "Could not delete video", getApiErrorMessage(err));
    }
  };

  const handleClearMedia = async () => {
    if (!window.confirm("Delete all uploaded videos from studio history?")) return;
    try {
      await videoApi.clearVideos();
      const latestVids = await videoApi.list();
      const latestJobs = await videoApi.jobs();
      setMediaList(latestVids);
      setJobs(latestJobs);
      if (latestVids.length > 0) hydratePreview(latestVids[0]);
      else setActiveMedia(null);
      notify("info", "Uploaded videos history cleared");
    } catch (err) {
      notify("error", "Could not clear videos", getApiErrorMessage(err));
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadPct(0);
    try {
      const uploaded = await videoApi.upload(file, (pct) => setUploadPct(pct));
      setMediaList((prev) => [uploaded, ...prev]);
      hydratePreview(uploaded);
      notify("success", "Video uploaded", `${uploaded.original_filename} metadata extracted.`);
    } catch (err) {
      notify("error", "Upload rejected", getApiErrorMessage(err));
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleAnalyzeVideo = async () => {
    if (!activeMedia) return;
    setAnalyzing(true);
    try {
      const updated = await videoApi.analyze(activeMedia.id, customNotes);
      setMediaList((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
      hydratePreview(updated);
      notify("success", "Video analyzed", "Frames sampled, audio transcribed, and content mapped.");
    } catch (err) {
      notify("error", "Video analysis failed", getApiErrorMessage(err));
    } finally {
      setAnalyzing(false);
    }
  };

  const handleGenerateMetadata = async () => {
    if (!activeMedia) return;
    setGeneratingMeta(true);
    try {
      const updated = await videoApi.generateMetadata(activeMedia.id, "Professional");
      setMediaList((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
      hydratePreview(updated);
      notify("success", "SEO metadata ready", "Review and edit the preview before publishing.");
    } catch (err) {
      notify("error", "Metadata generation failed", getApiErrorMessage(err));
    } finally {
      setGeneratingMeta(false);
    }
  };

  const handleConnectYouTube = async () => {
    try {
      const res = await videoApi.connectYouTube();
      if (res.configured && res.authorization_url) {
        window.location.href = res.authorization_url;
      } else {
        setOauthNotice(res.message);
        notify("info", "Google OAuth setup required", res.message);
      }
    } catch (err) {
      notify("error", "OAuth error", getApiErrorMessage(err));
    }
  };

  const handlePublishSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeMedia) return;
    if (pubAction !== "draft" && !userConfirmed) {
      notify("error", "Confirmation required", "You must explicitly check the confirmation box before uploading to YouTube.");
      return;
    }
    if (pubAction === "schedule") {
      const target = new Date(scheduledAt);
      if (!scheduledAt || Number.isNaN(target.getTime()) || target.getTime() <= Date.now()) {
        notify("error", "Invalid upload time", "Please set a future date and time for automatic YouTube upload.");
        return;
      }
    }
    setPublishing(true);
    try {
      const job = await videoApi.publish({
        media_id: activeMedia.id,
        channel_id: selectedChannelId || null,
        title: pubTitle.trim(),
        description: pubDescription,
        tags: pubTags
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
        category_id: pubCategoryId,
        privacy_status: pubPrivacy,
        publish_action: pubAction,
        scheduled_publish_at: pubAction === "schedule" && scheduledAt ? new Date(scheduledAt).toISOString() : null,
        pinned_comment: pubPinned,
        user_confirmed: userConfirmed,
      });
      setJobs((prev) => [job, ...prev]);
      notify(
        "success",
        pubAction === "draft"
          ? "Publishing draft saved"
          : pubAction === "schedule"
            ? "Auto-upload timer set"
            : "Upload job queued",
        pubAction === "draft"
          ? "Saved safely in your workspace."
          : pubAction === "schedule"
            ? `Video will automatically upload to YouTube at ${new Date(scheduledAt).toLocaleString()}.`
            : "Tracking resumable YouTube Data API upload status."
      );
    } catch (err) {
      notify("error", "Publishing action failed", getApiErrorMessage(err));
    } finally {
      setPublishing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white">AI Video Upload & Publishing Studio</h1>
          <p className="mt-1 text-sm text-slate-400">
            Upload videos, extract FFmpeg technical specs & audio transcripts, generate SEO metadata, and publish via
            official YouTube OAuth 2.0 with explicit confirmation.
          </p>
        </div>

        <button onClick={handleConnectYouTube} className="tm-btn-secondary">
          <Youtube className="h-4 w-4 text-rose-400" />
          Connect YouTube Channel (OAuth 2.0)
        </button>
      </div>

      {oauthNotice && <DisclaimerNote text={oauthNotice} variant="warning" />}

      {/* Connected Channels Strip */}
      {channels.length > 0 && (
        <div className="tm-card p-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-emerald-400">
            Connected YouTube Channels
          </p>
          <div className="flex flex-wrap gap-3">
            {channels.map((ch) => (
              <div
                key={ch.id}
                className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-xs"
              >
                <Youtube className="h-4 w-4 text-rose-400" />
                <div>
                  <p className="font-semibold text-white">{ch.channel_title}</p>
                  <p className="text-[10px] text-slate-400">{ch.subscriber_count.toLocaleString()} subscribers</p>
                </div>
                <button
                  onClick={async () => {
                    await videoApi.disconnectChannel(ch.id);
                    setChannels((prev) => prev.filter((c) => c.id !== ch.id));
                    notify("info", "Channel disconnected");
                  }}
                  className="ml-2 text-slate-500 hover:text-rose-400"
                  aria-label="Disconnect channel"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Step 1: Upload Dropzone */}
      <div className="tm-card border-dashed border-indigo-500/40 p-6 text-center">
        <UploadCloud className="mx-auto h-10 w-10 text-indigo-400" />
        <h3 className="mt-3 text-sm font-semibold text-white">Step 1: Upload Video File (MP4, MOV, WebM, MKV, AVI)</h3>
        <p className="mt-1 text-xs text-slate-400">
          Validated via MIME type & container header bytes. FFprobe automatically extracts duration, resolution, FPS &
          audio specs.
        </p>
        <div className="mt-4">
          <label className="tm-btn-primary cursor-pointer">
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Film className="h-4 w-4" />}
            {uploading ? `Uploading ${uploadPct}%...` : "Select Video File"}
            <input
              type="file"
              accept="video/mp4,video/quicktime,video/webm,video/x-matroska,video/x-msvideo,.mp4,.mov,.webm,.mkv,.avi"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
        {uploading && (
          <div className="mx-auto mt-4 h-2 w-full max-w-md overflow-hidden rounded-full bg-slate-800">
            <div className="h-full bg-indigo-500 transition-all" style={{ width: `${uploadPct}%` }} />
          </div>
        )}
      </div>

      {/* Uploaded Media Selector */}
      {mediaList.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Uploaded Videos ({mediaList.length})
            </span>
            <button
              type="button"
              onClick={() => void handleClearMedia()}
              className="inline-flex items-center gap-1 text-xs text-rose-400 hover:text-rose-300"
            >
              <Trash2 className="h-3.5 w-3.5" /> Clear Videos
            </button>
          </div>
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {mediaList.map((m) => (
              <div
                key={m.id}
                onClick={() => hydratePreview(m)}
                className={`flex shrink-0 cursor-pointer items-start gap-2 rounded-xl border px-3 py-2 text-left text-xs transition ${
                  activeMedia?.id === m.id
                    ? "border-indigo-500 bg-indigo-500/15 text-white"
                    : "border-slate-800 bg-slate-900/70 text-slate-400 hover:border-slate-700"
                }`}
              >
                <div>
                  <p className="max-w-[180px] truncate font-medium">{m.original_filename}</p>
                  <p className="text-[10px] text-slate-400">
                    {formatBytes(m.file_size_bytes)} • {m.analysis_status}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    void handleDeleteMedia(m.id);
                  }}
                  className="rounded p-1 text-slate-500 hover:bg-rose-500/20 hover:text-rose-300"
                  aria-label="Delete uploaded video"
                  title="Delete uploaded video"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {!activeMedia ? (
        <EmptyState
          icon={Film}
          title="Upload a video to start the studio workflow"
          description="Campaign Intelligence extracts video metadata, samples frames, transcribes audio, generates SEO titles/chapters, and prepares confirmed YouTube publishing."
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          {/* Left Column: Step 2 Technical Specs + Step 3 Analysis + Step 4 Metadata */}
          <div className="space-y-5 lg:col-span-6">
            <div className="tm-card p-5">
              <h3 className="text-sm font-semibold text-white">Step 2: Extracted Technical Metadata</h3>
              <div className="mt-3 grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
                {[
                  ["File Size", formatBytes(activeMedia.file_size_bytes)],
                  ["Duration", formatDuration(activeMedia.duration_seconds)],
                  ["Resolution", activeMedia.width ? `${activeMedia.width}×${activeMedia.height}` : "Install FFmpeg"],
                  ["Aspect Ratio", activeMedia.aspect_ratio],
                  ["Frame Rate", activeMedia.frame_rate ? `${activeMedia.frame_rate} fps` : "—"],
                  ["Audio", `${activeMedia.audio_codec} (${activeMedia.audio_channels}ch)`],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-xl bg-slate-900/80 p-3">
                    <p className="text-[10px] uppercase text-slate-500">{k}</p>
                    <p className="mt-0.5 font-semibold text-slate-200">{v}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="tm-card p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white">Step 3 & 4: AI Video Analysis & Metadata</h3>
              <input
                type="text"
                value={customNotes}
                onChange={(e) => setCustomNotes(e.target.value)}
                placeholder="Optional creator notes (e.g., product demo, target keywords)..."
                className="tm-input text-xs"
              />
              <div className="flex flex-wrap gap-2.5">
                <button onClick={handleAnalyzeVideo} disabled={analyzing} className="tm-btn-secondary text-xs">
                  {analyzing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5 text-cyan-400" />}
                  {analyzing ? "Transcribing & Analyzing..." : "Analyze Video & Transcribe"}
                </button>
                <button onClick={handleGenerateMetadata} disabled={generatingMeta} className="tm-btn-primary text-xs">
                  {generatingMeta ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                  {generatingMeta ? "Generating..." : "Auto-Generate SEO Metadata"}
                </button>
              </div>

              {activeMedia.transcript_text && (
                <div className="rounded-xl border border-slate-800 bg-[#080E1B] p-3 text-xs">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-semibold text-slate-300">Audio Transcript</span>
                    <CopyButton text={activeMedia.transcript_text} />
                  </div>
                  <p className="max-h-32 overflow-y-auto text-slate-400 leading-relaxed">
                    {activeMedia.transcript_text}
                  </p>
                </div>
              )}

              {activeMedia.generated_metadata_json?.titles && (
                <div className="space-y-2 pt-2">
                  <p className="text-xs font-semibold text-indigo-300">Suggested Titles (click to apply):</p>
                  {activeMedia.generated_metadata_json.titles.map((t, idx) => (
                    <button
                      type="button"
                      key={idx}
                      onClick={() => setPubTitle(t)}
                      className="block w-full rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-left text-xs text-slate-200 hover:border-indigo-500/50"
                    >
                      {t}
                    </button>
                  ))}
                </div>
              )}

              {activeMedia.generated_metadata_json?.thumbnail_concepts && (
                <div className="space-y-2 pt-2">
                  <p className="text-xs font-semibold text-violet-300">Thumbnail Concepts:</p>
                  {activeMedia.generated_metadata_json.thumbnail_concepts.map((tc, i) => (
                    <div key={i} className="rounded-lg bg-slate-900/70 p-2.5 text-xs">
                      <span className="font-bold text-amber-300">[{tc.overlay_text}]</span>{" "}
                      <span className="text-slate-300">{tc.concept}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Step 5-8 Editable Preview & Confirmed Publishing */}
          <div className="space-y-5 lg:col-span-6">
            <form onSubmit={handlePublishSubmit} className="tm-card p-5 space-y-4">
              <h3 className="text-sm font-semibold text-white">Step 5–8: Editable Preview & Publishing</h3>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">Video Title (max 100 chars)</label>
                <input
                  type="text"
                  required
                  maxLength={100}
                  value={pubTitle}
                  onChange={(e) => setPubTitle(e.target.value)}
                  className="tm-input"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">Description & Chapters</label>
                <textarea
                  rows={6}
                  value={pubDescription}
                  onChange={(e) => setPubDescription(e.target.value)}
                  className="tm-input font-mono text-xs"
                />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-300">SEO Tags (comma-separated)</label>
                  <input type="text" value={pubTags} onChange={(e) => setPubTags(e.target.value)} className="tm-input text-xs" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-300">YouTube Category ID</label>
                  <input type="text" value={pubCategoryId} onChange={(e) => setPubCategoryId(e.target.value)} className="tm-input text-xs" />
                </div>
              </div>

              <div>
                <label className="mb-1 block text-xs font-medium text-slate-300">Pinned Comment Suggestion</label>
                <input type="text" value={pubPinned} onChange={(e) => setPubPinned(e.target.value)} className="tm-input text-xs" />
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-300">Action</label>
                  <select
                    value={pubAction}
                    onChange={(e) => setPubAction(e.target.value as "draft" | "upload" | "schedule")}
                    className="tm-input text-xs"
                  >
                    <option value="draft">Save as Local Draft</option>
                    <option value="upload">Upload to YouTube Now</option>
                    <option value="schedule">Schedule Auto-Upload (Set Time)</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-medium text-slate-300">Visibility</label>
                  <select
                    value={pubPrivacy}
                    onChange={(e) => setPubPrivacy(e.target.value as "private" | "unlisted" | "public")}
                    className="tm-input text-xs"
                  >
                    <option value="private">Private</option>
                    <option value="unlisted">Unlisted</option>
                    <option value="public">Public</option>
                  </select>
                </div>
              </div>

              {pubAction === "schedule" && (
                <div className="rounded-xl border border-cyan-500/30 bg-cyan-500/5 p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <label className="flex items-center gap-1.5 text-xs font-semibold text-cyan-300">
                      <CalendarClock className="h-4 w-4" />
                      Auto-Upload Time Setter
                    </label>
                    <span className="text-[10px] text-slate-400">
                      Local time ({Intl.DateTimeFormat().resolvedOptions().timeZone})
                    </span>
                  </div>
                  <input
                    type="datetime-local"
                    required
                    min={toLocalDateTimeInput(new Date(nowMs))}
                    value={scheduledAt}
                    onChange={(e) => setScheduledAt(e.target.value)}
                    className="tm-input text-xs"
                  />
                  <div className="flex flex-wrap gap-1.5">
                    {[
                      { label: "+2 min", mins: 2 },
                      { label: "+5 min", mins: 5 },
                      { label: "+15 min", mins: 15 },
                      { label: "+1 hour", mins: 60 },
                    ].map((preset) => (
                      <button
                        key={preset.label}
                        type="button"
                        onClick={() => applyQuickScheduleOffset(preset.mins)}
                        className="rounded-lg border border-slate-700 bg-slate-900/80 px-2.5 py-1 text-[11px] text-slate-300 hover:border-cyan-500/60 hover:text-cyan-200 transition"
                      >
                        {preset.label}
                      </button>
                    ))}
                    <button
                      type="button"
                      onClick={applyTomorrowNineAm}
                      className="rounded-lg border border-slate-700 bg-slate-900/80 px-2.5 py-1 text-[11px] text-slate-300 hover:border-cyan-500/60 hover:text-cyan-200 transition"
                    >
                      Tomorrow 9:00 AM
                    </button>
                  </div>
                  {scheduledAt && (() => {
                    const dt = new Date(scheduledAt);
                    const valid = !Number.isNaN(dt.getTime()) && dt.getTime() > nowMs;
                    return (
                      <p className={`text-[11px] ${valid ? "text-cyan-200/90" : "text-rose-300"}`}>
                        {valid
                          ? `Will automatically upload to YouTube on ${dt.toLocaleString()} (in ${formatCountdown(dt, nowMs)}). Keep the backend server running.`
                          : "Please select a future date and time."}
                      </p>
                    );
                  })()}
                </div>
              )}

              {pubAction !== "draft" && (
                <>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-slate-300">Target Connected Channel</label>
                    <select
                      value={selectedChannelId}
                      onChange={(e) => setSelectedChannelId(e.target.value)}
                      className="tm-input text-xs"
                    >
                      <option value="">— Select connected channel —</option>
                      {channels.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.channel_title}
                        </option>
                      ))}
                    </select>
                  </div>

                  <label className="flex cursor-pointer items-start gap-2.5 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-200">
                    <input
                      type="checkbox"
                      checked={userConfirmed}
                      onChange={(e) => setUserConfirmed(e.target.checked)}
                      className="mt-0.5 rounded border-amber-500 bg-slate-900"
                    />
                    <span>
                      <strong className="text-amber-300">Explicit Confirmation Required:</strong> I confirm I want
                      Campaign Intelligence to{" "}
                      {pubAction === "schedule"
                        ? "automatically upload this video at the scheduled time"
                        : "upload this video"}{" "}
                      to my connected YouTube channel with visibility{" "}
                      <strong>{pubPrivacy.toUpperCase()}</strong> via the YouTube Data API v3.
                    </span>
                  </label>
                </>
              )}

              <button type="submit" disabled={publishing} className="tm-btn-primary w-full">
                {publishing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : pubAction === "schedule" ? (
                  <CalendarClock className="h-4 w-4" />
                ) : (
                  <Link2 className="h-4 w-4" />
                )}
                {pubAction === "draft"
                  ? "Save Publishing Draft"
                  : pubAction === "schedule"
                    ? "Confirm & Set Auto-Upload Timer"
                    : "Confirm & Queue YouTube Upload"}
              </button>
            </form>

            {/* Publishing Jobs History */}
            <div className="tm-card p-5">
              <div className="mb-3 flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-white">Publishing Jobs & Auto-Upload Queue</h3>
                <div className="flex items-center gap-3">
                  {hasActiveJobs && (
                    <span className="inline-flex items-center gap-1.5 text-[11px] text-cyan-300">
                      <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse" />
                      Auto-updating
                    </span>
                  )}
                  {jobs.length > 0 && (
                    <button
                      type="button"
                      onClick={() => void handleClearJobs()}
                      className="inline-flex items-center gap-1 text-[11px] text-rose-400 hover:text-rose-300"
                    >
                      <Trash2 className="h-3 w-3" /> Clear History
                    </button>
                  )}
                </div>
              </div>
              {jobs.length === 0 ? (
                <p className="text-xs text-slate-500">No drafts or upload jobs yet.</p>
              ) : (
                <div className="space-y-2.5">
                  {jobs.slice(0, 8).map((j) => {
                    const schedDate = parseUtcDate(j.scheduled_publish_at);
                    const isScheduledUpload = j.status === "scheduled_upload";
                    const isEditingThis = editingJobId === j.id;
                    return (
                      <div key={j.id} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-xs space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-white truncate">{j.title}</span>
                          <div className="flex shrink-0 items-center gap-1.5">
                            <span
                              className={`tm-badge ${
                                j.status === "published" || j.status === "scheduled"
                                  ? "bg-emerald-500/15 text-emerald-300"
                                  : isScheduledUpload
                                    ? "bg-cyan-500/15 text-cyan-300"
                                    : j.status === "failed" || j.status === "interrupted"
                                      ? "bg-rose-500/15 text-rose-300"
                                      : "bg-indigo-500/15 text-indigo-300"
                              }`}
                            >
                              {j.status === "published" ? (
                                <CheckCircle2 className="h-3 w-3" />
                              ) : j.status === "failed" ? (
                                <ShieldAlert className="h-3 w-3" />
                              ) : isScheduledUpload ? (
                                <CalendarClock className="h-3 w-3" />
                              ) : (
                                <Clock className="h-3 w-3" />
                              )}
                              {isScheduledUpload ? "auto-upload scheduled" : j.status} ({j.privacy_status})
                            </span>
                            {j.status !== "uploading" && (
                              <button
                                type="button"
                                disabled={updatingJobId === j.id}
                                onClick={() => void handleCancelJob(j.id)}
                                className="rounded p-1 text-slate-500 hover:bg-rose-500/20 hover:text-rose-300"
                                aria-label="Delete job from history"
                                title="Delete from history"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            )}
                          </div>
                        </div>

                        {isScheduledUpload && schedDate && (
                          <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 px-2.5 py-2 space-y-2">
                            <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
                              <span className="text-slate-300">
                                Scheduled: <strong className="text-white">{schedDate.toLocaleString()}</strong>
                              </span>
                              <span className="font-mono font-semibold text-cyan-300">
                                {formatCountdown(schedDate, nowMs)}
                              </span>
                            </div>

                            {isEditingThis ? (
                              <div className="flex flex-wrap items-center gap-2">
                                <input
                                  type="datetime-local"
                                  min={toLocalDateTimeInput(new Date(nowMs))}
                                  value={editingScheduleVal}
                                  onChange={(e) => setEditingScheduleVal(e.target.value)}
                                  className="tm-input py-1 text-[11px] flex-1 min-w-[180px]"
                                />
                                <button
                                  type="button"
                                  disabled={updatingJobId === j.id}
                                  onClick={() => handleRescheduleJob(j.id)}
                                  className="rounded-lg bg-cyan-600 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-cyan-500"
                                >
                                  Save
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setEditingJobId(null)}
                                  className="rounded-lg border border-slate-700 px-2.5 py-1 text-[11px] text-slate-300 hover:text-white"
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <div className="flex items-center gap-2">
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingJobId(j.id);
                                    setEditingScheduleVal(toLocalDateTimeInput(schedDate));
                                  }}
                                  className="text-[11px] text-cyan-300 hover:underline"
                                >
                                  Change time
                                </button>
                                <span className="text-slate-600">•</span>
                                <button
                                  type="button"
                                  disabled={updatingJobId === j.id}
                                  onClick={() => handleCancelJob(j.id)}
                                  className="text-[11px] text-rose-400 hover:underline"
                                >
                                  Cancel auto-upload
                                </button>
                              </div>
                            )}
                          </div>
                        )}

                        {j.upload_progress_pct > 0 && j.status === "uploading" && (
                          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                            <div className="h-full bg-indigo-500 transition-all" style={{ width: `${j.upload_progress_pct}%` }} />
                          </div>
                        )}
                        {j.youtube_video_url && (
                          <a
                            href={j.youtube_video_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-block text-indigo-400 hover:underline"
                          >
                            View published video →
                          </a>
                        )}
                        {j.error_message && <p className="text-rose-300">{j.error_message}</p>}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
