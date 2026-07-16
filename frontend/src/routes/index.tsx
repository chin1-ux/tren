import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bell, Zap, TrendingUp, Search, X, SlidersHorizontal, Globe } from "lucide-react";
import { fetchTrends, fetchEmergingTrends, fetchCrossCulturalTrends, type UiTrend } from "@/lib/api";
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

type FeedTab = "rising" | "emerging";
type SortMode = "velocity" | "time_left" | "newest";

function TrendsFeed() {
  const navigate = useNavigate();
  const [language, setLanguage] = useState<string>("all");
  const [feedTab, setFeedTab] = useState<FeedTab>("rising");
  const [sortMode] = useState<any>("velocity");
  const [danceTrend, setDanceTrend] = useState<UiTrend | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showTutorial, setShowTutorial] = useState(false);
  const [showFilterDrawer, setShowFilterDrawer] = useState(false);
  const [now, setNow] = useState(0);
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
    queryKey: ["reels-cross-cultural"],
    queryFn: () => fetchCrossCulturalTrends(),
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
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();
    return list.filter(
      (t) =>
        t.song?.toLowerCase().includes(q) ||
        t.artist?.toLowerCase().includes(q) ||
        t.contentType?.toLowerCase().includes(q)
    );
  }, [activeData, searchQuery]);

  const withCountdown = useCallback((t: UiTrend): UiTrend => ({
    ...t,
    hoursLeft: Math.max(0, Math.ceil((t.expiresAt - now) / 3600_000)),
  }), [now]);

  const totalActive = (risingData?.length ?? 0) + (emergingData?.length ?? 0);

  const avgLeadTime = useMemo(() => {
    const list = activeData ?? [];
    if (list.length === 0) return "14";
    const sum = list.reduce((acc, t) => acc + (t.hoursLeft || 0), 0);
    return (sum / list.length).toFixed(1);
  }, [activeData]);

  return (
    <div className="flex flex-col gap-0 pb-24">
      {/* Global discovery rail */}
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
              <div key={i} className="shrink-0 w-64 rounded-[1.5rem] border border-border/30 bg-muted/30 p-4">
                <div className="h-4 w-20 rounded-full bg-white/5 animate-pulse" />
                <div className="mt-4 h-4 w-40 rounded-full bg-white/5 animate-pulse" />
                <div className="mt-2 h-3 w-28 rounded-full bg-white/5 animate-pulse" />
                <div className="mt-5 h-2 w-full rounded-full bg-white/5 animate-pulse" />
                <div className="mt-4 h-8 w-full rounded-xl bg-white/5 animate-pulse" />
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
              const indiaPct = reel.india_saturation_pct ?? 0;
              const originFlag: Record<string, string> = {
                US: "US", BR: "BR", RU: "RU", KR: "KR", GB: "GB",
                DE: "DE", FR: "FR", MX: "MX",
              };
              const flag = originFlag[reel.trend_origin] ?? "Global";
              const audioUrl = reel.audio_id
                ? `https://www.instagram.com/reels/audio/${reel.audio_id}/`
                : `https://www.instagram.com/explore/tags/${encodeURIComponent(reel.audio_title || "")}/`;
              const windowH = reel.window_hours_remaining;
              const isDance = reel.is_dance || reel.niche_tag === "Dance";
              const borderClass = isDance
                ? "border border-amber-500/35 shadow-[0_0_16px_rgba(239,159,39,0.09)] bg-gradient-to-b from-[rgba(239,159,39,0.08)] to-transparent hover:border-amber-400/70"
                : "border border-primary/35 shadow-[0_0_16px_rgba(230,57,70,0.09)] bg-gradient-to-b from-[rgba(230,57,70,0.08)] to-transparent hover:border-primary/70";

              return (
                <div
                  key={reel.id}
                  className={`shrink-0 w-64 rounded-[1.5rem] p-4 space-y-3 transition-all ${borderClass}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-bold text-muted-foreground">
                      {flag} ? ????
                    </span>
                    {windowH > 0 && (
                      <span className="rounded-full border border-primary/20 bg-primary/10 px-2.5 py-0.5 text-[10px] font-bold text-primary">
                        ~{windowH}h window
                      </span>
                    )}
                  </div>

                  <div>
                    <p className="text-sm font-bold text-foreground truncate">
                      {reel.audio_title || "Original Audio"}
                    </p>
                    <p className="text-[10px] text-muted-foreground truncate">
                      by {reel.audio_artist || "Unknown"}
                    </p>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between text-[9px]">
                      <span className="text-muted-foreground">???? India saturation</span>
                      <span className="font-bold text-foreground">{Math.round(indiaPct)}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          indiaPct < 30 ? "bg-emerald-500" :
                          indiaPct < 60 ? "bg-amber-500" : "bg-red-500"
                        }`}
                        style={{ width: `${Math.min(100, indiaPct)}%` }}
                      />
                    </div>
                    {indiaPct < 30 ? (
                      <span className="text-[9px] font-bold text-emerald-400">
                        ???? Opportunity window open
                      </span>
                    ) : (
                      <span className="text-[9px] font-medium text-muted-foreground">
                        More saturated than the early window
                      </span>
                    )}
                  </div>

                  <a
                    href={audioUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex w-full items-center justify-center gap-1 rounded-xl bg-primary/12 border border-primary/20 text-primary text-[10px] font-bold px-2 py-2 hover:bg-primary/20 transition-all"
                  >
                    ?? Save Audio ?
                  </a>
                </div>
              );
            })}
          </div>
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

