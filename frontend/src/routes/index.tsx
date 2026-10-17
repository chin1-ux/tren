import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, X, Target } from "lucide-react";
import {
  fetchTrends,
  fetchEmergingTrends,
  fetchPeakedTrends,
  fetchExpiredTrends,
  fetchResurgingTrends,
  fetchTargetedTrends,
  type UiTrend,
} from "@/lib/api";
import { TrendCard } from "@/components/TrendCard";
import { SkeletonCard } from "@/components/SkeletonCard";
import { DanceTrendModal } from "@/components/DanceTrendModal";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { ParticleBackground } from "@/components/ParticleBackground";
import { TrenddropLogo } from "@/components/TrenddropLogo";
import { toast } from "sonner";
import { ThemeToggle } from "@/components/ThemeToggle";
import { ActiveLanguageBadge } from "@/components/ActiveLanguageBadge";
import { useUserStore } from "@/store/useAppStore";
import { useAuth } from "@/contexts/AuthContext";
import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Trendrop — India & Global Audio Intelligence" },
      {
        name: "description",
        content:
          "Know what's trending before your competitor even opens Instagram. Real-time viral audio intelligence.",
      },
    ],
  }),
  component: TrendsFeed,
  errorComponent: RouteErrorBoundary,
});

const LANGUAGES = [
  { code: "all", label: "🌐 All" },
  { code: "en", label: "🇺🇸 English" },
  { code: "hi", label: "🇮🇳 Hindi" },
  { code: "pa", label: "🌾 Punjabi" },
  { code: "ta", label: "🌴 Tamil" },
  { code: "te", label: "🌟 Telugu" },
  { code: "ml", label: "🥥 Malayalam" },
  { code: "kn", label: "🎯 Kannada" },
  { code: "bn", label: "🐯 Bengali" },
  { code: "mr", label: "🦁 Marathi" },
  { code: "gu", label: "🪔 Gujarati" },
  { code: "ne", label: "🏔️ Nepali" },
  { code: "pt", label: "🇧🇷 Brazilian" },
  { code: "ko", label: "🇰🇷 Korean" },
  { code: "ru", label: "🇷🇺 Russian" },
  { code: "es", label: "🇪🇸 Spanish" },
  { code: "instrumental", label: "🎼 Instrumental" },
];

const NICHES = [
  { id: "all", label: "All" },
  { id: "fitness", label: "💪 Fitness" },
  { id: "food", label: "🍜 Food" },
  { id: "comedy", label: "😂 Comedy" },
  { id: "fashion", label: "👗 Fashion" },
  { id: "business", label: "💼 Business" },
  { id: "travel", label: "✈️ Travel" },
  { id: "beauty", label: "💄 Beauty" },
  { id: "devotional", label: "🙏 Devotional" },
  { id: "tech", label: "💻 Tech" },
  { id: "dance", label: "💃 Dance" },
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
  if (t.semanticNiches && t.semanticNiches.some((s) => s.toLowerCase() === niche)) return true;
  if (t.contentType && t.contentType.toLowerCase() === niche) return true;

  // High-accuracy semantic match from whyThisWorks and used_for_note
  const context = `${t.whyThisWorks || ""} ${t.used_for_note || ""} ${t.used_for || ""} ${t.idealContentDescription || ""}`.toLowerCase();
  const kws = NICHE_KEYWORDS_MAP[niche] || [];
  return kws.some((kw) => context.includes(kw));
}

function TrendsFeed() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const userEmail = user?.email ?? null;

  // Filters State
  const [language, setLanguage] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("trendrop_pref_language") || "all";
    }
    return "all";
  });
  const [selectedNiche, setSelectedNiche] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("trendrop_pref_niche") || "all";
    }
    return "all";
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [showTargetedOnly, setShowTargetedOnly] = useState(false);
  const [danceTrend, setDanceTrend] = useState<UiTrend | null>(null);
  const [displayLimit, setDisplayLimit] = useState(30);

  const rawPreferredLanguages = useUserStore((s) => s.preferredLanguages);
  const preferredLanguages = useMemo(() => rawPreferredLanguages || [], [rawPreferredLanguages]);
  const setPreferredLanguages = useUserStore((s) => s.setPreferredLanguages);

  const activeLanguages = useMemo(() => {
    if (language !== "all") return [language];
    return preferredLanguages.length > 0 ? preferredLanguages : undefined;
  }, [language, preferredLanguages]);

  useEffect(() => {
    setDisplayLimit(30);
  }, [language, selectedNiche, showTargetedOnly, searchQuery]);

  // Data Queries
  const { data: targetedData } = useQuery({
    queryKey: ["trends-targeted"],
    queryFn: () => fetchTargetedTrends(),
    staleTime: 10_000,
  });

  const {
    data: feedData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ["unified-feed-home", language, activeLanguages],
    queryFn: async () => {
      try {
        const res = await fetchFeed({
          limit: 100,
          language: language !== "all" ? language : undefined,
          languages: activeLanguages,
          sort: "newest",
        });
        if (res && res.trends && res.trends.length > 0) {
          return res.trends;
        }
      } catch (err) {
        console.warn("fetchFeed fallback to fetchTrends:", err);
      }
      return fetchTrends(language !== "all" ? language : undefined, undefined, undefined, activeLanguages);
    },
    staleTime: 30_000,
    refetchInterval: 5 * 60_000,
    refetchOnWindowFocus: false,
  });

  // Filter trends by Targeted, Niche, and Search query
  const trends = useMemo(() => {
    let list = (showTargetedOnly && targetedData ? targetedData : feedData) || [];

    // Niche filter
    if (selectedNiche !== "all") {
      list = list.filter((t) => matchesNiche(t, selectedNiche));
    }

    // Search query filter (matches song, artist, niche, why_this_works, used_for_note)
    const q = searchQuery.toLowerCase().trim();
    if (q) {
      list = list.filter(
        (t) =>
          (t.song ?? "").toLowerCase().includes(q) ||
          (t.artist ?? "").toLowerCase().includes(q) ||
          (t.nicheTag ?? "").toLowerCase().includes(q) ||
          (t.whyThisWorks ?? "").toLowerCase().includes(q) ||
          (t.used_for_note ?? "").toLowerCase().includes(q) ||
          (t.contentType ?? "").toLowerCase().includes(q)
      );
    }

    return list;
  }, [feedData, targetedData, showTargetedOnly, selectedNiche, searchQuery]);

  const withCountdown = useCallback(
    (t: UiTrend): UiTrend => ({
      ...t,
      hoursLeft: Math.max(0, Math.ceil(((t.expiresAt || Date.now() + 24 * 3600_000) - Date.now()) / 3600_000)),
    }),
    []
  );

  return (
    <div className="flex flex-col gap-0 pb-24">
      {/* ── Hero Section with Coral Glow & Header ───────────────────────────────── */}
      <div className="relative overflow-hidden bg-gradient-to-b from-[rgba(255,77,61,0.14)] via-[rgba(255,77,61,0.05)] to-transparent px-4 pb-4 pt-6 rounded-b-[2rem] border-b border-border/30">
        <ParticleBackground />

        {/* Header Row */}
        <div className="relative flex items-center justify-between mb-4">
          <TrenddropLogo size={34} />

          <div className="flex items-center gap-2">
            <ThemeToggle />

            <button
              onClick={() => navigate({ to: "/settings" })}
              className="relative rounded-full overflow-hidden h-8 w-8 border border-white/10 hover:border-primary/50 transition-all flex-shrink-0 cursor-pointer"
              aria-label="Profile"
            >
              <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-primary/40 to-secondary/40 text-xs font-bold text-white uppercase">
                {userEmail ? userEmail.charAt(0) : "T"}
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* ── Sticky Filter Bar & Search ─────────────────────────────────────────── */}
      <div className="sticky top-0 z-20 bg-background/95 backdrop-blur-xl px-4 pt-3 pb-2 border-b border-border">
        {/* Niche Filter Chips */}
        <div className="flex gap-2 overflow-x-auto no-scrollbar pb-1 mb-2">
          {NICHES.map((n) => (
            <button
              key={n.id}
              id={`niche-chip-${n.id}`}
              onClick={() => {
                setSelectedNiche(n.id);
                if (typeof window !== "undefined") localStorage.setItem("trendrop_pref_niche", n.id);
              }}
              className={`flex-shrink-0 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
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
            onClick={() => setShowTargetedOnly((prev) => !prev)}
            className={`flex-shrink-0 flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-semibold transition-all cursor-pointer ${
              showTargetedOnly
                ? "bg-emerald-500 text-white shadow-sm ring-1 ring-emerald-400"
                : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20"
            }`}
          >
            <Target className="h-3 w-3" />
            Targeted {targetedData && targetedData.length > 0 ? `(${targetedData.length})` : ""}
          </button>
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              id={`lang-chip-${l.code}`}
              onClick={() => {
                const newLang = l.code === language ? "all" : l.code;
                setLanguage(newLang);
                if (typeof window !== "undefined") localStorage.setItem("trendrop_pref_language", newLang);
              }}
              className={`flex-shrink-0 rounded-full px-3 py-1 text-[11px] font-medium transition-all cursor-pointer ${
                language === l.code
                  ? "bg-primary text-white shadow-sm ring-1 ring-primary/50"
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
            placeholder="Search 2,000+ audios, artist, 'Gym beat drop', 'Fashion transition'..."
            className="w-full rounded-xl bg-muted/60 py-2.5 pl-9 pr-9 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery("")} className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer">
              <X className="h-4 w-4 text-muted-foreground" />
            </button>
          )}
        </div>
      </div>

      {/* ── Feed Container ────────────────────────────────────────────────────── */}
      <div className="space-y-4 px-4 pt-4 max-w-3xl mx-auto w-full">
        {/* Active Filter Clear Badge */}
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

        {isError && (
          <div className="space-y-2">
            <ApiErrorBanner message="Unable to load trends. Please try again." />
            <button onClick={refetch} className="text-xs font-semibold text-primary underline cursor-pointer">
              Try again
            </button>
          </div>
        )}

        {isLoading ? (
          <div className="space-y-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : !isError && trends.length === 0 ? (
          <div className="glass-card p-12 text-center rounded-2xl border border-border">
            <p className="text-4xl mb-3">{showTargetedOnly ? "🎯" : "🎵"}</p>
            <p className="text-base font-semibold">
              {showTargetedOnly ? "Your targeted workspace is empty" : "No trends found for this filter"}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {showTargetedOnly
                ? "Click 'Target Trend' on any trend card to save and track your targeted audios here."
                : 'Try selecting "All" or a different niche / language to discover more viral audios.'}
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {trends.slice(0, displayLimit).map((t) => (
              <div key={t.id} className={t.status === "expired" ? "opacity-50 grayscale-[25%]" : ""}>
                <TrendCard
                  trend={withCountdown(t)}
                  onDanceTap={setDanceTrend}
                  selectedNiche={selectedNiche}
                  showStatusBadge={true}
                />
              </div>
            ))}
          </div>
        )}

        {/* Load More Button (100% Free Catalog Access) */}
        {displayLimit < trends.length && (
          <div className="text-center py-6">
            <button
              id="load-more-btn"
              onClick={() => setDisplayLimit((prev) => Math.min(prev + 30, trends.length))}
              className="rounded-xl bg-primary text-white text-xs font-bold px-6 py-3 transition-all shadow-md shadow-primary/20 hover:bg-primary/90 cursor-pointer"
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
