import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { NewsTrendCard } from "@/components/NewsTrendCard";
import { Newspaper, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { useUserStore } from "@/store/useAppStore";

interface ContentTrend {
  id: number | string;
  trend_name: string;
  trend_type: string;
  confidence: number;
  status: "emerging" | "rising";
  topic_keywords: string[];
  niche_relevance: Record<string, number>;
  adaptation_briefs: Record<string, string>;
  last_updated_at: string;
  source?: string;
  recommended_angle?: string;
}

// News-type trends expected in content_trends table with trend_type = 'news_event'
export function NewsFeedPanel() {
  const [trends, setTrends] = useState<ContentTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const userNiche = useUserStore((s) => s.niche) || "current_affairs";

  useEffect(() => {
    fetchNewsTrends();
  }, []);

  const fetchNewsTrends = async () => {
    setLoading(true);
    try {
      // Try fetching from content_trends endpoint
      const res = await apiFetch("/api/content-trends?type=news_event");
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setTrends(data);
          setLoading(false);
          return;
        }
      }
    } catch {
      // fall through
    }

    // Fallback: pull from news_virality_predictions (the older endpoint)
    try {
      const res2 = await apiFetch("/api/news/virality-predictions?limit=10");
      if (res2.ok) {
        const data2 = await res2.json();
        if (Array.isArray(data2) && data2.length > 0) {
          // Normalize to ContentTrend shape
          setTrends(
            data2.map((n: any) => ({
              id: n.id ?? n.headline,
              trend_name: n.headline ?? n.title ?? "Trending Story",
              trend_type: "news_event",
              confidence: (n.viral_potential_score ?? 0) / 100,
              status: "rising",
              topic_keywords: n.keywords ?? [],
              niche_relevance: n.niche_relevance ?? {},
              adaptation_briefs: n.creator_opportunity ?? {},
              last_updated_at: n.detected_at ?? new Date().toISOString(),
              source: n.source,
              recommended_angle: n.recommended_angle,
            }))
          );
          setLoading(false);
          return;
        }
      }
    } catch {
      // fall through
    }

    // No data at all — show empty state
    setTrends([]);
    setLoading(false);
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 bg-card/50 border border-border/50 animate-pulse rounded-2xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold font-display flex items-center gap-2">
            <Newspaper className="h-5 w-5 text-blue-500" />
            Breaking News Feed
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            News events with content opportunity for {userNiche === "current_affairs" ? "current affairs creators" : "your niche"}
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="rounded-full gap-1.5 text-xs h-8"
          onClick={fetchNewsTrends}
        >
          <RefreshCw className="h-3 w-3" />
          Refresh
        </Button>
      </div>

      {trends.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Newspaper className="h-12 w-12 text-muted-foreground mb-3" />
          <p className="text-sm font-semibold text-muted-foreground">No breaking news signals right now</p>
          <p className="text-xs text-muted-foreground mt-1 max-w-xs">
            Our pipeline checks for news events every hour. Check back soon.
          </p>
        </div>
      ) : (
        trends.map((trend, idx) => (
          <NewsTrendCard key={trend.id} trend={trend as any} userNiche={userNiche} index={idx} />
        ))
      )}
    </div>
  );
}
