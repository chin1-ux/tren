import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bell, Zap, TrendingUp, Search, X, SlidersHorizontal, Clock, AlertCircle, Target } from "lucide-react";
import { fetchTrends, fetchEmergingTrends, fetchPeakedTrends, fetchExpiredTrends, fetchTargetedTrends, type UiTrend } from "@/lib/api";
import { TrendCard } from "@/components/TrendCard";
import { SkeletonCard } from "@/components/SkeletonCard";
import { DanceTrendModal } from "@/components/DanceTrendModal";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { PlanGate } from "@/components/PlanGate";
// import { OnboardingFlow } from "@/components/OnboardingFlow";
// import { FeatureTutorial } from "@/components/FeatureTutorial";
import { ParticleBackground } from "@/components/ParticleBackground";
import { TrenddropLogo } from "@/components/TrenddropLogo";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

import { ThemeToggle } from "@/components/ThemeToggle";
import { AudioIdentityCard } from "@/components/AudioIdentityCard";
import { useUserStore } from "@/store/useAppStore";
import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Trendrop — India's Trend Intelligence" },
      { name: "description", content: "Know what's trending before your competitor even opens Instagram. India-focused AI trend detection." },
    ],
  }),
  component: TrendsFeed,
  errorComponent: RouteErrorBoundary,
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
  { code: "pa",  label: "🌾 Punjabi" },
  { code: "ml",  label: "🥥 Malayalam" },
];

const NICHES = [
  { id: "all",      label: "All" },
  { id: "fitness",  label: "💪 Fitness" },
  { id: "food",     label: "🍜 Food" },
  { id: "comedy",   label: "😂 Comedy" },
  { id: "fashion",  label: "👗 Fashion" },
  { id: "business", label: "💼 Business" },
  { id: "travel",   label: "✈️ Travel" },
  { id: "beauty",   label: "💄 Beauty" },
  { id: "devotional", label: "🙏 Devotional" },
  { id: "tech",     label: "💻 Tech" },
  { id: "narrative_edit", label: "🎞️ Creative Edit" },
  { id: "romance_relationship", label: "💕 Romance" },
];

type FeedTab = "rising" | "emerging" | "peaked" | "expired" | "workspace";
type SortMode = "velocity" | "time_left" | "newest";

function TrendsFeed() {
  const navigate = useNavigate();
  const [language, setLanguage] = useState<string>("all");
  const [feedTab, setFeedTab] = useState<FeedTab>("rising");
  const [sortMode] = useState<any>("velocity");
  const [danceTrend, setDanceTrend] = useState<UiTrend | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showFilterDrawer, setShowFilterDrawer] = useState(false);
  const [, setNow] = useState(Date.now());
  const prevCountRef = useRef<number>(0);
  const lastTotalActiveRef = useRef<number>(0);

  // Niche filter — read from preferences
  const [selectedNiche, setSelectedNiche] = useState<string>("all");

  // Reactive user email for avatar — F-1/ADD-8: use selector, not getState()
  const userEmail = useUserStore((s) => s.email);
  const userPlan = useUserStore((s) => s.plan) || 'free';

  // Load preferences from localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      setLanguage(localStorage.getItem("trendrop_pref_language") ?? "all");
      setSelectedNiche(localStorage.getItem("trendrop_pref_niche") ?? "all");
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
    queryKey: ["trends", language, sortMode, selectedNiche],
    queryFn: () => fetchTrends(language, sortMode, selectedNiche),
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
    staleTime: 30_000, // 30 sec fast stale time for volatile emerging trends
    refetchInterval: 2 * 60_000, // 2 min polling
    enabled: userPlan === "pro",
  });

  const {
    data: peakedData,
    isLoading: peakedLoading,
    isError: peakedError,
    refetch: refetchPeaked,
  } = useQuery({
    queryKey: ["trends-peaked", language],
    queryFn: () => fetchPeakedTrends(language),
    staleTime: 15 * 60_000, // 15 min stale time for peaked trends
    refetchInterval: 30 * 60_000, // 30 min polling
  });

  const {
    data: expiredData,
    isLoading: expiredLoading,
    isError: expiredError,
    refetch: refetchExpired,
  } = useQuery({
    queryKey: ["trends-expired", language],
    queryFn: () => fetchExpiredTrends(language),
    staleTime: 30 * 60_000, // 30 min stale time for historical expired trends
    refetchInterval: 60 * 60_000, // 60 min polling
  });

  const {
    data: targetedData,
    isLoading: targetedLoading,
    isError: targetedError,
    refetch: refetchTargeted,
  } = useQuery({
    queryKey: ["trends-targeted"],
    queryFn: () => fetchTargetedTrends(),
    staleTime: 10_000,
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

  // Deduplication logic: ensure same audio_id appears only in highest-priority tab
  // Priority: rising > emerging > peaked > expired
  const deduplicatedTrends = useMemo(() => {
    const audioToTrend = new Map<string, { trend: UiTrend; priority: number }>();
    const statusPriority: Record<string, number> = { rising: 4, emerging: 3, peaked: 2, expired: 1 };

    // Collect all trends and assign priority
    [...(risingData || []), ...(emergingData || []), ...(peakedData || []), ...(expiredData || [])].forEach(t => {
      const audioId = (t.audioId && t.audioId !== "null") ? t.audioId : (t.song && t.song !== "Original Audio" && t.song !== "Unknown Song" ? `${t.song}-${t.artist}` : `trend-${t.id}`);
      const priority = statusPriority[t.status || "rising"] || 0;
      const existing = audioToTrend.get(audioId);

      // Keep the trend with higher priority (or newer if same priority)
      if (!existing || priority > existing.priority || (priority === existing.priority && t.id > existing.trend.id)) {
        audioToTrend.set(audioId, { trend: t, priority });
      }
    });

    // Separate back into tabs
    const deduplicatedRising: UiTrend[] = [];
    const deduplicatedEmerging: UiTrend[] = [];
    const deduplicatedPeaked: UiTrend[] = [];
    const deduplicatedExpired: UiTrend[] = [];

    audioToTrend.forEach(({ trend }) => {
      if (trend.status === "rising") deduplicatedRising.push(trend);
      else if (trend.status === "emerging") deduplicatedEmerging.push(trend);
      else if (trend.status === "peaked") deduplicatedPeaked.push(trend);
      else if (trend.status === "expired") deduplicatedExpired.push(trend);
    });

    return {
      rising: deduplicatedRising.slice(0, 50),
      emerging: deduplicatedEmerging.slice(0, 50),
      peaked: deduplicatedPeaked.slice(0, 50),
      expired: deduplicatedExpired.slice(0, 50),
    };
  }, [risingData, emergingData, peakedData, expiredData]);

  // When rising tab is empty but peaked has data, fall back to peaked so the app isn't empty
  const risingFallbackToPeaked =
    feedTab === "rising" &&
    !risingLoading &&
    deduplicatedTrends.rising.length === 0 &&
    deduplicatedTrends.peaked.length > 0;

  const activeData = feedTab === "rising"
    ? (risingFallbackToPeaked ? deduplicatedTrends.peaked : deduplicatedTrends.rising)
    : feedTab === "emerging" ? deduplicatedTrends.emerging
    : feedTab === "peaked" ? deduplicatedTrends.peaked
    : feedTab === "expired" ? deduplicatedTrends.expired
    : targetedData;
  const isLoading = feedTab === "rising" ? risingLoading 
    : feedTab === "emerging" ? emergingLoading 
    : feedTab === "peaked" ? peakedLoading 
    : feedTab === "expired" ? expiredLoading
    : targetedLoading;
  const isError = feedTab === "rising" ? risingError 
    : feedTab === "emerging" ? emergingError 
    : feedTab === "peaked" ? peakedError 
    : feedTab === "expired" ? expiredError
    : targetedError;

  const refetch = feedTab === "rising" ? refetchRising 
    : feedTab === "emerging" ? refetchEmerging 
    : feedTab === "peaked" ? refetchPeaked 
    : feedTab === "expired" ? refetchExpired
    : refetchTargeted;

  const trends = useMemo(() => {
    const list = activeData ?? [];
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();
    return list.filter(
      (t) =>
        (t.song ?? "").toLowerCase().includes(q) ||
        (t.artist ?? "").toLowerCase().includes(q) ||
        (t.contentType ?? "").toLowerCase().includes(q)
    );
  }, [activeData, searchQuery]);

  const withCountdown = useCallback((t: UiTrend): UiTrend => ({
    ...t,
    hoursLeft: Math.max(0, Math.ceil((t.expiresAt - Date.now()) / 3600_000)),
  }), []);

  const totalActive = useMemo(() => {
    const isRisingLoading = risingLoading && !risingData;
    const isEmergingLoading = emergingLoading && !emergingData;
    if (isRisingLoading || isEmergingLoading) {
      return lastTotalActiveRef.current;
    }
    const count = (risingData?.length ?? 0) + (emergingData?.length ?? 0);
    lastTotalActiveRef.current = count;
    return count;
  }, [risingData, emergingData, risingLoading, emergingLoading]);

  return (
    <div className="flex flex-col gap-0 pb-24">
        {/* ── Hero Section with Particle Background & Header ───────────────────────────────── */}
        <div className="relative overflow-hidden bg-gradient-to-b from-[rgba(230,57,70,0.12)] to-transparent px-4 pb-4 pt-6 rounded-b-[2rem] border-b border-border/30">
          <ParticleBackground />

          {/* Header Row */}
          <div className="relative flex items-center justify-between mb-4">
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

            {/* Theme Toggle */}
            <ThemeToggle />

            {/* User avatar */}
            <button
              onClick={() => navigate({ to: "/settings" })}
              className="relative rounded-full overflow-hidden h-8 w-8 border border-white/10 hover:border-primary/50 transition-all flex-shrink-0"
              aria-label="Profile"
            >
              <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-primary/40 to-secondary/40 text-xs font-bold text-white uppercase">
                {userEmail ? userEmail.charAt(0) : "T"}
              </div>
            </button>
          </div>
        </div>

        {/* Simplified Stats */}
        <div className="relative z-10 text-center mt-2">
          <p className="text-xs font-bold tracking-wide uppercase text-muted-foreground">
            {totalActive.toLocaleString()} active trends tracked
          </p>
        </div>
      </div>

      {/* ── Feed Tabs & Search ─────────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 bg-background/90 backdrop-blur-xl px-4 pt-3 pb-2 border-b border-border">
        <div className="flex gap-1 rounded-xl bg-muted p-1 mb-3 overflow-x-auto no-scrollbar">
          <TabButton
            active={feedTab === "rising"}
            onClick={() => setFeedTab("rising")}
            icon={<TrendingUp className="h-3.5 w-3.5" />}
            label="Rising"
            count={Math.min(50, deduplicatedTrends.rising.length)}
          />
          <TabButton
            active={feedTab === "emerging"}
            onClick={() => setFeedTab("emerging")}
            icon={<Zap className="h-3.5 w-3.5" />}
            label="Emerging"
            count={Math.min(50, deduplicatedTrends.emerging.length)}
            urgent
          />
          <TabButton
            active={feedTab === "workspace"}
            onClick={() => setFeedTab("workspace")}
            icon={<Target className="h-3.5 w-3.5" />}
            label="Workspace"
            count={targetedData?.length ?? 0}
          />
          <TabButton
            active={feedTab === "peaked"}
            onClick={() => setFeedTab("peaked")}
            icon={<Clock className="h-3.5 w-3.5" />}
            label="Peaked"
            count={Math.min(50, deduplicatedTrends.peaked.length)}
          />
          <TabButton
            active={feedTab === "expired"}
            onClick={() => setFeedTab("expired")}
            icon={<AlertCircle className="h-3.5 w-3.5" />}
            label="Expired"
            count={Math.min(50, deduplicatedTrends.expired.length)}
          />
        </div>

        {/* Search */}
        <div className="relative">
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

        {/* Niche Selection Chip Strip */}
        <div className="flex gap-2 overflow-x-auto no-scrollbar py-2 mt-2 px-1">
          {NICHES.map((nicheItem) => (
            <button
              key={nicheItem.id}
              onClick={() => {
                setSelectedNiche(nicheItem.id);
                if (typeof window !== "undefined") {
                  localStorage.setItem("trendrop_pref_niche", nicheItem.id);
                }
              }}
              className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold transition-all border ${
                selectedNiche === nicheItem.id
                  ? "bg-primary text-white border-primary"
                  : "bg-muted text-muted-foreground border-border/30 hover:text-foreground"
              }`}
            >
              {nicheItem.label}
            </button>
          ))}
        </div>

        {/* Language Selection Chip Strip (Hidden temporarily) */}
        {/* <div className="flex gap-2 overflow-x-auto no-scrollbar py-2 mt-2 px-1">
          {LANGUAGES.map((lang) => (
            <button
              key={lang.code}
              onClick={() => {
                setLanguage(lang.code);
                if (typeof window !== "undefined") {
                  localStorage.setItem("trendrop_pref_language", lang.code);
                }
              }}
              className={`shrink-0 rounded-full px-3 py-1 text-xs font-semibold transition-all border ${
                language === lang.code
                  ? "bg-primary text-white border-primary"
                  : "bg-muted text-muted-foreground border-border/30 hover:text-foreground"
              }`}
            >
              {lang.label}
            </button>
          ))}
        </div> */}
      </div>

      {/* ── Feed ──────────────────────────────────────────────────────────────── */}
      <div className="space-y-4 px-4 pt-4">
        {feedTab === "rising" && risingFallbackToPeaked && (
          <div className="rounded-xl border border-primary/30 bg-[rgba(230,57,70,0.06)] p-3">
            <p className="text-xs text-primary font-semibold">
              🔄 <strong>Trend engine is warming up</strong> — Showing recently peaked trends while new rising trends are being detected. Fresh trends will appear here automatically.
            </p>
          </div>
        )}
        {feedTab === "emerging" && (
          <div className="rounded-xl border border-[#ff006e]/30 bg-[rgba(255,0,110,0.05)] p-3">
            <p className="text-xs text-[#ff006e] font-semibold">
              ⚡ <strong>Early Access Feed</strong> — These trends were detected recently while still rising. You are seeing them before they go mainstream. Act fast!
            </p>
          </div>
        )}
        {feedTab === "peaked" && (
          <div className="rounded-xl border border-amber-500/30 bg-[rgba(245,158,11,0.05)] p-3">
            <p className="text-xs text-amber-500 font-semibold">
              📉 <strong>Peaked Trends</strong> — These trends have already peaked but still have significant momentum. Good for established creators looking for proven content.
            </p>
          </div>
        )}
        {feedTab === "expired" && (
          <div className="rounded-xl border border-slate-500/30 bg-[rgba(100,116,139,0.05)] p-3">
            <p className="text-xs text-slate-400 font-semibold">
              ⏰ <strong>Expired Trends</strong> — These trends have passed their window. View for historical reference and analysis.
            </p>
          </div>
        )}
        {feedTab === "workspace" && (
          <div className="rounded-xl border border-emerald-500/30 bg-[rgba(16,185,129,0.05)] p-3">
            <p className="text-xs text-emerald-400 font-semibold">
              🎯 <strong>My Workspace</strong> — Trends you are actively targeting. Follow the filming guides, download templates, and publish your content before other creators jump in.
            </p>
          </div>
        )}

        {isError && (
          <div className="space-y-2">
            <ApiErrorBanner message={(risingError as any)?.message || (emergingError as any)?.message || "Service temporarily unavailable"} />
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
            <p className="text-4xl mb-3">
              {feedTab === "workspace" ? "🎯" : "🎵"}
            </p>
            <p className="text-base font-semibold">
              {feedTab === "workspace" ? "Your workspace is empty" : "No trends right now"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {feedTab === "workspace"
                ? "Target trends using the 'Target Trend' button on any trend card. They'll appear here for tracking."
                : "Our active trend rail is warming up. New trends will appear soon."}
            </p>
          </div>
        ) : feedTab === "emerging" ? (
          <PlanGate
            feature="Early Detection Feed"
            requiredPlan="pro"
            currentPlan={userPlan}
            onUpgrade={() => window.location.href = '/pricing'}
          >
            <div className="flex flex-col gap-4">
              {trends.map((t) => (
                <TrendCard
                  key={t.id}
                  trend={withCountdown(t)}
                  onDanceTap={setDanceTrend}
                  selectedNiche={selectedNiche}
                />
              ))}
            </div>
          </PlanGate>
        ) : (
          trends.map((t) => (
            <TrendCard
              key={t.id}
              trend={withCountdown(t)}
              onDanceTap={setDanceTrend}
              selectedNiche={selectedNiche}
            />
          ))
        )}
      </div>



      <DanceTrendModal trend={danceTrend} onClose={() => setDanceTrend(null)} />


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
      className={`flex flex-1 min-w-max px-3 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-bold uppercase tracking-wide transition-all ${
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
