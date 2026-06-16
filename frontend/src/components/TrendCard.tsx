import { useNavigate } from "@tanstack/react-router";
import {
  Clock, Flame, Video, ChevronDown, ChevronUp,
  Copy, CheckCheck, Info, Zap, TrendingUp,
} from "lucide-react";
import type { UiTrend } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTrendReels } from "@/lib/api";
import { toast } from "sonner";

interface Props {
  trend: UiTrend;
  onDanceTap: (trend: UiTrend) => void;
}

// Saturation indicator config
function getSaturationMeta(score: number): { label: string; color: string; dot: string } {
  if (score < 0.2) return { label: "Very Early 🟢", color: "text-emerald-400", dot: "bg-emerald-400" };
  if (score < 0.5) return { label: "Getting Popular 🟡", color: "text-amber-400", dot: "bg-amber-400" };
  if (score < 0.75) return { label: "Trending 🟠", color: "text-orange-400", dot: "bg-orange-400" };
  return { label: "Almost Peaked 🔴", color: "text-red-400", dot: "bg-red-400" };
}

function getPlatformMeta(platform: string): { label: string; icon: string } {
  if (platform === "youtube_shorts") return { label: "YouTube Shorts", icon: "▶" };
  return { label: "Instagram", icon: "◎" };
}

export function TrendCard({ trend, onDanceTap }: Props) {
  const navigate = useNavigate();
  const [showReels, setShowReels] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showWhy, setShowWhy] = useState(false);
  const cardRef = useRef<HTMLElement>(null);

  const isEmerging = trend.isEmerging || trend.status === "emerging";
  const isUrgent = trend.hoursLeft <= 6;

  const satMeta = getSaturationMeta(trend.saturationScore ?? 0);
  const platformMeta = getPlatformMeta(trend.bestPlatformFirst ?? "instagram");
  const viralPct = Math.min(100, (trend.viralMultiplier / 30) * 100);

  const { data: reels } = useQuery({
    queryKey: ["trend-reels", trend.id],
    queryFn: () => fetchTrendReels(trend.id),
    enabled: showReels,
    staleTime: 5 * 60_000,
  });

  // 3D Tilt effect
  const onMouseMove = useCallback((e: React.MouseEvent<HTMLElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const rotX = ((y - cy) / cy) * -6;
    const rotY = ((x - cx) / cx) * 6;
    cardRef.current.style.transform = `perspective(800px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateZ(4px)`;
  }, []);

  const onMouseLeave = useCallback(() => {
    if (!cardRef.current) return;
    cardRef.current.style.transform = "perspective(800px) rotateX(0deg) rotateY(0deg) translateZ(0)";
  }, []);

  const formatViews = (v: number) => {
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
    return v.toString();
  };

  const copyCaption = () => {
    // Copy a quick caption based on trend info
    const text = `${trend.idealContentDescription || trend.song} 🔥 #trending #reels #${trend.contentType?.toLowerCase().replace(/\s+/g, "")}`;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      toast.success("Caption copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <article
      ref={cardRef}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      className={`tilt-card relative space-y-4 rounded-2xl p-5 transition-all duration-200 ${
        isEmerging
          ? "neon-border-emerging animate-pulse-urgent bg-[rgba(255,0,110,0.04)]"
          : isUrgent
          ? "neon-border bg-[rgba(230,57,70,0.04)]"
          : "glass-card"
      }`}
    >
      {/* Emerging badge */}
      {isEmerging && (
        <div className="absolute -top-3 left-4">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-[#ff006e] px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-white shadow-lg">
            <Zap className="h-3 w-3" /> EMERGING FIRST
          </span>
        </div>
      )}

      {/* Top row: status + timer */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-primary">
            <Flame className="h-3 w-3" /> {isEmerging ? "Emerging" : "Trending"}
          </span>
          {/* Platform badge */}
          <span className="inline-flex items-center gap-1 rounded-full bg-white/5 px-2 py-1 text-[10px] font-semibold text-muted-foreground">
            {platformMeta.icon} {platformMeta.label}
          </span>
        </div>
        <span className={`inline-flex items-center gap-1 text-xs font-semibold ${isUrgent ? "text-primary" : "text-muted-foreground"}`}>
          <Clock className="h-3.5 w-3.5" />
          {trend.hoursLeft > 0 ? `${trend.hoursLeft}h left` : "Ending soon"}
        </span>
      </div>

      {/* Song info */}
      <div className="space-y-0.5">
        <h3 className="font-display text-2xl font-bold leading-tight tracking-tight text-foreground">
          {trend.song}
        </h3>
        <p className="text-sm text-muted-foreground">by {trend.artist}</p>
      </div>

      {/* Waveform velocity meter */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold uppercase tracking-wide text-muted-foreground">Velocity</span>
          <span className="font-bold text-primary">{trend.viralMultiplier}x normal</span>
        </div>
        <div className="flex items-end gap-[3px] h-8">
          {Array.from({ length: 20 }).map((_, i) => {
            const filled = i < Math.round((viralPct / 100) * 20);
            return (
              <div
                key={i}
                className={`flex-1 rounded-sm transition-all duration-300 ${
                  filled
                    ? "bg-gradient-to-t from-primary to-secondary"
                    : "bg-muted/40"
                }`}
                style={{ height: `${20 + Math.sin(i * 0.8) * 14}px` }}
              />
            );
          })}
        </div>
      </div>

      {/* Saturation indicator */}
      <div className="flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${satMeta.dot}`} />
        <span className={`text-xs font-semibold ${satMeta.color}`}>{satMeta.label}</span>
        {trend.optimalPostHourIst !== undefined && (
          <span className="ml-auto text-xs text-muted-foreground">
            Best: {trend.optimalPostHourIst}:00 IST
          </span>
        )}
      </div>

      {/* Chips */}
      <div className="flex flex-wrap gap-2">
        <Chip>{trend.contentTypeEmoji} {trend.contentType}</Chip>
        {trend.languageEmoji && trend.language && (
          <Chip>{trend.languageEmoji} {trend.language}</Chip>
        )}
        {trend.isDance && <Chip className="bg-secondary/15 text-secondary">FILM YOURSELF</Chip>}
        {trend.isNarrativeEdit && <Chip className="bg-narrative/15 text-narrative">NARRATIVE EDIT</Chip>}
        {trend.reelCount !== undefined && (
          <Chip className="bg-white/5 text-muted-foreground">{trend.reelCount} reels</Chip>
        )}
      </div>

      {/* Ideal content description */}
      <p className="rounded-xl bg-white/[0.03] px-3 py-2 text-sm italic text-muted-foreground border border-border">
        💡 {trend.idealContentDescription || "Great for reels and short-form content"}
      </p>

      {/* Why this works tooltip */}
      {trend.whyThisWorks && (
        <button
          onClick={() => setShowWhy(!showWhy)}
          className="flex w-full items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <Info className="h-3.5 w-3.5 shrink-0" />
          <span>{showWhy ? trend.whyThisWorks : "Why is this trending? ↓"}</span>
        </button>
      )}

      {/* Quick copy caption */}
      <button
        onClick={copyCaption}
        className="flex w-full items-center justify-between rounded-xl border border-border bg-white/[0.02] px-3 py-2 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground transition-all"
      >
        <span>📋 Quick copy caption + hashtags</span>
        {copied ? <CheckCheck className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
      </button>

      {/* Source reels collapsible */}
      <div className="border-t border-border pt-3">
        <button
          onClick={() => setShowReels(!showReels)}
          className="flex w-full items-center justify-between py-1 text-xs font-bold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <TrendingUp className="h-3.5 w-3.5" /> Source Reels
          </span>
          {showReels ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>

        {showReels && (
          <div className="mt-3 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
            {!reels ? (
              <div className="text-center py-4 text-xs text-muted-foreground">Loading reels...</div>
            ) : reels.length === 0 ? (
              <div className="text-center py-4 text-xs text-muted-foreground">No reels found yet.</div>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {reels.slice(0, 4).map((reel) => (
                  <div key={reel.id} className="flex flex-col gap-2 rounded-xl bg-white/[0.03] p-3 border border-border/50">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-primary">@{reel.owner_username}</span>
                      <span className="text-muted-foreground">{formatViews(reel.view_count)} views</span>
                    </div>
                    {reel.caption && (
                      <p className="text-xs text-muted-foreground line-clamp-2 italic">"{reel.caption}"</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="space-y-2 pt-1">
        <Button
          onClick={() => navigate({ to: "/generate", search: { trendId: trend.id } })}
          className="h-12 w-full bg-success font-bold uppercase tracking-wide text-success-foreground hover:bg-success/90 transition-all hover:scale-[1.01]"
        >
          <Video className="h-4 w-4" /> Generate My Reel
        </Button>
        {trend.isDance && (
          <Button
            onClick={() => onDanceTap(trend)}
            className="h-12 w-full bg-secondary font-bold uppercase tracking-wide text-secondary-foreground hover:bg-secondary/90"
          >
            💃 How To Film This
          </Button>
        )}
      </div>
    </article>
  );
}

function Chip({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-semibold text-foreground ${className}`}>
      {children}
    </span>
  );
}
