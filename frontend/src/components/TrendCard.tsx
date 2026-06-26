import { useNavigate } from "@tanstack/react-router";
import {
  Clock, Flame, Video, ChevronDown, ChevronUp,
  Copy, CheckCheck, Zap, TrendingUp,
  Bookmark, BookmarkCheck, Sparkles, Film, HelpCircle,
  ExternalLink, Eye, Heart, MessageCircle, Share2
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

// ── Helpers ──────────────────────────────────────────────────────────────────

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

/** 2026-algo: optimal reel length in seconds by content type */
function getOptimalLength(category: string): string {
  const c = category.toLowerCase();
  if (c === "dance") return "15–20s";
  if (c === "scenic" || c === "travel") return "20–25s";
  if (c === "fitness" || c === "motivation") return "30–45s";
  if (c === "food" || c === "fashion") return "15–30s";
  if (c === "narrative" || c === "study") return "45–60s";
  if (c === "faceless") return "20–30s";
  return "20–30s";
}

/** 2026-algo: save-bait tip by content type */
function getSaveBaitTip(category: string): string {
  const c = category.toLowerCase();
  if (c === "travel") return "Add '3 must-pack items for this trip' as text overlay";
  if (c === "fitness") return "Show the exact rep/set breakdown in text on-screen";
  if (c === "food") return "List the 2–3 key ingredients as a text overlay";
  if (c === "fashion") return "Tag where to buy each item — saves triple when links are visible";
  if (c === "motivation") return "Use a numbered list (e.g. '5 habits') to trigger saves";
  if (c === "study") return "Share a framework or template viewers can screenshot";
  if (c === "dance") return "Add a 'step breakdown' comment to get saves from learners";
  return "Include a numbered tip or stat viewers want to refer back to";
}

/** Estimated DM-shareability score 0–10 based on trend signals */
function getDMShareScore(trend: UiTrend): number {
  const base = (trend.hookRetentionScore ?? 0) * 5
    + (trend.creatorFitScore ?? 0) * 3
    + Math.min(3, (trend.viralMultiplier / 10));
  return Math.min(10, Math.round(base * 10) / 10);
}

const formatViews = (v: number) => {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return v.toString();
};

// ── Main Component ────────────────────────────────────────────────────────────

export function TrendCard({ trend, onDanceTap }: Props) {
  const navigate = useNavigate();
  const [isExpanded, setIsExpanded] = useState(false);
  const [showReels, setShowReels] = useState(false);
  const [copied, setCopied] = useState(false);
  const cardRef = useRef<HTMLElement>(null);

  // Saved trend tracking
  const [isSaved, setIsSaved] = useState(() => {
    if (typeof window === "undefined") return false;
    try {
      const arr = JSON.parse(localStorage.getItem("saved_trends") || "[]");
      return Array.isArray(arr) && arr.includes(String(trend.id));
    } catch { return false; }
  });

  const toggleSave = (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      let arr: string[] = JSON.parse(localStorage.getItem("saved_trends") || "[]");
      if (!Array.isArray(arr)) arr = [];
      if (isSaved) {
        arr = arr.filter((id) => id !== String(trend.id));
        toast.success("Trend removed from saved collection");
      } else {
        arr.push(String(trend.id));
        toast.success("Trend saved! 🔖");
      }
      localStorage.setItem("saved_trends", JSON.stringify(arr));
      setIsSaved(!isSaved);
    } catch { /* ignore */ }
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
  const dmShareScore = getDMShareScore(trend);
  const optimalLength = getOptimalLength(trend.category);
  const saveBaitTip = getSaveBaitTip(trend.category);
  const trialReco = compositeScore < 2.5
    ? { label: "Use Trial Reel first", color: "text-amber-400", bg: "bg-amber-400/10 border-amber-400/20" }
    : compositeScore > 4
    ? { label: "Post directly ✓", color: "text-emerald-400", bg: "bg-emerald-400/10 border-emerald-400/20" }
    : { label: "Trial Reel recommended", color: "text-blue-400", bg: "bg-blue-400/10 border-blue-400/20" };

  const { data: reels } = useQuery({
    queryKey: ["trend-reels", trend.id],
    queryFn: () => fetchTrendReels(trend.id),
    enabled: showReels,
    staleTime: 5 * 60_000,
  });

  // 3D tilt
  const onMouseMove = useCallback((e: React.MouseEvent<HTMLElement>) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const rotX = (((e.clientY - rect.top) / rect.height) - 0.5) * -6;
    const rotY = (((e.clientX - rect.left) / rect.width) - 0.5) * 6;
    cardRef.current.style.transform = `perspective(800px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateZ(4px)`;
  }, []);

  const onMouseLeave = useCallback(() => {
    if (!cardRef.current) return;
    cardRef.current.style.transform = "perspective(800px) rotateX(0deg) rotateY(0deg) translateZ(0)";
  }, []);

  const copyCaption = (e: React.MouseEvent) => {
    e.stopPropagation();
    const text = `${trend.idealContentDescription || trend.song} 🔥 #trending #reels #${trend.contentType?.toLowerCase().replace(/\s+/g, "")}`;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      toast.success("Caption copied! 📋");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const getBorderClass = () => {
    if (trend.isDance || trend.category === "Dance")
      return "border border-amber/40 shadow-[0_0_12px_rgba(239,159,39,0.08)] bg-gradient-to-b from-[rgba(239,159,39,0.05)] to-transparent hover:border-amber/80";
    if (trend.isNarrativeEdit || trend.category === "Narrative")
      return "border border-purple/40 shadow-[0_0_12px_rgba(127,119,221,0.08)] bg-gradient-to-b from-[rgba(127,119,221,0.05)] to-transparent hover:border-purple/80";
    if (trend.category?.toLowerCase() === "faceless")
      return "border border-teal/40 shadow-[0_0_12px_rgba(29,158,117,0.08)] bg-gradient-to-b from-[rgba(29,158,117,0.05)] to-transparent hover:border-teal/80";
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
      whileHover={{ y: -4, boxShadow: "0 15px 40px rgba(0,0,0,0.4)" }}
      className={`tilt-card relative rounded-2xl p-5 cursor-pointer overflow-hidden space-y-4 ${getBorderClass()} ${isEmerging ? "animate-pulse-urgent" : ""}`}
    >
      {/* Badges */}
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

      {/* Top row */}
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
      <div className="space-y-0.5 min-w-0">
        <h3
          className="font-display text-xl font-bold leading-snug tracking-tight text-foreground flex items-center justify-between gap-2"
          title={trend.song}
        >
          <span className="line-clamp-1 min-w-0 flex-1">{trend.song}</span>
          <button
            onClick={toggleSave}
            className="shrink-0 text-muted-foreground hover:text-primary transition-colors p-1"
            aria-label="Save trend"
          >
            {isSaved ? <BookmarkCheck className="h-5 w-5 text-primary" /> : <Bookmark className="h-5 w-5" />}
          </button>
        </h3>
        <p className="text-xs text-muted-foreground truncate">by {trend.artist}</p>
      </div>

      {/* Velocity waveform */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold uppercase tracking-wide text-muted-foreground">Velocity</span>
          <span className="font-bold text-primary">{trend.viralMultiplier}x normal</span>
        </div>
        <div className="flex items-end gap-[3px] h-7">
          {Array.from({ length: 20 }).map((_, i) => {
            const filled = i < Math.round((viralPct / 100) * 20);
            const h = 15 + Math.sin(i * 0.8) * 10;
            return (
              <motion.div
                key={i}
                initial={{ height: 0 }}
                animate={{ height: `${h}px` }}
                transition={{ type: "spring", stiffness: 80, damping: 10, delay: i * 0.02 }}
                className={`flex-1 rounded-sm ${filled ? "bg-gradient-to-t from-primary to-secondary" : "bg-muted/30"}`}
              />
            );
          })}
        </div>
      </div>

      {/* Chips */}
      <div className="flex flex-wrap gap-1.5 min-w-0">
        <Chip>{trend.contentTypeEmoji} {trend.contentType}</Chip>
        {trend.languageEmoji && trend.language && (
          <Chip>{trend.languageEmoji} {trend.language}</Chip>
        )}
        {trend.isDance && <Chip className="bg-amber/15 text-amber border border-amber/20">💃 Dance</Chip>}
        {trend.isNarrativeEdit && <Chip className="bg-purple/15 text-purple border border-purple/20">🎞️ Narrative</Chip>}
        {trend.reelCount !== undefined && (
          <Chip className="bg-white/5 text-muted-foreground">{trend.reelCount.toLocaleString()} reels</Chip>
        )}
      </div>

      {/* Expand hint */}
      <div className="flex items-center justify-between text-[11px] text-muted-foreground/80 border-t border-border/50 pt-2">
        <span>Tap to {isExpanded ? "collapse" : "see strategy & actions"}</span>
        {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </div>

      {/* Expanded section */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="space-y-4 pt-2 overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >

            {/* ── 2026 Algorithm Insight ── */}
            <div className="rounded-xl border border-primary/20 bg-primary/[0.04] p-3 space-y-3">
              <p className="text-[10px] font-bold text-primary uppercase tracking-wider">⚡ 2026 Algorithm Insights</p>

              {/* Row 1: DM Share + Optimal Length */}
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-lg bg-white/[0.03] border border-border/40 p-2 text-center">
                  <Share2 className="h-3.5 w-3.5 text-[#ff006e] mx-auto mb-1" />
                  <p className="text-[9px] font-bold uppercase tracking-wide text-muted-foreground">DM Share Score</p>
                  <p className="text-base font-extrabold text-[#ff006e]">{dmShareScore}<span className="text-[10px] text-muted-foreground">/10</span></p>
                  <p className="text-[8px] text-muted-foreground/70 mt-0.5">1 DM = 15× likes in reach</p>
                </div>
                <div className="rounded-lg bg-white/[0.03] border border-border/40 p-2 text-center">
                  <Film className="h-3.5 w-3.5 text-secondary mx-auto mb-1" />
                  <p className="text-[9px] font-bold uppercase tracking-wide text-muted-foreground">Optimal Length</p>
                  <p className="text-base font-extrabold text-secondary">{optimalLength}</p>
                  <p className="text-[8px] text-muted-foreground/70 mt-0.5">for {trend.category} content</p>
                </div>
              </div>

              {/* Hook */}
              <div className="rounded-lg bg-white/[0.02] border border-border/40 px-3 py-2">
                <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground mb-1">🪝 Hook (first 3 seconds)</p>
                <p className="text-xs text-foreground/90 leading-relaxed">
                  {trend.whyThisWorks || `Open with the beat drop — grab attention in second 1 before viewers scroll away.`}
                </p>
              </div>

              {/* Save-bait */}
              <div className="rounded-lg bg-white/[0.02] border border-border/40 px-3 py-2">
                <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground mb-1">💾 Save-Bait (1 save = 10× likes)</p>
                <p className="text-xs text-foreground/80 leading-relaxed">{saveBaitTip}</p>
              </div>

              {/* Trial reel decision */}
              <div className={`rounded-lg border px-3 py-2 ${trialReco.bg}`}>
                <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">🎯 Posting Strategy</p>
                <p className={`text-xs font-bold ${trialReco.color}`}>{trialReco.label}</p>
              </div>
            </div>

            {/* Content Concept */}
            <div className="rounded-xl border border-border/40 bg-white/[0.02] px-3 py-2">
              <p className="text-[10px] font-bold text-secondary uppercase tracking-wider">💡 Content Concept</p>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed italic">
                {trend.idealContentDescription || "Sync high-impact transitions with the main beats of this song for maximum reach."}
              </p>
            </div>

            {/* Saturation + scores */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className={`h-1.5 w-1.5 rounded-full shrink-0 ${satMeta.dot}`} />
                <span className={`text-[11px] font-semibold ${satMeta.color}`}>{satMeta.label}</span>
                {trend.optimalPostHourIst !== undefined && (
                  <span className="ml-auto text-[11px] text-muted-foreground shrink-0">
                    Best post: {trend.optimalPostHourIst}:00 IST
                  </span>
                )}
              </div>
              <div className="grid grid-cols-3 gap-2">
                <ScorePill label="Fit" value={creatorFit} tone={creatorFit >= 0.7 ? "good" : creatorFit >= 0.5 ? "mid" : "bad"} />
                <ScorePill label="Hook" value={hookRetention} tone={hookRetention >= 0.7 ? "good" : hookRetention >= 0.5 ? "mid" : "bad"} />
                <ScorePill label="Space" value={1 - saturationPenalty} tone={(1 - saturationPenalty) >= 0.7 ? "good" : (1 - saturationPenalty) >= 0.5 ? "mid" : "bad"} />
              </div>
            </div>

            {/* Copy caption */}
            <button
              onClick={copyCaption}
              className="flex w-full items-center justify-between rounded-xl border border-border bg-white/[0.02] px-3 py-2 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground transition-all"
            >
              <span>📋 Copy caption + hashtags</span>
              {copied ? <CheckCheck className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
            </button>

            {/* ── Trending Reels using this sound ── */}
            <div className="border-t border-border/40 pt-3">
              <button
                onClick={(e) => { e.stopPropagation(); setShowReels(!showReels); }}
                className="flex w-full items-center justify-between py-1 text-[10px] font-bold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <Eye className="h-3.5 w-3.5" /> Trending Reels using this sound
                </span>
                {showReels ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {showReels && (
                <div className="mt-3 space-y-2">
                  {!reels ? (
                    <div className="text-center py-4 text-xs text-muted-foreground">Loading reels…</div>
                  ) : reels.length === 0 ? (
                    <div className="text-center py-4 text-xs text-muted-foreground">No reels indexed yet — check back soon!</div>
                  ) : (
                    reels.slice(0, 3).map((reel) => (
                      <a
                        key={reel.id}
                        href={`https://instagram.com/reel/${reel.reel_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex flex-col gap-2 rounded-xl bg-white/[0.02] p-3 border border-border/40 hover:bg-white/[0.05] hover:border-primary/30 transition-all text-left group"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {/* Creator row */}
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            {/* Avatar */}
                            <div className="h-7 w-7 rounded-full bg-gradient-to-br from-primary/60 to-secondary/60 flex items-center justify-center shrink-0 text-[10px] font-bold text-white">
                              {(reel.owner_username?.[0] ?? "?").toUpperCase()}
                            </div>
                            <div className="min-w-0">
                              <p className="text-[11px] font-bold text-foreground truncate">@{reel.owner_username}</p>
                              {reel.owner_follower_count && (
                                <p className="text-[9px] text-muted-foreground">{formatViews(reel.owner_follower_count)} followers</p>
                              )}
                            </div>
                          </div>
                          {/* Instagram badge */}
                          <span className="shrink-0 text-[9px] font-semibold text-muted-foreground bg-white/5 rounded-full px-2 py-0.5">
                            ◎ Instagram
                          </span>
                        </div>

                        {/* Stats row */}
                        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                          <span className="flex items-center gap-1"><Eye className="h-3 w-3" />{formatViews(reel.view_count)}</span>
                          <span className="flex items-center gap-1"><Heart className="h-3 w-3 text-rose-400" />{formatViews(reel.like_count)}</span>
                          {reel.comment_count > 0 && (
                            <span className="flex items-center gap-1"><MessageCircle className="h-3 w-3 text-blue-400" />{formatViews(reel.comment_count)}</span>
                          )}
                        </div>

                        {/* Caption snippet */}
                        {reel.caption && (
                          <p className="text-[11px] text-muted-foreground line-clamp-2 italic leading-relaxed">
                            "{reel.caption.slice(0, 120)}{reel.caption.length > 120 ? "…" : ""}"
                          </p>
                        )}

                        {/* View link */}
                        <div className="flex items-center gap-1 text-[10px] font-semibold text-primary group-hover:underline">
                          <ExternalLink className="h-3 w-3" /> View on Instagram
                        </div>
                      </a>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Action buttons */}
            <div className="space-y-2 pt-2 border-t border-border/40">
              <Button
                onClick={(e) => { e.stopPropagation(); navigate({ to: "/generate", search: { trendId: trend.id } }); }}
                className="h-11 w-full bg-primary font-bold uppercase tracking-wide text-white hover:bg-primary/90 transition-all hover:scale-[1.01]"
              >
                <Video className="h-4 w-4" /> Generate My Reel
              </Button>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  onClick={(e) => { e.stopPropagation(); navigate({ to: "/generate", search: { trendId: trend.id } }); }}
                  className="h-11 bg-teal font-bold uppercase tracking-wide text-white hover:bg-teal/90"
                >
                  <Sparkles className="h-3.5 w-3.5" /> Faceless
                </Button>

                {trend.isDance || trend.category === "Dance" ? (
                  <Button
                    onClick={(e) => { e.stopPropagation(); onDanceTap(trend); }}
                    className="h-11 bg-amber font-bold uppercase tracking-wide text-white hover:bg-amber/90"
                  >
                    <Film className="h-3.5 w-3.5" /> How To Film
                  </Button>
                ) : (
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      toast.info("Filming guide", { description: trend.idealContentDescription || "Film transitions and align with the beats." });
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

// ── Sub-components ────────────────────────────────────────────────────────────

function Chip({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full bg-white/[0.04] border border-border/50 px-2.5 py-0.5 text-[10px] font-semibold text-foreground/90 ${className}`}>
      {children}
    </span>
  );
}

function ScorePill({ label, value, tone }: { label: string; value: number; tone: "good" | "mid" | "bad" }) {
  const clz =
    tone === "good" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
    tone === "mid"  ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                     "bg-rose-500/10 text-rose-400 border-rose-500/20";
  return (
    <div className={`rounded-lg border px-2 py-2 text-center ${clz}`}>
      <p className="text-[9px] font-bold uppercase tracking-wide opacity-80">{label}</p>
      <p className="text-sm font-extrabold mt-0.5">{Math.round(value * 100)}</p>
    </div>
  );
}
