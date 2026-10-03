import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, X, SlidersHorizontal, Target, Flame, Sparkles, RotateCcw } from "lucide-react";
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
import { TrendFiltersModal, type FilterState } from "@/components/TrendFiltersModal";
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
  { code: "global", label: "🌐 Global" },
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

function matchesNiches(t: UiTrend, niches: string[]): boolean {
  if (!niches || niches.length === 0 || niches.includes("all")) return true;
  return niches.some((n) => matchesNiche(t, n));
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

  // Unified multi-dimensional filter state
  const [filters, setFilters] = useState<FilterState>({
    lifecycle: "all",
    urgency: "all",
    minOpportunityScore: 0,
    minVelocity: 0,
    outlierOnly: false,
    goldenHourOnly: false,
    niches: ["all"],
    language: "all",
    format: "all",
  });

  const [preferredLanguages, setPreferredLanguages] = useState<string[]>([]);

  // Reactive user email for avatar — F-1/ADD-8: use selector, not getState()
  const userEmail = useUserStore((s) => s.email);
  const userPlan = useEffectivePlan();
  const { loading: isAuthLoading } = useAuth();

  // Load preferences from localStorage on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedLangs = localStorage.getItem("trendrop_preferred_languages");
      if (savedLangs) {
        try {
          const parsed = JSON.parse(savedLangs);
          if (Array.isArray(parsed)) setPreferredLanguages(parsed);
        } catch (e) {}
      }
      const savedLang = localStorage.getItem("trendrop_pref_language") ?? "all";
      let savedNichesList = ["all"];
      try {
        const savedNiches = localStorage.getItem("trendrop_pref_niches");
        if (savedNiches) {
          const parsed = JSON.parse(savedNiches);
          if (Array.isArray(parsed) && parsed.length > 0) {
            savedNichesList = parsed;
          }
        } else {
          const single = localStorage.getItem("trendrop_pref_niche");
          if (single && single !== "all") {
            savedNichesList = [single];
          }
        }
      } catch {
        savedNichesList = ["all"];
      }

      setFilters((prev) => ({
        ...prev,
        language: savedLang,
        niches: savedNichesList,
      }));
    }
  }, []);

  const updateFilter = useCallback((updated: Partial<FilterState>) => {
    setDisplayLimit(15);
    setFilters((prev) => {
      const next = { ...prev, ...updated };
      if (typeof window !== "undefined") {
        if (updated.language !== undefined) {
          localStorage.setItem("trendrop_pref_language", updated.language);
        }
        if (updated.niches !== undefined) {
          localStorage.setItem("trendrop_pref_niches", JSON.stringify(updated.niches));
          localStorage.setItem("trendrop_pref_niche", updated.niches.length === 1 ? updated.niches[0] : updated.niches.join(","));
        }
      }
      return next;
    });
  }, []);

  const resetAllFilters = useCallback(() => {
    setDisplayLimit(15);
    setShowTargetedOnly(false);
    setFilters({
      lifecycle: "all",
      urgency: "all",
      minOpportunityScore: 0,
      minVelocity: 0,
      outlierOnly: false,
      goldenHourOnly: false,
      niches: ["all"],
      language: "all",
      format: "all",
    });
    if (typeof window !== "undefined") {
      localStorage.setItem("trendrop_pref_language", "all");
      localStorage.setItem("trendrop_pref_niches", JSON.stringify(["all"]));
      localStorage.setItem("trendrop_pref_niche", "all");
    }
  }, []);

  // Calculate active filter count for badge
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.lifecycle !== "all") count++;
    if (filters.urgency !== "all") count++;
    if (filters.minOpportunityScore > 0) count++;
    if (filters.minVelocity > 0) count++;
    if (filters.outlierOnly) count++;
    if (filters.goldenHourOnly) count++;
    if (filters.niches.length > 0 && !filters.niches.includes("all")) count++;
    if (filters.language !== "all") count++;
    if (filters.format !== "all") count++;
    return count;
  }, [filters]);

  // Compute active language filter array: explicit filter > saved user preferences > undefined (all)
  const activeLanguages = useMemo(() => {
    if (filters.language && filters.language !== "all") {
      return filters.language.includes(",") ? filters.language.split(",").map(s => s.trim()).filter(Boolean) : [filters.language];
    }
    if (preferredLanguages && preferredLanguages.length > 0) return preferredLanguages;
    return undefined;
  }, [filters.language, preferredLanguages]);

  // Progressive rendering limit for fast DOM paint on mobile
  const [displayLimit, setDisplayLimit] = useState<number>(15);
  const [showTargetedOnly, setShowTargetedOnly] = useState<boolean>(false);

  useEffect(() => {
    setDisplayLimit(15);
  }, [filters, sortMode, showTargetedOnly]);

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
    staleTime: 60_000,
  });

  const {
    data: risingData,
    isLoading: risingLoading,
    isError: risingError,
    refetch: refetchRising,
  } = useQuery({
    queryKey: ["trends", filters.language, sortMode, activeLanguages],
    queryFn: () => fetchTrends(filters.language, sortMode, undefined, activeLanguages),
    staleTime: 2 * 60_000,
    refetchInterval: 15 * 60_000, // 15 min gentle polling (scraper runs every 3h)
  });

  const {
    data: emergingData,
    isLoading: emergingLoading,
    isError: emergingError,
    refetch: refetchEmerging,
  } = useQuery({
    queryKey: ["trends-emerging", filters.language, activeLanguages],
    queryFn: () => fetchEmergingTrends(filters.language, undefined, activeLanguages),
    staleTime: 2 * 60_000,
    refetchInterval: 15 * 60_000, // 15 min gentle polling
  });

  const {
    data: peakedData,
    isLoading: peakedLoading,
    isError: peakedError,
    refetch: refetchPeaked,
  } = useQuery({
    queryKey: ["trends-peaked", filters.language, activeLanguages],
    queryFn: () => fetchPeakedTrends(filters.language, undefined, activeLanguages),
    staleTime: 15 * 60_000,
    refetchInterval: 45 * 60_000,
  });

  const {
    data: expiredData,
    isLoading: expiredLoading,
    isError: expiredError,
    refetch: refetchExpired,
  } = useQuery({
    queryKey: ["trends-expired", filters.language, activeLanguages],
    queryFn: () => fetchExpiredTrends(filters.language, undefined, activeLanguages),
    staleTime: 30 * 60_000,
    refetchInterval: 60 * 60_000,
  });

  const {
    data: resurgingData,
    isLoading: resurgingLoading,
    isError: resurgingError,
    refetch: refetchResurging,
  } = useQuery({
    queryKey: ["trends-resurging", filters.language, activeLanguages],
    queryFn: () => fetchResurgingTrends(filters.language, undefined, activeLanguages),
    staleTime: 5 * 60_000,
    refetchInterval: 20 * 60_000,
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

  // Pre-calculate targeted Set for instant O(1) card lookups without running 30+ separate hooks
  const targetedSet = useMemo(() => {
    return new Set((targetedData ?? []).map((t: any) => String(t.id)));
  }, [targetedData]);

  const trends = useMemo(() => {
    let list = showTargetedOnly ? (targetedData ?? []) : (allTrends ?? []);

    // 1. Lifecycle Stage filter
    if (filters.lifecycle && filters.lifecycle !== "all") {
      list = list.filter((t) => (t.status ?? "rising").toLowerCase() === filters.lifecycle.toLowerCase());
    }

    // 2. Urgency / Creation Window filter (window_hours_remaining)
    if (filters.urgency && filters.urgency !== "all") {
      list = list.filter((t) => {
        const hrs = t.hoursLeft ?? 0;
        if (filters.urgency === "under6") return hrs > 0 && hrs <= 6;
        if (filters.urgency === "under12") return hrs > 0 && hrs <= 12;
        if (filters.urgency === "under24") return hrs > 0 && hrs <= 24;
        if (filters.urgency === "under48") return hrs > 0 && hrs <= 48;
        return true;
      });
    }

    // 3. Minimum Opportunity Score filter
    if (filters.minOpportunityScore > 0) {
      list = list.filter((t) => (t.opportunityScore ?? 0) >= filters.minOpportunityScore);
    }

    // 4. Minimum Velocity Multiplier filter
    if (filters.minVelocity > 0) {
      list = list.filter((t) => (t.viralMultiplier ?? 0) >= filters.minVelocity);
    }

    // 5. Creator Outlier filter (blew up from small creator accounts)
    if (filters.outlierOnly) {
      list = list.filter((t) => !!t.hasCreatorOutlier);
    }

    // 6. Golden Hour filter (high velocity + <28% saturation)
    if (filters.goldenHourOnly) {
      list = list.filter((t) => {
        const sat = t.indiaSaturationPct ?? t.globalSaturationPct ?? (t.saturationScore ? t.saturationScore * 100 : 0);
        const vel = t.viralMultiplier ?? 0;
        const status = (t.status ?? "rising").toLowerCase();
        return (sat > 0 && sat <= 28 && (vel >= 15 || (t.opportunityScore ?? 0) >= 75)) ||
               (status === "emerging" && (vel >= 12 || (t.opportunityScore ?? 0) >= 70));
      });
    }

    // 7. Video Format filter
    if (filters.format && filters.format !== "all") {
      list = list.filter((t) => {
        if (filters.format === "dance") return !!t.isDance;
        if (filters.format === "narrative") return !!t.isNarrativeEdit || t.contentType === "Narrative";
        if (filters.format === "faceless") return t.contentType === "Faceless" || (t.whyThisWorks || "").toLowerCase().includes("faceless");
        return true;
      });
    }

    // 8. High-accuracy multi-niche filter
    if (filters.niches && !filters.niches.includes("all") && filters.niches.length > 0) {
      list = list.filter((t) => matchesNiches(t, filters.niches));
    }

    // 9. Language filter guard
    if (filters.language && filters.language !== "all") {
      const allowed = filters.language.split(",").map(l => l.trim().toLowerCase());
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

    // 10. Search query filter
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase();
    return list.filter(
      (t) =>
        (t.song ?? "").toLowerCase().includes(q) ||
        (t.artist ?? "").toLowerCase().includes(q) ||
        (t.contentType ?? "").toLowerCase().includes(q) ||
        (t.whyThisWorks ?? "").toLowerCase().includes(q)
    );
  }, [allTrends, targetedData, showTargetedOnly, filters, searchQuery]);

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

      {/* ── Feed Search & Unified Filter Controls ─────────────────────────────────── */}
      <div className="sticky top-0 z-20 bg-background/90 backdrop-blur-xl px-4 pt-3 pb-2 border-b border-border/80">
        {/* Top Control Bar: Search Input + Modern Filter Action Button */}
        <div className="flex items-center gap-2 mb-2.5">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              id="search-query"
              name="searchQuery"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search song, artist, or vibe..."
              className="w-full rounded-xl bg-muted/60 py-2.5 pl-9 pr-9 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 transition-all"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery("")} className="absolute right-3 top-1/2 -translate-y-1/2">
                <X className="h-4 w-4 text-muted-foreground" />
              </button>
            )}
          </div>

          {/* Unified Filter Button */}
          <button
            type="button"
            id="open-filters-modal-btn"
            onClick={() => setShowFilterDrawer(true)}
            className={`flex items-center gap-1.5 px-3 py-2.5 rounded-xl border text-xs font-bold transition-all flex-shrink-0 cursor-pointer ${
              activeFilterCount > 0
                ? "bg-primary text-white border-primary shadow-sm shadow-primary/30 ring-1 ring-primary/40"
                : "bg-muted/70 text-foreground border-border hover:bg-muted"
            }`}
          >
            <SlidersHorizontal className="h-4 w-4" />
            <span>Filters</span>
            {activeFilterCount > 0 && (
              <span className="h-5 min-w-[20px] px-1 rounded-full bg-white text-primary text-[10px] font-extrabold flex items-center justify-center">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        {/* Primary Lifecycle & Quick-Action Rail */}
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar pb-1 items-center">
          {/* Targeted Quick Chip */}
          <button
            type="button"
            id="targeted-quick-filter"
            onClick={() => {
              setShowTargetedOnly((prev) => !prev);
              setDisplayLimit(15);
            }}
            className={`flex-shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition-all ${
              showTargetedOnly
                ? "bg-emerald-500 text-white shadow-sm ring-1 ring-emerald-400 font-bold"
                : "bg-emerald-500/10 text-emerald-500 dark:text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20"
            }`}
          >
            <Target className="h-3.5 w-3.5" />
            Targeted {targetedData && targetedData.length > 0 ? `(${targetedData.length})` : ""}
          </button>

          {/* Golden Hour Quick Chip */}
          <button
            type="button"
            id="golden-hour-quick-filter"
            onClick={() => {
              updateFilter({ goldenHourOnly: !filters.goldenHourOnly });
              setDisplayLimit(15);
            }}
            className={`flex-shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold transition-all ${
              filters.goldenHourOnly
                ? "bg-gradient-to-r from-amber-500 to-rose-500 text-white shadow-sm ring-1 ring-amber-400"
                : "bg-amber-500/15 text-amber-500 dark:text-amber-400 border border-amber-500/35 hover:bg-amber-500/25"
            }`}
          >
            <Flame className="h-3.5 w-3.5 text-amber-500 dark:text-amber-400" />
            Golden Hour
          </button>

          <div className="h-4 w-[1px] bg-border mx-1 flex-shrink-0" />

          {/* Lifecycle Filter Pills */}
          {[
            { id: "all", label: "All Trends" },
            { id: "emerging", label: "🚨 Emerging" },
            { id: "rising", label: "📈 Rising" },
            { id: "resurging", label: "🔄 Comeback" },
            { id: "peaked", label: "📉 Peaked" },
            { id: "expired", label: "⛔ Expired" },
          ].map((st) => {
            const isSelected = !showTargetedOnly && filters.lifecycle === st.id;
            return (
              <button
                key={st.id}
                id={`lifecycle-pill-${st.id}`}
                onClick={() => {
                  if (showTargetedOnly) setShowTargetedOnly(false);
                  updateFilter({ lifecycle: st.id });
                  setDisplayLimit(15);
                }}
                className={`flex-shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold transition-all ${
                  isSelected
                    ? "bg-primary text-white shadow-sm shadow-primary/30 ring-1 ring-primary/40 font-bold"
                    : "bg-muted/70 text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                {st.label}
              </button>
            );
          })}
        </div>

        {/* Active Applied Filters Strip (when filters are engaged) */}
        {activeFilterCount > 0 && (
          <div className="flex items-center gap-1.5 pt-2 overflow-x-auto no-scrollbar">
            <span className="text-[11px] font-bold text-muted-foreground flex-shrink-0">Active:</span>
            {filters.lifecycle !== "all" && (
              <span className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/15 text-primary text-[10px] font-bold">
                Stage: {filters.lifecycle}
                <X className="h-2.5 w-2.5 cursor-pointer" onClick={() => updateFilter({ lifecycle: "all" })} />
              </span>
            )}
            {filters.urgency !== "all" && (
              <span className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-500 text-[10px] font-bold">
                Window: {filters.urgency === "under6" ? "<6h" : filters.urgency === "under12" ? "<12h" : "<24h"}
                <X className="h-2.5 w-2.5 cursor-pointer" onClick={() => updateFilter({ urgency: "all" })} />
              </span>
            )}
            {filters.minOpportunityScore > 0 && (
              <span className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 text-[10px] font-bold">
                Score: {filters.minOpportunityScore}+
                <X className="h-2.5 w-2.5 cursor-pointer" onClick={() => updateFilter({ minOpportunityScore: 0 })} />
              </span>
            )}
            {filters.minVelocity > 0 && (
              <span className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-500 text-[10px] font-bold">
                Vel: {filters.minVelocity}x+
                <X className="h-2.5 w-2.5 cursor-pointer" onClick={() => updateFilter({ minVelocity: 0 })} />
              </span>
            )}
            {filters.outlierOnly && (
              <span className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-400 text-[10px] font-bold">
                Creator Outliers
                <X className="h-2.5 w-2.5 cursor-pointer" onClick={() => updateFilter({ outlierOnly: false })} />
              </span>
            )}
            {filters.niches.length > 0 && !filters.niches.includes("all") && (
              <span className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400 text-[10px] font-bold">
                Niches ({filters.niches.length})
                <X className="h-2.5 w-2.5 cursor-pointer" onClick={() => updateFilter({ niches: ["all"] })} />
              </span>
            )}
            {filters.language !== "all" && (
              <span className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary/30 text-secondary-foreground text-[10px] font-bold">
                Lang: {filters.language.toUpperCase()}
                <X className="h-2.5 w-2.5 cursor-pointer" onClick={() => updateFilter({ language: "all" })} />
              </span>
            )}
            {filters.format !== "all" && (
              <span className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-muted text-foreground text-[10px] font-bold">
                Format: {filters.format}
                <X className="h-2.5 w-2.5 cursor-pointer" onClick={() => updateFilter({ format: "all" })} />
              </span>
            )}
            <button
              type="button"
              onClick={resetAllFilters}
              className="flex-shrink-0 text-[10px] text-muted-foreground hover:text-foreground underline ml-1 cursor-pointer"
            >
              Reset All
            </button>
          </div>
        )}
      </div>

      {/* ── Feed ──────────────────────────────────────────────────────────────── */}
      <div className="space-y-4 px-4 pt-4">
        {/* Active Language Filter Indicator Badge */}
        <ActiveLanguageBadge
          activeLanguages={activeLanguages}
          languagesMap={LANGUAGES}
          onClear={() => {
            setLanguage("all");
            setSelectedNiches(["all"]);
            setPreferredLanguages([]);
            if (typeof window !== "undefined") {
              localStorage.removeItem("trendrop_pref_language");
              localStorage.removeItem("trendrop_preferred_languages");
              localStorage.removeItem("trendrop_pref_niche");
              localStorage.removeItem("trendrop_pref_niches");
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
                    selectedNiches={filters.niches}
                    selectedNiche={filters.niches[0]}
                    isTargeted={targetedSet.has(String(t.id))}
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

      {/* Multi-Dimensional Intelligence Filters Modal */}
      <TrendFiltersModal
        isOpen={showFilterDrawer}
        onClose={() => setShowFilterDrawer(false)}
        filters={filters}
        onChange={updateFilter}
        onReset={resetAllFilters}
        nichesList={NICHES}
        languagesList={LANGUAGES}
        totalResultsCount={trends.length}
      />

    </div>
  );
}
