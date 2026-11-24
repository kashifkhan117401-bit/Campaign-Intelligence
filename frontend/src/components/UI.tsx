import React, { useState } from "react";
import { AlertTriangle, Check, Copy, FlaskConical, Info, LucideIcon } from "lucide-react";

export function SkeletonCard({ className = "h-32" }: { className?: string }) {
  return (
    <div className={`animate-pulse rounded-2xl border border-slate-800/70 bg-slate-900/70 ${className}`} />
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="tm-card flex flex-col items-center justify-center px-6 py-14 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-indigo-500/30 bg-indigo-500/10 text-indigo-400">
        <Icon className="h-7 w-7" />
      </div>
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="mt-1.5 max-w-md text-sm text-slate-400">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}

export function DemoDataBanner({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-xs text-amber-200">
      <FlaskConical className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
      <div>
        <span className="font-semibold text-amber-300">Development Demo Data Active:</span>{" "}
        These results were generated using visibly labeled demo data because external YouTube or Gemini AI API keys are not yet configured in <code className="rounded bg-amber-950/60 px-1 py-0.5 font-mono">.env</code>.
      </div>
    </div>
  );
}

export function DisclaimerNote({ text, variant = "info" }: { text: string; variant?: "info" | "warning" }) {
  const isWarn = variant === "warning";
  return (
    <div
      className={`flex items-start gap-2.5 rounded-xl border px-3.5 py-2.5 text-xs ${
        isWarn
          ? "border-amber-500/30 bg-amber-500/5 text-amber-200/90"
          : "border-slate-700/70 bg-slate-900/60 text-slate-400"
      }`}
    >
      {isWarn ? (
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
      ) : (
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-indigo-400" />
      )}
      <span>{text}</span>
    </div>
  );
}

export function StatCard({
  label,
  value,
  subtext,
  icon: Icon,
  accent = "indigo",
}: {
  label: string;
  value: string | number;
  subtext?: string;
  icon: LucideIcon;
  accent?: "indigo" | "emerald" | "violet" | "cyan" | "amber" | "rose";
}) {
  const accentMap: Record<string, string> = {
    indigo: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
    emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    violet: "text-violet-400 bg-violet-500/10 border-violet-500/20",
    cyan: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
    amber: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    rose: "text-rose-400 bg-rose-500/10 border-rose-500/20",
  };
  return (
    <div className="tm-card-hover p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-slate-400">{label}</p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-white">{value}</p>
          {subtext && <p className="mt-1 text-xs text-slate-400">{subtext}</p>}
        </div>
        <div className={`flex h-10 w-10 items-center justify-center rounded-xl border ${accentMap[accent]}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      // Fallback ignored
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700/80 bg-slate-800/80 px-2.5 py-1 text-xs font-medium text-slate-300 hover:border-indigo-500/50 hover:text-white transition"
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
      {copied ? "Copied" : label}
    </button>
  );
}
