import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState, useCallback } from "react";
import { useQuery, useInfiniteQuery } from "@tanstack/react-query";
import {
  Layers,
  Compass,
  BookmarkCheck,
  Settings,
  LayoutDashboard,
  Wrench,
  LogOut,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import {
  fetchFeed,
  fetchRecentScraperRuns,
  toggleTrendTarget,
  type UiTrend,
} from "@/lib/api";
import { DeckView } from "@/components/DeckView";
import { ExploreView } from "@/components/ExploreView";
import { PicksView } from "@/components/PicksView";
import { ThemeToggle } from "@/components/ThemeToggle";
import { TrenddropLogo } from "@/components/TrenddropLogo";
import { useUserStore } from "@/store/useAppStore";
import { useAuth } from "@/contexts/AuthContext";
import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";
import { toast } from "sonner";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Trendrop — Audio Intelligence & Deck" },
      {
        name: "description",
        content: "Discover breakout audios before your competitors. High-speed swipe deck and trend intelligence.",
      },
    ],
  }),
  component: TrendsFeed,
  errorComponent: RouteErrorBoundary,
});

function TrendsFeed() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const userEmail = useUserStore((s) => s.email);

  // Tab State: explore (default catalog discovery) | deck | picks
  const [activeTab, setActiveTab] = useState<"deck" | "explore" | "picks">(() => {
    if (typeof window !== "undefined") {
      const p = new URLSearchParams(window.location.search);
      const t = p.get("tab");
      if (t === "deck" || t === "picks") return t;
    }
    return "explore";
  });

  const [showAvatarMenu, setShowAvatarMenu] = useState(false);

  // Sync tab with URL
  const handleTabChange = (tab: "deck" | "explore" | "picks") => {
    setActiveTab(tab);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      if (tab === "explore") {
        url.searchParams.delete("tab");
      } else {
        url.searchParams.set("tab", tab);
      }
      window.history.replaceState({}, "", url.toString());
    }
  };

  // ── Scraper Runs Query (For Data Delay Banner & Next Drop Calculation) ──────
  const { data: scraperRuns = [] } = useQuery({
    queryKey: ["scraper-runs"],
    queryFn: () => fetchRecentScraperRuns(5),
    staleTime: 5 * 60_000,
    refetchOnWindowFocus: false,
  });

  const { isDataDelayed, nextDropTime } = useMemo(() => {
    if (!scraperRuns || scraperRuns.length === 0) {
      return { isDataDelayed: false, nextDropTime: "in 2 hours" };
    }
    const latest = scraperRuns[0];
    const ts = new Date(latest.run_at || latest.created_at).getTime();
    if (isNaN(ts)) {
      return { isDataDelayed: false, nextDropTime: "in 2 hours" };
    }

    const ageHours = (Date.now() - ts) / (1000 * 60 * 60);
    const nextDropHours = Math.max(0.5, Math.round((3.0 - (ageHours % 3.0)) * 10) / 10);
    return {
      isDataDelayed: ageHours > 6.0,
      nextDropTime: `in ~${nextDropHours}h`,
    };
  }, [scraperRuns]);

  // ── Infinite Unified Feed Query ───────────────────────────────────────────
  const {
    data: infiniteFeedData,
    isLoading: isFeedLoading,
    isError: isFeedError,
    refetch: refetchFeed,
    hasNextPage,
    isFetchingNextPage,
    fetchNextPage,
  } = useInfiniteQuery({
    queryKey: ["unified-feed-deck"],
    queryFn: ({ pageParam = 1 }) =>
      fetchFeed({
        page: pageParam as number,
        limit: 30,
        sort: "newest",
      }),
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) =>
      lastPage.has_more ? allPages.length + 1 : undefined,
    staleTime: 5 * 60_000,
    refetchInterval: false, // Order 81: Disabled periodic refetch to prevent idle tabs from burning Vercel Edge requests
    refetchOnWindowFocus: false,
  });

  const allTrends = useMemo(() => {
    return infiniteFeedData?.pages.flatMap((p) => p.trends) ?? [];
  }, [infiniteFeedData]);

  // ── Saved Picks State ─────────────────────────────────────────────────────
  const [savedPicks, setSavedPicks] = useState<UiTrend[]>(() => {
    if (typeof window !== "undefined") {
      try {
        const raw = localStorage.getItem("trendrop_saved_picks");
        if (raw) return JSON.parse(raw);
      } catch {}
    }
    return [];
  });

  const handleSavePick = useCallback(async (trend: UiTrend) => {
    setSavedPicks((prev) => {
      if (prev.some((p) => p.id === trend.id)) return prev;
      const next = [trend, ...prev];
      if (typeof window !== "undefined") {
        localStorage.setItem("trendrop_saved_picks", JSON.stringify(next));
      }
      return next;
    });

    try {
      await toggleTrendTarget(trend.id, "target");
    } catch {}
  }, []);

  const handleRemovePick = useCallback((trendId: string) => {
    setSavedPicks((prev) => {
      const next = prev.filter((p) => p.id !== trendId);
      if (typeof window !== "undefined") {
        localStorage.setItem("trendrop_saved_picks", JSON.stringify(next));
      }
      return next;
    });
    toast.info("Removed from Picks");
  }, []);

  const handleSelectTrend = (trend: UiTrend) => {
    navigate({ to: "/trend/$id", params: { id: trend.id } });
  };

  const handleLogout = async () => {
    await logout();
    navigate({ to: "/login" });
  };

  return (
    <div className="flex flex-col min-h-screen pb-20 max-w-xl mx-auto px-4 pt-4">
      {/* ── HEADER ──────────────────────────────────────────────────────────── */}
      <header className="flex items-center justify-between pb-3 mb-3 border-b border-white/10 relative">
        <TrenddropLogo size={32} />

        <div className="flex items-center gap-2.5">
          <ThemeToggle />

          {/* Profile Avatar with Dropdown */}
          <div className="relative">
            <button
              type="button"
              id="header-profile-avatar"
              onClick={() => setShowAvatarMenu(!showAvatarMenu)}
              className="h-8 w-8 rounded-full overflow-hidden border border-white/20 hover:border-primary/60 transition-all flex items-center justify-center bg-gradient-to-br from-primary/30 to-purple-600/30 text-white font-bold text-xs uppercase cursor-pointer"
              aria-label="User Menu"
            >
              {userEmail ? userEmail.charAt(0) : "T"}
            </button>

            {showAvatarMenu && (
              <div
                className="absolute right-0 top-10 w-52 rounded-2xl bg-zinc-950 border border-white/15 p-2 shadow-2xl z-50 flex flex-col gap-1 backdrop-blur-xl animate-fade-in-up"
                onClick={() => setShowAvatarMenu(false)}
              >
                <div className="px-3 py-2 border-b border-white/10">
                  <span className="text-[10px] text-zinc-500 uppercase font-bold block">Account</span>
                  <p className="text-xs text-white font-semibold truncate">{userEmail || "Guest User"}</p>
                </div>

                <button
                  type="button"
                  onClick={() => navigate({ to: "/dashboard" })}
                  className="w-full px-3 py-2 rounded-xl text-left text-xs text-zinc-300 hover:text-white hover:bg-zinc-900 flex items-center gap-2 cursor-pointer"
                >
                  <LayoutDashboard className="h-4 w-4 text-zinc-400" />
                  <span>Dashboard</span>
                </button>

                <button
                  type="button"
                  onClick={() => navigate({ to: "/studio" })}
                  className="w-full px-3 py-2 rounded-xl text-left text-xs text-zinc-300 hover:text-white hover:bg-zinc-900 flex items-center gap-2 cursor-pointer"
                >
                  <Wrench className="h-4 w-4 text-zinc-400" />
                  <span>Studio</span>
                </button>

                <button
                  type="button"
                  onClick={() => navigate({ to: "/settings" })}
                  className="w-full px-3 py-2 rounded-xl text-left text-xs text-zinc-300 hover:text-white hover:bg-zinc-900 flex items-center gap-2 cursor-pointer"
                >
                  <Settings className="h-4 w-4 text-zinc-400" />
                  <span>Settings</span>
                </button>

                {user && (
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="w-full px-3 py-2 rounded-xl text-left text-xs text-red-400 hover:bg-red-500/10 flex items-center gap-2 cursor-pointer border-t border-white/5 mt-1"
                  >
                    <LogOut className="h-4 w-4" />
                    <span>Log out</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* ── TOP THREE TABS: Deck | Explore | Picks ───────────────────────────── */}
      <div className="grid grid-cols-3 gap-1 p-1 bg-zinc-900/80 border border-white/10 rounded-2xl mb-4 backdrop-blur-md">
        <button
          type="button"
          id="nav-tab-deck"
          onClick={() => handleTabChange("deck")}
          className={`py-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
            activeTab === "deck"
              ? "bg-white text-black shadow-md font-black"
              : "text-zinc-400 hover:text-white"
          }`}
        >
          <Layers className="h-4 w-4" />
          <span>Deck</span>
        </button>

        <button
          type="button"
          id="nav-tab-explore"
          onClick={() => handleTabChange("explore")}
          className={`py-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
            activeTab === "explore"
              ? "bg-white text-black shadow-md font-black"
              : "text-zinc-400 hover:text-white"
          }`}
        >
          <Compass className="h-4 w-4" />
          <span>Explore</span>
        </button>

        <button
          type="button"
          id="nav-tab-picks"
          onClick={() => handleTabChange("picks")}
          className={`py-2 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
            activeTab === "picks"
              ? "bg-white text-black shadow-md font-black"
              : "text-zinc-400 hover:text-white"
          }`}
        >
          <BookmarkCheck className="h-4 w-4" />
          <span>Picks ({savedPicks.length})</span>
        </button>
      </div>

      {/* ── ACTIVE TAB VIEW ──────────────────────────────────────────────────── */}
      {activeTab === "deck" && (
        <DeckView
          trends={allTrends}
          isLoading={isFeedLoading && allTrends.length === 0}
          isError={isFeedError}
          onRetry={refetchFeed}
          nextDropTime={nextDropTime}
          isDataDelayed={isDataDelayed}
          onSavePick={handleSavePick}
        />
      )}

      {activeTab === "explore" && (
        <ExploreView
          trends={allTrends}
          onSelectTrend={handleSelectTrend}
          onSavePick={handleSavePick}
          hasMore={hasNextPage}
          isLoadingMore={isFetchingNextPage}
          onLoadMore={() => fetchNextPage()}
        />
      )}

      {activeTab === "picks" && (
        <PicksView picks={savedPicks} onRemovePick={handleRemovePick} />
      )}
    </div>
  );
}
