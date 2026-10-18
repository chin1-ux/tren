import React from 'react';
import { ExternalLink, X, Calendar, Layers, Music, Hash, Globe } from 'lucide-react';
import { type DeckTrend } from '@/lib/deck-ranking';
import { formatCount } from '@/lib/deck-tokens';

interface DeckInfoSheetProps {
  trend: DeckTrend | null;
  isOpen: boolean;
  onClose: () => void;
}

export function DeckInfoSheet({ trend, isOpen, onClose }: DeckInfoSheetProps) {
  if (!isOpen || !trend) return null;

  const reelCount = trend.reel_count || 1;
  const reelLabel = reelCount === 1 ? '1 reel tracked' : `${formatCount(reelCount)} reels tracked`;
  const useCountFormatted = trend.audio_use_count > 0
    ? `${formatCount(trend.audio_use_count)} uses on Instagram`
    : 'New breakout audio';

  const caughtDateFormatted = trend.first_detected_at
    ? new Date(trend.first_detected_at).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      })
    : 'Recently';

  const instagramUrl = `https://www.instagram.com/reels/audio/${trend.id}/`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-xs p-0 sm:p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-t-3xl sm:rounded-3xl p-6 text-zinc-100 shadow-2xl space-y-5 animate-in slide-in-from-bottom duration-250"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <span className="text-[11px] font-mono tracking-wider uppercase text-zinc-400 block mb-1">
              Audio Intel
            </span>
            <h3 className="text-xl font-bold text-white truncate font-display">
              {trend.audio_title}
            </h3>
            <p className="text-sm text-zinc-400 truncate">
              {trend.audio_artist}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 -mr-2 -mt-2 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
            aria-label="Close sheet"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Fact Sheet Grid */}
        <div className="grid grid-cols-2 gap-3 pt-1">
          <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-2xl p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-zinc-400 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-zinc-400" />
              Volume
            </span>
            <p className="text-sm font-semibold text-zinc-200">
              {useCountFormatted}
            </p>
          </div>

          <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-2xl p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-zinc-400 flex items-center gap-1.5">
              <Music className="w-3.5 h-3.5 text-zinc-400" />
              Tracked Reels
            </span>
            <p className="text-sm font-semibold text-zinc-200">
              {reelLabel}
            </p>
          </div>

          <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-2xl p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-zinc-400 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-zinc-400" />
              First caught
            </span>
            <p className="text-sm font-semibold text-zinc-200">
              {caughtDateFormatted}
            </p>
          </div>

          <div className="bg-zinc-950/60 border border-zinc-800/80 rounded-2xl p-3.5 space-y-1">
            <span className="text-[11px] font-mono text-zinc-400 flex items-center gap-1.5">
              <Globe className="w-3.5 h-3.5 text-zinc-400" />
              Language & Niche
            </span>
            <p className="text-sm font-semibold text-zinc-200 truncate">
              {trend.language.toUpperCase() || 'Global'}
              {trend.niche ? ` · ${trend.niche}` : ''}
            </p>
          </div>
        </div>

        {/* The ONLY outbound link per B2 */}
        <div className="pt-2">
          <a
            href={instagramUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-white text-sm font-medium transition-colors"
          >
            <span>Open on Instagram</span>
            <ExternalLink className="w-4 h-4" />
          </a>
        </div>
      </div>
    </div>
  );
}
