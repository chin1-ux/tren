import { useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, Clock, Zap, Flame, TrendingUp, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface NewsTrend {
  id: number | string;
  trend_name: string;
  trend_type: "news_event";
  confidence: number;
  status: "emerging" | "rising";
  topic_keywords: string[];
  niche_relevance: Record<string, number>;
  adaptation_briefs: Record<string, string>;
  last_updated_at: string;
  url?: string;
  source?: string;
  recommended_angle?: string;
}

interface NewsTrendCardProps {
  trend: NewsTrend;
  userNiche: string;
  index?: number;
}

const URGENCY_WINDOWS: Record<string, { label: string; color: string; bgColor: string }> = {
  current_affairs: { label: "4h window", color: "text-red-500", bgColor: "bg-red-500/10 border-red-500/30" },
  travel:          { label: "24h window", color: "text-orange-500", bgColor: "bg-orange-500/10 border-orange-500/30" },
  comedy:          { label: "12h window", color: "text-yellow-500", bgColor: "bg-yellow-500/10 border-yellow-500/30" },
  sports:          { label: "6h window", color: "text-blue-500", bgColor: "bg-blue-500/10 border-blue-500/30" },
  default:         { label: "12h window", color: "text-purple-500", bgColor: "bg-purple-500/10 border-purple-500/30" },
};

function getTimeSince(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function getViralPotentialLabel(confidence: number): { label: string; color: string } {
  if (confidence >= 0.8) return { label: "Very High", color: "text-green-500" };
  if (confidence >= 0.6) return { label: "High", color: "text-yellow-500" };
  if (confidence >= 0.4) return { label: "Medium", color: "text-orange-500" };
  return { label: "Low", color: "text-slate-400" };
}

export function NewsTrendCard({ trend, userNiche, index = 0 }: NewsTrendCardProps) {
  const [saved, setSaved] = useState(false);
  const urgency = URGENCY_WINDOWS[userNiche] ?? URGENCY_WINDOWS.default;
  const potentialScore = Math.round((trend.niche_relevance?.[userNiche] ?? trend.confidence) * 100);
  const viralLabel = getViralPotentialLabel(trend.confidence);
  const brief =
    trend.adaptation_briefs?.[userNiche] ??
    trend.recommended_angle ??
    "Create a timely reaction or commentary reel on this breaking story.";
  const timeSince = getTimeSince(trend.last_updated_at);

  const handleSave = () => {
    setSaved(true);
    toast.success("Trend saved to your list");
  };

  const handleUseAngle = () => {
    toast.info("Opening AI Content Generator with this angle...");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08 }}
      className={`rounded-2xl border p-5 ${urgency.bgColor} transition-all hover:shadow-md`}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">📰</span>
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${urgency.bgColor} ${urgency.color} uppercase tracking-wide`}
          >
            BREAKING
          </span>
          <span className="text-[10px] text-muted-foreground">{timeSince}</span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Flame className="h-4 w-4 text-orange-500" />
          <span className={`text-xs font-bold ${viralLabel.color}`}>{viralLabel.label}</span>
        </div>
      </div>

      {/* Title */}
      <h3 className="text-sm font-bold font-display mb-1 leading-snug">{trend.trend_name}</h3>

      {/* Keywords */}
      {trend.topic_keywords?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {trend.topic_keywords.slice(0, 5).map((kw) => (
            <span
              key={kw}
              className="px-2 py-0.5 text-[10px] bg-white/10 text-muted-foreground rounded-full border border-border/40"
            >
              #{kw}
            </span>
          ))}
        </div>
      )}

      <div className="border-t border-border/30 my-3" />

      {/* Creator Brief */}
      <div className="mb-3">
        <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1">
          <BookOpen className="h-3 w-3" />
          Your Angle
        </p>
        <p className="text-xs text-foreground/80 leading-relaxed">{brief}</p>
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 mb-4 text-[10px] text-muted-foreground">
        <div className="flex items-center gap-1">
          <TrendingUp className="h-3 w-3" />
          <span>
            Viral Potential:{" "}
            <span className={`font-bold ${viralLabel.color}`}>{potentialScore}%</span>
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          <span className={`font-semibold ${urgency.color}`}>{urgency.label}</span>
        </div>
        {trend.source && (
          <div className="flex items-center gap-1">
            <ExternalLink className="h-3 w-3" />
            <span>{trend.source}</span>
          </div>
        )}
      </div>

      {/* CTA */}
      <div className="flex gap-2">
        <Button size="sm" className="flex-1 rounded-full text-xs h-8 gap-1.5" onClick={handleUseAngle}>
          <Zap className="h-3 w-3" />
          Use This Angle
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="rounded-full text-xs h-8 px-3"
          onClick={handleSave}
          disabled={saved}
        >
          {saved ? "Saved ✓" : "Save"}
        </Button>
      </div>
    </motion.div>
  );
}
