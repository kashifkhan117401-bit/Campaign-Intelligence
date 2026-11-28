import React from "react";
import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { RealtimeProvider } from "@neon/realtime-react";
import { Loader2 } from "lucide-react";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ToastProvider } from "./contexts/ToastContext";
import { neonRealtimeClient } from "./lib/neon";
import { DashboardLayout } from "./layouts/DashboardLayout";
import { AuthPage } from "./pages/AuthPage";
import { OverviewPage } from "./pages/OverviewPage";
import { YouTubeAnalyzerPage } from "./pages/YouTubeAnalyzerPage";
import { AudienceIntelligencePage } from "./pages/AudienceIntelligencePage";
import { ContentStudioPage } from "./pages/ContentStudioPage";
import { VideoStudioPage } from "./pages/VideoStudioPage";
import { AdsPlannerPage } from "./pages/AdsPlannerPage";
import { ReportsPage } from "./pages/ReportsPage";
import { CampaignHistoryPage } from "./pages/CampaignHistoryPage";
import { LegalPage } from "./pages/LegalPage";
import { SettingsPage } from "./pages/SettingsPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#070B14] text-indigo-400">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function PublicOnlyRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function App() {
  const tree = (
    <ToastProvider>
      <AuthProvider>
        <HashRouter>
          <Routes>
            <Route
              path="/login"
              element={
                <PublicOnlyRoute>
                  <AuthPage initialMode="login" />
                </PublicOnlyRoute>
              }
            />
            <Route
              path="/register"
              element={
                <PublicOnlyRoute>
                  <AuthPage initialMode="register" />
                </PublicOnlyRoute>
              }
            />

            <Route path="/privacy" element={<LegalPage docType="privacy" />} />
            <Route path="/terms" element={<LegalPage docType="terms" />} />

            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <DashboardLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<OverviewPage />} />
              <Route path="analyzer" element={<YouTubeAnalyzerPage />} />
              <Route path="audience" element={<AudienceIntelligencePage />} />
              <Route path="content-studio" element={<ContentStudioPage />} />
              <Route path="video-studio" element={<VideoStudioPage />} />
              <Route path="ads-planner" element={<AdsPlannerPage />} />
              <Route path="reports" element={<ReportsPage />} />
              <Route path="history" element={<CampaignHistoryPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </HashRouter>
      </AuthProvider>
    </ToastProvider>
  );

  return neonRealtimeClient ? <RealtimeProvider client={neonRealtimeClient}>{tree}</RealtimeProvider> : tree;
}

export default App;
