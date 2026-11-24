import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft, FileCheck2, Lock } from "lucide-react";
import { BrandLogo } from "../components/BrandLogo";
import { LegalDocumentContent, type LegalDocType } from "../components/LegalModal";

export function LegalPage({ docType }: { docType: LegalDocType }) {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#070B14] px-4 py-10 text-slate-100">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <BrandLogo size={40} variant="emerald" />
            <div>
              <h1 className="text-lg font-bold text-white">Campaign Intelligence</h1>
              <p className="text-xs text-amber-300">Know Pakistan&apos;s audience before you spend a rupee.</p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => navigate(-1)}
            className="tm-btn-secondary py-2 text-xs"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Go Back
          </button>
        </div>

        <div className="flex gap-2">
          <Link
            to="/privacy"
            className={`inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-semibold transition ${
              docType === "privacy"
                ? "bg-emerald-600 text-white"
                : "border border-slate-800 bg-slate-900 text-slate-400 hover:text-white"
            }`}
          >
            <Lock className="h-3.5 w-3.5" /> Privacy &amp; Security
          </Link>
          <Link
            to="/terms"
            className={`inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-semibold transition ${
              docType === "terms"
                ? "bg-indigo-600 text-white"
                : "border border-slate-800 bg-slate-900 text-slate-400 hover:text-white"
            }`}
          >
            <FileCheck2 className="h-3.5 w-3.5" /> Terms &amp; Conditions
          </Link>
        </div>

        <div className="tm-card p-6 sm:p-8">
          <LegalDocumentContent docType={docType} />
        </div>

        <p className="text-center text-xs text-slate-500">
          © {new Date().getFullYear()} Kashif Hafeez. All rights reserved.
        </p>
      </div>
    </div>
  );
}
