import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createFileRoute, useNavigate, Link } from '@tanstack/react-router';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RotateCcw,
  X,
  Check,
  Compass,
  Bookmark,
  Layers,
  Settings,
  LayoutDashboard,
  ChevronDown,
  Sparkles,
  RefreshCw,
} from 'lucide-react';

import {
  type DeckTrend,
  type UserSwipe,
  rankDeck
} from '@/lib/deck-ranking';
import { VinylRecord }     from '@/components/deck/VinylRecord';
import { VinylInfoModal }  from '@/components/deck/VinylInfoModal';
import { VinylBackground } from '@/components/deck/VinylBackground';
import { DeckExplore }     from '@/components/deck/DeckExplore';
import { DeckPicks }       from '@/components/deck/DeckPicks';
import { DeckOnboarding }  from '@/components/deck/DeckOnboarding';
import { API_URL, getAuthToken } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { RouteErrorBoundary } from '@/components/RouteErrorBoundary';


export const Route = createFileRoute('/deck')({
  head: () => ({
    meta: [
      { title: "Deck — Trendrop" },
      { name: "description", content: "Swipe through verified breakout audio trends before anyone else." },
    ],
  }),
  component: DeckScreen,
  errorComponent: RouteErrorBoundary,
});

function DeckScreen() {
  const navigate = useNavigate();
  const auth = useAuth?.() || { user: null, loginWithGoogle: async () => {} };

  // Current active tab: 'deck' | 'explore' | 'picks'
  const [activeTab, setActiveTab] = useState<'deck' | 'explore' | 'picks'>('deck');

  // Preferences
  const [mode, setMode] = useState<string>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('trendrop_deck_mode') || 'india';
    }
    return 'india';
  });

  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = JSON.parse(localStorage.getItem('trendrop_deck_languages') || '[]');
        if (Array.isArray(saved) && saved.length > 0) return saved;
      } catch {
        return [];
      }
    }
    return [];
  });

  const [includeExpiredDeck, setIncludeExpiredDeck] = useState<boolean>(false);

  const [selectedNiches, setSelectedNiches] = useState<string[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        return JSON.parse(localStorage.getItem('trendrop_deck_niches') || '[]');
      } catch {
        return [];
      }
    }
    return [];
  });

  // State: Raw pool and Ranked 15-card Deck
  const [rawPool, setRawPool] = useState<DeckTrend[]>([]);
  const [deck, setDeck] = useState<DeckTrend[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Swipes history & queue
  const [swipes, setSwipes] = useState<UserSwipe[]>([]);
  const swipeQueueRef = useRef<Array<{ trend_id: number; action: 'use' | 'skip'; reason?: string }>>([]);
  const [savedAudios, setSavedAudios] = useState<DeckTrend[]>([]);
  const [lastSwipedCard, setLastSwipedCard] = useState<DeckTrend | null>(null);

  // Sheet dialogs
  const [selectedVinyl, setSelectedVinyl] = useState<DeckTrend | null>(null);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const [skipToast, setSkipToast] = useState<{ show: boolean; trendId?: number }>({ show: false });
  const [showGooglePrompt, setShowGooglePrompt] = useState(false);

  // Freshness
  const [freshnessMinutes, setFreshnessMinutes] = useState(12);

  // Streak calculation
  const [streakDays, setStreakDays] = useState<number>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('trendrop_swipe_streak');
      return stored ? parseInt(stored, 10) || 1 : 1;
    }
    return 1;
  });

  // Onboarding check
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('deck_beta');
      const onboarded = localStorage.getItem('trendrop_deck_onboarded');
      if (!onboarded) {
        setIsOnboardingOpen(true);
      }
    }
  }, []);

  // Fetch freshness
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

  // Flush queued swipes to backend
  const flushSwipeQueue = useCallback(async () => {
    if (swipeQueueRef.current.length === 0) return;
    const batch = [...swipeQueueRef.current];
    swipeQueueRef.current = [];

    const token = getAuthToken();
    if (!token) return; // Guests store locally only

    try {
      const payload = JSON.stringify({ swipes: batch });
      if (typeof navigator !== 'undefined' && 'sendBeacon' in navigator) {
        // Use sendBeacon or fetch keepalive
        fetch(`${API_URL}/api/swipes`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: payload,
          keepalive: true,
        }).catch(() => {});
      } else {
        await fetch(`${API_URL}/api/swipes`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: payload,
        });
      }
    } catch (e) {
      console.warn('Failed to flush swipes:', e);
    }
  }, []);

  // Flush on visibilitychange / pagehide per C5
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'hidden') {
        flushSwipeQueue();
      }
    };
    const handlePageHide = () => {
      flushSwipeQueue();
    };

    window.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('pagehide', handlePageHide);
    return () => {
      window.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('pagehide', handlePageHide);
    };
  }, [flushSwipeQueue]);

  // Load swipes from server if logged in, else localStorage (cap 500)
  useEffect(() => {
    const loadSwipes = async () => {
      let loaded: UserSwipe[] = [];
      const token = getAuthToken();
      if (token) {
        try {
          const res = await fetch(`${API_URL}/api/swipes?limit=300`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (res.ok) {
            const data = await res.json();
            loaded = data.swipes || [];
          }
        } catch {
          // fallback
        }
      }

      if (loaded.length === 0 && typeof window !== 'undefined') {
        try {
          loaded = JSON.parse(localStorage.getItem('trendrop_local_swipes') || '[]');
        } catch {
          loaded = [];
        }
      }

      setSwipes(loaded);
    };
    loadSwipes();
  }, []);

  // Fetch deck pool once per session per C5
  useEffect(() => {
    const fetchDeckPool = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({
          mode,
          limit: '120',
        });
        if (selectedLanguages.length > 0) {
          params.append('langs', selectedLanguages.join(','));
        }
        if (selectedNiches.length > 0) {
          params.append('niches', selectedNiches.join(','));
        }
        if (includeExpiredDeck || selectedNiches.length > 0) {
          params.append('include_expired', 'true');
        }

        const res = await fetch(`${API_URL}/api/deck?${params.toString()}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const pool: DeckTrend[] = data.trends || [];
        setRawPool(pool);

        // Rank the 15-card deck
        const ranked = rankDeck(pool, swipes, 15);
        setDeck(ranked);
        setCurrentIndex(0);
      } catch (err: any) {
        console.error('Failed to load deck:', err);
        setError('Failed to load trending audio cards.');
      } finally {
        setLoading(false);
      }
    };

    fetchDeckPool();
  }, [mode, selectedLanguages, selectedNiches, includeExpiredDeck]);

  // Handle Swipe (Use / Skip)
  const handleSwipe = useCallback(
    (action: 'use' | 'skip', reason?: string) => {
      if (currentIndex >= deck.length) return;
      const currentCard = deck[currentIndex];
      setLastSwipedCard(currentCard);

      const newSwipe: UserSwipe = {
        trend_id: currentCard.id,
        action,
        reason: reason || null,
        updated_at: new Date().toISOString(),
        niche: currentCard.niche,
        language: currentCard.language,
        artist: currentCard.audio_artist,
      };

      // Add to in-memory swipes
      setSwipes((prev) => [newSwipe, ...prev]);

      // Add to queue
      swipeQueueRef.current.push({
        trend_id: currentCard.id,
        action,
        reason: reason || undefined,
      });

      // Save locally (cap 500)
      if (typeof window !== 'undefined') {
        try {
          const stored: UserSwipe[] = JSON.parse(
            localStorage.getItem('trendrop_local_swipes') || '[]'
          );
          const updated = [newSwipe, ...stored].slice(0, 500);
          localStorage.setItem('trendrop_local_swipes', JSON.stringify(updated));

          // Update streak
          const lastDate = localStorage.getItem('trendrop_last_swipe_date');
          const today = new Date().toDateString();
          if (lastDate !== today) {
            const newStreak = (parseInt(localStorage.getItem('trendrop_swipe_streak') || '0', 10) || 0) + 1;
            localStorage.setItem('trendrop_swipe_streak', newStreak.toString());
            localStorage.setItem('trendrop_last_swipe_date', today);
            setStreakDays(newStreak);
          }
        } catch {
          // ignore
        }
      }

      // If 'use', add to saved audios
      if (action === 'use') {
        setSavedAudios((prev) => [currentCard, ...prev.filter((c) => c.id !== currentCard.id)]);

        // Gentle Google sign-in prompt for guest if not logged in
        if (!auth.user && !getAuthToken()) {
          setShowGooglePrompt(true);
        }
      }

      // If 'skip', show optional 3-second toast with reason chips per Section D
      if (action === 'skip') {
        setSkipToast({ show: true, trendId: currentCard.id });
        setTimeout(() => {
          setSkipToast({ show: false });
        }, 3000);
      }

      // Flush queue every 10 swipes per C5
      if (swipeQueueRef.current.length >= 10) {
        flushSwipeQueue();
      }

      // Advance card
      setCurrentIndex((prev) => prev + 1);
    },
    [currentIndex, deck, auth.user, flushSwipeQueue]
  );

  // Handle Undo (restores the last card with a reverse spring per Section E)
  const handleUndo = useCallback(() => {
    if (currentIndex > 0 && lastSwipedCard) {
      setCurrentIndex((prev) => Math.max(0, prev - 1));
      // Remove last swipe
      setSwipes((prev) => prev.slice(1));
      if (swipeQueueRef.current.length > 0) {
        swipeQueueRef.current.pop();
      }
      setLastSwipedCard(null);
    }
  }, [currentIndex, lastSwipedCard]);

  // Keyboard shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (activeTab !== 'deck' || isOnboardingOpen || selectedVinyl) return;
      if (e.key === 'ArrowUp')    { handleSwipe('use');  }
      else if (e.key === 'ArrowDown') { handleSwipe('skip'); }
      else if (e.key === 'z')         { handleUndo(); }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, isOnboardingOpen, selectedVinyl, deck, currentIndex, handleSwipe, handleUndo]);

  const currentVinyl = deck[currentIndex];
  const isCaughtUp = currentIndex >= deck.length && !loading;

  return (
    <div
      className="flex flex-col w-full min-h-[calc(100dvh-5rem)] pb-20 font-sans select-none relative bg-background text-foreground"
    >
      {/* Animated background */}
      <VinylBackground />

      {/* Top Header Bar */}
      <header
        className="flex flex-col gap-2.5 px-4 pt-3 pb-2.5 border-b border-border/40 z-40 sticky top-0 bg-background/85 backdrop-blur-xl"
      >
        <div className="flex items-center justify-between">
          {/* Left: Mode Toggle & Niche Chip */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                const newMode = mode === 'india' ? 'global' : 'india';
                setMode(newMode);
                if (typeof window !== 'undefined') {
                  localStorage.setItem('trendrop_deck_mode', newMode);
                }
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold transition-all shadow-xs active:scale-95"
              style={{
                background: '#FF4D3D', color: '#fff',
                border: 'none', boxShadow: '0 2px 8px rgba(255,77,61,0.3)',
              }}
            >
              <span>{mode === 'india' ? '🇮🇳 India' : '🌍 Global'}</span>
            </button>

            <button
              onClick={() => setIsOnboardingOpen(true)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-full text-xs transition-all active:scale-95"
              style={{
                background: 'rgba(255,77,61,0.08)',
                border: '1px solid rgba(255,77,61,0.2)',
                color: '#FF4D3D',
              }}
            >
              <span className="truncate max-w-[100px]">
                {selectedNiches.length > 0 ? selectedNiches.join(', ') : 'All Niches'}
              </span>
              <ChevronDown className="w-3.5 h-3.5 shrink-0" />
            </button>

            {/* Expired Toggle Chip in Deck Header */}
            {activeTab === 'deck' && (
              <button
                onClick={() => setIncludeExpiredDeck((prev) => !prev)}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-full text-xs transition-all active:scale-95"
                style={{
                  background: includeExpiredDeck ? 'rgba(100,116,139,0.18)' : 'rgba(0,0,0,0.05)',
                  border: `1px solid ${includeExpiredDeck ? 'rgba(100,116,139,0.35)' : 'rgba(0,0,0,0.08)'}`,
                  color: includeExpiredDeck ? '#334155' : '#9A9AA8',
                  fontWeight: includeExpiredDeck ? 700 : 500,
                }}
                title="Toggle including expired tracks in deck"
              >
                <span>{includeExpiredDeck ? '⛔ +Expired' : 'Active Only'}</span>
              </button>
            )}
          </div>

          {/* Right: Progress */}
          {activeTab === 'deck' && (
            <div className="flex items-center gap-2">
              <span
                className="text-xs font-mono font-medium px-2.5 py-1 rounded-full"
                style={{ background: 'rgba(255,77,61,0.08)', color: '#FF4D3D', border: '1px solid rgba(255,77,61,0.15)' }}
              >
                {Math.min(currentIndex + 1, deck.length || 15)} / {deck.length || 15}
              </span>
            </div>
          )}
        </div>

        {/* Sub-view Switcher */}
        <div
          className="flex items-center justify-center p-1 rounded-full max-w-sm mx-auto w-full"
          style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
        >
          <button
            onClick={() => setActiveTab('deck')}
            className={`flex-1 py-1.5 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-1.5`}
            style={activeTab === 'deck'
              ? { background: '#FF4D3D', color: '#fff', boxShadow: '0 2px 8px rgba(255,77,61,0.35)' }
              : { color: '#9A9AA8' }
            }
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Deck</span>
          </button>
          <Link
            to="/"
            className="flex-1 py-1.5 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-1.5"
            style={{ color: '#9A9AA8' }}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>Feed</span>
          </Link>
          <button
            onClick={() => setActiveTab('picks')}
            className="flex-1 py-1.5 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-1.5 relative"
            style={activeTab === 'picks'
              ? { background: '#FF4D3D', color: '#fff', boxShadow: '0 2px 8px rgba(255,77,61,0.35)' }
              : { color: '#9A9AA8' }
            }
          >
            <Bookmark className="w-3.5 h-3.5" />
            <span>Picks</span>
            {savedAudios.length > 0 && (
              <span className="px-1.5 py-0.2 text-[10px] rounded-full font-mono"
                style={{ background: 'rgba(199,242,58,0.8)', color: '#0E0E10' }}
              >
                {savedAudios.length}
              </span>
            )}
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden relative flex flex-col justify-center items-center px-4 py-2">
        {activeTab === 'deck' ? (
          loading ? (
            // Skeleton Card State
            <div className="w-full max-w-[390px] h-[520px] rounded-[28px] bg-zinc-900/60 border border-zinc-800 p-6 flex flex-col justify-between animate-pulse">
              <div className="flex justify-between">
                <div className="h-6 w-20 bg-zinc-800 rounded-full" />
                <div className="h-8 w-8 bg-zinc-800 rounded-full" />
              </div>
              <div className="space-y-3">
                <div className="h-8 w-3/4 bg-zinc-800 rounded-lg" />
                <div className="h-5 w-1/2 bg-zinc-800/60 rounded-lg" />
                <div className="h-6 w-32 bg-zinc-800/40 rounded-lg mt-4" />
              </div>
              <div className="flex gap-2">
                <div className="h-6 w-16 bg-zinc-800 rounded-lg" />
                <div className="h-6 w-20 bg-zinc-800 rounded-lg" />
              </div>
            </div>
          ) : error ? (
            <div className="w-full max-w-[390px] p-8 text-center bg-zinc-900/50 border border-zinc-800 rounded-3xl space-y-4">
              <p className="text-sm text-zinc-300">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#FF3B5C] text-xs font-semibold text-white shadow-lg"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Retry Deck
              </button>
            </div>
          ) : isCaughtUp ? (
            // Caught up state
            <div
              className="w-full max-w-[390px] p-8 text-center rounded-3xl space-y-5 animate-in fade-in duration-300"
              style={{ background: '#fff', border: '1px solid rgba(255,77,61,0.12)', boxShadow: '0 4px 24px rgba(255,77,61,0.08)' }}
            >
              <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto"
                style={{ background: 'rgba(199,242,58,0.15)', border: '1.5px solid rgba(199,242,58,0.5)' }}
              >
                <Check className="w-8 h-8" style={{ color: '#4A7C00' }} />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-2xl font-bold" style={{ color: '#0E0E10', fontFamily: "'Bricolage Grotesque', system-ui" }}>
                  You're caught up
                </h3>
                <p className="text-xs font-mono" style={{ color: '#9A9AA8' }}>Updated {freshnessMinutes}m ago</p>
                <p className="text-xs pt-1" style={{ color: '#9A9AA8' }}>You've reviewed today's top verified breakout audios.</p>
              </div>
              <div className="pt-2">
                <button
                  onClick={() => setActiveTab('explore')}
                  className="w-full py-3.5 px-6 rounded-2xl text-white text-sm font-semibold shadow-xl transition-all active:scale-95"
                  style={{ background: '#FF4D3D', boxShadow: '0 6px 20px rgba(255,77,61,0.35)' }}
                >
                  Explore All Trends
                </button>
              </div>
            </div>
          ) : (
            // Vinyl stack + action buttons
            <div className="w-full max-w-[390px] flex flex-col items-center h-full max-h-[660px]">
              {/* Single Vinyl Showcase (one at a time) */}
              <div className="w-full flex-1 relative min-h-[460px] max-h-[540px]">
                <AnimatePresence mode="wait">
                  {currentVinyl && (
                    <VinylRecord
                      key={currentVinyl.id}
                      trend={currentVinyl}
                      isFront={true}
                      stackIndex={0}
                      onSwipe={(act) => handleSwipe(act)}
                      onClick={() => setSelectedVinyl(currentVinyl)}
                    />
                  )}
                </AnimatePresence>
              </div>

              {/* Action buttons — vertical swipe hint */}
              <div className="w-full flex items-center justify-center gap-4 py-4 px-2">
                {/* Undo */}
                <button
                  onClick={handleUndo}
                  disabled={currentIndex === 0}
                  className="w-12 h-12 rounded-full flex items-center justify-center disabled:opacity-30 disabled:pointer-events-none active:scale-90 transition-all"
                  style={{ background: 'rgba(0,0,0,0.06)', border: '1px solid rgba(0,0,0,0.08)', color: '#9A9AA8' }}
                  aria-label="Undo"
                >
                  <RotateCcw className="w-5 h-5" />
                </button>

                {/* Pass (down) */}
                <button
                  onClick={() => handleSwipe('skip')}
                  className="w-15 h-15 rounded-full flex items-center justify-center active:scale-90 transition-all"
                  style={{
                    background: 'rgba(255,77,61,0.08)',
                    border: '1.5px solid rgba(255,77,61,0.25)',
                    color: '#FF4D3D',
                  }}
                  aria-label="Pass (flick down)"
                >
                  <X className="w-7 h-7" />
                </button>

                {/* Use It (up) */}
                <button
                  onClick={() => handleSwipe('use')}
                  className="w-15 h-15 rounded-full text-white flex items-center justify-center active:scale-90 transition-all"
                  style={{
                    background: '#FF4D3D',
                    boxShadow: '0 6px 20px rgba(255,77,61,0.4)',
                  }}
                  aria-label="Use It (flick up)"
                >
                  <Check className="w-8 h-8 stroke-[3]" />
                </button>
              </div>

              {/* Swipe hint label */}
              <p className="text-[11px] pb-2" style={{ color: '#C7A09A', fontFamily: 'Inter, sans-serif' }}>
                Flick up to use · Flick down to pass · Tap to open
              </p>
            </div>
          )
        ) : activeTab === 'explore' ? (
          <DeckExplore
            onSelectTrend={(t) => setSelectedVinyl(t)}
            mode={mode}
            onModeChange={(m) => setMode(m)}
          />
        ) : (
          <DeckPicks
            savedAudios={savedAudios}
            swipes={swipes}
            onRemove={(id) => {
              setSavedAudios((prev) => prev.filter((a) => a.id !== id));
            }}
            onResetTaste={() => {
              setSwipes([]);
              if (typeof window !== 'undefined') {
                localStorage.removeItem('trendrop_local_swipes');
              }
            }}
            streakDays={streakDays}
            onSelectTrend={(t) => setSelectedVinyl(t)}
          />
        )}

        {/* 3-Second Skip Feedback Toast with Reason Chips (Section D) */}
        {skipToast.show && (
          <div className="absolute top-4 inset-x-4 max-w-sm mx-auto bg-zinc-900 border border-zinc-700/80 rounded-2xl p-3 shadow-2xl z-50 flex items-center justify-between gap-2 animate-in fade-in duration-150">
            <span className="text-xs text-zinc-300">Adjust taste:</span>
            <div className="flex gap-1.5">
              {['Wrong vibe', 'Wrong language', 'Seen it'].map((reason) => (
                <button
                  key={reason}
                  onClick={() => {
                    if (skipToast.trendId) {
                      swipeQueueRef.current.push({
                        trend_id: skipToast.trendId,
                        action: 'skip',
                        reason,
                      });
                    }
                    setSkipToast({ show: false });
                  }}
                  className="px-2.5 py-1 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-[11px] font-medium text-zinc-200 transition-colors"
                >
                  {reason}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Gentle Google Sign-In Prompt for Guests (Section B1) */}
        {showGooglePrompt && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 animate-in fade-in">
            <div className="w-full max-w-sm bg-zinc-900 border border-zinc-800 rounded-3xl p-6 text-center space-y-4 shadow-2xl">
              <div className="w-12 h-12 rounded-full bg-[#FF3B5C]/10 text-[#FF3B5C] flex items-center justify-center mx-auto">
                <Bookmark className="w-6 h-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-lg font-bold text-white font-display">
                  Audio saved to your Picks!
                </h3>
                <p className="text-xs text-zinc-400">
                  Connect your Google account to sync your saved picks and taste across devices.
                </p>
              </div>
              <div className="pt-2 space-y-2">
                <button
                  onClick={async () => {
                    setShowGooglePrompt(false);
                    try {
                      await auth.loginWithGoogle();
                    } catch {}
                  }}
                  className="w-full py-3 px-4 rounded-xl bg-white hover:bg-zinc-100 text-zinc-950 font-semibold text-xs transition-colors flex items-center justify-center gap-2"
                >
                  <span>Continue with Google</span>
                </button>
                <button
                  onClick={() => setShowGooglePrompt(false)}
                  className="w-full py-2.5 text-xs text-zinc-400 hover:text-white"
                >
                  Stay as Guest
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Vinyl Info Modal */}
      {selectedVinyl && (
        <VinylInfoModal
          trend={selectedVinyl}
          onClose={() => setSelectedVinyl(null)}
          onUse={() => { handleSwipe('use'); setSelectedVinyl(null); }}
          onSkip={() => { handleSwipe('skip'); setSelectedVinyl(null); }}
        />
      )}

      <DeckOnboarding
        isOpen={isOnboardingOpen}
        onComplete={(prefs) => {
          setMode(prefs.mode);
          setSelectedLanguages(prefs.languages);
          setSelectedNiches(prefs.niches);
          setIsOnboardingOpen(false);
        }}
        onClose={() => setIsOnboardingOpen(false)}
        initialMode={mode}
        initialLanguages={selectedLanguages}
        initialNiches={selectedNiches}
      />
    </div>
  );
}
