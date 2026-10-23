import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Sparkles,
  Flame,
  Bookmark,
  Layers,
  Play,
  Pause,
  RotateCcw,
  Compass,
  ArrowRight,
  Music,
  Check,
} from 'lucide-react';
import { type DeckTrend } from '@/lib/deck-ranking';
import { useAudioStore } from '@/store/useAudioStore';
import { resolveAudioTrack } from '@/lib/audio-resolver';

interface MilestoneRecapCardProps {
  batchCount: number;
  sessionSwipesCount: number;
  savedAudios: DeckTrend[];
  streakDays: number;
  freshnessMinutes: number;
  remainingCandidatesCount: number;
  onDealMore: () => void;
  onViewPicks: () => void;
  onGoToFeed: () => void;
  onReshufflePassed: () => void;
  onSelectTrend: (trend: DeckTrend) => void;
  isLoadingMore?: boolean;
}

export function MilestoneRecapCard({
  batchCount,
  sessionSwipesCount,
  savedAudios,
  streakDays,
  freshnessMinutes,
  remainingCandidatesCount,
  onDealMore,
  onViewPicks,
  onGoToFeed,
  onReshufflePassed,
  onSelectTrend,
  isLoadingMore = false,
}: MilestoneRecapCardProps) {
  const { currentTrack, isPlaying, playTrack, togglePlay } = useAudioStore();
  const [resolvingId, setResolvingId] = useState<number | null>(null);

  const handlePlayAudio = async (e: React.MouseEvent, trend: DeckTrend) => {
    e.stopPropagation();
    const isThisPlaying = Boolean(
      isPlaying && currentTrack && String(currentTrack.id) === String(trend.id)
    );
    if (isThisPlaying) {
      togglePlay();
      return;
    }

    setResolvingId(trend.id);
    try {
      const resolved = await resolveAudioTrack({
        id: trend.id,
        audio_id: trend.audio_id || undefined,
        audio_title: trend.audio_title,
        audio_artist: trend.audio_artist,
        reel_count: trend.reel_count,
        trend_status: trend.status,
      });
      if (resolved) {
        playTrack(resolved);
      }
    } catch (err) {
      console.warn('Playback resolution failed:', err);
    } finally {
      setResolvingId(null);
    }
  };

  const recentSaves = savedAudios.slice(0, 3);
  const nextDealCount = Math.min(15, remainingCandidatesCount);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.94, y: 16 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="w-full max-w-[420px] rounded-[32px] p-5 sm:p-6 text-foreground relative overflow-hidden flex flex-col gap-4 sm:gap-5 shadow-2xl border"
      style={{
        background: 'linear-gradient(180deg, rgba(24, 24, 27, 0.98) 0%, rgba(10, 10, 12, 1) 100%)',
        borderColor: 'rgba(255, 77, 61, 0.2)',
        boxShadow: '0 20px 48px -10px rgba(0, 0, 0, 0.6), 0 0 32px rgba(255, 77, 61, 0.1)',
      }}
    >
      {/* Top Ambient Glow */}
      <div
        className="absolute -top-24 left-1/2 -translate-x-1/2 w-72 h-40 pointer-events-none rounded-full blur-3xl"
        style={{
          background: 'radial-gradient(ellipse at center, rgba(255,77,61,0.25) 0%, transparent 70%)',
        }}
      />

      {/* Header Section */}
      <div className="relative z-10 flex flex-col items-center text-center">
        <div
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold tracking-wide uppercase mb-2.5"
          style={{
            background: 'rgba(255, 77, 61, 0.12)',
            color: '#FF4D3D',
            border: '1px solid rgba(255, 77, 61, 0.3)',
          }}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>Batch {batchCount} Conquered 🎉</span>
        </div>

        <h3
          className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight"
          style={{ fontFamily: "'Bricolage Grotesque', system-ui, sans-serif" }}
        >
          15 Audios Reviewed!
        </h3>
        <p className="text-xs text-zinc-400 mt-1 max-w-[280px]">
          Taste engine updated · Fresh catalog updated {freshnessMinutes}m ago.
        </p>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-3 gap-2 relative z-10">
        <div
          className="p-3 rounded-2xl flex flex-col items-center justify-center text-center border transition-all"
          style={{
            background: 'rgba(255, 255, 255, 0.03)',
            borderColor: 'rgba(255, 255, 255, 0.08)',
          }}
        >
          <Layers className="w-4 h-4 text-zinc-400 mb-1" />
          <span className="text-lg font-bold text-white font-mono leading-none">
            {sessionSwipesCount}
          </span>
          <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider mt-1">
            Swiped
          </span>
        </div>

        <div
          className="p-3 rounded-2xl flex flex-col items-center justify-center text-center border transition-all"
          style={{
            background: 'rgba(255, 77, 61, 0.06)',
            borderColor: 'rgba(255, 77, 61, 0.25)',
          }}
        >
          <Bookmark className="w-4 h-4 text-[#FF4D3D] mb-1" />
          <span className="text-lg font-bold text-[#FF4D3D] font-mono leading-none">
            {savedAudios.length}
          </span>
          <span className="text-[10px] text-[#FF4D3D]/80 font-medium uppercase tracking-wider mt-1">
            Saved Picks
          </span>
        </div>

        <div
          className="p-3 rounded-2xl flex flex-col items-center justify-center text-center border transition-all"
          style={{
            background: 'rgba(255, 255, 255, 0.03)',
            borderColor: 'rgba(255, 255, 255, 0.08)',
          }}
        >
          <Flame className="w-4 h-4 text-amber-400 mb-1" />
          <span className="text-lg font-bold text-amber-400 font-mono leading-none">
            {streakDays}d
          </span>
          <span className="text-[10px] text-zinc-400 font-medium uppercase tracking-wider mt-1">
            Day Streak
          </span>
        </div>
      </div>

      {/* Recent Picks Mini-Showcase */}
      <div className="relative z-10 flex flex-col gap-2">
        <div className="flex items-center justify-between px-0.5">
          <span className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
            <Music className="w-3.5 h-3.5 text-[#FF4D3D]" />
            Session Saves ({savedAudios.length})
          </span>
          {savedAudios.length > 0 && (
            <button
              onClick={onViewPicks}
              className="text-[11px] font-medium text-[#FF4D3D] hover:underline flex items-center gap-0.5 transition-colors"
            >
              Open Picks <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>

        {savedAudios.length > 0 ? (
          <div className="flex flex-col gap-1.5">
            {recentSaves.map((trend) => {
              const isThisPlaying = Boolean(
                isPlaying && currentTrack && String(currentTrack.id) === String(trend.id)
              );
              return (
                <div
                  key={trend.id}
                  onClick={() => onSelectTrend(trend)}
                  className="flex items-center justify-between p-2.5 rounded-xl border transition-all cursor-pointer group"
                  style={{
                    background: 'rgba(255, 255, 255, 0.03)',
                    borderColor: 'rgba(255, 255, 255, 0.06)',
                  }}
                >
                  <div className="flex items-center gap-2.5 min-w-0 pr-2">
                    <button
                      onClick={(e) => handlePlayAudio(e, trend)}
                      disabled={resolvingId === trend.id}
                      className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-transform active:scale-90"
                      style={{
                        background: isThisPlaying ? '#FF4D3D' : 'rgba(255, 77, 61, 0.15)',
                        color: isThisPlaying ? '#fff' : '#FF4D3D',
                      }}
                      title={isThisPlaying ? 'Pause audio' : 'Play preview'}
                    >
                      {resolvingId === trend.id ? (
                        <div className="w-3 h-3 border-2 border-[#FF4D3D] border-t-transparent rounded-full animate-spin" />
                      ) : isThisPlaying ? (
                        <Pause className="w-3.5 h-3.5 fill-current" />
                      ) : (
                        <Play className="w-3.5 h-3.5 ml-0.5 fill-current" />
                      )}
                    </button>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-white truncate group-hover:text-[#FF4D3D] transition-colors">
                        {trend.audio_title}
                      </p>
                      <p className="text-[10px] text-zinc-400 truncate">
                        {trend.audio_artist || 'Original Audio'}
                      </p>
                    </div>
                  </div>

                  {trend.niche && (
                    <span
                      className="shrink-0 text-[10px] px-2 py-0.5 rounded-md font-medium capitalize"
                      style={{
                        background: 'rgba(255, 255, 255, 0.06)',
                        color: '#A1A1AA',
                      }}
                    >
                      {trend.niche}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div
            className="p-3 rounded-xl border text-center"
            style={{
              background: 'rgba(255, 255, 255, 0.02)',
              borderColor: 'rgba(255, 255, 255, 0.06)',
            }}
          >
            <p className="text-[11px] text-zinc-400">
              No audios saved this batch. Your pass signals helped narrow down what sounds hit.
            </p>
          </div>
        )}
      </div>

      {/* Action Center */}
      <div className="relative z-10 flex flex-col gap-2 pt-1">
        {/* Primary Action Button */}
        <button
          onClick={onDealMore}
          disabled={isLoadingMore}
          className="w-full py-3.5 px-6 rounded-2xl text-white font-bold text-sm tracking-wide shadow-xl transition-all active:scale-95 flex items-center justify-center gap-2 group relative overflow-hidden"
          style={{
            background: 'linear-gradient(135deg, #FF4D3D 0%, #FF2E63 100%)',
            boxShadow: '0 8px 24px rgba(255, 77, 61, 0.35)',
          }}
        >
          {isLoadingMore ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Dealing Next Batch...</span>
            </>
          ) : remainingCandidatesCount > 0 ? (
            <>
              <Sparkles className="w-4 h-4 transition-transform group-hover:rotate-12" />
              <span>Deal {nextDealCount} More Audios</span>
              <span className="text-[11px] font-normal opacity-85 ml-1 bg-white/20 px-2 py-0.5 rounded-full">
                {remainingCandidatesCount} left
              </span>
            </>
          ) : (
            <>
              <RotateCcw className="w-4 h-4 transition-transform group-hover:-rotate-45" />
              <span>Re-deal Fresh Catalog</span>
            </>
          )}
        </button>

        {/* Secondary Row */}
        <div className="grid grid-cols-2 gap-2">
          {savedAudios.length > 0 ? (
            <button
              onClick={onViewPicks}
              className="py-2.5 px-3 rounded-xl text-xs font-semibold transition-all border flex items-center justify-center gap-1.5 active:scale-95"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                borderColor: 'rgba(255, 255, 255, 0.12)',
                color: '#fff',
              }}
            >
              <Bookmark className="w-3.5 h-3.5 text-[#FF4D3D]" />
              <span>Picks ({savedAudios.length})</span>
            </button>
          ) : (
            <button
              onClick={onReshufflePassed}
              className="py-2.5 px-3 rounded-xl text-xs font-semibold transition-all border flex items-center justify-center gap-1.5 active:scale-95"
              style={{
                background: 'rgba(255, 255, 255, 0.06)',
                borderColor: 'rgba(255, 255, 255, 0.12)',
                color: '#fff',
              }}
            >
              <RotateCcw className="w-3.5 h-3.5 text-zinc-300" />
              <span>Re-deal Skips</span>
            </button>
          )}

          <button
            onClick={onGoToFeed}
            className="py-2.5 px-3 rounded-xl text-xs font-semibold transition-all border flex items-center justify-center gap-1.5 active:scale-95"
            style={{
              background: 'rgba(255, 255, 255, 0.06)',
              borderColor: 'rgba(255, 255, 255, 0.12)',
              color: '#fff',
            }}
          >
            <Compass className="w-3.5 h-3.5 text-zinc-300" />
            <span>Browse Feed</span>
          </button>
        </div>

        {/* Reshuffle option if user has saves */}
        {savedAudios.length > 0 && (
          <button
            onClick={onReshufflePassed}
            className="text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors py-1 flex items-center justify-center gap-1"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Re-shuffle passed tracks without losing your saved picks</span>
          </button>
        )}
      </div>
    </motion.div>
  );
}
