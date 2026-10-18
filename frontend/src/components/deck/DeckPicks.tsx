import React from 'react';
import { ExternalLink, Trash2, Flame, RotateCcw, Music, Sparkles } from 'lucide-react';
import { type DeckTrend, type UserSwipe } from '@/lib/deck-ranking';
import { formatAge, formatCount } from '@/lib/deck-tokens';

interface DeckPicksProps {
  savedAudios: DeckTrend[];
  swipes: UserSwipe[];
  onRemove: (trendId: number) => void;
  onResetTaste: () => void;
  streakDays: number;
}

export function DeckPicks({
  savedAudios,
  swipes,
  onRemove,
  onResetTaste,
  streakDays,
}: DeckPicksProps) {
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

  return (
    <div className="flex flex-col h-full overflow-y-auto px-4 py-4 space-y-5 max-w-lg mx-auto w-full pb-24">
      {/* Top Header & Streak */}
      <div className="flex items-center justify-between pt-1">
        <div>
          <h2 className="text-xl font-bold font-display text-white">Your Saved Picks</h2>
          <p className="text-xs text-zinc-400">
            {savedAudios.length} {savedAudios.length === 1 ? 'audio' : 'audios'} ready to use
          </p>
        </div>

        {/* Streak Counter shown subtly per B5 */}
        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400">
          <Flame className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
          <span className="text-xs font-mono font-bold">{streakDays}d streak</span>
        </div>
      </div>

      {/* Small Explainable "Your Taste" Card */}
      <div className="p-4 rounded-2xl bg-zinc-900 border border-zinc-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-[#FF3B5C]" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-300">
              Your Taste Profile
            </h3>
          </div>
          <button
            onClick={onResetTaste}
            className="flex items-center gap-1 text-[11px] font-mono text-zinc-400 hover:text-white transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            Reset
          </button>
        </div>

        <p className="text-xs text-zinc-400 leading-relaxed">
          {topNiches.length > 0 || topLangs.length > 0
            ? `Your deck prioritizes ${[
                topNiches.length > 0 ? topNiches.join(', ') : '',
                topLangs.length > 0 ? topLangs.join(', ') : '',
              ]
                .filter(Boolean)
                .join(' · ')} based on your recent swipes.`
            : 'Swipe right on audios you love to help the deck tune to your style.'}
        </p>

        {(topNiches.length > 0 || topLangs.length > 0) && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {topNiches.map((n) => (
              <span
                key={n}
                className="px-2 py-0.5 rounded-md bg-zinc-800 text-[11px] font-medium text-zinc-300"
              >
                {n}
              </span>
            ))}
            {topLangs.map((l) => (
              <span
                key={l}
                className="px-2 py-0.5 rounded-md bg-zinc-800 text-[11px] font-mono font-medium text-zinc-400"
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
          <div className="p-12 text-center bg-zinc-900/30 border border-zinc-800/60 rounded-2xl space-y-3">
            <div className="w-12 h-12 rounded-full bg-zinc-800/80 flex items-center justify-center mx-auto text-zinc-500">
              <Music className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-zinc-300">No saved picks yet</p>
              <p className="text-xs text-zinc-500 max-w-xs mx-auto">
                Swipe right or tap "Use It" in the Deck to save sounds you want to create with.
              </p>
            </div>
          </div>
        ) : (
          savedAudios.map((t) => {
            const instagramUrl = `https://www.instagram.com/reels/audio/${t.id}/`;
            return (
              <div
                key={t.id}
                className="p-4 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-between gap-3 shadow-md"
              >
                <div className="min-w-0 flex-1">
                  <h4 className="text-sm font-bold text-white truncate font-display">
                    {t.audio_title}
                  </h4>
                  <p className="text-xs text-zinc-400 truncate mt-0.5">
                    {t.audio_artist}
                  </p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[11px] font-mono text-zinc-500">
                      {formatCount(t.creator_count || 1)} creators
                    </span>
                    <span className="text-zinc-600">·</span>
                    <span className="text-[11px] text-zinc-400">
                      {t.stage_label}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <a
                    href={instagramUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white transition-colors"
                    title="Open on Instagram"
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                  <button
                    onClick={() => onRemove(t.id)}
                    className="p-2.5 rounded-xl bg-zinc-800/60 hover:bg-rose-950/60 text-zinc-400 hover:text-rose-400 transition-colors"
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
