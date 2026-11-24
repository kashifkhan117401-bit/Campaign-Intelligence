import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2, KeyRound, Lock, Mail, RefreshCw, ShieldCheck, User as UserIcon } from "lucide-react";
import { BrandLogo } from "../components/BrandLogo";
import { LegalModal, type LegalDocType } from "../components/LegalModal";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import { authApi } from "../services/api";
import { getApiErrorMessage } from "../utils/format";

type AuthMode = "login" | "register" | "reset";

export function AuthPage({ initialMode = "login" }: { initialMode?: AuthMode }) {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [resetRequested, setResetRequested] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // CAPTCHA & Legal Consent
  const [captchaToken, setCaptchaToken] = useState("");
  const [captchaImg, setCaptchaImg] = useState("");
  const [captchaAnswer, setCaptchaAnswer] = useState("");
  const [loadingCaptcha, setLoadingCaptcha] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [legalDoc, setLegalDoc] = useState<LegalDocType | null>(null);

  const { login, register } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();

  const loadCaptcha = useCallback(async () => {
    setLoadingCaptcha(true);
    try {
      const res = await authApi.captcha();
      setCaptchaToken(res.captcha_token);
      setCaptchaImg(res.image_data_url);
      setCaptchaAnswer("");
    } catch {
      // Handled gracefully if backend is momentarily unreachable
    } finally {
      setLoadingCaptcha(false);
    }
  }, []);

  useEffect(() => {
    if (mode !== "reset") {
      void loadCaptcha();
    }
  }, [mode, loadCaptcha]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (mode !== "reset") {
      if (!acceptedTerms) {
        notify("error", "Agreement required", "Please accept the Terms & Conditions and Privacy & Security Policy.");
        return;
      }
      if (!captchaAnswer.trim()) {
        notify("error", "CAPTCHA required", "Please enter the security verification code.");
        return;
      }
    }
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password, { captcha_token: captchaToken, captcha_answer: captchaAnswer.trim() });
        notify("success", "Welcome back", "Signed in to Campaign Intelligence.");
        navigate("/");
      } else if (mode === "register") {
        await register({
          email,
          password,
          full_name: fullName,
          company_name: companyName,
          captcha_token: captchaToken,
          captcha_answer: captchaAnswer.trim(),
          accepted_terms: acceptedTerms,
        });
        notify("success", "Account created", "Let's configure your intelligence workspace.");
        navigate("/");
      } else if (!resetRequested) {
        const res = await authApi.requestPasswordReset(email);
        setResetRequested(true);
        if (res.dev_reset_token) {
          setResetToken(res.dev_reset_token);
          notify("info", "Dev reset token generated", "Token auto-filled for local development.");
        } else {
          notify("info", "Check your email", res.message);
        }
      } else {
        await authApi.confirmPasswordReset(resetToken, newPassword);
        notify("success", "Password updated", "You can now sign in with your new password.");
        setMode("login");
        setResetRequested(false);
      }
    } catch (err) {
      notify("error", "Authentication failed", getApiErrorMessage(err));
      if (mode !== "reset") {
        void loadCaptcha();
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* Left Brand Showcase */}
      <div className="relative flex flex-1 flex-col justify-between overflow-hidden border-b border-slate-800/80 bg-gradient-to-br from-[#071D17] via-[#0B2A22] to-[#08151B] p-8 lg:border-b-0 lg:border-r lg:p-14">
        <div className="flex items-center gap-3.5">
          <BrandLogo size={46} variant="emerald" className="shadow-lg" />
          <div>
            <h1 className="text-xl font-extrabold tracking-tight text-white">Campaign Intelligence</h1>
            <p className="text-xs font-medium text-amber-300">Every city. Every community. Every conversation, one engine.</p>
          </div>
        </div>

        <div className="my-10 max-w-xl">
          <span className="tm-badge border border-emerald-500/40 bg-emerald-500/15 text-emerald-300">
            Campaign Intelligence Engine
          </span>
          <h2 className="mt-4 text-3xl font-extrabold leading-tight tracking-tight text-white sm:text-4xl">
            Know Pakistan&apos;s audience before you spend a rupee.
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-slate-300">
            Analyze up to 2,000 real audience comments per video, uncover buyer objections and unanswered questions,
            generate SEO-backed scripts, schedule automatic YouTube uploads, and export executive PDF reports.
          </p>

          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {[
              "Real-time Sentiment & Emotion Intelligence",
              "Transparent Audience Opportunity Scoring",
              "AI Script, SEO & Multi-Platform Content Studio",
              "FFmpeg Video Studio + OAuth Publishing",
              "3-Tier YouTube Ads Strategy & Budget Planner",
              "18-Section ReportLab Executive PDF Exports",
            ].map((feat) => (
              <div key={feat} className="flex items-center gap-2 text-xs text-slate-200">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                <span>{feat}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400">
          <ShieldCheck className="h-4 w-4 text-indigo-400" />
          <span>Encrypted OAuth token storage, prompt-injection defense, and full user data isolation.</span>
        </div>
      </div>

      {/* Right Auth Form */}
      <div className="flex flex-1 items-center justify-center p-6 sm:p-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="tm-card w-full max-w-md p-7 sm:p-8"
        >
          <div className="mb-6 flex rounded-xl border border-slate-800 bg-[#080E1B] p-1">
            <button
              type="button"
              onClick={() => {
                setMode("login");
                setResetRequested(false);
              }}
              className={`flex-1 rounded-lg py-2 text-xs font-semibold transition ${
                mode === "login" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("register");
                setResetRequested(false);
              }}
              className={`flex-1 rounded-lg py-2 text-xs font-semibold transition ${
                mode === "register" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              Create Account
            </button>
          </div>

          <h3 className="text-xl font-bold text-white">
            {mode === "login"
              ? "Sign in to your workspace"
              : mode === "register"
                ? "Start your Campaign Intelligence workspace"
                : "Reset your password"}
          </h3>
          <p className="mt-1 text-xs text-slate-400">
            {mode === "login"
              ? "Access your saved analyses, content packs, and publishing studio."
              : mode === "register"
                ? "Create your free creator or agency account in seconds."
                : "Enter your email to receive a password reset token."}
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            {mode === "register" && (
              <>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-300">Full Name</label>
                  <div className="relative">
                    <UserIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                    <input
                      type="text"
                      required
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Alex Mercer"
                      className="tm-input pl-9"
                    />
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-300">Company / Channel (Optional)</label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Creator Studio LLC"
                    className="tm-input"
                  />
                </div>
              </>
            )}

            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-300">Email Address</label>
              <div className="relative">
                <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  className="tm-input pl-9"
                />
              </div>
            </div>

            {mode !== "reset" && (
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <label className="text-xs font-medium text-slate-300">Password</label>
                  {mode === "login" && (
                    <button
                      type="button"
                      onClick={() => setMode("reset")}
                      className="text-xs font-medium text-indigo-400 hover:text-indigo-300"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min. 8 characters"
                    className="tm-input pl-9"
                  />
                </div>
              </div>
            )}

            {mode === "reset" && resetRequested && (
              <>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-300">Reset Token</label>
                  <div className="relative">
                    <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                    <input
                      type="text"
                      required
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      placeholder="Paste reset token"
                      className="tm-input pl-9"
                    />
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-300">New Password</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Min. 8 characters"
                    className="tm-input"
                  />
                </div>
              </>
            )}

            {mode !== "reset" && (
              <>
                {/* Security CAPTCHA */}
                <div className="rounded-xl border border-slate-800 bg-[#080E1B] p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-1.5 text-xs font-medium text-slate-300">
                      <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                      Security Verification (CAPTCHA)
                    </label>
                    <button
                      type="button"
                      onClick={() => void loadCaptcha()}
                      disabled={loadingCaptcha}
                      className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400 hover:text-emerald-300"
                    >
                      <RefreshCw className={`h-3 w-3 ${loadingCaptcha ? "animate-spin" : ""}`} />
                      Refresh
                    </button>
                  </div>

                  <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center">
                    <div className="flex h-14 w-[180px] shrink-0 items-center justify-center overflow-hidden rounded-lg border border-emerald-500/30 bg-[#0B2A22]">
                      {captchaImg ? (
                        <img
                          src={captchaImg}
                          alt="Security CAPTCHA challenge"
                          className="h-full w-full select-none object-contain"
                          draggable={false}
                        />
                      ) : (
                        <span className="text-[11px] text-slate-400">Loading...</span>
                      )}
                    </div>
                    <input
                      type="text"
                      required
                      maxLength={8}
                      autoComplete="off"
                      value={captchaAnswer}
                      onChange={(e) => setCaptchaAnswer(e.target.value.toUpperCase())}
                      placeholder="Enter 5-char code"
                      className="tm-input flex-1 font-mono text-sm tracking-widest uppercase"
                    />
                  </div>
                </div>

                {/* Privacy & Terms Consent */}
                <label className="flex cursor-pointer items-start gap-2.5 text-xs text-slate-300">
                  <input
                    type="checkbox"
                    checked={acceptedTerms}
                    onChange={(e) => setAcceptedTerms(e.target.checked)}
                    className="mt-0.5 rounded border-slate-700 bg-slate-900 text-emerald-500"
                  />
                  <span className="leading-relaxed">
                    I agree to the{" "}
                    <button
                      type="button"
                      onClick={() => setLegalDoc("terms")}
                      className="font-medium text-indigo-400 underline hover:text-indigo-300"
                    >
                      Terms &amp; Conditions
                    </button>{" "}
                    and{" "}
                    <button
                      type="button"
                      onClick={() => setLegalDoc("privacy")}
                      className="font-medium text-emerald-400 underline hover:text-emerald-300"
                    >
                      Privacy &amp; Security Policy
                    </button>
                    .
                  </span>
                </label>
              </>
            )}

            <button type="submit" disabled={submitting} className="tm-btn-primary w-full py-3">
              <span>
                {submitting
                  ? "Processing..."
                  : mode === "login"
                    ? "Sign In"
                    : mode === "register"
                      ? "Create Account"
                      : resetRequested
                        ? "Confirm New Password"
                        : "Request Reset Token"}
              </span>
              <ArrowRight className="h-4 w-4" />
            </button>
          </form>

          <div className="mt-5 space-y-2 border-t border-slate-800/80 pt-4 text-center text-[11px] text-slate-400">
            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => setLegalDoc("privacy")}
                className="hover:text-emerald-300 transition"
              >
                Privacy &amp; Security
              </button>
              <span className="text-slate-600">•</span>
              <button
                type="button"
                onClick={() => setLegalDoc("terms")}
                className="hover:text-indigo-300 transition"
              >
                Terms &amp; Conditions
              </button>
            </div>
            <p className="text-[10px] text-slate-500">
              © {new Date().getFullYear()} Kashif Hafeez. All rights reserved.
            </p>
          </div>
        </motion.div>
      </div>

      <LegalModal
        docType={legalDoc}
        onClose={() => setLegalDoc(null)}
        onSwitch={(next) => setLegalDoc(next)}
      />
    </div>
  );
}
