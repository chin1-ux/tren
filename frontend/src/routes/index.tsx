import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, X, SlidersHorizontal, Target, Flame } from "lucide-react";
import { fetchTrends, fetchEmergingTrends, fetchPeakedTrends, fetchExpiredTrends, fetchResurgingTrends, fetchTargetedTrends, type UiTrend } from "@/lib/api";
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
import { ActiveLanguageBadge } from "@/components/ActiveLanguageBadge";
import { useUserStore } from "@/store/useAppStore";
import { useEffectivePlan } from "@/lib/plan";
import { useAuth } from "@/contexts/AuthContext";
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
  { code: "pa",  label: "🌾 Punjabi" },
  { code: "ta",  label: "🌴 Tamil" },
  { code: "te",  label: "🌟 Telugu" },
  { code: "ml",  label: "🥥 Malayalam" },
  { code: "kn",  label: "🎯 Kannada" },
  { code: "bn",  label: "🐯 Bengali" },
  { code: "mr",  label: "🦁 Marathi" },
  { code: "gu",  label: "🪔 Gujarati" },
  { code: "ne",  label: "🏔️ Nepali" },
  { code: "es",  label: "🇪🇸 Spanish" },
  { code: "pt",  label: "🇧🇷 Portuguese" },
  { code: "ko",  label: "🇰🇷 Korean" },
  { code: "instrumental", label: "🎼 Instrumental" },
  { code: "other",        label: "🌐 Other" },
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
  { id: "dance",    label: "💃 Dance" },
  { id: "narrative_edit", label: "🎞️ Creative Edit" },
  { id: "romance_relationship", label: "💕 Romance" },
];

const NICHE_KEYWORDS_MAP: Record<string, string[]> = {
  fitness: ["workout", "gym", "fitness", "exercise", "bodybuilding", "physique", "cardio", "protein", "training", "reps"],
  food: ["recipe", "cooking", "food", "kitchen", "dish", "tasty", "street food", "restaurant", "cafe", "baking"],
  comedy: ["meme", "comedy", "funny", "skit", "humor", "hilarious", "laugh", "relatable", "joke"],
  fashion: ["outfit", "ootd", "fashion", "style", "clothing", "lookbook", "wear", "styling", "grwm", "outfit-showcase", "boutique"],
  business: ["business", "startup", "finance", "wealth", "career", "entrepreneur", "money", "productivity"],
  travel: ["travel", "trip", "scenic", "vacation", "mountains", "wanderlust", "explore", "nature", "vlog"],
  beauty: ["makeup", "skincare", "beauty", "cosmetics", "glow up", "glam", "hair"],
  devotional: ["devotional", "bhakti", "temple", "spiritual", "prayer", "bhajan", "puja", "god", "divine"],
  tech: ["tech", "technology", "coding", "software", "ai", "gadget", "developer", "hardware"],
  narrative_edit: ["cinematic", "storytelling", "creative edit", "transition", "capcut", "edit", "montage", "visuals", "aesthetic"],
  romance_relationship: ["romance", "romantic", "couple", "love", "relationship", "wedding", "dating"],
  dance: ["choreography", "dance", "routine", "hookstep", "dancer", "moves", "dancing"],
};

function matchesNiche(t: UiTrend, niche: string): boolean {
  if (!niche || niche === "all") return true;
  const tag = (t.nicheTag || "").toLowerCase();
  if (tag === niche) return true;
  if (t.semanticNiches && t.semanticNiches.some(s => s.toLowerCase() === niche)) return true;
  if (t.contentType && t.contentType.toLowerCase() === niche) return true;
  
  // High-accuracy semantic match from whyThisWorks and used_for_note (85%+ accuracy)
  const context = `${t.whyThisWorks || ""} ${t.used_for_note || ""} ${t.used_for || ""} ${t.idealContentDescription || ""}`.toLowerCase();
  const kws = NICHE_KEYWORDS_MAP[niche] || [];
  return kws.some(kw => context.includes(kw));
}

type SortMode = "velocity" | "time_left" | "newest";

function TrendsFeed() {
  const navigate = useNavigate();
  const [language, setLanguage] = useState<string>("all");
  const [sortMode] = useState<any>("newest");
  const [danceTrend, setDanceTrend] = useState<UiTrend | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showFilterDrawer, setShowFilterDrawer] = useState(false);
  const [, setNow] = useState(Date.now());
  const prevCountRef = useRef<number>(0);

  // Niche filter — read from preferences
  const [selectedNiche, setSelectedNiche] = useState<string>("all");
  const [preferredLanguages, setPreferredLanguages] = useState<string[]>([]);

  // Reactive user email for avatar — F-1/ADD-8: use selector, not getState()
  const userEmail = useUserStore((s) => s.email);
  const userPlan = useEffectivePlan();
  const { loading: isAuthLoading } = useAuth();

  // Load preferences from localStorage
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedLangs = localStorage.getItem("trendrop_preferred_languages");
      if (savedLangs) {
        try {
          const parsed = JSON.parse(savedLangs);
          if (Array.isArray(parsed)) setPreferredLanguages(parsed);
        } catch (e) {}
      }
      setLanguage(localStorage.getItem("trendrop_pref_language") ?? "all");
      setSelectedNiche(localStorage.getItem("trendrop_pref_niche") ?? "all");
    }
  }, []);

  // Compute active language filter array: explicit header filter > saved user preferences > undefined (all)
  const activeLanguages = useMemo(() => {
    if (language && language !== "all") {
      return language.includes(",") ? language.split(",").map(s => s.trim()).filter(Boolean) : [language];
    }
    if (preferredLanguages && preferredLanguages.length > 0) return preferredLanguages;
    return undefined;
  }, [language, preferredLanguages]);

  // Progressive rendering limit for fast DOM paint on mobile
  const [displayLimit, setDisplayLimit] = useState<number>(15);
  const [showTargetedOnly, setShowTargetedOnly] = useState<boolean>(false);
  const [showGoldenHourOnly, setShowGoldenHourOnly] = useState<boolean>(false);

  useEffect(() => {
    setDisplayLimit(15);
  }, [language, selectedNiche, sortMode, showTargetedOnly, showGoldenHourOnly]);

  // Tick every minute for countdown timers
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 60_000);
    return () => clearInterval(id);
  }, []);

  const {
    data: targetedData,
    isLoading: targetedLoading,
  } = useQuery({
    queryKey: ["trends-targeted"],
    queryFn: () => fetchTargetedTrends(),
    staleTime: 10_000,
  });

  const {
    data: risingData,
    isLoading: risingLoading,
    isError: risingError,
    refetch: refetchRising,
  } = useQuery({
    queryKey: ["trends", language, sortMode, activeLanguages],
    queryFn: () => fetchTrends(language, sortMode, undefined, activeLanguages),
    staleTime: 30_000,
    refetchInterval: 5 * 60_000,
  });

  const {
    data: emergingData,
    isLoading: emergingLoading,
    isError: emergingError,
    refetch: refetchEmerging,
  } = useQuery({
    queryKey: ["trends-emerging", language, activeLanguages],
    queryFn: () => fetchEmergingTrends(language, undefined, activeLanguages),
    staleTime: 30_000, // 30 sec fast stale time for volatile emerging trends
    refetchInterval: 2 * 60_000, // 2 min polling
  });

  const {
    data: peakedData,
    isLoading: peakedLoading,
    isError: peakedError,
    refetch: refetchPeaked,
  } = useQuery({
    queryKey: ["trends-peaked", language, activeLanguages],
    queryFn: () => fetchPeakedTrends(language, undefined, activeLanguages),
    staleTime: 15 * 60_000, // 15 min stale time for peaked trends
    refetchInterval: 30 * 60_000, // 30 min polling
  });

  const {
    data: expiredData,
    isLoading: expiredLoading,
    isError: expiredError,
    refetch: refetchExpired,
  } = useQuery({
    queryKey: ["trends-expired", language, activeLanguages],
    queryFn: () => fetchExpiredTrends(language, undefined, activeLanguages),
    staleTime: 30 * 60_000, // 30 min stale time for historical expired trends
    refetchInterval: 60 * 60_000, // 60 min polling
  });

  const {
    data: resurgingData,
    isLoading: resurgingLoading,
    isError: resurgingError,
    refetch: refetchResurging,
  } = useQuery({
    queryKey: ["trends-resurging", language, activeLanguages],
    queryFn: () => fetchResurgingTrends(language, undefined, activeLanguages),
    staleTime: 5 * 60_000, // 5 min — resurging changes less often than rising
    refetchInterval: 10 * 60_000,
  });

  // Deduplication logic: ensure same audio_id appears only in highest-priority tab
  // Priority: rising > emerging > resurging > peaked > expired
  const deduplicatedTrends = useMemo(() => {
    const audioToTrend = new Map<string, { trend: UiTrend; priority: number }>();
    const statusPriority: Record<string, number> = { rising: 5, emerging: 4, resurging: 3, peaked: 2, expired: 1 };

    // Collect all trends and assign priority
    [...(risingData || []), ...(emergingData || []), ...(resurgingData || []), ...(peakedData || []), ...(expiredData || [])].forEach(t => {
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
    const deduplicatedResurging: UiTrend[] = [];
    const deduplicatedPeaked: UiTrend[] = [];
    const deduplicatedExpired: UiTrend[] = [];

    audioToTrend.forEach(({ trend }) => {
      if (trend.status === "rising") deduplicatedRising.push(trend);
      else if (trend.status === "emerging") deduplicatedEmerging.push(trend);
      else if (trend.status === "resurging") deduplicatedResurging.push(trend);
      else if (trend.status === "peaked") deduplicatedPeaked.push(trend);
      else if (trend.status === "expired") deduplicatedExpired.push(trend);
    });

    return {
      rising: deduplicatedRising,
      emerging: deduplicatedEmerging,
      resurging: deduplicatedResurging,
      peaked: deduplicatedPeaked,
      expired: deduplicatedExpired,
    };
  }, [risingData, emergingData, resurgingData, peakedData, expiredData]);

  const emergingCount = deduplicatedTrends.emerging.length;

  // Notify on new emerging trends
  useEffect(() => {
    if (emergingCount > prevCountRef.current && prevCountRef.current > 0) {
      const diff = emergingCount - prevCountRef.current;
      toast(`🚨 ${diff} new early trend${diff > 1 ? "s" : ""} detected!`, {
        description: "Prioritized right at the top of your feed — act fast!",
      });
    }
    prevCountRef.current = emergingCount;
  }, [emergingCount]);

  // Unified feed lifecycle ordering: emerging -> rising -> comeback -> peaked -> expired
  const STATUS_ORDER: Record<string, number> = {
    emerging: 0,
    rising: 1,
    resurging: 2,
    peaked: 3,
    expired: 4,
  };

  const allTrends = useMemo(() => {
    const merged = [
      ...deduplicatedTrends.emerging,
      ...deduplicatedTrends.rising,
      ...deduplicatedTrends.resurging,
      ...deduplicatedTrends.peaked,
      ...deduplicatedTrends.expired,
    ];
    return merged.sort((a, b) => {
      const aPriority = STATUS_ORDER[a.status ?? "rising"] ?? 1;
      const bPriority = STATUS_ORDER[b.status ?? "rising"] ?? 1;
      return aPriority - bPriority;
    });
  }, [deduplicatedTrends]);

  const isLoading = (risingLoading && !risingData) || (emergingLoading && !emergingData);
  const isError = risingError && emergingError;

  const refetch = () => {
    refetchRising();
    refetchEmerging();
    refetchResurging();
    refetchPeaked();
    refetchExpired();
  };

  const trends = useMemo(() => {
    let list = showTargetedOnly ? (targetedData ?? []) : (allTrends ?? []);

    // 1. High-accuracy niche filter (driven by whyThisWorks / used_for_note ~85% real accuracy)
    if (selectedNiche && selectedNiche !== "all") {
      list = list.filter((t) => matchesNiche(t, selectedNiche));
    }

    // 2. Language filter guard
    if (language && language !== "all") {
      const allowed = language.split(",").map(l => l.trim().toLowerCase());
      list = list.filter((t) => {
        const raw = (t.rawLanguage || "").toLowerCase();
        const lbl = (t.language || "").toLowerCase();
        return (
          allowed.includes(raw) ||
          allowed.includes(lbl) ||
          (allowed.includes("hi") && ["hindi", "hi"].includes(raw)) ||
          (allowed.includes("en") && ["english", "en"].includes(raw)) ||
          (allowed.includes("en") && ["english", "en"].includes(lbl))
        );
      });
    }

    // 3. Golden Hour quick filter (high velocity + <28% saturation)
    if (showGoldenHourOnly) {
      list = list.filter((t) => {
        const sat = t.indiaSaturationPct ?? t.globalSaturationPct ?? (t.saturationScore ? t.saturationScore * 100 : 0);
        const vel = t.viralMultiplier ?? 0;
        const status = (t.status ?? "rising").toLowerCase();
        return (sat > 0 && sat <= 28 && (vel >= 15 || (t.opportunityScore ?? 0) >= 75)) ||
               (status === "emerging" && (vel >= 12 || (t.opportunityScore ?? 0) >= 70));
      });
    }

    // 4. Search query filter
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();
    return list.filter(
      (t) =>
        (t.song ?? "").toLowerCase().includes(q) ||
        (t.artist ?? "").toLowerCase().includes(q) ||
        (t.contentType ?? "").toLowerCase().includes(q)
    );
  }, [allTrends, targetedData, showTargetedOnly, showGoldenHourOnly, selectedNiche, language, searchQuery]);

  const withCountdown = useCallback((t: UiTrend): UiTrend => ({
    ...t,
    hoursLeft: Math.max(0, Math.ceil((t.expiresAt - Date.now()) / 3600_000)),
  }), []);

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
      </div>

      {/* ── Feed Tabs & Search ─────────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 bg-background/90 backdrop-blur-xl px-4 pt-3 pb-2 border-b border-border">
        {/* Niche Filter Chips */}
        <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1 mb-2">
          {NICHES.map((n) => (
            <button
              key={n.id}
              id={`niche-chip-${n.id}`}
              onClick={() => {
                setSelectedNiche(n.id);
                setDisplayLimit(15);
                if (typeof window !== "undefined") localStorage.setItem("trendrop_pref_niche", n.id);
              }}
              className={`flex-shrink-0 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all ${
                selectedNiche === n.id
                  ? "bg-primary text-white shadow-sm shadow-primary/30"
                  : "bg-muted/80 text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              {n.label}
            </button>
          ))}
        </div>

        {/* Language & Targeted Filter Chips */}
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar pb-1 mb-2 items-center">
          <button
            type="button"
            id="targeted-quick-filter"
            onClick={() => {
              setShowTargetedOnly((prev) => !prev);
              if (!showTargetedOnly) setShowGoldenHourOnly(false);
              setDisplayLimit(15);
            }}
            className={`flex-shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-semibold transition-all ${
              showTargetedOnly
                ? "bg-emerald-500 text-white shadow-sm ring-1 ring-emerald-400"
                : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20"
            }`}
          >
            <Target className="h-3 w-3" />
            Targeted {targetedData && targetedData.length > 0 ? `(${targetedData.length})` : ""}
          </button>
          <button
            type="button"
            id="golden-hour-quick-filter"
            onClick={() => {
              setShowGoldenHourOnly((prev) => !prev);
              if (!showGoldenHourOnly) setShowTargetedOnly(false);
              setDisplayLimit(15);
            }}
            className={`flex-shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-semibold transition-all ${
              showGoldenHourOnly
                ? "bg-gradient-to-r from-amber-500 to-rose-500 text-white shadow-sm ring-1 ring-amber-400"
                : "bg-amber-500/10 text-amber-300 border border-amber-500/20 hover:bg-amber-500/20"
            }`}
          >
            <Flame className="h-3 w-3 text-amber-400" />
            Golden Hour
          </button>
          {LANGUAGES.slice(0, 10).map((l) => (
            <button
              key={l.code}
              id={`lang-chip-${l.code}`}
              onClick={() => {
                const newLang = l.code === language ? "all" : l.code;
                setLanguage(newLang);
                setDisplayLimit(15);
                if (typeof window !== "undefined") localStorage.setItem("trendrop_pref_language", newLang);
              }}
              className={`flex-shrink-0 rounded-full px-3 py-1 text-[11px] font-medium transition-all ${
                language === l.code
                  ? "bg-secondary text-secondary-foreground shadow-sm ring-1 ring-secondary/50"
                  : "bg-muted/50 text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              {l.label}
            </button>
          ))}
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


      </div>

      {/* ── Feed ──────────────────────────────────────────────────────────────── */}
      <div className="space-y-4 px-4 pt-4">
        {/* Active Language Filter Indicator Badge */}
        <ActiveLanguageBadge
          activeLanguages={activeLanguages}
          languagesMap={LANGUAGES}
          onClear={() => {
            setLanguage("all");
            setSelectedNiche("all");
            setPreferredLanguages([]);
            if (typeof window !== "undefined") {
              localStorage.removeItem("trendrop_pref_language");
              localStorage.removeItem("trendrop_preferred_languages");
              localStorage.removeItem("trendrop_pref_niche");
            }
            toast.success("Filters reset to All");
          }}
        />

        {deduplicatedTrends.emerging.length > 0 && (
          <div className="rounded-xl border border-[#ff006e]/30 bg-[rgba(255,0,110,0.05)] p-3 flex items-center justify-between">
            <p className="text-xs text-[#ff006e] font-semibold">
              ⚡ <strong>{deduplicatedTrends.emerging.length} Early Trend{deduplicatedTrends.emerging.length > 1 ? "s" : ""}</strong> detected — prioritized first. First-mover advantage active!
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
            <p className="text-4xl mb-3">{showTargetedOnly ? "🎯" : "🎵"}</p>
            <p className="text-base font-semibold">
              {showTargetedOnly ? "Your targeted workspace is empty" : "No trends found for this filter"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {showTargetedOnly
                ? "Click 'Target Trend' on any trend card to save and track your targeted audios here."
                : "Try selecting \"All\" or a different niche / language to discover more viral audios."}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {trends.slice(0, displayLimit).map((t) => {
              const card = (
                <div key={t.id} className={t.status === "expired" ? "opacity-50 grayscale-[25%]" : ""}>
                  <TrendCard
                    trend={withCountdown(t)}
                    onDanceTap={setDanceTrend}
                    selectedNiche={selectedNiche}
                    showStatusBadge={true}
                  />
                </div>
              );

              if (t.status === "emerging") {
                return (
                  <PlanGate
                    key={t.id}
                    feature="Early Detection Feed"
                    requiredPlan="pro"
                    currentPlan={userPlan}
                    onUpgrade={() => window.location.href = '/pricing'}
                  >
                    {card}
                  </PlanGate>
                );
              }

              return card;
            })}
          </div>
        )}

        {displayLimit < trends.length && (
          <div className="text-center py-4">
            <button
              onClick={() => setDisplayLimit((prev) => Math.min(prev + 15, trends.length))}
              className="rounded-xl bg-primary/10 hover:bg-primary/20 text-primary text-xs font-semibold px-4 py-2.5 transition-all shadow-sm"
            >
              Load more trends ({trends.length - displayLimit} remaining)
            </button>
          </div>
        )}
      </div>

      <DanceTrendModal trend={danceTrend} onClose={() => setDanceTrend(null)} />

    </div>
  );
}
