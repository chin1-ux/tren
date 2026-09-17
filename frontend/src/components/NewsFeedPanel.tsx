import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Newspaper, RefreshCw, AlertCircle, Clock,
  ExternalLink, BookOpen, TrendingUp, Zap
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { useUserStore } from "@/store/useAppStore";

interface NewsTrend {
  id: string;
  trend_name: string;
  trend_type: string;
  confidence: number;
  status: "emerging" | "rising";
  topic_keywords: string[];
  niche_relevance: Record<string, number>;
  adaptation_briefs: Record<string, string>;
  last_updated_at: string;
  recommended_angle?: string;
}

function getTimeSince(isoString: string): string {
  try {
    const diff = Date.now() - new Date(isoString).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  } catch {
    return "";
  }
}

function getConfidenceBadge(confidence: number): { label: string; color: string; bg: string } {
  const c = confidence > 1 ? confidence / 100 : confidence;
  if (c >= 0.8) return { label: "High Impact", color: "text-green-400", bg: "bg-green-500/10 border-green-500/20" };
  if (c >= 0.6) return { label: "Rising", color: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/20" };
  return { label: "Emerging", color: "text-blue-400", bg: "bg-blue-500/10 border-blue-500/20" };
}

// Strip source attribution from headline (e.g. " - NDTV" at the end)
function cleanHeadline(name: string): string {
  return name.replace(/ - [A-Za-z][A-Za-z ]{1,40}$/, "").trim();
}

function getSource(name: string): string | null {
  const match = name.match(/ - ([A-Za-z][A-Za-z ]{1,40})$/);
  return match ? match[1].trim() : null;
}

export function NewsFeedPanel() {
  const [trends, setTrends] = useState<NewsTrend[]>([]);
  const [loading, setLoading] = useState(true);
  const [isEmpty, setIsEmpty] = useState(false);
  const userNiche = useUserStore((s) => s.niche) || "general";

  useEffect(() => {
    fetchNews();
  }, []);

  const fetchNews = async () => {
    setLoading(true);
    setIsEmpty(false);
    try {
      // Fixed: was querying news_event, DB has type='news'
      const res = await apiFetch("/api/content-trends?type=news");
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setTrends(data);
          setLoading(false);
          return;
        }
      }
    } catch (err) {
      console.error("news fetch error:", err);
    }

    // Try alias endpoint
    try {
      const res2 = await apiFetch("/api/news/virality-predictions?limit=15");
      if (res2.ok) {
        const data2 = await res2.json();
        if (Array.isArray(data2) && data2.length > 0) {
          setTrends(data2);
          setLoading(false);
          return;
        }
      }
    } catch (err2) {
      console.error("virality-predictions fetch error:", err2);
    }

    setTrends([]);
    setIsEmpty(true);
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
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold font-display flex items-center gap-2">
            <Newspaper className="h-5 w-5 text-blue-400" />
            Breaking News Feed
            <span
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                trends.length > 0
                  ? "bg-green-500/10 border-green-500/30 text-green-400"
                  : "bg-muted border-border text-muted-foreground"
              }`}
            >
              {trends.length > 0 ? `🟢 ${trends.length} stories` : "No data"}
            </span>
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Real-time pop culture, sports & news signals for instant reel ideas · filtered for creator relevance
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          className="rounded-full gap-1.5 text-xs h-8 shrink-0"
          onClick={fetchNews}
        >
          <RefreshCw className="h-3 w-3" />
          Refresh
        </Button>
      </div>

      {/* Empty state — honest, not fabricated */}
      {isEmpty || trends.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
          <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center">
            <Newspaper className="h-7 w-7 text-muted-foreground" />
          </div>
          <div>
            <p className="text-sm font-semibold text-muted-foreground">No fresh news signals right now</p>
            <p className="text-xs text-muted-foreground mt-1 max-w-sm leading-relaxed">
              Our pipeline ingests news from verified Indian media sources every hour. Stories older
              than 72 hours are automatically filtered out to keep the feed fresh.
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="rounded-full gap-1.5 text-xs mt-2"
            onClick={fetchNews}
          >
            <RefreshCw className="h-3 w-3" />
            Try Again
          </Button>
          <p className="text-[11px] text-muted-foreground/60">
            Tip: News signals refresh every 60 minutes during peak hours (9am–10pm IST)
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {trends.map((trend, idx) => {
            const confidence = trend.confidence > 1 ? trend.confidence / 100 : trend.confidence;
            const badge = getConfidenceBadge(confidence);
            const headline = cleanHeadline(trend.trend_name);
            const source = getSource(trend.trend_name);
            const brief =
              trend.adaptation_briefs?.[userNiche] ??
              trend.recommended_angle ??
              "Create a timely reaction or commentary reel on this story.";
            const timeAgo = getTimeSince(trend.last_updated_at);
            const nicheScore = Math.round(
              ((trend.niche_relevance?.[userNiche] ?? confidence) * 100)
            );

            return (
              <motion.div
                key={trend.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.07 }}
                className="bg-card border border-border/60 p-4 rounded-2xl hover:border-blue-500/20 hover:shadow-md transition-all"
              >
                {/* Header row */}
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-base">📰</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badge.bg} ${badge.color} uppercase tracking-wide`}
                    >
                      {badge.label}
                    </span>
                    {timeAgo && (
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {timeAgo}
                      </span>
                    )}
                    {source && (
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <ExternalLink className="h-3 w-3" />
                        {source}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <TrendingUp className="h-3.5 w-3.5 text-blue-400" />
                    <span className={`text-xs font-bold ${badge.color}`}>{nicheScore}%</span>
                  </div>
                </div>

                {/* Headline */}
                <h3 className="text-sm font-bold font-display leading-snug mb-2">{headline}</h3>

                {/* Keywords */}
                {trend.topic_keywords?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {trend.topic_keywords.slice(0, 4).map((kw) => (
                      <span
                        key={kw}
                        className="px-2 py-0.5 text-[10px] bg-muted text-muted-foreground rounded-full"
                      >
                        #{kw}
                      </span>
                    ))}
                  </div>
                )}

                <div className="border-t border-border/30 my-2" />

                {/* Creator angle */}
                <div className="mb-3">
                  <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
                    <BookOpen className="h-3 w-3" />
                    Your Angle
                  </p>
                  <p className="text-xs text-foreground/80 leading-relaxed">{brief}</p>
                </div>

                {/* CTA */}
                <Button
                  size="sm"
                  className="w-full rounded-full text-xs h-8 gap-1.5"
                  onClick={() => {
                    // Copy headline to clipboard for quick use
                    navigator.clipboard?.writeText(headline).catch(() => {});
                    // Navigate to AI generator with this as context
                    window.location.href = "/generate";
                  }}
                >
                  <Zap className="h-3 w-3" />
                  Create Reel on This Story
                </Button>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
