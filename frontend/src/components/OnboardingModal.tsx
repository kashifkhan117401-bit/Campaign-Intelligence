import React, { useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Target, Youtube } from "lucide-react";
import { BrandLogo } from "./BrandLogo";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import { authApi } from "../services/api";

const GOALS = [
  "Analyze competitor YouTube comments & audience pain points",
  "Generate high-converting SEO scripts & Shorts ideas",
  "Upload, transcribe & publish optimized YouTube videos",
  "Plan YouTube Ads strategies & transparent budgets",
];

export function OnboardingModal() {
  const { user, refreshUser } = useAuth();
  const { notify } = useToast();
  const [niche, setNiche] = useState(user?.profile?.niche || "");
  const [company, setCompany] = useState(user?.profile?.company_name || "");
  const [goal, setGoal] = useState(user?.profile?.primary_goal || GOALS[0]);
  const [saving, setSaving] = useState(false);

  if (!user || user.profile?.onboarding_completed) return null;

  const handleComplete = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await authApi.updateProfile({
        niche: niche || "Creator & SaaS Marketing",
        company_name: company,
        primary_goal: goal,
        onboarding_completed: true,
      });
      await refreshUser();
      notify("success", "Workspace configured", "Welcome to Campaign Intelligence!");
    } catch {
      notify("error", "Could not save onboarding preferences");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="tm-card w-full max-w-lg border-indigo-500/30 p-6 sm:p-8"
      >
        <div className="mb-5 flex items-center gap-3">
          <BrandLogo size={44} variant="emerald" className="shadow-md" />
          <div>
            <h2 className="text-xl font-bold text-white">Welcome to Campaign Intelligence</h2>
            <p className="text-xs text-slate-400">Know Pakistan&apos;s audience before you spend a rupee</p>
          </div>
        </div>

        <form onSubmit={handleComplete} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Your Channel Niche / Industry</label>
            <input
              type="text"
              className="tm-input"
              placeholder="e.g., B2B SaaS, Tech Reviews, Fitness Coaching, E-commerce"
              value={niche}
              onChange={(e) => setNiche(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-300">Channel or Agency Name (Optional)</label>
            <input
              type="text"
              className="tm-input"
              placeholder="e.g., GrowthLab Media"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-2 block text-xs font-medium text-slate-300">Primary Objective</label>
            <div className="space-y-2">
              {GOALS.map((g) => (
                <button
                  type="button"
                  key={g}
                  onClick={() => setGoal(g)}
                  className={`flex w-full items-center gap-2.5 rounded-xl border px-3.5 py-2.5 text-left text-xs transition ${
                    goal === g
                      ? "border-indigo-500 bg-indigo-500/15 text-white"
                      : "border-slate-800 bg-slate-900/60 text-slate-300 hover:border-slate-700"
                  }`}
                >
                  {goal === g ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-indigo-400" />
                  ) : (
                    <Target className="h-4 w-4 shrink-0 text-slate-500" />
                  )}
                  <span>{g}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-between pt-3">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Youtube className="h-4 w-4 text-rose-400" />
              <span>You can update this anytime in Settings</span>
            </div>
            <button type="submit" disabled={saving} className="tm-btn-primary">
              {saving ? "Saving..." : "Launch Workspace"}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
