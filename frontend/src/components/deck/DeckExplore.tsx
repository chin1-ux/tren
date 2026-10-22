import React, { useState, useEffect, useRef } from 'react';
import { Search, Globe, ChevronDown, Sparkles, Filter, RefreshCw } from 'lucide-react';
import { type DeckTrend } from '@/lib/deck-ranking';
import { API_URL } from '@/lib/api';
import { formatAge, formatCount } from '@/lib/deck-tokens';

interface DeckExploreProps {
  onSelectTrend: (trend: DeckTrend) => void;
  mode: string;
  onModeChange: (newMode: string) => void;
}

const STAGES = [
  { id: 'all', label: 'All Active' },
  { id: 'just_starting', label: 'Just starting' },
  { id: 'blowing_up', label: 'Blowing up' },
  { id: 'everyones_using_it', label: "Everyone's using it" },
  { id: 'comeback', label: 'Comeback' },
  { id: 'expired', label: '⛔ Expired' },
];

const NICHES = [
  { id: 'all', label: 'All Niches' },
  { id: 'fitness', label: 'Fitness' },
  { id: 'food', label: 'Food' },
  { id: 'comedy', label: 'Comedy' },
  { id: 'fashion', label: 'Fashion' },
  { id: 'business', label: 'Business' },
  { id: 'travel', label: 'Travel' },
  { id: 'beauty', label: 'Beauty' },
  { id: 'tech', label: 'Tech' },
  { id: 'dance', label: 'Dance' },
];

const LANGUAGES = [
  { id: 'all', label: 'All Languages' },
  { id: 'hi', label: 'Hindi' },
  { id: 'en', label: 'English' },
  { id: 'pa', label: 'Punjabi' },
  { id: 'ta', label: 'Tamil' },
  { id: 'te', label: 'Telugu' },
  { id: 'ml', label: 'Malayalam' },
  { id: 'kn', label: 'Kannada' },
];

export function DeckExplore({ onSelectTrend, mode, onModeChange }: DeckExploreProps) {
  const [trends, setTrends] = useState<DeckTrend[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [nextCursor, setNextCursor] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 4 Controls
  const [selectedStage, setSelectedStage] = useState('all');
  const [includeExpired, setIncludeExpired] = useState(false);
  const [selectedNiche, setSelectedNiche] = useState('all');
  const [selectedLanguage, setSelectedLanguage] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const [freshnessMinutes, setFreshnessMinutes] = useState<number>(14);

  // Load trends from /api/trends/explore
  const fetchExploreTrends = async (cursorVal?: number | null, isAppend = false) => {
    if (isAppend) {
      setLoadingMore(true);
    } else {
      setLoading(true);
      setError(null);
    }

    try {
      const params = new URLSearchParams({
        limit: '20',
        mode,
      });

      if (cursorVal) params.append('cursor', cursorVal.toString());
      if (selectedStage !== 'all') params.append('stage', selectedStage);
      if (includeExpired || selectedStage === 'expired' || selectedNiche !== 'all' || selectedLanguage !== 'all' || searchQuery.trim()) {
        params.append('include_expired', 'true');
      }
      if (selectedNiche !== 'all') params.append('niche', selectedNiche);
      if (selectedLanguage !== 'all') params.append('language', selectedLanguage);
      if (searchQuery.trim()) params.append('search', searchQuery.trim());

      const res = await fetch(`${API_URL}/api/trends/explore?${params.toString()}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      const newItems: DeckTrend[] = data.trends || [];

      if (isAppend) {
        setTrends((prev) => [...prev, ...newItems]);
      } else {
        setTrends(newItems);
        setTotalCount(data.total || newItems.length);
      }
      setNextCursor(data.next_cursor || null);
    } catch (err: any) {
      console.error('Error loading explore trends:', err);
      setError('Unable to load explore trends');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  // Freshness check
  useEffect(() => {
    fetch(`${API_URL}/api/trends/freshness`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.sources?.instagram?.age_hours !== undefined) {
          setFreshnessMinutes(Math.max(1, Math.round(data.sources.instagram.age_hours * 60)));
        }
      })
      .catch(() => {});
  }, []);

  // Refetch when filters change
  useEffect(() => {
    fetchExploreTrends(null, false);
  }, [selectedStage, includeExpired, selectedNiche, selectedLanguage, mode]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchExploreTrends(null, false);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  return (
    <div className="flex flex-col h-full overflow-y-auto px-4 py-4 space-y-4 max-w-lg mx-auto w-full pb-24">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search by title or artist..."
          className="w-full pl-10 pr-4 py-2.5 rounded-2xl bg-zinc-900 border border-zinc-800 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-700 transition-colors"
        />
      </div>

      {/* Control 1: Stage Pills + Expired Toggle */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-mono uppercase text-zinc-400">Stages</span>
          <label className="flex items-center gap-1.5 cursor-pointer text-[11px] text-zinc-400">
            <input
              type="checkbox"
              checked={includeExpired}
              onChange={(e) => setIncludeExpired(e.target.checked)}
              className="rounded bg-zinc-800 border-zinc-700 text-[#FF3B5C] focus:ring-0"
            />
            <span className={includeExpired ? 'text-zinc-300' : 'text-zinc-500'}>
              Include expired
            </span>
          </label>
        </div>

        <div className="flex gap-1.5 overflow-x-auto no-scrollbar pb-1">
          {STAGES.map((st) => {
            const isSelected = selectedStage === st.id;
            return (
              <button
                key={st.id}
                onClick={() => setSelectedStage(st.id)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                  isSelected
                    ? 'bg-zinc-100 text-zinc-950 font-bold'
                    : 'bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200'
                }`}
              >
                {st.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Control 2: Niche Chips */}
      <div className="space-y-1.5">
        <span className="text-[11px] font-mono uppercase text-zinc-400">Niches</span>
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar pb-1">
          {NICHES.map((n) => {
            const isSelected = selectedNiche === n.id;
            return (
              <button
                key={n.id}
                onClick={() => setSelectedNiche(n.id)}
                className={`px-3 py-1 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                  isSelected
                    ? 'bg-[#FF3B5C] text-white font-bold'
                    : 'bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200'
                }`}
              >
                {n.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Controls 3 & 4: Mode (India/Global) + Language dropdown */}
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={() => onModeChange(mode === 'india' ? 'global' : 'india')}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-zinc-900 border border-zinc-800 text-xs font-medium text-zinc-300 hover:border-zinc-700 transition-colors"
        >
          <span>{mode === 'india' ? '🇮🇳 India' : '🌍 Global'}</span>
          <ChevronDown className="w-3.5 h-3.5 text-zinc-400" />
        </button>

        <select
          value={selectedLanguage}
          onChange={(e) => setSelectedLanguage(e.target.value)}
          aria-label="Filter by language"
          className="flex-1 py-2 px-3 rounded-xl bg-zinc-900 border border-zinc-800 text-xs font-medium text-zinc-300 hover:border-zinc-700 focus:outline-none transition-colors"
        >
          {LANGUAGES.map((l) => (
            <option key={l.id} value={l.id}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs text-zinc-400 px-1 pt-2">
        <span>{totalCount} audios available</span>
        <span className="font-mono text-[11px]">Updated {freshnessMinutes}m ago</span>
      </div>

      {/* Results List: Skeletons, Compact Rows, or Honest End State */}
      <div className="space-y-2">
        {loading ? (
          // Skeletons, never spinners (Section F)
          Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-18 rounded-2xl bg-zinc-900/60 border border-zinc-800/60 p-3.5 flex items-center justify-between animate-pulse"
            >
              <div className="space-y-2 w-2/3">
                <div className="h-4 bg-zinc-800 rounded-md w-3/4" />
                <div className="h-3 bg-zinc-800/60 rounded-md w-1/2" />
              </div>
              <div className="h-5 bg-zinc-800/60 rounded-full w-16" />
            </div>
          ))
        ) : error ? (
          <div className="p-8 text-center bg-zinc-900/40 border border-zinc-800 rounded-2xl space-y-3">
            <p className="text-xs text-zinc-400">{error}</p>
            <button
              onClick={() => fetchExploreTrends(null, false)}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-zinc-800 text-xs font-medium text-zinc-200 hover:bg-zinc-700"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </button>
          </div>
        ) : trends.length === 0 ? (
          <div className="p-12 text-center bg-zinc-900/20 border border-zinc-800/60 rounded-2xl space-y-2">
            <p className="text-sm font-semibold text-zinc-300">No audios match filters</p>
            <p className="text-xs text-zinc-500">Try adjusting your stage, language or niche criteria.</p>
          </div>
        ) : (
          trends.map((t) => {
            const creators = t.creator_count || 1;
            const rawSnippet = (t.why_this_works || t.used_for_note || t.used_for || '').trim();
            const isCanned = (s: string) => {
              if (!s || s.length < 8) return true;
              const l = s.toLowerCase();
              return (
                l.includes('currently driving high engagement') ||
                l.includes('automated fallback') ||
                l.includes('sporadic') ||
                l.includes('creators consistently use this sound') ||
                l.includes('fast-paced visual storytelling') ||
                l.includes('adapt the visual style')
              );
            };
            const isExpired = (t.status || '').toLowerCase() === 'expired';
            const detailSnippet = !isCanned(rawSnippet) ? rawSnippet : '';

            return (
              <div
                key={t.id}
                onClick={() => onSelectTrend(t)}
                className={`p-3.5 rounded-2xl border transition-all flex flex-col gap-2.5 cursor-pointer active:scale-[0.99] ${
                  isExpired
                    ? 'bg-zinc-950/80 border-zinc-800/80 hover:border-zinc-700'
                    : 'bg-zinc-900/70 border-zinc-800 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-bold text-white truncate font-display">
                        {t.audio_title}
                      </h4>
                      {t.is_new_today && !isExpired && (
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                      )}
                    </div>
                    <p className="text-xs text-zinc-400 truncate mt-0.5">
                      {t.audio_artist}
                    </p>
                    <p className="text-[11px] font-mono text-zinc-500 mt-1">
                      {formatCount(creators)} creators · caught {formatAge(t.age_hours)}
                    </p>
                  </div>

                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    <span
                      className={`px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
                        isExpired
                          ? 'bg-slate-800/80 text-slate-300 border-slate-700/60'
                          : t.status === 'emerging'
                          ? 'bg-pink-500/15 text-pink-300 border-pink-500/30'
                          : t.status === 'resurging'
                          ? 'bg-purple-500/15 text-purple-300 border-purple-500/30'
                          : 'bg-zinc-800 text-zinc-300 border-zinc-700/60'
                      }`}
                    >
                      {isExpired ? '⛔ Expired' : t.stage_label}
                    </span>
                    <div className="flex items-center gap-1.5">
                      {t.niche && (
                        <span className="text-[10px] font-mono text-zinc-400 px-1.5 py-0.5 rounded bg-zinc-800/60 border border-zinc-800">
                          {t.niche}
                        </span>
                      )}
                      {t.language && (
                        <span className="text-[10px] font-mono text-zinc-400 uppercase px-1.5 py-0.5 rounded bg-zinc-800/60 border border-zinc-800">
                          {t.language}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Details Banner: Why this works / Used for pattern */}
                {detailSnippet && (
                  <div className="rounded-xl bg-zinc-950/70 border border-zinc-800/80 p-2.5 text-xs text-zinc-300 leading-snug">
                    <span className="font-bold text-amber-400">💡 Why this works: </span>
                    {detailSnippet}
                  </div>
                )}

                {isExpired && (
                  <div className="flex items-center gap-1.5 text-[10px] font-mono text-zinc-500 pt-0.5">
                    <span>⚠️ Historical reference · Past viral window</span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Infinite Scroll / Honest End Message */}
      {trends.length > 0 && !loading && (
        <div className="pt-2 text-center">
          {nextCursor ? (
            <button
              onClick={() => fetchExploreTrends(nextCursor, true)}
              disabled={loadingMore}
              className="px-5 py-2 rounded-full bg-zinc-900 border border-zinc-800 text-xs font-medium text-zinc-300 hover:border-zinc-700 disabled:opacity-50"
            >
              {loadingMore ? 'Loading more...' : 'Load more (20)'}
            </button>
          ) : (
            <p className="text-xs font-mono text-zinc-500 py-4">
              You've seen all {trends.length} — updated {freshnessMinutes}m ago
            </p>
          )}
        </div>
      )}
    </div>
  );
}
