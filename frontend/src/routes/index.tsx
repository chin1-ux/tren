import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bell, Zap, TrendingUp, Search, X, SlidersHorizontal } from "lucide-react";
import { fetchTrends, fetchEmergingTrends, type UiTrend } from "@/lib/api";
import { FilterPills } from "@/components/FilterPills";
import { TrendCard } from "@/components/TrendCard";
import { SkeletonCard } from "@/components/SkeletonCard";
import { DanceTrendModal } from "@/components/DanceTrendModal";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { OnboardingFlow } from "@/components/OnboardingFlow";
import { ParticleBackground } from "@/components/ParticleBackground";
import { TrenddropLogo } from "@/components/TrenddropLogo";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Trendrop — India's Trend Intelligence" },
      { name: "description", content: "Know what's trending before your competitor even opens Instagram. India-first AI trend detection." },
    ],
  }),
  component: TrendsFeed,
});

const LANGUAGES = [
  { code: "all", label: "🌐 All" },
  { code: "en",  label: "🇬🇧 English" },
  { code: "hi",  label: "🇮🇳 Hindi" },
  { code: "kn",  label: "🎯 Kannada" },
  { code: "ta",  label: "🌴 Tamil" },
  { code: "te",  label: "🌟 Telugu" },
  { code: "bn",  label: "🐯 Bengali" },
  { code: "mr",  label: "🦁 Marathi" },
];

type FeedTab = "rising" | "emerging";
type SortMode = "velocity" | "time_left" | "newest";

function TrendsFeed() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<string>("All");
  const [language, setLanguage] = useState<string>("all");
  const [feedTab, setFeedTab] = useState<FeedTab>("rising");
  const [sortMode] = useState<SortMode>("velocity");
  const [danceTrend, setDanceTrend] = useState<UiTrend | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showFilterDrawer, setShowFilterDrawer] = useState(false);
  const [, setNow] = useState(Date.now());
  const prevCountRef = useRef<number>(0);

  // Check if first visit → show onboarding
  useEffect(() => {
    const visited = localStorage.getItem("trendrop_visited");
    if (!visited) {
      setShowOnboarding(true);
      localStorage.setItem("trendrop_visited", "1");
    }
  }, []);

  // Tick every minute for countdown timers
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  const {
    data: risingData,
    isLoading: risingLoading,
    isError: risingError,
    refetch: refetchRising,
  } = useQuery({
    queryKey: ["trends", language, sortMode],
    queryFn: () => fetchTrends(language, sortMode),
    staleTime: 3 * 60_000,
    refetchInterval: 5 * 60_000,
  });

  const {
    data: emergingData,
    isLoading: emergingLoading,
    isError: emergingError,
    refetch: refetchEmerging,
  } = useQuery({
    queryKey: ["trends-emerging", language],
    queryFn: () => fetchEmergingTrends(language),
    staleTime: 3 * 60_000,
    refetchInterval: 5 * 60_000,
  });

  const emergingCount = emergingData?.length ?? 0;

  // Notify on new emerging trends
  useEffect(() => {
    if (emergingCount > prevCountRef.current && prevCountRef.current > 0) {
      const diff = emergingCount - prevCountRef.current;
      toast(`🚨 ${diff} new emerging trend${diff > 1 ? "s" : ""} just detected!`, {
        description: "Switch to the Emerging tab to see them first.",
        action: { label: "View", onClick: () => setFeedTab("emerging") }
      });
    }
    prevCountRef.current = emergingCount;
  }, [emergingCount]);

  const activeData = feedTab === "rising" ? risingData : emergingData;
  const isLoading = feedTab === "rising" ? risingLoading : emergingLoading;
  const isError = feedTab === "rising" ? risingError : emergingError;
  const refetch = feedTab === "rising" ? refetchRising : refetchEmerging;

  const trends = useMemo(() => {
    const list = activeData ?? [];
    const byCategory = filter === "All" ? list : list.filter((t) => t.category?.toLowerCase() === filter.toLowerCase());
    if (!searchQuery.trim()) return byCategory;
    const q = searchQuery.toLowerCase();
    return byCategory.filter(
      (t) =>
        t.song?.toLowerCase().includes(q) ||
        t.artist?.toLowerCase().includes(q) ||
        t.contentType?.toLowerCase().includes(q)
    );
  }, [activeData, filter, searchQuery]);

  const withCountdown = useCallback((t: UiTrend): UiTrend => ({
    ...t,
    hoursLeft: Math.max(0, Math.ceil((t.expiresAt - Date.now()) / 3600_000)),
  }), []);

  const totalActive = (risingData?.length ?? 0) + (emergingData?.length ?? 0);

  const avgLeadTime = useMemo(() => {
    const list = activeData ?? [];
    if (list.length === 0) return "14";
    const sum = list.reduce((acc, t) => acc + (t.hoursLeft || 0), 0);
    return (sum / list.length).toFixed(1);
  }, [activeData]);

  return (
    <div className="flex flex-col gap-0 pb-24">
      {/* ── Hero Section with Particle Background & Header ───────────────────────────────── */}
      <div className="relative overflow-hidden bg-gradient-to-b from-[rgba(230,57,70,0.12)] to-transparent px-4 pb-6 pt-6 rounded-b-[2rem] border-b border-border/30">
        <ParticleBackground />

        {/* Header Row */}
        <div className="relative flex items-center justify-between mb-6">
          {/* Logo */}
          <TrenddropLogo size={34} />

          <div className="flex items-center gap-2">
            {/* Notification bell — switches to Emerging tab when tapped */}
            <button
              id="notification-bell"
              onClick={() => {
                setFeedTab("emerging");
                toast("⚡ Switched to Emerging feed", {
                  description: emergingCount > 0
                    ? `${emergingCount} early trend${emergingCount > 1 ? "s" : ""} detected right now`
                    : "No new emerging trends yet — check back soon!",
                });
              }}
              className="relative rounded-full bg-white/5 p-2 text-foreground transition-colors hover:bg-white/10 active:scale-95"
              aria-label={`Notifications${emergingCount > 0 ? ` — ${emergingCount} emerging trends` : ""}`}
            >
              <Bell className="h-4 w-4" />
              {emergingCount > 0 && (
                <span className="absolute -right-0.5 -top-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-[#ff006e] text-[8px] font-bold text-white animate-pulse">
                  {emergingCount}
                </span>
              )}
            </button>

            {/* Filter / Settings drawer trigger */}
            <button
              id="filter-settings-btn"
              onClick={() => setShowFilterDrawer(true)}
              className={`relative rounded-full p-2 transition-colors ${
                filter !== "All" ? "bg-primary/20 text-primary" : "bg-white/5 text-foreground hover:bg-white/10"
              }`}
              aria-label="Filter settings"
            >
              <SlidersHorizontal className="h-4 w-4" />
              {filter !== "All" && (
                <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-primary" />
              )}
            </button>

            {/* User avatar */}
            <button
              onClick={() => navigate({ to: "/profile" })}
              className="relative rounded-full overflow-hidden h-8 w-8 border border-white/10 hover:border-primary/50 transition-all"
              aria-label="Profile"
            >
              <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-primary/40 to-secondary/40 text-xs font-bold text-white">
                U
              </div>
            </button>
          </div>
        </div>

        {/* Hero copy and Stats */}
        <div className="space-y-4 relative z-10 text-center">
          <div>
            <p className="text-[10px] font-extrabold uppercase tracking-widest text-primary animate-pulse">⚡ Live Trend Engine</p>
            <h2 className="text-xl font-extrabold mt-1 tracking-tight text-foreground">India's Trend Intelligence</h2>
            <p className="text-xs text-muted-foreground mt-1 max-w-[280px] mx-auto">Early trend detection signals to capitalize before they peak.</p>
          </div>

          <div className="grid grid-cols-2 gap-3 mt-4">
            <div className="rounded-xl border border-white/5 bg-white/[0.02] backdrop-blur-md p-3 text-center">
              <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Trend Count</span>
              <p className="text-xl font-extrabold text-primary mt-0.5">{totalActive} Active</p>
              <p className="text-[9px] text-muted-foreground/60">Real-time signals</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-white/[0.02] backdrop-blur-md p-3 text-center">
              <span className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Avg Lead Time</span>
              <p className="text-xl font-extrabold text-secondary mt-0.5">{avgLeadTime} hrs</p>
              <p className="text-[9px] text-muted-foreground/60">Early window</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Feed Tabs & Filters ─────────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 bg-background/90 backdrop-blur-xl px-4 pt-3 pb-2 border-b border-border">
        <div className="flex gap-1 rounded-xl bg-muted p-1 mb-3">
          <TabButton
            active={feedTab === "rising"}
            onClick={() => setFeedTab("rising")}
            icon={<TrendingUp className="h-3.5 w-3.5" />}
            label="Rising"
            count={risingData?.length}
          />
          <TabButton
            active={feedTab === "emerging"}
            onClick={() => setFeedTab("emerging")}
            icon={<Zap className="h-3.5 w-3.5" />}
            label="Emerging"
            count={emergingCount}
            urgent
          />
        </div>

        {/* Search */}
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            id="search-query"
            name="searchQuery"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search song or artist..."
            className="w-full rounded-xl bg-muted/60 py-2.5 pl-9 pr-9 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery("")} className="absolute right-3 top-1/2 -translate-y-1/2">
              <X className="h-4 w-4 text-muted-foreground" />
            </button>
          )}
        </div>

        {/* Language filter */}
        <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1 mb-2">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              onClick={() => setLanguage(l.code)}
              className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold transition-all ${
                language === l.code
                  ? "bg-primary text-white shadow-sm shadow-primary/30"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>

      </div>

      {/* ── Feed ──────────────────────────────────────────────────────────────── */}
      <div className="space-y-4 px-4 pt-4">
        {feedTab === "emerging" && (
          <div className="rounded-xl border border-[#ff006e]/30 bg-[rgba(255,0,110,0.05)] p-3">
            <p className="text-xs text-[#ff006e] font-semibold">
              ⚡ <strong>Early Access Feed</strong> — These trends were detected in the last 6 hours. You are seeing them before they go mainstream. Act fast!
            </p>
          </div>
        )}

        {isError && (
          <div className="space-y-2">
            <ApiErrorBanner />
            <button onClick={() => refetch()} className="text-xs font-semibold text-primary underline">
              Try again
            </button>
          </div>
        )}

        {isLoading ? (
          <>
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </>
        ) : !isError && trends.length === 0 ? (
          <div className="glass-card p-12 text-center">
            <p className="text-4xl mb-3">🎵</p>
            <p className="text-base font-semibold">No trends right now</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {feedTab === "emerging"
                ? "No emerging trends detected yet. Check back in an hour!"
                : "Our scrapers are working. New trends will appear soon."}
            </p>
          </div>
        ) : (
          trends.map((t) => (
            <TrendCard
              key={t.id}
              trend={withCountdown(t)}
              onDanceTap={setDanceTrend}
            />
          ))
        )}
      </div>

      <DanceTrendModal trend={danceTrend} onClose={() => setDanceTrend(null)} />
      {showOnboarding && <OnboardingFlow onComplete={() => setShowOnboarding(false)} />}

      {/* ── Filter / Settings Drawer ─────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {showFilterDrawer && (
          <>
            {/* Backdrop */}
            <motion.div
              key="filter-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
              onClick={() => setShowFilterDrawer(false)}
            />
            {/* Drawer */}
            <motion.div
              key="filter-drawer"
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 28, stiffness: 300 }}
              className="fixed bottom-0 left-1/2 z-50 w-full max-w-md -translate-x-1/2 rounded-t-3xl bg-[#0d0d14] border-t border-border/40 px-5 pt-4 pb-10 shadow-2xl"
            >
              {/* Handle */}
              <div className="mx-auto mb-5 h-1 w-10 rounded-full bg-border/60" />
              <div className="flex items-center justify-between mb-5">
                <h3 className="font-display text-base font-bold text-foreground">Filters & Sort</h3>
                <button onClick={() => setShowFilterDrawer(false)} className="rounded-full p-1.5 text-muted-foreground hover:text-foreground transition-colors">
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Category Filter */}
              <div className="mb-5">
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2.5">Category</p>
                <FilterPills active={filter} onChange={(cat) => { setFilter(cat); }} />
              </div>

              {/* Active filter indicator */}
              {filter !== "All" && (
                <button
                  onClick={() => setFilter("All")}
                  className="flex items-center gap-1.5 rounded-full border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary mb-4 transition-all hover:bg-primary/20"
                >
                  <X className="h-3 w-3" /> Clear filter: {filter}
                </button>
              )}

              {/* Apply button */}
              <button
                onClick={() => setShowFilterDrawer(false)}
                className="w-full rounded-xl bg-primary py-3 text-sm font-bold text-white tracking-wide hover:bg-primary/90 transition-all active:scale-[0.98]"
              >
                Apply Filters
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

function TabButton({
  active, onClick, icon, label, count, urgent,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  count?: number;
  urgent?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-bold uppercase tracking-wide transition-all ${
        active
          ? urgent
            ? "bg-[#ff006e] text-white shadow-sm shadow-[rgba(255,0,110,0.3)]"
            : "bg-primary text-white shadow-sm shadow-primary/30"
          : "text-muted-foreground hover:text-foreground"
      }`}
    >
      {icon}
      {label}
      {count !== undefined && count > 0 && (
        <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-extrabold ${active ? "bg-white/20" : urgent ? "bg-[#ff006e]/20 text-[#ff006e]" : "bg-primary/15 text-primary"}`}>
          {count}
        </span>
      )}
    </button>
  );
}
