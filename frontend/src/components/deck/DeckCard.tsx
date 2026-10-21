import React, { useState } from 'react';
import { motion, useMotionValue, useTransform, PanInfo } from 'framer-motion';
import { Info, Play, Sparkles, Check, X, RotateCcw } from 'lucide-react';
import { type DeckTrend } from '@/lib/deck-ranking';
import { getTitleGradient, formatAge, formatCount } from '@/lib/deck-tokens';

interface DeckCardProps {
  trend: DeckTrend;
  isFront: boolean;
  stackIndex: number;
  onSwipe: (action: 'use' | 'skip') => void;
  onOpenInfo: () => void;
  onOpenWatch: () => void;
  isDark?: boolean;
}

export function DeckCard({
  trend,
  isFront,
  stackIndex,
  onSwipe,
  onOpenInfo,
  onOpenWatch,
  isDark = true,
}: DeckCardProps) {
  const [exitDirection, setExitDirection] = useState<'left' | 'right' | null>(null);

  const x = useMotionValue(0);
  // Rotation up to +-12 degrees
  const rotate = useTransform(x, [-200, 200], [-12, 12]);
  // USE IT stamp opacity fades in when dragging right
  const useStampOpacity = useTransform(x, [20, 100], [0, 1]);
  // SKIP stamp opacity fades in when dragging left
  const skipStampOpacity = useTransform(x, [-20, -100], [0, 1]);

  const { background, accentColor } = getTitleGradient(trend.audio_title, isDark);

  const handleDragEnd = (_: any, info: PanInfo) => {
    const threshold = 120;
    const velocityThreshold = 500;

    if (info.offset.x > threshold || info.velocity.x > velocityThreshold) {
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate(10);
      }
      setExitDirection('right');
      onSwipe('use');
    } else if (info.offset.x < -threshold || info.velocity.x < -velocityThreshold) {
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        navigator.vibrate(10);
      }
      setExitDirection('left');
      onSwipe('skip');
    }
  };

  // Stack scale and vertical offset: next card scales 0.94 -> 1 and rises
  const scale = stackIndex === 0 ? 1 : stackIndex === 1 ? 0.94 : 0.88;
  const translateY = stackIndex === 0 ? 0 : stackIndex === 1 ? 16 : 28;

  const creators = trend.creator_count || 1;
  const proofLine = `${formatCount(creators)} creators · caught ${formatAge(trend.age_hours)}`;

  // Stage pill mapping: emerging -> "Just starting", rising -> "Blowing up"
  const stagePill = trend.stage_label || (trend.status === 'rising' ? 'Blowing up' : 'Just starting');

  // Stage-specific pulsating outline and glow
  const stageGlowClass = (() => {
    const s = (trend.status || '').toLowerCase();
    if (s === 'rising') {
      return 'border-2 border-rose-500 shadow-[0_0_35px_rgba(244,63,94,0.45)] ring-1 ring-rose-400/60 animate-pulse';
    }
    if (s === 'emerging') {
      return 'border-2 border-cyan-400 shadow-[0_0_30px_rgba(34,211,238,0.4)] ring-1 ring-cyan-300/60 animate-pulse';
    }
    if (s === 'peaked') {
      return 'border-2 border-amber-400 shadow-[0_0_30px_rgba(251,191,36,0.4)] ring-1 ring-amber-300/60';
    }
    if (s === 'resurging') {
      return 'border-2 border-purple-500 shadow-[0_0_35px_rgba(168,85,247,0.45)] ring-1 ring-purple-400/60 animate-pulse';
    }
    return 'border border-white/20 shadow-2xl';
  })();

  const stageBadgeStyle = (() => {
    const s = (trend.status || '').toLowerCase();
    if (s === 'rising') return 'bg-rose-500/25 text-rose-300 border-rose-500/40';
    if (s === 'emerging') return 'bg-cyan-500/25 text-cyan-300 border-cyan-500/40';
    if (s === 'peaked') return 'bg-amber-500/25 text-amber-300 border-amber-500/40';
    if (s === 'resurging') return 'bg-purple-500/25 text-purple-300 border-purple-500/40';
    return 'bg-white/10 text-white/90 border-white/15';
  })();

  return (
    <motion.div
      style={{
        zIndex: 10 - stackIndex,
        scale,
        y: translateY,
        transformOrigin: 'top center',
      }}
      animate={{
        scale,
        y: translateY,
        opacity: stackIndex > 2 ? 0 : 1,
      }}
      transition={{
        type: 'spring',
        stiffness: 350,
        damping: 25,
      }}
      className="absolute inset-0 select-none touch-none"
    >
      <motion.div
        style={{
          x: isFront ? x : 0,
          rotate: isFront ? rotate : 0,
          background,
        }}
        drag={isFront ? 'x' : false}
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.7}
        onDragEnd={handleDragEnd}
        onClick={() => {
          if (isFront) onOpenWatch();
        }}
        className={`w-full h-full rounded-[28px] ${stageGlowClass} flex flex-col justify-between p-6 overflow-hidden relative cursor-grab active:cursor-grabbing backdrop-blur-xl ${
          isDark ? 'text-white' : 'text-zinc-900'
        }`}
      >
        {/* Drag Feedback Stamps */}
        {isFront && (
          <>
            <motion.div
              style={{ opacity: useStampOpacity }}
              className="absolute top-8 left-8 border-3 border-emerald-400 text-emerald-400 font-extrabold text-xl px-4 py-1.5 rounded-xl rotate-[-12deg] tracking-wider pointer-events-none z-30 uppercase bg-emerald-950/40 backdrop-blur-xs"
            >
              USE IT
            </motion.div>
            <motion.div
              style={{ opacity: skipStampOpacity }}
              className="absolute top-8 right-8 border-3 border-rose-500 text-rose-500 font-extrabold text-xl px-4 py-1.5 rounded-xl rotate-[12deg] tracking-wider pointer-events-none z-30 uppercase bg-rose-950/40 backdrop-blur-xs"
            >
              SKIP
            </motion.div>
          </>
        )}

        {/* Top Badges Row */}
        <div className="flex items-center justify-between z-20" onClick={(e) => e.stopPropagation()}>
          <div className="flex flex-wrap items-center gap-2">
            {trend.is_top_5 && (
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-amber-400/20 text-amber-300 border border-amber-400/30 text-xs font-bold font-mono tracking-wide">
                <Sparkles className="w-3 h-3 text-amber-300" />
                Top 5
              </span>
            )}
            {trend.is_new_today && (
              <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] font-bold font-mono">
                New today
              </span>
            )}
            <span className={`px-2.5 py-1 rounded-full border text-[11px] font-semibold tracking-wide backdrop-blur-xs ${stageBadgeStyle}`}>
              {stagePill}
            </span>
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onOpenInfo();
            }}
            className="w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 active:scale-95 flex items-center justify-center text-white/80 hover:text-white transition-all backdrop-blur-xs"
            aria-label="Audio Details"
          >
            <Info className="w-4 h-4" />
          </button>
        </div>

        {/* Center Content: Title, Artist, Proof Line */}
        <div className="space-y-3.5 my-2 z-20">
          <div className="space-y-1.5">
            <h2
              className="text-2xl sm:text-3xl font-extrabold leading-[1.2] tracking-tight font-display line-clamp-2"
              style={{ color: isDark ? '#FFFFFF' : '#111827' }}
            >
              {trend.audio_title}
            </h2>
            <p className="text-sm sm:text-base text-white/70 font-medium truncate">
              {trend.audio_artist}
            </p>
          </div>

          {/* Hard Fact Proof Line */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-black/35 border border-white/10 backdrop-blur-md">
            <span className="text-xs font-mono font-medium text-white/85">
              {proofLine}
            </span>
          </div>
        </div>

        {/* Creator Use-Case Section ("What kind of reels this audio is being used for") - Only rendered when real data exists */}
        {trend.used_for && (
          <div className="rounded-2xl bg-black/40 border border-white/10 p-3.5 backdrop-blur-md space-y-1.5 z-20" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-1.5 text-[10px] sm:text-[11px] font-mono font-bold tracking-wider uppercase text-amber-300/90">
              <Sparkles className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span>What kind of reels this audio is being used for</span>
            </div>
            <p className="text-xs text-white/85 leading-relaxed font-normal line-clamp-3">
              {trend.used_for}
            </p>
          </div>
        )}

        {/* Bottom Tags and Tap-to-Watch CTA */}
        <div className="space-y-3 z-20">
          <div className="flex flex-wrap items-center gap-2">
            {trend.language && (
              <span className="px-2.5 py-1 rounded-lg bg-white/10 text-white/90 text-xs font-mono font-medium uppercase">
                {trend.language}
              </span>
            )}
            {trend.niche && trend.niche.toLowerCase() !== 'other' && (
              <span className="px-2.5 py-1 rounded-lg bg-white/10 text-white/90 text-xs font-medium">
                {trend.niche}
              </span>
            )}
          </div>

          <div className="flex items-center justify-between text-xs text-white/50 pt-2 border-t border-white/10">
            <span className="flex items-center gap-1.5 text-white/70">
              <Play className="w-3.5 h-3.5" /> Tap card to preview reel
            </span>
            <span className="font-mono text-[11px] text-white/40">
              Swipe left / right
            </span>
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
