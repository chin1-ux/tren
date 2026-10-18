import React, { useEffect, useState } from 'react';
import { X, ExternalLink, ChevronLeft, ChevronRight, Play } from 'lucide-react';
import { type DeckTrend } from '@/lib/deck-ranking';
import { supabase } from '@/lib/supabase';

interface DeckWatchSheetProps {
  trend: DeckTrend | null;
  isOpen: boolean;
  onClose: () => void;
}

interface TrackedReel {
  reel_id: string;
  owner_username?: string;
  view_count?: number;
}

export function DeckWatchSheet({ trend, isOpen, onClose }: DeckWatchSheetProps) {
  const [reels, setReels] = useState<TrackedReel[]>([]);
  const [loading, setLoading] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (!isOpen || !trend) {
      setReels([]);
      setCurrentIndex(0);
      return;
    }

    setLoading(true);
    supabase
      .from('reels')
      .select('reel_id, owner_username, view_count')
      .eq('audio_id', String(trend.audio_id || trend.id))
      .order('view_count', { ascending: false })
      .limit(5)
      .then(({ data, error }) => {
        if (!error && data && data.length > 0) {
          setReels(data as TrackedReel[]);
        } else {
          setReels([]);
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [isOpen, trend]);

  if (!isOpen || !trend) return null;

  const currentReel = reels[currentIndex];
  const totalReels = reels.length;

  const instagramAudioUrl = trend.audio_id
    ? `https://www.instagram.com/reels/audio/${trend.audio_id}/`
    : `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(trend.audio_title + ' ' + trend.audio_artist)}`;
  const instagramReelUrl = currentReel?.reel_id
    ? `https://www.instagram.com/reel/${currentReel.reel_id}/`
    : instagramAudioUrl;

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-black/95 text-white animate-in fade-in duration-200">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
        <div className="min-w-0 pr-3">
          <p className="text-sm font-bold truncate font-display">{trend.audio_title}</p>
          <p className="text-xs text-zinc-400 truncate">{trend.audio_artist}</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <a
            href={instagramReelUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-white transition-colors"
          >
            <span>Open on Instagram</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
          <button
            onClick={onClose}
            className="p-2 rounded-full text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
            aria-label="Close watch sheet"
          >
            <X className="w-6 h-6" />
          </button>
        </div>
      </div>

      {/* Main Embed Content */}
      <div className="flex-1 flex flex-col items-center justify-center p-2 sm:p-4 overflow-hidden relative">
        {loading ? (
          <div className="w-full max-w-sm aspect-[9/16] bg-zinc-900 rounded-2xl animate-pulse flex flex-col items-center justify-center text-zinc-500 gap-3 border border-zinc-800">
            <Play className="w-10 h-10 opacity-30" />
            <span className="text-xs font-mono">Loading reel embed...</span>
          </div>
        ) : currentReel ? (
          <div className="w-full max-w-sm h-full max-h-[720px] rounded-2xl overflow-hidden shadow-2xl bg-black border border-zinc-800 relative">
            {/* The single iframe is mounted here and destroyed when watch sheet closes */}
            <iframe
              key={currentReel.reel_id}
              src={`https://www.instagram.com/reel/${currentReel.reel_id}/embed/`}
              className="w-full h-full border-0"
              allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
              title={`Instagram Reel ${currentReel.reel_id}`}
            />
          </div>
        ) : (
          <div className="w-full max-w-sm aspect-[9/16] bg-zinc-900/60 rounded-2xl border border-zinc-800 flex flex-col items-center justify-center p-6 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400">
              <Play className="w-8 h-8 opacity-50 ml-1" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-zinc-200">Watch on Instagram</h4>
              <p className="text-xs text-zinc-400 max-w-[240px]">
                Direct audio feed contains active reels created with this sound.
              </p>
            </div>
            <a
              href={instagramAudioUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#FF3B5C] hover:bg-[#E02A4A] text-white text-xs font-semibold shadow-lg transition-colors"
            >
              <span>Explore Audio on Instagram</span>
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        )}
      </div>

      {/* Pager bar when more than one reel */}
      {totalReels > 1 && (
        <div className="flex items-center justify-between px-6 py-3 border-t border-zinc-800/80 bg-zinc-950/80">
          <button
            onClick={() => setCurrentIndex((prev) => Math.max(0, prev - 1))}
            disabled={currentIndex === 0}
            className="flex items-center gap-1 text-xs text-zinc-400 disabled:opacity-30 hover:text-white transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Prev reel
          </button>
          <span className="text-xs font-mono text-zinc-400">
            {currentIndex + 1} / {totalReels}
          </span>
          <button
            onClick={() => setCurrentIndex((prev) => Math.min(totalReels - 1, prev + 1))}
            disabled={currentIndex === totalReels - 1}
            className="flex items-center gap-1 text-xs text-zinc-400 disabled:opacity-30 hover:text-white transition-colors"
          >
            Next reel
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
