import React, { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bell,
  ChevronLeft,
  ChevronRight,
  FileBarChart2,
  Film,
  History,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Menu,
  Search,
  Settings,
  Sparkles,
  Users,
  X,
  Youtube,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { BrandLogo } from "../components/BrandLogo";
import { OnboardingModal } from "../components/OnboardingModal";

const NAV_ITEMS = [
  { label: "Overview", path: "/", icon: LayoutDashboard },
  { label: "YouTube Analyzer", path: "/analyzer", icon: Youtube },
  { label: "Audience Intelligence", path: "/audience", icon: Users },
  { label: "AI Content Studio", path: "/content-studio", icon: Sparkles },
  { label: "Video Publishing Studio", path: "/video-studio", icon: Film },
  { label: "Ads Strategy Planner", path: "/ads-planner", icon: Megaphone },
  { label: "PDF Reports", path: "/reports", icon: FileBarChart2 },
  { label: "Campaign History", path: "/history", icon: History },
  { label: "Settings", path: "/settings", icon: Settings },
];

export function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [notifOpen, setNotifOpen] = useState(false);

  const handleGlobalSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = searchQuery.trim().toLowerCase();
    if (!q) return;
    const match = NAV_ITEMS.find((item) => item.label.toLowerCase().includes(q));
    if (match) {
      navigate(match.path);
    } else if (q.includes("youtube.com") || q.includes("youtu.be")) {
      navigate(`/analyzer?url=${encodeURIComponent(searchQuery.trim())}`);
    } else {
      navigate(`/history?q=${encodeURIComponent(searchQuery.trim())}`);
    }
    setSearchQuery("");
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const displayName = user?.profile?.full_name || user?.email?.split("@")[0] || "Creator";
  const initials = displayName
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const SidebarContent = ({ isMobile = false }: { isMobile?: boolean }) => (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center justify-between border-b border-slate-800/80 px-4">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <BrandLogo size={36} variant="emerald" className="shadow-md" />
          {(!collapsed || isMobile) && (
            <div className="truncate">
              <p className="text-sm font-bold leading-tight tracking-tight text-white">Campaign Intelligence</p>
              <p className="text-[10px] font-medium uppercase tracking-widest text-emerald-400">
                Audience Engine
              </p>
            </div>
          )}
        </div>
        {isMobile ? (
          <button
            onClick={() => setMobileOpen(false)}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
            aria-label="Close navigation menu"
          >
            <X className="h-5 w-5" />
          </button>
        ) : (
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="hidden rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white lg:inline-flex"
            aria-label="Toggle sidebar width"
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        )}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all ${
                  isActive
                    ? "bg-gradient-to-r from-indigo-600/25 to-violet-600/15 text-white border border-indigo-500/30 shadow-sm"
                    : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-100 border border-transparent"
                }`
              }
              title={collapsed && !isMobile ? item.label : undefined}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {(!collapsed || isMobile) && <span className="truncate">{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      <div className="border-t border-slate-800/80 p-3 space-y-2">
        {(!collapsed || isMobile) && (
          <div className="flex items-center justify-between px-2 text-[11px] text-slate-400">
            <NavLink to="/privacy" onClick={() => setMobileOpen(false)} className="hover:text-emerald-300 transition">
              Privacy &amp; Security
            </NavLink>
            <span className="text-slate-700">•</span>
            <NavLink to="/terms" onClick={() => setMobileOpen(false)} className="hover:text-indigo-300 transition">
              Terms
            </NavLink>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-400 hover:bg-rose-500/10 hover:text-rose-300 transition"
          title="Sign out"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          {(!collapsed || isMobile) && <span>Sign Out</span>}
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-[#070B14] text-slate-100">
      <OnboardingModal />

      {/* Desktop Sidebar */}
      <aside
        className={`hidden shrink-0 border-r border-slate-800/80 bg-[#0A1020]/95 backdrop-blur-xl transition-all duration-200 lg:block ${
          collapsed ? "w-[74px]" : "w-64"
        }`}
      >
        <div className="sticky top-0 h-screen">
          <SidebarContent />
        </div>
      </aside>

      {/* Mobile Drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
              className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            />
            <motion.aside
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: "spring", damping: 26, stiffness: 280 }}
              className="relative h-full w-72 border-r border-slate-800 bg-[#0A1020]"
            >
              <SidebarContent isMobile />
            </motion.aside>
          </div>
        )}
      </AnimatePresence>

      {/* Main Column */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Top Bar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b border-slate-800/80 bg-[#080E1C]/85 px-4 backdrop-blur-xl sm:px-6">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(true)}
              className="rounded-xl border border-slate-800 bg-slate-900 p-2 text-slate-300 hover:text-white lg:hidden"
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <form onSubmit={handleGlobalSearch} className="relative hidden sm:block sm:w-72 md:w-96">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Jump to module or paste YouTube URL..."
                className="w-full rounded-xl border border-slate-800 bg-[#0C1324] py-2 pl-9 pr-3 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
              />
            </form>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="relative">
              <button
                onClick={() => setNotifOpen((o) => !o)}
                className="relative rounded-xl border border-slate-800 bg-slate-900/70 p-2 text-slate-300 hover:border-slate-700 hover:text-white transition"
                aria-label="Notifications"
              >
                <Bell className="h-4 w-4" />
                <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-indigo-500" />
              </button>
              {notifOpen && (
                <div className="tm-card absolute right-0 mt-2 w-72 p-4 shadow-2xl">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-semibold text-white">Workspace Status</p>
                    <button onClick={() => setNotifOpen(false)} className="text-xs text-slate-400 hover:text-white">
                      Close
                    </button>
                  </div>
                  <div className="mt-3 space-y-2 text-xs text-slate-300">
                    <p className="rounded-lg bg-slate-900/80 p-2.5">
                      Real-time background processing active for YouTube comment analysis and PDF exports.
                    </p>
                    <button
                      onClick={() => {
                        setNotifOpen(false);
                        navigate("/settings");
                      }}
                      className="w-full rounded-lg border border-indigo-500/30 bg-indigo-500/10 py-1.5 text-center font-medium text-indigo-300 hover:bg-indigo-500/20"
                    >
                      Check API Integration Status
                    </button>
                  </div>
                </div>
              )}
            </div>

            <button
              onClick={() => navigate("/settings")}
              className="flex items-center gap-2.5 rounded-xl border border-slate-800 bg-slate-900/70 py-1.5 pl-2 pr-3 hover:border-indigo-500/40 transition"
            >
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-xs font-bold text-white">
                {initials}
              </div>
              <div className="hidden text-left md:block">
                <p className="text-xs font-semibold leading-none text-white">{displayName}</p>
                <p className="mt-0.5 text-[10px] text-slate-400">{user?.email}</p>
              </div>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="mx-auto max-w-7xl"
          >
            <Outlet />
          </motion.div>
        </main>

        <footer className="border-t border-slate-800/70 px-4 py-3 text-center text-[11px] text-slate-500 sm:flex sm:items-center sm:justify-between sm:px-6">
          <span>© {new Date().getFullYear()} Kashif Hafeez. All rights reserved.</span>
          <div className="mt-1 flex items-center justify-center gap-3 sm:mt-0">
            <NavLink to="/privacy" className="hover:text-emerald-300 transition">
              Privacy &amp; Security
            </NavLink>
            <span className="text-slate-700">•</span>
            <NavLink to="/terms" className="hover:text-indigo-300 transition">
              Terms &amp; Conditions
            </NavLink>
          </div>
        </footer>
      </div>
    </div>
  );
}
