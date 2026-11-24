import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  CheckCircle2,
  Download,
  FileCheck2,
  KeyRound,
  Lock,
  LogOut,
  Save,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Trash2,
  User as UserIcon,
  XCircle,
} from "lucide-react";
import { LegalModal, type LegalDocType } from "../components/LegalModal";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import { authApi, clearStoredTokens } from "../services/api";
import type { IntegrationStatus } from "../types";
import { getApiErrorMessage } from "../utils/format";

export function SettingsPage() {
  const { user, refreshUser, logout } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState(user?.profile?.full_name || "");
  const [company, setCompany] = useState(user?.profile?.company_name || "");
  const [jobTitle, setJobTitle] = useState(user?.profile?.job_title || "");
  const [niche, setNiche] = useState(user?.profile?.niche || "");
  const [bio, setBio] = useState(user?.profile?.bio || "");

  const [defaultTone, setDefaultTone] = useState(user?.settings?.default_tone || "Professional");
  const [defaultCurrency, setDefaultCurrency] = useState(user?.settings?.default_currency || "USD");
  const [cpv, setCpv] = useState(user?.settings?.benchmark_cpv ?? 0.035);
  const [cpm, setCpm] = useState(user?.settings?.benchmark_cpm ?? 8.5);
  const [ctr, setCtr] = useState(user?.settings?.benchmark_ctr ?? 0.012);
  const [emailNotifications, setEmailNotifications] = useState(user?.settings?.email_notifications ?? true);

  const [integrations, setIntegrations] = useState<IntegrationStatus | null>(null);
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);

  // Privacy & Security state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [exportingData, setExportingData] = useState(false);
  const [revokingSessions, setRevokingSessions] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [legalDoc, setLegalDoc] = useState<LegalDocType | null>(null);

  useEffect(() => {
    authApi
      .integrations()
      .then(setIntegrations)
      .catch(() => {});
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingProfile(true);
    try {
      await authApi.updateProfile({
        full_name: fullName,
        company_name: company,
        job_title: jobTitle,
        niche,
        bio,
      });
      await refreshUser();
      notify("success", "Profile updated");
    } catch (err) {
      notify("error", "Profile update failed", getApiErrorMessage(err));
    } finally {
      setSavingProfile(false);
    }
  };

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    try {
      await authApi.updateSettings({
        default_tone: defaultTone,
        default_currency: defaultCurrency,
        benchmark_cpv: Number(cpv),
        benchmark_cpm: Number(cpm),
        benchmark_ctr: Number(ctr),
        email_notifications: emailNotifications,
      });
      await refreshUser();
      notify("success", "Workspace settings saved");
    } catch (err) {
      notify("error", "Settings update failed", getApiErrorMessage(err));
    } finally {
      setSavingSettings(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setChangingPassword(true);
    try {
      const res = await authApi.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      notify("success", "Password changed", res.message);
    } catch (err) {
      notify("error", "Password change failed", getApiErrorMessage(err));
    } finally {
      setChangingPassword(false);
    }
  };

  const handleRevokeAllSessions = async () => {
    setRevokingSessions(true);
    try {
      await authApi.logout(null);
      clearStoredTokens();
      notify("info", "All sessions signed out", "Please sign in again.");
      navigate("/login");
    } catch (err) {
      notify("error", "Could not revoke sessions", getApiErrorMessage(err));
    } finally {
      setRevokingSessions(false);
    }
  };

  const handleExportData = async () => {
    setExportingData(true);
    try {
      const data = await authApi.exportPrivacyData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "campaign_intelligence_my_data.json";
      a.click();
      URL.revokeObjectURL(url);
      notify("success", "Account data exported", "Downloaded JSON archive of your workspace records.");
    } catch (err) {
      notify("error", "Export failed", getApiErrorMessage(err));
    } finally {
      setExportingData(false);
    }
  };

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (deleteConfirm.trim().toUpperCase() !== "DELETE") {
      notify("error", "Confirmation required", 'Type "DELETE" to confirm permanent account removal.');
      return;
    }
    setDeletingAccount(true);
    try {
      await authApi.deleteAccount(deletePassword, deleteConfirm.trim());
      await logout();
      notify("info", "Account deleted", "Your account and all workspace data have been permanently erased.");
      navigate("/login");
    } catch (err) {
      notify("error", "Account deletion failed", getApiErrorMessage(err));
    } finally {
      setDeletingAccount(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Workspace Settings & Integrations</h1>
        <p className="mt-1 text-sm text-slate-400">
          Manage your profile, advertising benchmark defaults, and inspect backend API integration health.
        </p>
      </div>

      {/* API Integration Health */}
      <div className="tm-card p-5">
        <div className="mb-4 flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-indigo-400" />
          <h2 className="text-sm font-semibold text-white">Server API & Tooling Status (Keys Never Exposed to Browser)</h2>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              label:
                integrations?.llm_provider === "openai"
                  ? `OpenAI (${integrations?.llm_model || "gpt-4o-mini"})`
                  : `Google Gemini (${integrations?.llm_model || "gemini-2.5-flash"})`,
              ok: integrations?.ai_configured ?? integrations?.gemini_configured ?? integrations?.openai_configured,
              env: integrations?.llm_provider === "openai" ? "OPENAI_API_KEY" : "GEMINI_API_KEY",
            },
            { label: "YouTube Data API v3", ok: integrations?.youtube_api_configured, env: "YOUTUBE_API_KEY" },
            { label: "Google OAuth 2.0", ok: integrations?.google_oauth_configured, env: "GOOGLE_CLIENT_ID" },
            { label: "FFmpeg / FFprobe", ok: integrations?.ffmpeg_available, env: "System PATH / Docker" },
          ].map((item) => (
            <div key={item.label} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3.5 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">{item.label}</span>
                {item.ok ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                ) : (
                  <XCircle className="h-4 w-4 text-amber-400" />
                )}
              </div>
              <p className="mt-1 text-[11px] text-slate-400">
                {item.ok ? "Configured & Active" : `Set ${item.env} in backend .env`}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Profile Form */}
        <form onSubmit={handleSaveProfile} className="tm-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <UserIcon className="h-4 w-4 text-cyan-400" />
            <h2 className="text-sm font-semibold text-white">User Profile</h2>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-slate-300">Full Name</label>
              <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} className="tm-input" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-300">Company / Channel</label>
              <input type="text" value={company} onChange={(e) => setCompany(e.target.value)} className="tm-input" />
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-slate-300">Role / Title</label>
              <input type="text" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} className="tm-input" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-300">Primary Niche</label>
              <input type="text" value={niche} onChange={(e) => setNiche(e.target.value)} className="tm-input" />
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs text-slate-300">Bio / Channel Focus</label>
            <textarea rows={3} value={bio} onChange={(e) => setBio(e.target.value)} className="tm-input text-xs" />
          </div>

          <button type="submit" disabled={savingProfile} className="tm-btn-primary">
            <Save className="h-4 w-4" /> {savingProfile ? "Saving..." : "Save Profile"}
          </button>
        </form>

        {/* Preferences & Benchmarks Form */}
        <form onSubmit={handleSaveSettings} className="tm-card p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Sliders className="h-4 w-4 text-violet-400" />
            <h2 className="text-sm font-semibold text-white">AI & Ads Benchmark Defaults</h2>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-slate-300">Default Content Tone</label>
              <select value={defaultTone} onChange={(e) => setDefaultTone(e.target.value)} className="tm-input">
                {["Professional", "Educational", "Conversational", "Persuasive", "Entertaining"].map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-300">Default Currency</label>
              <select value={defaultCurrency} onChange={(e) => setDefaultCurrency(e.target.value)} className="tm-input">
                {["USD", "EUR", "GBP", "CAD", "AUD", "AED", "INR", "PKR"].map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs text-slate-300">Base CPV</label>
              <input
                type="number"
                step="0.005"
                min="0.005"
                value={cpv}
                onChange={(e) => setCpv(Number(e.target.value))}
                className="tm-input"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-300">Base CPM</label>
              <input
                type="number"
                step="0.25"
                min="0.5"
                value={cpm}
                onChange={(e) => setCpm(Number(e.target.value))}
                className="tm-input"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-slate-300">Base CTR (decimal)</label>
              <input
                type="number"
                step="0.001"
                min="0.001"
                max="0.3"
                value={ctr}
                onChange={(e) => setCtr(Number(e.target.value))}
                className="tm-input"
              />
            </div>
          </div>

          <label className="flex cursor-pointer items-center gap-2.5 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={emailNotifications}
              onChange={(e) => setEmailNotifications(e.target.checked)}
              className="rounded border-slate-700 bg-slate-900 text-indigo-500"
            />
            Receive workspace completion notifications
          </label>

          <button type="submit" disabled={savingSettings} className="tm-btn-primary">
            <Save className="h-4 w-4" /> {savingSettings ? "Saving..." : "Save Settings"}
          </button>
        </form>
      </div>

      {/* Privacy & Security + Terms & Conditions */}
      <div className="tm-card p-5 space-y-5">
        <div className="flex flex-col justify-between gap-3 border-b border-slate-800 pb-4 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2.5">
            <Lock className="h-5 w-5 text-emerald-400" />
            <div>
              <h2 className="text-sm font-semibold text-white">Privacy, Security &amp; Legal Center</h2>
              <p className="text-xs text-slate-400">
                Manage password security, active sessions, personal data exports, and review legal policies.
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setLegalDoc("privacy")}
              className="tm-btn-secondary py-1.5 text-xs"
            >
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" /> Privacy &amp; Security Policy
            </button>
            <button
              type="button"
              onClick={() => setLegalDoc("terms")}
              className="tm-btn-secondary py-1.5 text-xs"
            >
              <FileCheck2 className="h-3.5 w-3.5 text-indigo-400" /> Terms &amp; Conditions
            </button>
          </div>
        </div>

        {/* Security Controls Status */}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { title: "Login CAPTCHA", desc: "Single-use server-signed SVG challenge active" },
            { title: "OAuth Token Encryption", desc: "Fernet AES-128 + HMAC encryption at rest" },
            { title: "Prompt-Injection Shield", desc: "Untrusted comments isolated before AI runs" },
            { title: "Per-User Data Isolation", desc: "Strict account-level query & storage scoping" },
          ].map((item) => (
            <div key={item.title} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-xs">
              <div className="flex items-center gap-1.5 font-semibold text-emerald-300">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>{item.title}</span>
              </div>
              <p className="mt-1 text-[11px] text-slate-400">{item.desc}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Change Password & Session Controls */}
          <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <form onSubmit={handleChangePassword} className="space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-white">
                <KeyRound className="h-4 w-4 text-indigo-400" /> Change Password
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <input
                  type="password"
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Current password"
                  className="tm-input text-xs"
                />
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="New password (min 8 chars)"
                  className="tm-input text-xs"
                />
              </div>
              <button type="submit" disabled={changingPassword} className="tm-btn-primary py-2 text-xs">
                <KeyRound className="h-3.5 w-3.5" />
                {changingPassword ? "Updating..." : "Update Password"}
              </button>
            </form>

            <div className="flex flex-wrap gap-2 border-t border-slate-800 pt-3">
              <button
                type="button"
                onClick={() => void handleExportData()}
                disabled={exportingData}
                className="tm-btn-secondary py-2 text-xs"
              >
                <Download className="h-3.5 w-3.5 text-cyan-400" />
                {exportingData ? "Exporting..." : "Download My Data (JSON)"}
              </button>
              <button
                type="button"
                onClick={() => void handleRevokeAllSessions()}
                disabled={revokingSessions}
                className="tm-btn-secondary py-2 text-xs text-amber-300 hover:border-amber-500/40"
              >
                <LogOut className="h-3.5 w-3.5" />
                {revokingSessions ? "Revoking..." : "Sign Out All Devices"}
              </button>
            </div>
          </div>

          {/* Delete Account */}
          <form
            onSubmit={handleDeleteAccount}
            className="space-y-3 rounded-xl border border-rose-500/30 bg-rose-500/5 p-4"
          >
            <div className="flex items-center gap-2 text-xs font-semibold text-rose-300">
              <ShieldAlert className="h-4 w-4" /> Danger Zone — Permanently Delete Account
            </div>
            <p className="text-[11px] leading-relaxed text-slate-300">
              Permanently erases your account, connected OAuth tokens, analyses, uploaded videos, publishing history,
              ad strategies, and PDF reports. This cannot be undone.
            </p>
            <div className="grid gap-3 sm:grid-cols-2">
              <input
                type="password"
                required
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                placeholder="Enter your password"
                className="tm-input text-xs"
              />
              <input
                type="text"
                required
                value={deleteConfirm}
                onChange={(e) => setDeleteConfirm(e.target.value)}
                placeholder='Type "DELETE" to confirm'
                className="tm-input text-xs"
              />
            </div>
            <button
              type="submit"
              disabled={deletingAccount}
              className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/50 bg-rose-600/20 px-3.5 py-2 text-xs font-semibold text-rose-200 hover:bg-rose-600/35 transition"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {deletingAccount ? "Deleting Account..." : "Permanently Delete Account"}
            </button>
          </form>
        </div>
      </div>

      <LegalModal
        docType={legalDoc}
        onClose={() => setLegalDoc(null)}
        onSwitch={(next) => setLegalDoc(next)}
      />
    </div>
  );
}
