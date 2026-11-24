import React from "react";
import { FileCheck2, Lock, ShieldCheck, X } from "lucide-react";
import { BrandLogo } from "./BrandLogo";

export type LegalDocType = "privacy" | "terms";

export function LegalDocumentContent({ docType }: { docType: LegalDocType }) {
  if (docType === "privacy") {
    return (
      <div className="space-y-5 text-xs leading-relaxed text-slate-300">
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-emerald-200">
          <div className="flex items-center gap-2 font-semibold text-emerald-300">
            <ShieldCheck className="h-4 w-4" />
            <span>Campaign Intelligence — Privacy &amp; Security Commitment</span>
          </div>
          <p className="mt-1.5 text-emerald-100/90">
            We treat your workspace data, audience analytics, and connected YouTube credentials with strict
            encryption, isolation, and transparency. Effective Date: November 2026.
          </p>
        </div>

        <section className="space-y-1.5">
          <h3 className="text-sm font-semibold text-white">1. Information We Collect</h3>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong>Account &amp; Profile Data:</strong> Email address, full name, optional company/channel name,
              niche preferences, and benchmark defaults you configure.
            </li>
            <li>
              <strong>Public YouTube Data:</strong> Public video metadata and top-level public comments retrieved via
              the YouTube Data API v3 solely for videos you submit for analysis.
            </li>
            <li>
              <strong>Uploaded Videos &amp; Publishing Metadata:</strong> Videos you upload to Video Publishing Studio,
              sampled keyframes, transcripts, and publishing job schedules you create.
            </li>
            <li>
              <strong>Google OAuth 2.0 Tokens:</strong> When you connect a YouTube channel, access and refresh tokens
              are stored strictly server-side and never exposed to browser JavaScript.
            </li>
          </ul>
        </section>

        <section className="space-y-1.5">
          <h3 className="text-sm font-semibold text-white">2. Security Architecture &amp; Controls</h3>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong>Password Protection:</strong> Passwords are hashed using adaptive bcrypt and are never stored or
              logged in plaintext.
            </li>
            <li>
              <strong>Session &amp; Login Security:</strong> Short-lived JWT access tokens, SHA-256 hashed rotating
              refresh tokens, and server-verified single-use CAPTCHA challenges protect login and registration.
            </li>
            <li>
              <strong>Encryption at Rest:</strong> YouTube OAuth access and refresh tokens are encrypted at rest using
              Fernet authenticated symmetric encryption.
            </li>
            <li>
              <strong>Prompt-Injection Defense:</strong> Untrusted user-generated YouTube comments and transcripts are
              sanitized and delimited before AI processing.
            </li>
            <li>
              <strong>Strict User Isolation:</strong> Every analysis, content pack, video upload, publishing job, ad
              strategy, and PDF report is scoped exclusively to your authenticated account.
            </li>
          </ul>
        </section>

        <section className="space-y-1.5">
          <h3 className="text-sm font-semibold text-white">3. AI &amp; Third-Party Services</h3>
          <p>
            Campaign Intelligence connects to Google Gemini AI (or your configured LLM provider) to analyze comment
            sentiment, generate content packs, and transcribe uploaded videos, and uses Google YouTube Data API v3 &amp;
            OAuth 2.0 for comment retrieval and user-confirmed video uploads. You can revoke Google OAuth access at any
            time from Settings/Video Studio or your Google Account security page.
          </p>
        </section>

        <section className="space-y-1.5">
          <h3 className="text-sm font-semibold text-white">4. Your Privacy Rights &amp; Data Control</h3>
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <strong>Granular Deletion:</strong> Delete individual records or clear entire history across Analyses,
              Content Studio, Video Studio, Ads Planner, PDF Reports, and Campaign History at any time.
            </li>
            <li>
              <strong>Data Portability:</strong> Download a complete JSON export of your account and workspace records
              from Settings → Privacy &amp; Security.
            </li>
            <li>
              <strong>Right to Erasure:</strong> Permanently delete your account, uploaded files, PDF reports, and all
              associated records from Settings → Privacy &amp; Security.
            </li>
          </ul>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-5 text-xs leading-relaxed text-slate-300">
      <div className="rounded-xl border border-indigo-500/30 bg-indigo-500/10 p-4 text-indigo-200">
        <div className="flex items-center gap-2 font-semibold text-indigo-300">
          <FileCheck2 className="h-4 w-4" />
          <span>Campaign Intelligence — Terms &amp; Conditions</span>
        </div>
        <p className="mt-1.5 text-indigo-100/90">
          By signing in, creating an account, or using Campaign Intelligence, you agree to the terms below. Effective
          Date: November 2026.
        </p>
      </div>

      <section className="space-y-1.5">
        <h3 className="text-sm font-semibold text-white">1. Acceptance &amp; Authorized Use</h3>
        <p>
          You agree to use Campaign Intelligence solely for lawful marketing research, audience intelligence, content
          creation, and channel management. You are responsible for maintaining the confidentiality of your account
          credentials and for all actions performed under your account.
        </p>
      </section>

      <section className="space-y-1.5">
        <h3 className="text-sm font-semibold text-white">2. YouTube API Services &amp; Publishing</h3>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            Use of YouTube comment analysis and OAuth video publishing is subject to the{" "}
            <span className="text-white font-medium">YouTube Terms of Service</span> and{" "}
            <span className="text-white font-medium">Google Privacy Policy</span>.
          </li>
          <li>
            You must own or hold valid rights and permissions for every video you upload, schedule, or publish to a
            connected YouTube channel.
          </li>
          <li>
            Scheduled automatic uploads require explicit confirmation and run when the scheduled time is reached while
            the service is active.
          </li>
        </ul>
      </section>

      <section className="space-y-1.5">
        <h3 className="text-sm font-semibold text-white">3. AI-Generated Content &amp; Estimates Disclaimer</h3>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            Sentiment classifications, emotion labels, audience opportunity scores, scripts, SEO titles, and hashtags
            are AI-generated suggestions and are not guaranteed to achieve specific search rankings, views, or revenue.
          </li>
          <li>
            Advertising budget calculations (estimated views, impressions, reach, and clicks) are illustrative
            estimates based on configurable benchmark formulas and are not official Google Ads forecasts.
          </li>
        </ul>
      </section>

      <section className="space-y-1.5">
        <h3 className="text-sm font-semibold text-white">4. Prohibited Conduct &amp; Termination</h3>
        <p>
          You may not attempt to bypass CAPTCHA or authentication controls, scrape private/unauthorized data, upload
          malicious files, or abuse external API quotas. We reserve the right to suspend accounts violating these
          terms. You may delete your account and workspace data at any time from Settings → Privacy &amp; Security.
        </p>
      </section>

      <section className="space-y-1.5">
        <h3 className="text-sm font-semibold text-white">5. Intellectual Property &amp; Ownership</h3>
        <p>
          Campaign Intelligence, its brand identity, logo, software, and platform design are the intellectual property
          of <strong>Kashif Hafeez</strong>. © {new Date().getFullYear()} Kashif Hafeez. All rights reserved.
        </p>
      </section>
    </div>
  );
}

interface LegalModalProps {
  docType: LegalDocType | null;
  onClose: () => void;
  onSwitch?: (next: LegalDocType) => void;
}

export function LegalModal({ docType, onClose, onSwitch }: LegalModalProps) {
  if (!docType) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="tm-card flex max-h-[85vh] w-full max-w-2xl flex-col overflow-hidden border-slate-700/80 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div className="flex items-center gap-3">
            <BrandLogo size={32} variant="emerald" />
            <div>
              <h2 className="text-base font-bold text-white">
                {docType === "privacy" ? "Privacy & Security Policy" : "Terms & Conditions"}
              </h2>
              <p className="text-[11px] text-slate-400">Campaign Intelligence Legal &amp; Security Center</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {onSwitch && (
          <div className="flex gap-2 border-b border-slate-800 bg-[#080E1B] px-5 py-2.5">
            <button
              type="button"
              onClick={() => onSwitch("privacy")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                docType === "privacy"
                  ? "bg-emerald-600 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <Lock className="h-3.5 w-3.5" /> Privacy &amp; Security
            </button>
            <button
              type="button"
              onClick={() => onSwitch("terms")}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                docType === "terms"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <FileCheck2 className="h-3.5 w-3.5" /> Terms &amp; Conditions
            </button>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-5 py-4">
          <LegalDocumentContent docType={docType} />
        </div>

        <div className="flex items-center justify-between border-t border-slate-800 px-5 py-3">
          <span className="text-[11px] text-slate-500">© {new Date().getFullYear()} Kashif Hafeez. All rights reserved.</span>
          <button type="button" onClick={onClose} className="tm-btn-primary py-2 text-xs">
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
