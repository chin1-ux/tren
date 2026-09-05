import { useNavigate } from "@tanstack/react-router";
import {
  Flame, Video, ChevronDown, ChevronUp,
  Copy, CheckCheck, Zap, TrendingUp,
  Bookmark, BookmarkCheck, HelpCircle,
  ExternalLink, Eye, Heart, MessageCircle, Share2, Music2
} from "lucide-react";
import type { UiTrend } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useState, useRef, useCallback, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchTrendReels, toggleTrendTarget, fetchTargetedTrends } from "@/lib/api";
import { FEATURES } from "@/lib/features";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { TrendCardVideo } from "./TrendCardVideo";
import { TrendPreviewModal } from "./TrendPreviewModal";
import { TrendProofSection } from "./TrendProofSection";

interface Props {
  trend: UiTrend;
  onDanceTap: (trend: UiTrend) => void;
  selectedNiche?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const LANG_EMOJIS: Record<string, string> = {
  en: "🇬🇧 English",
  hi: "🇮🇳 Hindi",
  kn: "🎯 Kannada",
  ta: "🌴 Tamil",
  te: "🌟 Telugu",
  bn: "🐯 Bengali",
  mr: "🦁 Marathi",
  pa: "🌾 Punjabi",
  ml: "🥥 Malayalam",
};

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

/** Trend classification badge for display differentiation */
function getTrendClassificationBadge(classification?: string): { label: string; color: string; bgColor: string; icon: string } {
  switch (classification) {
    case "viral_revival":
      return { label: "Viral Revival", color: "text-purple-300", bgColor: "bg-purple-500/15", icon: "🔄" };
    case "evergreen_popular":
      return { label: "Evergreen Popular", color: "text-emerald-300", bgColor: "bg-emerald-500/15", icon: "🌿" };
    case "classic_hit":
      return { label: "Classic Hit", color: "text-amber-300", bgColor: "bg-amber-500/15", icon: "🎵" };
    case "new_viral":
    default:
      return { label: "New Viral", color: "text-primary", bgColor: "bg-primary/15", icon: "🔥" };
  }
}

/** Velocity pattern indicator */
function getVelocityPatternIndicator(pattern?: string): { label: string; icon: string } {
  switch (pattern) {
    case "sudden_spike":
      return { label: "Sudden Spike", icon: "📈" };
    case "gradual_growth":
      return { label: "Gradual Growth", icon: "📊" };
    case "steady_popular":
      return { label: "Steady Popular", icon: "📉" };
    case "declining":
      return { label: "Declining", icon: "📉" };
    default:
      return { label: "Unknown", icon: "❓" };
  }
}

/** 2026-algo: optimal reel length in seconds by content type */
function getTargetedSaturationMeta(count: number): { label: string; color: string; bgColor: string } {
  if (count === 0) return { label: "0 targeting", color: "text-emerald-400 border-emerald-500/20", bgColor: "bg-emerald-500/10" };
  if (count <= 2) return { label: `${count} targeting`, color: "text-amber-400 border-amber-500/20", bgColor: "bg-amber-500/10" };
  return { label: `${count} targeting`, color: "text-primary border-primary/20", bgColor: "bg-primary/10" };
}

const formatViews = (v: number) => {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return v.toString();
};

function formatAudioUseCount(count: number): string {
  if (!count) return "—";
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${count.toLocaleString()}`;
  return count.toString();
}

/** Format a scraped-at ISO string into a human-readable "Aug 27, 06:21 AM" */
function formatScrapedAt(iso: string | null | undefined): string | null {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return null;
    return d.toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
      timeZone: "Asia/Kolkata",
    });
  } catch {
    return null;
  }
}

/** Saturation bar component (Global / India) */
function SaturationBar({
  label,
  pct,
  showOpportunity = false,
}: {
  label: string;
  pct: number;
  showOpportunity?: boolean;
}) {
  const barColor =
    pct < 30 ? "bg-emerald-500" :
    pct < 60 ? "bg-amber-500" :
    pct < 80 ? "bg-orange-500" :
    "bg-red-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px]">
        <span className="font-semibold text-muted-foreground">{label}</span>
        <div className="flex items-center gap-1.5">
          {showOpportunity && pct > 0 && pct < 30 && (
            <span className="inline-flex items-center gap-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-1.5 py-0.5 text-[9px] font-bold text-emerald-400">
              🇮🇳 Opportunity
            </span>
          )}
          <span className="font-bold text-foreground">{Math.round(pct)}%</span>
        </div>
      </div>
      <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${barColor}`}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, pct)}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

/** Trial Reel Advisor Badge */
function TrialReelBadge({
  globalPct,
  indiaPct,
  hoursLeft,
}: {
  globalPct: number;
  indiaPct: number;
  hoursLeft: number;
}) {
  if (globalPct > 75) {
    if (indiaPct < 20) {
      return (
        <span
          title="Saturated globally but India window barely open"
          className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2.5 py-0.5 text-[10px] font-bold text-amber-300 cursor-help"
        >
          🚀 Post now for India
        </span>
      );
    }
    return (
      <span
        title="Trend has peaked globally — use caution"
        className="inline-flex items-center gap-1 rounded-full bg-red-500/15 border border-red-500/30 px-2.5 py-0.5 text-[10px] font-bold text-red-400 cursor-help"
      >
        ⚠️ Saturated globally
      </span>
    );
  }
  if (globalPct >= 35 && indiaPct < 30) {
    return (
      <span
        title="Global peak but India window still open"
        className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-0.5 text-[10px] font-bold text-emerald-300 cursor-help"
      >
        🚀 Post now for India
      </span>
    );
  }
  if (globalPct < 35 && hoursLeft > 8) {
    return (
      <span
        title="Trend is early — test with non-followers before posting broadly"
        className="inline-flex items-center gap-1 rounded-full bg-blue-500/15 border border-blue-500/30 px-2.5 py-0.5 text-[10px] font-bold text-blue-300 cursor-help"
      >
        🧪 Try as Trial Reel first
      </span>
    );
  }
  return null;
}

/** Audio deep-link builder */
function buildAudioUrl(audioId?: string | null, audioName?: string): string {
  if (audioId) return `https://www.instagram.com/reels/audio/${audioId}/`;
  const q = encodeURIComponent(audioName || "");
  return `https://www.instagram.com/explore/search/keyword/?q=${q}`;
}

// ── Main Component ─────────────────────────────────────────────────────────────

export function TrendCard({ trend, onDanceTap, selectedNiche }: Props) {
  const navigate = useNavigate();
  const [isExpanded, setIsExpanded] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [showReels, setShowReels] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [targetLoading, setTargetLoading] = useState(false);
  const cardRef = useRef<HTMLElement>(null);
  const queryClient = useQueryClient();

  const { data: targetedTrends = [] } = useQuery({
    queryKey: ["trends-targeted"],
    queryFn: fetchTargetedTrends,
    staleTime: 10_000,
  });

  const isTargeted = targetedTrends.some((t: any) => String(t.id) === String(trend.id));

  // Saved trend tracking is hydrated after mount to avoid SSR/client text mismatch.
  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const arr = JSON.parse(localStorage.getItem("saved_trends") || "[]");
      setIsSaved(Array.isArray(arr) && arr.includes(String(trend.id)));
    } catch {
      setIsSaved(false);
    }
  }, [trend.id]);

  const handleTarget = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (targetLoading) return;
    setTargetLoading(true);
    const action = isTargeted ? "untarget" : "target";
    try {
      const res = await toggleTrendTarget(trend.id, action);
      if (res.success) {
        queryClient.invalidateQueries({ queryKey: ["trends-targeted"] });
        if (action === "target") {
          toast.success("Trend added to Workspace 🎯");
        } else {
          toast.success("Removed from Workspace");
        }
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to update target");
    } finally {
      setTargetLoading(false);
    }
  };

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
  const isMegaTrend = (trend.viralMultiplier ?? 0) >= 50;
  
  const platformMeta = getPlatformMeta(trend.bestPlatformFirst ?? "instagram");
  const creatorFit = trend.creatorFitScore ?? 0;
  const hookRetention = trend.hookRetentionScore ?? 0;
  const saturationPenalty = trend.saturationPenalty ?? 0;
  const velocityStrength = trend.viralMultiplier ?? 0;
  
  // Trend classification for display differentiation
  const trendBadge = getTrendClassificationBadge(trend.trendClassification);
  const velocityPattern = getVelocityPatternIndicator(trend.velocityPattern);

  // v2 saturation data
  const globalPct = trend.globalSaturationPct ?? 0;
  const indiaPct = trend.indiaSaturationPct ?? 0;
  const audioUseCount = trend.audioUseCount ?? 0;
  const hookBrief = trend.hookBrief ?? [];
  const primaryHook = hookBrief[0] ?? null;
  const nicheTag = trend.nicheTag ?? "general";
  const audioId = trend.audioId;
  const audioUrl = buildAudioUrl(audioId, trend.song);
  const saturationCount = trend.saturationCount ?? 0;
  const vibeTag = trend.vibeTag ?? "general";

  const allNiches = Array.from(new Set([
    ...(nicheTag && nicheTag !== "general" ? [nicheTag] : []),
    ...(trend.semanticNiches ?? [])
  ].filter(n => n && n !== "general")));

  let nichesToDisplay = [...allNiches];
  const matchedIndex = selectedNiche && selectedNiche !== "all"
    ? nichesToDisplay.findIndex(n => (n ?? "").toLowerCase() === (selectedNiche ?? "all").toLowerCase())
    : -1;

  if (matchedIndex > 0) {
    const [matchedNiche] = nichesToDisplay.splice(matchedIndex, 1);
    nichesToDisplay.unshift(matchedNiche);
  }

  const displayNiches = nichesToDisplay.slice(0, 2);
  const remainingCount = nichesToDisplay.length - displayNiches.length;

  const { data: reels } = useQuery({
    queryKey: ["trend-reels", trend.id],
    queryFn: () => fetchTrendReels(trend.id),
    enabled: showReels,
    staleTime: 5 * 60_000,
  });

  const hasCreatorBreakout = trend.hasCreatorOutlier || reels?.some((r) => r.is_creator_outlier) || false;

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
    const contentSlug = (trend.contentType || "viral").toLowerCase().replace(/\s+/g, "");
    const text = `${trend.idealContentDescription || trend.song} 🔥 #trending #reels #${contentSlug}`;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      toast.success("Caption copied! 📋");
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const getBorderClass = () => {
    // Glassmorphic styling: light themed glass in light mode, dark themed obsidian in dark mode
    const baseBg = "bg-surface/85 dark:bg-zinc-950/70 backdrop-blur-xl transition-all duration-300";
    const baseShadow = "shadow-[0_8px_30px_rgb(0,0,0,0.04)] dark:shadow-[0_12px_32px_rgba(0,0,0,0.4)]";

    if (trend.opportunityScore && trend.opportunityScore >= 80)
      return `${baseBg} ${baseShadow} border border-emerald-500/20 dark:border-emerald-500/20 hover:border-emerald-500/55`;
    if (trend.isDance || trend.category === "Dance")
      return `${baseBg} ${baseShadow} border border-amber-500/20 dark:border-amber-500/20 hover:border-amber-500/55`;
    if (trend.isNarrativeEdit || trend.category === "Narrative")
      return `${baseBg} ${baseShadow} border border-purple-500/20 dark:border-purple-500/20 hover:border-purple-500/55`;
    return `${baseBg} ${baseShadow} border border-border/80 dark:border-white/10 hover:border-violet-500/30 dark:hover:border-violet-500/30`;
  };

  const getOpportunityScoreBadgeColor = (score: number) => {
    if (score >= 80) return "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 shadow-[0_0_12px_rgba(16,185,129,0.1)]";
    if (score >= 60) return "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20 shadow-[0_0_12px_rgba(245,158,11,0.1)]";
    if (score >= 40) return "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20";
    return "bg-primary/10 text-primary dark:text-primary border-primary/20";
  };

  const getOpportunityScoreStatus = (score: number) => {
    if (score >= 80) return "Act now — window closing fast";
    if (score >= 60) return "Still time to jump in";
    if (score >= 40) return "Saturating — post today";
    return "Too late for this trend";
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
      className={`tilt-card relative rounded-2xl p-5 cursor-pointer overflow-hidden space-y-4 ${getBorderClass()} card-glow-light dark:card-glow-dark ${isEmerging ? "animate-pulse-urgent" : ""}`}
    >
      {/* Opportunity Score Indicator removed from absolute — now in badge row below as ml-auto item */}

      {/* ── 1. Top row: status and key badges ── */}
      <div className="flex flex-wrap items-center gap-1.5 pt-1">
        <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[9px] font-bold uppercase tracking-wide border ${
          trend.status === "emerging" ? "bg-amber-500/20 text-amber-400 border-amber-500/30" :
          trend.status === "peaked" ? "bg-blue-500/20 text-blue-400 border-blue-500/30" :
          trend.status === "expired" ? "bg-zinc-500/20 text-zinc-400 border-zinc-500/30" :
          "bg-primary/10 text-primary border-primary/20"
        }`}>
          {trend.status === "emerging" ? "⚡ Emerging" :
           trend.status === "peaked" ? "📉 Peaked" :
           trend.status === "expired" ? "⏰ Expired" :
           "📈 Rising"}
        </span>

        {isMegaTrend && (
          <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 text-[9px] font-bold">
            🔥 MEGA
          </span>
        )}
        {hasCreatorBreakout && (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 text-[9px] font-bold">
            🚀 BREAKOUT
          </span>
        )}
        {trend.isRegionalCrossover && (
          <span className="inline-flex items-center gap-1 rounded-full bg-orange-500/10 text-orange-400 border border-orange-500/20 px-2 py-0.5 text-[9px] font-bold">
            🌐 CROSSOVER
          </span>
        )}
        {trend.language && trend.language !== "en" && (
          <span className="inline-flex items-center gap-1 rounded-full bg-white/5 px-2 py-0.5 text-[9px] font-semibold text-muted-foreground">
            {LANG_EMOJIS[trend.language] || trend.language.toUpperCase()}
          </span>
        )}
        {trend.opportunityScore !== undefined && trend.opportunityScore > 0 && (
          <span className={`ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-extrabold border ${getOpportunityScoreBadgeColor(trend.opportunityScore)}`}>
            🟢 {Math.round(trend.opportunityScore)}
          </span>
        )}
      </div>

      {/* Video/Audio Identity Card replacing Image Thumbnail */}
      <div onClick={(e) => e.stopPropagation()} className="relative z-10">
        <TrendCardVideo
          reel={{
            id: String(trend.id),
            audio_title: trend.song,
            audio_artist: trend.artist,
            audio_use_count: audioUseCount,
            audio_id: trend.audioId,
          }}
          trendId={trend.id}
          opportunityScore={trend.opportunityScore}
        />
      </div>

      {/* ── 1. Song info ─────────────────────────────────────────────────── */}
      <div className="space-y-0.5 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <h3
            className="font-extrabold text-foreground tracking-tight text-base md:text-lg flex items-center gap-1.5 group hover:text-primary transition-colors truncate"
            title={trend.song}
          >
            <span className="truncate">{trend.song}</span>
          </h3>
          <button
            onClick={toggleSave}
            className="shrink-0 text-muted-foreground hover:text-primary transition-colors p-1"
            aria-label="Save trend"
          >
            {isSaved ? <BookmarkCheck className="h-5 w-5 text-primary" /> : <Bookmark className="h-5 w-5" />}
          </button>
        </div>
        <p className="text-xs text-muted-foreground mt-0.5 truncate">by {trend.artist}</p>
        
        {/* Saturation advice subtitle */}
        {trend.opportunityScore !== undefined && (
          <p className="text-[10px] text-muted-foreground/80 italic mt-0.5">
            {getOpportunityScoreStatus(trend.opportunityScore)}
          </p>
        )}
      </div>

      {/* ── 2. Audio use count ────────────────────────────────────────────── */}
      {audioUseCount > 0 && (
        <div className="flex items-center gap-2 rounded-xl bg-white/[0.03] border border-border/40 px-3 py-2 text-xs">
          <Music2 className="h-3.5 w-3.5 text-primary shrink-0" />
          <span className="text-muted-foreground">Reels using this audio:</span>
          <div className="flex items-center gap-1.5 ml-auto">
            {trend.viewsDelta !== undefined && trend.viewsDelta > 0 && (
              <span className="text-[10px] font-bold text-emerald-400 mr-1 bg-emerald-500/10 px-1.5 py-0.5 rounded">
                📈 +{formatViews(trend.viewsDelta)}
              </span>
            )}
            <span className="font-bold text-foreground">{formatAudioUseCount(audioUseCount)}</span>
          </div>
        </div>
      )}

      {/* ── 3. Chips row ─── */}
      <div className="flex flex-wrap gap-1.5 min-w-0">
        <Chip>{trend.contentTypeEmoji} {trend.contentType}</Chip>
        {trend.isRegionalCrossover && trend.crossoverFromLanguage && (
          <Chip className="bg-amber-500/20 text-amber-300 border border-amber-500/30 font-bold">
            🔀 {trend.crossoverFromLanguage} crossover
          </Chip>
        )}
        {trend.creatorFitScore !== undefined && trend.creatorFitScore >= 0.8 && (
          <Chip className="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-bold">
            🎯 Niche Match
          </Chip>
        )}
        {!trend.isClassificationVerified && (
          <Chip className="bg-amber-500/15 text-amber-300 border border-amber-500/20">
            ⏳ Classifying
          </Chip>
        )}
        {trend.isClassificationVerified && trend.languageEmoji && trend.language && (
          <Chip>{trend.languageEmoji} {trend.language}</Chip>
        )}
        {trend.isDance && <Chip className="bg-amber/15 text-amber border border-amber/20">💃 Dance</Chip>}
        {trend.isNarrativeEdit && <Chip className="bg-purple/15 text-purple border border-purple/20">🎞️ Narrative</Chip>}
        {displayNiches.map((n) => {
          const isMatched = selectedNiche && selectedNiche !== "all" && (n || "").toLowerCase() === selectedNiche.toLowerCase();
          return (
            <Chip
              key={n}
              className={
                isMatched
                  ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30 font-bold shadow-[0_0_8px_rgba(16,185,129,0.2)]"
                  : "bg-secondary/15 text-secondary border border-secondary/20"
              }
            >
              # {n}
            </Chip>
          );
        })}
        {remainingCount > 0 && (
          <Chip className="bg-white/5 text-muted-foreground cursor-help">
            +{remainingCount} more
          </Chip>
        )}
        {trend.reelCount != null && trend.reelCount > 0 && (
          <Chip className="bg-white/5 text-muted-foreground">{trend.reelCount.toLocaleString()} reels</Chip>
        )}
      </div>

      {/* ── 4. Velocity waveform ──────────────────────────────────────────── */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-semibold uppercase tracking-wide text-muted-foreground">Velocity</span>
          {velocityStrength > 0 ? (
            <span className="font-bold text-primary">
              {velocityStrength.toFixed(1)}x normal
              {(trend.reelCount ?? 0) < 5 && (
                <span className="ml-1 text-[9px] text-muted-foreground font-normal">(n={trend.reelCount})</span>
              )}
            </span>
          ) : (
            <span className="font-bold text-primary">Trend strength</span>
          )}
        </div>
        <div className="flex items-end gap-[3px] h-7">
          {Array.from({ length: 20 }).map((_, i) => {
            const filled = velocityStrength > 0 && i < Math.round((Math.min(100, (velocityStrength / 30) * 100) / 100) * 20);
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

      {/* Expand hint */}
      <div className="flex items-center justify-between text-[11px] text-muted-foreground/80 border-t border-border/50 pt-2">
        <span>Tap to {isExpanded ? "collapse" : "see strategy & actions"}</span>
        {(() => {
          const scraped = formatScrapedAt(trend.firstDetectedAt);
          return scraped ? (
            <span
              title={`First scraped: ${scraped} IST`}
              className="flex items-center gap-1 text-[9px] text-muted-foreground/50 font-mono tabular-nums"
            >
              <svg className="h-2.5 w-2.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              {scraped} IST
            </span>
          ) : null;
        })()}
        {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </div>

      {/* ── Expanded section ─────────────────────────────────────────────── */}
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

            {/* Crossover notification bar */}
            {trend.isRegionalCrossover && trend.crossoverMessage && (
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/[0.04] p-3 text-xs text-amber-300">
                ⚠️ <strong>Crossover Alert:</strong> {trend.crossoverMessage}
              </div>
            )}

            {/* ── Content Strategy ── */}
            <div className="rounded-xl border border-primary/20 bg-primary/[0.04] p-3 space-y-3">
              <p className="text-[10px] font-bold text-primary uppercase tracking-wider">Content Strategy</p>

              {/* Hook */}
              <div className="rounded-lg bg-white/[0.02] border border-border/40 px-3 py-2">
                <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground mb-1">🪝 Hook (first 3 seconds)</p>
                <p className="text-xs text-foreground/90 leading-relaxed">
                  {trend.llmClassificationStatus === "completed" 
                    ? (trend.whyThisWorks || "No hook advice available.") 
                    : "Not enough data yet for a tailored strategy."}
                </p>
              </div>

              {/* Trial reel badge row */}
              <div className="flex items-center gap-2 flex-wrap">
                <TrialReelBadge
                  globalPct={globalPct}
                  indiaPct={indiaPct}
                  hoursLeft={trend.hoursLeft}
                />
              </div>
            </div>

            {/* ── 5. Hook Brief section (Groq-extracted) ── */}
            {primaryHook && (
              <div className="rounded-xl border border-secondary/20 bg-secondary/[0.04] p-3 space-y-2">
                <p className="text-[10px] font-bold text-secondary uppercase tracking-wider">🎬 Hook Brief</p>
                {primaryHook.hook_brief_one_line && (
                  <p className="text-sm font-semibold text-foreground leading-snug italic">
                    "{primaryHook.hook_brief_one_line}"
                  </p>
                )}
                {primaryHook.dominant_hook_type && (
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-muted-foreground">Hook type:</span>
                    <span className="inline-flex rounded-full bg-secondary/15 border border-secondary/25 px-2 py-0.5 text-[10px] font-bold text-secondary capitalize">
                      {primaryHook.dominant_hook_type.replace(/_/g, " ")}
                    </span>
                  </div>
                )}
                {primaryHook.hook_opening_patterns && primaryHook.hook_opening_patterns.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Opening patterns creators use:</p>
                    <ul className="space-y-0.5">
                      {primaryHook.hook_opening_patterns.slice(0, 3).map((p, i) => (
                        <li key={i} className="flex items-start gap-1.5 text-[11px] text-foreground/80">
                           <span className="text-secondary mt-0.5 shrink-0">▸</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Content Concept */}
            <div className="rounded-xl border border-border/40 bg-white/[0.02] px-3 py-2">
              <p className="text-[10px] font-bold text-secondary uppercase tracking-wider">💡 Content Concept</p>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed italic">
                {trend.llmClassificationStatus === "completed" 
                  ? (trend.idealContentDescription || "No content concept available.") 
                  : "Not enough data yet for a tailored strategy."}
              </p>
            </div>

            {/* ── 6. Saturation dual clocks comparison ── */}
            <div className="rounded-xl border border-border/40 bg-white/[0.02] p-3 space-y-3">
              <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">📊 Saturation Clock</p>
              <div className="grid grid-cols-2 gap-4">
                <SaturationBar label="🌍 Global Saturation" pct={globalPct} />
                <SaturationBar label="🇮🇳 India Saturation" pct={indiaPct} showOpportunity={true} />
              </div>
            </div>

            {/* Creator scores */}
            <div className="space-y-2">
              {trend.optimalPostHourIst !== undefined && (
                <div className="flex items-center text-[11px] text-muted-foreground">
                  <span>Best post time: {trend.optimalPostHourIst}:00 IST</span>
                </div>
              )}
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

            {/* ── Trending Reels using this sound (audio deep-link replaces post link) ── */}
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
                      <div
                        key={reel.id}
                        className="flex flex-col gap-2 rounded-xl bg-white/[0.02] p-3 border border-border/40"
                      >
                        {/* Creator row — no link to profile */}
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
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
                          <div className="flex items-center gap-1.5 shrink-0">
                            {reel.is_creator_outlier && (
                              <span className="text-[9px] font-bold text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 rounded-full px-2 py-0.5">
                                🎯 Breakout
                              </span>
                            )}
                            <span className="text-[9px] font-semibold text-muted-foreground bg-white/5 rounded-full px-2 py-0.5">
                              ◎ Instagram
                            </span>
                          </div>
                        </div>

                        {/* Stats row */}
                        <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                          <span className="flex items-center gap-1"><Eye className="h-3 w-3" />{formatViews(reel.view_count)}</span>
                          <span className="flex items-center gap-1"><Heart className="h-3 w-3 text-primary" />{formatViews(reel.like_count)}</span>
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
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* ── 8. Save Audio deep-link button ── */}
            <a
              href={audioUrl}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary/40 bg-primary/10 px-3 py-2.5 text-xs font-bold text-primary hover:bg-primary/20 hover:border-primary/70 transition-all"
            >
              <Music2 className="h-3.5 w-3.5" />
              {audioId ? "Save Audio on Instagram →" : "Search Audio on Instagram →"}
              <ExternalLink className="h-3 w-3 opacity-60" />
            </a>

            {/* Action buttons */}
            <div className="space-y-2 pt-2 border-t border-border/40">
              {/* Target Trend — primary CTA to add to Workspace */}
              <Button
                onClick={handleTarget}
                disabled={targetLoading}
                className={`h-11 w-full font-bold uppercase tracking-wide transition-all hover:scale-[1.01] ${
                  isTargeted
                    ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                    : "bg-gradient-to-r from-primary to-[#ff006e] text-white hover:opacity-90"
                }`}
              >
                {targetLoading ? (
                  <span className="animate-spin mr-2">⏳</span>
                ) : isTargeted ? (
                  <>
                    <span className="mr-1.5">✅</span> In Workspace — Untarget
                  </>
                ) : (
                  <>
                    <span className="mr-1.5">🎯</span> Target Trend
                  </>
                )}
              </Button>

              {FEATURES.GENERATE_ENABLED && (
                <Button
                  onClick={(e) => { e.stopPropagation(); navigate({ to: "/generate", search: { trendId: trend.id } }); }}
                  className="h-11 w-full bg-primary font-bold uppercase tracking-wide text-white hover:bg-primary/90 transition-all hover:scale-[1.01]"
                >
                  <Video className="h-4 w-4" /> Generate My Reel
                </Button>
              )}

            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <TrendProofSection 
        trendId={trend.id} 
        isPeaking={!!(trend.peakingScore && trend.peakingScore >= 70)}
      />
      <TrendPreviewModal
        trend={trend}
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
      />
    </motion.article>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

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
                     "bg-primary/10 text-primary border-primary/20";
  return (
    <div className={`rounded-lg border px-2 py-2 text-center ${clz}`}>
      <p className="text-[9px] font-bold uppercase tracking-wide opacity-80">{label}</p>
      <p className="text-sm font-extrabold mt-0.5">{Math.round(value * 100)}</p>
    </div>
  );
}
