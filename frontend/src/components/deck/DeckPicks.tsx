import React from 'react';
import { ExternalLink, Trash2, Flame, RotateCcw, Music, Sparkles, Play, Pause } from 'lucide-react';
import { type DeckTrend, type UserSwipe } from '@/lib/deck-ranking';
import { formatCount } from '@/lib/deck-tokens';
import { useAudioStore } from '@/store/useAudioStore';
import { resolveAudioTrack } from '@/lib/audio-resolver';

interface DeckPicksProps {
  savedAudios: DeckTrend[];
  swipes: UserSwipe[];
  onRemove: (trendId: number) => void;
  onResetTaste: () => void;
  streakDays: number;
  onSelectTrend?: (trend: DeckTrend) => void;
}

export function DeckPicks({
  savedAudios,
  swipes,
  onRemove,
  onResetTaste,
  streakDays,
  onSelectTrend,
}: DeckPicksProps) {
  const { currentTrack, isPlaying, playTrack, togglePlay } = useAudioStore();

  // Compute top niches and languages from user's 'use' swipes
  const useSwipes = swipes.filter((s) => s.action === 'use');

  const nicheCounts: Record<string, number> = {};
  const langCounts: Record<string, number> = {};

  useSwipes.forEach((s) => {
    if (s.niche && s.niche.toLowerCase() !== 'other') {
      nicheCounts[s.niche] = (nicheCounts[s.niche] || 0) + 1;
    }
    if (s.language) {
      langCounts[s.language.toUpperCase()] = (langCounts[s.language.toUpperCase()] || 0) + 1;
    }
  });

  const topNiches = Object.entries(nicheCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([n]) => n);

  const topLangs = Object.entries(langCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([l]) => l);

  const handlePlayAudio = async (e: React.MouseEvent, t: DeckTrend) => {
    e.stopPropagation();
    const isThisPlaying = Boolean(isPlaying && currentTrack && String(currentTrack.id) === String(t.id));
    if (isThisPlaying) {
      togglePlay();
      return;
    }
    try {
      const resolved = await resolveAudioTrack({
        id: t.id,
        song: t.audio_title,
        artist: t.audio_artist,
        audioId: t.audio_id,
      });
      if (!resolved.previewUrl) {
        if (t.audio_id) {
          window.open(`https://www.instagram.com/reels/audio/${t.audio_id}/`, '_blank');
        }
        return;
      }
      playTrack({
        id: t.id,
        title: resolved.title,
        artist: resolved.artist,
        coverUrl: resolved.coverUrl || undefined,
        instagramAudioId: t.audio_id || undefined,
        viralStartSec: resolved.viralStartSec,
        viralDurationSec: resolved.viralDurationSec,
        previewUrl: resolved.previewUrl,
        sourceType: resolved.sourceType,
      });
    } catch (err) {
      console.warn("Failed to play pick audio:", err);
    }
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto px-4 py-4 space-y-5 max-w-lg mx-auto w-full pb-24">
      {/* Top Header & Streak */}
      <div className="flex items-center justify-between pt-1">
        <div>
          <h2 className="text-xl font-extrabold text-[#0E0E10]" style={{ fontFamily: "'Bricolage Grotesque', system-ui" }}>
            Your Saved Picks
          </h2>
          <p className="text-xs text-[#6B6B78] mt-0.5" style={{ fontFamily: 'Inter, sans-serif' }}>
            {savedAudios.length} {savedAudios.length === 1 ? 'audio' : 'audios'} ready to use
          </p>
        </div>

        {/* Streak Counter shown with logo warm amber */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/25 text-amber-600 dark:text-amber-500">
          <Flame className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
          <span className="text-xs font-mono font-bold">{streakDays}d streak</span>
        </div>
      </div>

      {/* Taste Profile Card */}
      <div
        className="p-4 rounded-2xl border space-y-3 shadow-xs"
        style={{
          background: '#FFFFFF',
          borderColor: 'rgba(255,77,61,0.12)',
        }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-[#FF4D3D]" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#FF4D3D]" style={{ fontFamily: 'Inter, sans-serif' }}>
              Your Taste Profile
            </h3>
          </div>
          <button
            onClick={onResetTaste}
            className="flex items-center gap-1 text-[11px] font-mono text-[#9A9AA8] hover:text-[#0E0E10] transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            Reset
          </button>
        </div>

        <p className="text-xs text-[#6B6B78] leading-relaxed" style={{ fontFamily: 'Inter, sans-serif' }}>
          {topNiches.length > 0 || topLangs.length > 0
            ? `Your deck prioritizes ${[
                topNiches.length > 0 ? topNiches.join(', ') : '',
                topLangs.length > 0 ? topLangs.join(', ') : '',
              ]
                .filter(Boolean)
                .join(' · ')} based on your recent swipes.`
            : 'Swipe right on audios you love to tune the deck to your creative style.'}
        </p>

        {(topNiches.length > 0 || topLangs.length > 0) && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {topNiches.map((n) => (
              <span
                key={n}
                className="px-2.5 py-0.5 rounded-full text-[11px] font-medium"
                style={{ background: 'rgba(255,77,61,0.08)', color: '#FF4D3D' }}
              >
                {n}
              </span>
            ))}
            {topLangs.map((l) => (
              <span
                key={l}
                className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium"
                style={{ background: 'rgba(0,0,0,0.05)', color: '#6B6B78' }}
              >
                {l}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Saved Audios List */}
      <div className="space-y-2.5">
        {savedAudios.length === 0 ? (
          <div
            className="p-10 text-center border rounded-2xl space-y-3"
            style={{
              background: '#FFFFFF',
              borderColor: 'rgba(255,77,61,0.12)',
            }}
          >
            <div
              className="w-12 h-12 rounded-full flex items-center justify-center mx-auto"
              style={{ background: 'rgba(255,77,61,0.08)', color: '#FF4D3D' }}
            >
              <Music className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-bold text-[#0E0E10]" style={{ fontFamily: 'Inter, sans-serif' }}>
                No saved picks yet
              </p>
              <p className="text-xs text-[#6B6B78] max-w-xs mx-auto" style={{ fontFamily: 'Inter, sans-serif' }}>
                Flick up or tap "Use It" in the Vinyl Deck to collect breakout audio trends you want to create with.
              </p>
            </div>
          </div>
        ) : (
          savedAudios.map((t) => {
            const instagramUrl = t.audio_id
              ? `https://www.instagram.com/reels/audio/${t.audio_id}/`
              : `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(t.audio_title + ' ' + t.audio_artist)}`;
            const isThisPlaying = Boolean(isPlaying && currentTrack && String(currentTrack.id) === String(t.id));

            return (
              <div
                key={t.id}
                onClick={() => onSelectTrend?.(t)}
                className="p-3.5 rounded-2xl border flex items-center justify-between gap-3 shadow-xs hover:shadow-md transition-all cursor-pointer group"
                style={{
                  background: '#FFFFFF',
                  borderColor: isThisPlaying ? '#FF4D3D' : 'rgba(255,77,61,0.14)',
                }}
              >
                {/* Audio Play/Pause Button */}
                <button
                  onClick={(e) => handlePlayAudio(e, t)}
                  className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 transition-transform active:scale-90"
                  style={{
                    background: isThisPlaying ? '#FF4D3D' : 'rgba(255,77,61,0.1)',
                    color: isThisPlaying ? '#fff' : '#FF4D3D',
                    boxShadow: isThisPlaying ? '0 4px 12px rgba(255,77,61,0.35)' : 'none',
                  }}
                  title={isThisPlaying ? "Pause audio" : "Play audio preview"}
                >
                  {isThisPlaying ? (
                    <Pause className="w-4 h-4 fill-current" />
                  ) : (
                    <Play className="w-4 h-4 fill-current ml-0.5" />
                  )}
                </button>

                {/* Info Text */}
                <div className="min-w-0 flex-1">
                  <h4 className="text-sm font-bold text-[#0E0E10] truncate group-hover:text-[#FF4D3D] transition-colors" style={{ fontFamily: "'Bricolage Grotesque', system-ui" }}>
                    {t.audio_title}
                  </h4>
                  <p className="text-xs text-[#6B6B78] truncate mt-0.5" style={{ fontFamily: 'Inter, sans-serif' }}>
                    {t.audio_artist}
                  </p>
                  <div className="flex items-center gap-2 mt-1.5">
                    {t.audio_use_count > 0 && (
                      <span className="text-[11px] font-mono text-[#9A9AA8]">
                        {formatCount(t.audio_use_count)} uses
                      </span>
                    )}
                    {t.audio_use_count > 0 && <span className="text-[#D1D1D8]">·</span>}
                    <span
                      className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                      style={{
                        background: 'rgba(255,77,61,0.08)',
                        color: '#FF4D3D',
                      }}
                    >
                      {t.stage_label || t.status}
                    </span>
                  </div>
                </div>

                {/* Action buttons */}
                <div className="flex items-center gap-1.5 shrink-0" onClick={(e) => e.stopPropagation()}>
                  <a
                    href={instagramUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2.5 rounded-xl text-[#9A9AA8] hover:text-[#FF4D3D] hover:bg-rose-50 transition-colors"
                    title="Open on Instagram"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                  <button
                    onClick={() => onRemove(t.id)}
                    className="p-2.5 rounded-xl text-[#9A9AA8] hover:text-rose-600 hover:bg-rose-50 transition-colors"
                    title="Remove from Picks"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
