import { useNavigate } from "@tanstack/react-router";
import {
  Clock, Flame, Video, ChevronDown, ChevronUp,
  Copy, CheckCheck, Info, Zap, TrendingUp,
  Bookmark, BookmarkCheck, Sparkles, Film, HelpCircle
} from "lucide-react";
import type { UiTrend } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTrendReels } from "@/lib/api";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

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
  const [isExpanded, setIsExpanded] = useState(false);
  const [showReels, setShowReels] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showWhy, setShowWhy] = useState(false);
  const cardRef = useRef<HTMLElement>(null);

  // Local storage "Save Trend" tracking
  const [isSaved, setIsSaved] = useState(() => {
    if (typeof window === "undefined") return false;
    const saved = localStorage.getItem("saved_trends");
    if (!saved) return false;
    try {
      const arr = JSON.parse(saved);
      return Array.isArray(arr) && arr.includes(String(trend.id));
    } catch {
      return false;
    }
  });

  const toggleSave = (e: React.MouseEvent) => {
    e.stopPropagation();
    const saved = localStorage.getItem("saved_trends");
    let arr: string[] = [];
    if (saved) {
      try {
        arr = JSON.parse(saved);
        if (!Array.isArray(arr)) arr = [];
      } catch {}
    }
    if (isSaved) {
      arr = arr.filter((id) => id !== String(trend.id));
      toast.success("Trend removed from saved collection");
    } else {
      arr.push(String(trend.id));
      toast.success("Trend saved successfully!");
    }
    localStorage.setItem("saved_trends", JSON.stringify(arr));
    setIsSaved(!isSaved);
  };

  const isEmerging = trend.isEmerging || trend.status === "emerging";
  const isUrgent = trend.hoursLeft <= 6;
  const isMegaTrend = (trend.viralMultiplier ?? 0) >= 12 || (trend.reelCount ?? 0) > 10000;

  const satMeta = getSaturationMeta(trend.saturationScore ?? 0);
  const platformMeta = getPlatformMeta(trend.bestPlatformFirst ?? "instagram");
  const viralPct = Math.min(100, (trend.viralMultiplier / 30) * 100);
  const creatorFit = trend.creatorFitScore ?? 0;
  const hookRetention = trend.hookRetentionScore ?? 0;
  const saturationPenalty = trend.saturationPenalty ?? 0;
  const compositeScore = trend.compositeScore ?? 0;

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
    const rotX = ((y - cy) / cy) * -4;
    const rotY = ((x - cx) / cx) * 4;
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

  const copyCaption = (e: React.MouseEvent) => {
    e.stopPropagation();
    const text = `${trend.idealContentDescription || trend.song} 🔥 #trending #reels #${trend.contentType?.toLowerCase().replace(/\s+/g, "")}`;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      toast.success("Caption copied to clipboard!");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  // Determine border color class
  const getBorderAndBgClass = () => {
    const isDanceCat = trend.isDance || trend.category === "Dance";
    const isNarrativeCat = trend.isNarrativeEdit || trend.category === "Narrative";
    const isFacelessCat = trend.category === "Faceless" || trend.contentType === "Faceless";

    if (isDanceCat) {
      return "border border-amber/40 shadow-[0_0_12px_rgba(239,159,39,0.08)] bg-gradient-to-b from-[rgba(239,159,39,0.05)] to-transparent hover:border-amber/80";
    }
    if (isNarrativeCat) {
      return "border border-purple/40 shadow-[0_0_12px_rgba(127,119,221,0.08)] bg-gradient-to-b from-[rgba(127,119,221,0.05)] to-transparent hover:border-purple/80";
    }
    if (isFacelessCat) {
      return "border border-teal/40 shadow-[0_0_12px_rgba(29,158,117,0.08)] bg-gradient-to-b from-[rgba(29,158,117,0.05)] to-transparent hover:border-teal/80";
    }
    // Regular = red border
    return "border border-primary/40 shadow-[0_0_12px_rgba(230,57,70,0.08)] bg-gradient-to-b from-[rgba(230,57,70,0.05)] to-transparent hover:border-primary/80";
  };

  return (
    <motion.article
      ref={cardRef as any}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      onClick={() => setIsExpanded(!isExpanded)}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      whileHover={{ y: -5, boxShadow: "0 15px 40px rgba(0, 0, 0, 0.4)" }}
      className={`tilt-card relative space-y-4 rounded-2xl p-5 cursor-pointer overflow-hidden ${getBorderAndBgClass()} ${
        isEmerging ? "animate-pulse-urgent" : ""
      }`}
    >
      {/* Emerging & Mega badges */}
      <div className="absolute -top-1 left-4 flex gap-2">
        {isEmerging && (
          <span className="inline-flex items-center gap-1 rounded-b-lg bg-[#ff006e] px-2.5 py-1 text-[9px] font-bold uppercase tracking-widest text-white shadow-md">
            <Zap className="h-2.5 w-2.5" /> EMERGING
          </span>
        )}
        {isMegaTrend && (
          <span className="inline-flex items-center gap-1 rounded-b-lg bg-gradient-to-r from-purple to-pink-500 px-2.5 py-1 text-[9px] font-bold uppercase tracking-widest text-white shadow-md">
            <Flame className="h-2.5 w-2.5 animate-bounce" /> MEGA TREND
          </span>
        )}
      </div>

      {/* Top row: status + timer */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-primary">
            <TrendingUp className="h-3 w-3" /> Trending
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-white/5 px-2 py-0.5 text-[9px] font-semibold text-muted-foreground">
            {platformMeta.icon} {platformMeta.label}
          </span>
        </div>
        <span className={`inline-flex items-center gap-1 text-xs font-semibold ${isUrgent ? "text-primary animate-pulse" : "text-muted-foreground"}`}>
          <Clock className="h-3.5 w-3.5" />
          {trend.hoursLeft > 0 ? `${trend.hoursLeft}h left` : "Ending soon"}
        </span>
      </div>

      {/* Song info */}
      <div className="space-y-0.5">
        <h3 className="font-display text-xl font-bold leading-snug tracking-tight text-foreground transition-colors flex items-center justify-between gap-1.5">
          <span className="truncate">{trend.song}</span>
          <button
            onClick={toggleSave}
            className="text-muted-foreground hover:text-primary transition-colors p-1"
            aria-label="Save trend"
          >
            {isSaved ? <BookmarkCheck className="h-5 w-5 text-primary" /> : <Bookmark className="h-5 w-5" />}
          </button>
        </h3>
        <p className="text-xs text-muted-foreground">by {trend.artist}</p>
      </div>

      {/* Waveform velocity meter */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold uppercase tracking-wide text-muted-foreground">Velocity</span>
          <span className="font-bold text-primary">{trend.viralMultiplier}x normal</span>
        </div>
        <div className="flex items-end gap-[3px] h-7">
          {Array.from({ length: 20 }).map((_, i) => {
            const filled = i < Math.round((viralPct / 100) * 20);
            const targetHeight = 15 + Math.sin(i * 0.8) * 10;
            return (
              <motion.div
                key={i}
                initial={{ height: 0 }}
                animate={{ height: `${targetHeight}px` }}
                transition={{
                  type: "spring",
                  stiffness: 80,
                  damping: 10,
                  delay: i * 0.02
                }}
                className={`flex-1 rounded-sm ${
                  filled
                    ? "bg-gradient-to-t from-primary to-secondary"
                    : "bg-muted/30"
                }`}
              />
            );
          })}
        </div>
      </div>

      {/* Chips */}
      <div className="flex flex-wrap gap-1.5">
        <Chip>{trend.contentTypeEmoji} {trend.contentType}</Chip>
        {trend.languageEmoji && trend.language && (
          <Chip>{trend.languageEmoji} {trend.language}</Chip>
        )}
        {trend.isDance && <Chip className="bg-amber/15 text-amber border border-amber/20">💃 Dance</Chip>}
        {trend.isNarrativeEdit && <Chip className="bg-purple/15 text-purple border border-purple/20">🎞️ Narrative</Chip>}
        {trend.reelCount !== undefined && (
          <Chip className="bg-white/5 text-muted-foreground">{trend.reelCount} reels</Chip>
        )}
      </div>

      {/* Tap to expand hint */}
      <div className="flex items-center justify-between text-[11px] text-muted-foreground/80 border-t border-border/50 pt-2">
        <span>Click to {isExpanded ? "collapse" : "expand strategy & actions"}</span>
        {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </div>

      {/* Expanded strategy details & actions */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="space-y-4 pt-2 overflow-hidden"
            onClick={(e) => e.stopPropagation()} // Prevent collapse when interacting with controls
          >
            {/* Hook Preview */}
            <div className="rounded-xl border border-border/40 bg-white/[0.02] px-3 py-2">
              <p className="text-[10px] font-bold text-primary uppercase tracking-wider">🪝 Hook Preview</p>
              <p className="text-xs text-foreground/90 mt-1 leading-relaxed">
                {trend.whyThisWorks ? trend.whyThisWorks : `Introduce this concept in the first 2 seconds to retain viewers while the beat drops.`}
              </p>
            </div>

            {/* Content Description */}
            <div className="rounded-xl border border-border/40 bg-white/[0.02] px-3 py-2">
              <p className="text-[10px] font-bold text-secondary uppercase tracking-wider">💡 Content Concept</p>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed italic">
                {trend.idealContentDescription || "Sync high-impact transitions with the main beats of this song for maximum reach."}
              </p>
            </div>

            {/* Saturation indicator */}
            <div className="flex items-center gap-2">
              <div className={`h-1.5 w-1.5 rounded-full ${satMeta.dot}`} />
              <span className={`text-[11px] font-semibold ${satMeta.color}`}>{satMeta.label}</span>
              {trend.optimalPostHourIst !== undefined && (
                <span className="ml-auto text-[11px] text-muted-foreground">
                  Best post time: {trend.optimalPostHourIst}:00 IST
                </span>
              )}
            </div>

            {/* Score indicators */}
            <div className="grid grid-cols-3 gap-1.5 text-[9px]">
              <ScorePill label="Fit" value={creatorFit} tone={creatorFit >= 0.7 ? "good" : creatorFit >= 0.5 ? "mid" : "bad"} />
              <ScorePill label="Hook" value={hookRetention} tone={hookRetention >= 0.7 ? "good" : hookRetention >= 0.5 ? "mid" : "bad"} />
              <ScorePill label="Crowd" value={1 - saturationPenalty} tone={(1 - saturationPenalty) >= 0.7 ? "good" : (1 - saturationPenalty) >= 0.5 ? "mid" : "bad"} />
            </div>

            {/* Quick copy caption */}
            <button
              onClick={copyCaption}
              className="flex w-full items-center justify-between rounded-xl border border-border bg-white/[0.02] px-3 py-2 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground transition-all"
            >
              <span>📋 Copy caption + hashtags</span>
              {copied ? <CheckCheck className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
            </button>

            {/* Source reels collapsible */}
            <div className="border-t border-border/40 pt-3">
              <button
                onClick={(e) => { e.stopPropagation(); setShowReels(!showReels); }}
                className="flex w-full items-center justify-between py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <TrendingUp className="h-3.5 w-3.5" /> Reference Reels
                </span>
                {showReels ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {showReels && (
                <div className="mt-3 space-y-3">
                  {!reels ? (
                    <div className="text-center py-4 text-xs text-muted-foreground">Loading reels...</div>
                  ) : reels.length === 0 ? (
                    <div className="text-center py-4 text-xs text-muted-foreground">No reels found yet.</div>
                  ) : (
                    <div className="grid grid-cols-1 gap-2">
                      {reels.slice(0, 3).map((reel) => (
                        <a
                          key={reel.id}
                          href={`https://instagram.com/reel/${reel.reel_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex flex-col gap-1 rounded-xl bg-white/[0.02] p-2.5 border border-border/40 hover:bg-white/[0.05] transition-colors text-left"
                        >
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-bold text-primary">@{reel.owner_username}</span>
                            <span className="text-muted-foreground">{formatViews(reel.view_count)} views</span>
                          </div>
                          {reel.caption && (
                            <p className="text-[11px] text-muted-foreground line-clamp-1 italic">"{reel.caption}"</p>
                          )}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Action buttons */}
            <div className="space-y-2 pt-2 border-t border-border/40">
              <Button
                onClick={(e) => {
                  e.stopPropagation();
                  navigate({ to: "/generate", search: { trendId: trend.id } });
                }}
                className="h-11 w-full bg-primary font-bold uppercase tracking-wide text-white hover:bg-primary/90 transition-all hover:scale-[1.01]"
              >
                <Video className="h-4 w-4" /> Generate My Reel
              </Button>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    toast.success("Faceless video creation started!", {
                      description: `Using templates matching "${trend.song}"...`
                    });
                    navigate({ to: "/generate", search: { trendId: trend.id } });
                  }}
                  className="h-11 bg-teal font-bold uppercase tracking-wide text-white hover:bg-teal/90"
                >
                  <Sparkles className="h-3.5 w-3.5" /> Generate Faceless
                </Button>

                {trend.isDance || trend.category === "Dance" ? (
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDanceTap(trend);
                    }}
                    className="h-11 bg-amber font-bold uppercase tracking-wide text-white hover:bg-amber/90"
                  >
                    <Film className="h-3.5 w-3.5" /> How To Film This
                  </Button>
                ) : (
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      toast.info("Filming guide", {
                        description: trend.idealContentDescription || "Film transitions and align them with the beats."
                      });
                    }}
                    variant="outline"
                    className="h-11 border-border text-xs font-bold uppercase tracking-wide hover:bg-white/5"
                  >
                    <HelpCircle className="h-3.5 w-3.5" /> How To Film
                  </Button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.article>
  );
}

function Chip({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full bg-white/[0.04] border border-border/50 px-2.5 py-0.5 text-[10px] font-semibold text-foreground/90 ${className}`}>
      {children}
    </span>
  );
}

function ScorePill({ label, value, tone }: { label: string; value: number; tone: "good" | "mid" | "bad" }) {
  const clz = tone === "good" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : tone === "mid" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" : "bg-rose-500/10 text-rose-400 border-rose-500/20";
  return (
    <div className={`rounded-lg border px-2 py-1 text-center ${clz}`}>
      <div className="flex items-center justify-between gap-1">
        <span className="font-semibold uppercase tracking-wide">{label}</span>
        <span className="font-bold">{Math.round(value * 100)}</span>
      </div>
    </div>
  );
}
