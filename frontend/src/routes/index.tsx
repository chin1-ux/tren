import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bell, Zap, TrendingUp, Search, X, SlidersHorizontal, Globe } from "lucide-react";
import { fetchTrends, fetchEmergingTrends, fetchAllActiveTrends, type UiTrend } from "@/lib/api";
import { TrendCard } from "@/components/TrendCard";
import { SkeletonCard } from "@/components/SkeletonCard";
import { DanceTrendModal } from "@/components/DanceTrendModal";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { OnboardingFlow } from "@/components/OnboardingFlow";
import { FeatureTutorial } from "@/components/FeatureTutorial";
import { ParticleBackground } from "@/components/ParticleBackground";
import { TrenddropLogo } from "@/components/TrenddropLogo";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

import { ThemeToggle } from "@/components/ThemeToggle";
import { AudioIdentityCard } from "@/components/AudioIdentityCard";
import { useUserStore } from "@/store/useAppStore";

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

const NICHES = [
  { id: "all",      label: "All" },
  { id: "fitness",  label: "💪 Fitness" },
  { id: "food",     label: "🍜 Food" },
  { id: "comedy",   label: "😂 Comedy" },
  { id: "fashion",  label: "👗 Fashion" },
  { id: "business", label: "💼 Business" },
  { id: "travel",   label: "✈️ Travel" },
  { id: "beauty",   label: "💄 Beauty" },
];

type FeedTab = "global" | "india" | "emerging";
type SortMode = "velocity" | "time_left" | "newest";

function TrendsFeed() {
  const navigate = useNavigate();
  const [language, setLanguage] = useState<string>("all");
  const [feedTab, setFeedTab] = useState<FeedTab>("global");
  const [sortMode] = useState<any>("velocity");
  const [danceTrend, setDanceTrend] = useState<UiTrend | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showTutorial, setShowTutorial] = useState(false);
  const [showFilterDrawer, setShowFilterDrawer] = useState(false);
  const [, setNow] = useState(Date.now());
  const prevCountRef = useRef<number>(0);

  // Niche filter — read from preferences
  const [selectedNiche, setSelectedNiche] = useState<string>("all");

  // Check if first visit → show onboarding
  useEffect(() => {
    if (typeof window !== "undefined") {
      setLanguage(localStorage.getItem("trendrop_pref_language") ?? "all");
      setSelectedNiche(localStorage.getItem("trendrop_pref_niche") ?? "all");
    }

    const visited = localStorage.getItem("trendrop_visited");
    if (!visited) {
      setShowOnboarding(true);
      localStorage.setItem("trendrop_visited", "1");
    } else {
      const tutorialDone = localStorage.getItem("trendrop_tutorial_done");
      if (!tutorialDone) {
        setShowTutorial(true);
      }
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
    staleTime: 3 * 60_000,
    refetchInterval: 5 * 60_000,
  });

  const {
    data: crossCulturalData,
    isLoading: crossCulturalLoading,
  } = useQuery({
    queryKey: ["trends-all-active", language, selectedNiche],
    queryFn: () => fetchAllActiveTrends(),
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

  const activeData = feedTab === "global"
    ? crossCulturalData
    : feedTab === "emerging"
    ? emergingData
    : risingData;

  const isLoading = feedTab === "global"
    ? crossCulturalLoading
    : feedTab === "emerging"
    ? emergingLoading
    : risingLoading;

  const isError = feedTab === "global"
    ? false
    : feedTab === "emerging"
    ? emergingError
    : risingError;

  const refetch = feedTab === "global"
    ? refetchRising
    : feedTab === "emerging"
    ? refetchEmerging
    : refetchRising;

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

  const totalActive = (risingData?.length ?? 0) + (emergingData?.length ?? 0);

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
              onClick={() => navigate({ to: "/profile" })}
              className="relative rounded-full overflow-hidden h-8 w-8 border border-white/10 hover:border-primary/50 transition-all flex-shrink-0"
              aria-label="Profile"
            >
              <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-primary/40 to-secondary/40 text-xs font-bold text-white uppercase">
                {useUserStore.getState().email ? useUserStore.getState().email.charAt(0) : "T"}
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

      {/* Global-first discovery rail */}
      <div className="mx-4 mt-6 overflow-hidden rounded-[1.75rem] border border-primary/20 bg-gradient-to-b from-primary/10 via-background to-background shadow-[0_24px_80px_rgba(230,57,70,0.08)]">
        <div className="flex items-center justify-between gap-4 border-b border-border/30 px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-primary/15 text-primary ring-1 ring-primary/20">
              <Globe className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-primary/80">
                Global-first discovery
              </p>
              <h2 className="text-base font-bold font-display tracking-tight text-foreground">
                Global trends entering India
              </h2>
            </div>
          </div>
          <span className="rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-[10px] font-bold uppercase tracking-wide text-primary">
            Cross-cultural
          </span>
        </div>

        {crossCulturalLoading ? (
          <div className="flex gap-3 overflow-x-auto no-scrollbar px-4 py-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="shrink-0 w-64 rounded-[1.5rem] border border-border/30 bg-muted/30 p-4 animate-pulse">
                <div className="h-4 w-20 rounded-full bg-foreground/10" />
                <div className="mt-4 h-4 w-40 rounded-full bg-foreground/10" />
                <div className="mt-2 h-3 w-28 rounded-full bg-foreground/10" />
                <div className="mt-5 h-2 w-full rounded-full bg-foreground/10" />
                <div className="mt-4 h-8 w-full rounded-xl bg-foreground/10" />
              </div>
            ))}
          </div>
        ) : !crossCulturalData || (crossCulturalData as any).length === 0 ? (
          <div className="px-4 py-6 text-sm text-muted-foreground">
            No global cross-cultural trends detected yet.
          </div>
        ) : (
          <div className="flex gap-3 overflow-x-auto no-scrollbar px-4 py-4">
            {(crossCulturalData as any[]).map((reel: any) => {
              const indiaPct = reel.indiaSaturationPct ?? 0;
              const audioUrl = reel.audioId
                ? `https://www.instagram.com/reels/audio/${reel.audioId}/`
                : `https://www.instagram.com/explore/tags/${encodeURIComponent(reel.song || "")}/`;
              const windowH = reel.hoursLeft;
              const isDance = reel.isDance || reel.nicheTag === "Dance";
              const borderClass = isDance
                ? "border border-amber-500/35 shadow-[0_0_16px_rgba(239,159,39,0.09)] bg-gradient-to-b from-[rgba(239,159,39,0.08)] to-transparent hover:border-amber-400/70"
                : "border border-primary/35 shadow-[0_0_16px_rgba(230,57,70,0.09)] bg-gradient-to-b from-[rgba(230,57,70,0.08)] to-transparent hover:border-primary/70";

              return (
                <div key={reel.id} className="shrink-0 w-64">
                  <AudioIdentityCard
                    audioId={reel.audioId}
                    audioTitle={reel.song}
                    audioArtist={reel.artist}
                    audioUseCount={reel.audioUseCount}
                    trendId={reel.id}
                    opportunityScore={reel.opportunityScore}
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Feed Tabs & Search ─────────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 bg-background/90 backdrop-blur-xl px-4 pt-3 pb-2 border-b border-border">
        <div className="flex gap-1 rounded-xl bg-muted p-1 mb-3">
          <TabButton
            active={feedTab === "global"}
            onClick={() => setFeedTab("global")}
            icon={<Globe className="h-3.5 w-3.5" />}
            label="Global"
            count={crossCulturalData?.length}
          />
          <TabButton
            active={feedTab === "india"}
            onClick={() => setFeedTab("india")}
            icon={<TrendingUp className="h-3.5 w-3.5" />}
            label="India"
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

        {/* Language Selection Chip Strip */}
        <div className="flex gap-2 overflow-x-auto no-scrollbar py-2 mt-2 px-1">
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
            <p className="text-4xl mb-3">🎵</p>
            <p className="text-base font-semibold">No trends right now</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {feedTab === "india"
                ? "Our scrapers are working. New India trends will appear soon."
                : feedTab === "emerging"
                ? "No emerging trends detected in the last 6 hours. Check back soon!"
                : "Our active trend rail is warming up. New trends will appear soon."}
            </p>
          </div>
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
      {showOnboarding && (
        <OnboardingFlow
          onComplete={() => {
            setShowOnboarding(false);
            setShowTutorial(true);
          }}
        />
      )}
      {showTutorial && <FeatureTutorial onClose={() => setShowTutorial(false)} />}


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
