import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
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
  HelpCircle,
} from 'lucide-react';
import { toast } from 'sonner';

import {
  type DeckTrend,
  type UserSwipe,
  rankDeck
} from '@/lib/deck-ranking';
import { VinylRecord }        from '@/components/deck/VinylRecord';
import { VinylInfoModal }     from '@/components/deck/VinylInfoModal';
import { VinylBackground }    from '@/components/deck/VinylBackground';
import { DeckPicks }          from '@/components/deck/DeckPicks';
import { DeckOnboarding }     from '@/components/deck/DeckOnboarding';
import { MilestoneRecapCard } from '@/components/deck/MilestoneRecapCard';
import { API_URL, getAuthToken, fetchTargetedTrends } from '@/lib/api';
import { useAuth } from '@/contexts/AuthContext';
import { useQueryClient } from '@tanstack/react-query';
import { saveAudioToWorkspace, removeAudioFromWorkspace, getLocalTargeted, toDeckTrend } from '@/lib/workspace-storage';
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
  const queryClient = useQueryClient();
  const auth = useAuth?.() || { user: null, loginWithGoogle: async () => {} };

  // Current active tab: 'deck' | 'picks'
  const [activeTab, setActiveTab] = useState<'deck' | 'picks'>('deck');

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

  const currentVinyl = deck[currentIndex];
  const isCaughtUp = currentIndex >= deck.length && !loading;

  // Swipes history & queue - Synchronously rehydrate from localStorage so first render excludes swiped cards
  const [swipes, setSwipes] = useState<UserSwipe[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const local = JSON.parse(localStorage.getItem('trendrop_local_swipes') || '[]');
        if (Array.isArray(local) && local.length > 0) return local;
      } catch {
        return [];
      }
    }
    return [];
  });
  const swipeQueueRef = useRef<Array<{ trend_id: number; action: 'use' | 'skip'; reason?: string }>>([]);
  const [savedAudios, setSavedAudios] = useState<DeckTrend[]>(() => getLocalTargeted());
  const [lastSwipedCard, setLastSwipedCard] = useState<DeckTrend | null>(null);
  const [batchCount, setBatchCount] = useState<number>(1);
  const [isDealingMore, setIsDealingMore] = useState<boolean>(false);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

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

  // Onboarding & Walkthrough check — opens automatically for first-time deck viewers
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('deck_beta');
      const seenWalkthrough = localStorage.getItem('trendrop_deck_walkthrough_v1');
      if (!seenWalkthrough) {
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

  // Load swipes from server if logged in, merge with local
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

      setSwipes((prev) => {
        const combined = [...loaded, ...prev];
        const unique = Array.from(new Map(combined.map((s) => [s.trend_id, s])).values()).slice(0, 500);
        if (typeof window !== 'undefined') {
          try {
            localStorage.setItem('trendrop_local_swipes', JSON.stringify(unique));
          } catch {}
        }
        return unique;
      });
    };
    loadSwipes();
  }, []);

  // Fetch deck pool with auto-update and cache-busting
  const fetchDeckPool = useCallback(async (isSilent = false) => {
    if (!isSilent) {
      setLoading(true);
      setError(null);
    }
    try {
      const params = new URLSearchParams({
        mode,
        limit: '120',
        fresh: 'true',
        _t: Date.now().toString(),
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

      const res = await fetch(`${API_URL}/api/deck?${params.toString()}`, {
        headers: {
          'Cache-Control': 'no-cache, no-store',
          'Pragma': 'no-cache',
        },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const pool: DeckTrend[] = data.trends || [];
      setRawPool(pool);

      // On silent background polling: only update pool in memory, do NOT wipe or disrupt the active vinyl card
      if (!isSilent) {
        const ranked = rankDeck(pool, [], 15);
        setDeck(ranked);
        setCurrentIndex(0);
      }
    } catch (err: any) {
      console.error('Failed to load deck:', err);
      if (!isSilent) {
        setError('Failed to load trending audio cards.');
      }
    } finally {
      if (!isSilent) {
        setLoading(false);
      }
    }
  }, [mode, selectedLanguages, selectedNiches, includeExpiredDeck, swipes]);

  // Switch between India and Global mode cleanly without leaving stale state
  const handleSwitchMode = useCallback((newMode: 'india' | 'global') => {
    setMode(newMode);
    if (typeof window !== 'undefined') {
      localStorage.setItem('trendrop_deck_mode', newMode);
    }
    setCurrentIndex(0);
    setBatchCount(1);
    setDeck([]);
    setLoading(true);
  }, []);

  // Refresh deck from start & sync latest trends (places brand new breakout tracks at Card 1)
  const handleRefreshDeckFromStart = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // 1. Keep saved audios ('use'), clear passed ('skip') so creator can see them again
      const keptSwipes = swipes.filter((s) => s.action === 'use');
      setSwipes(keptSwipes);
      if (typeof window !== 'undefined') {
        localStorage.setItem('trendrop_local_swipes', JSON.stringify(keptSwipes));
      }

      // 2. Fetch fresh trends with cache-busting timestamp & fresh=true
      const params = new URLSearchParams({
        mode,
        limit: '120',
        fresh: 'true',
        _t: Date.now().toString(),
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

      const res = await fetch(`${API_URL}/api/deck?${params.toString()}`, {
        headers: {
          'Cache-Control': 'no-cache, no-store',
          'Pragma': 'no-cache',
        },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const pool: DeckTrend[] = data.trends || [];
      setRawPool(pool);

      // 3. Re-rank from the beginning (index 0) with newly fetched trends prioritizing first
      const freshRanked = rankDeck(pool, [], 15);

      const currentIds = new Set(deck.map((d) => d.id));
      const hasNewBreakouts = freshRanked.some((t) => !currentIds.has(t.id));

      if (freshRanked.length > 0) {
        setDeck(freshRanked);
        setCurrentIndex(0);
        setBatchCount(1);
      }

      if (hasNewBreakouts) {
        toast.success('Synced latest live audios', {
          description: `Loaded fresh breakout tracks · Card 1 is newest`,
        });
      } else {
        toast.info('Catalog is up to date', {
          description: `Latest scraper verified · ${freshRanked.length} tracks active`,
        });
      }
    } catch (err: any) {
      console.error('Failed to refresh deck:', err);
      toast.error('Sync failed', { description: 'Could not connect to live audio server' });
    } finally {
      setIsRefreshing(false);
    }
  }, [mode, selectedLanguages, selectedNiches, includeExpiredDeck, swipes, deck]);

  // Initial fetch on mount & filter changes
  useEffect(() => {
    fetchDeckPool(false);
  }, [mode, selectedLanguages, selectedNiches, includeExpiredDeck]);

  // Continuous auto-polling every 60s & window focus to instantly reflect new ingestions
  useEffect(() => {
    const timer = setInterval(() => {
      fetchDeckPool(true);
    }, 60_000);

    const onFocus = () => {
      fetchDeckPool(true);
    };

    window.addEventListener('focus', onFocus);
    return () => {
      clearInterval(timer);
      window.removeEventListener('focus', onFocus);
    };
  }, [fetchDeckPool]);

  // Rehydrate savedAudios from rawPool matching 'use' swipes
  useEffect(() => {
    if (rawPool.length > 0 && swipes.length > 0) {
      const useIds = new Set(swipes.filter((s) => s.action === 'use').map((s) => s.trend_id));
      setSavedAudios((prev) => {
        const existingIds = new Set(prev.map((p) => p.id));
        const fromPool = rawPool.filter((c) => useIds.has(c.id) && !existingIds.has(c.id));
        if (fromPool.length === 0) return prev;
        return [...prev, ...fromPool];
      });
    }
  }, [rawPool, swipes]);

  // Synchronize savedAudios with unified creator workspace (Targeted on Feed & Picks on Deck)
  useEffect(() => {
    let isMounted = true;
    fetchTargetedTrends()
      .then((targeted) => {
        if (!isMounted || !Array.isArray(targeted) || targeted.length === 0) return;
        const converted = targeted.map(toDeckTrend);
        setSavedAudios((prev) => {
          const existingIds = new Set(prev.map((p) => p.id));
          const toAdd = converted.filter((c) => !existingIds.has(c.id));
          if (toAdd.length === 0) return prev;
          return [...prev, ...toAdd];
        });
        // Also register targeted audios into swipes with action 'use'
        setSwipes((prev) => {
          const swipedIds = new Set(prev.map((s) => s.trend_id));
          const newSwipes = converted
            .filter((c) => !swipedIds.has(c.id))
            .map((c) => ({
              trend_id: c.id,
              action: 'use' as const,
              updated_at: new Date().toISOString(),
              niche: c.niche,
              language: c.language,
              artist: c.audio_artist,
              audio_id: c.audio_id,
              audio_title: c.audio_title,
            }));
          if (newSwipes.length === 0) return prev;
          return [...prev, ...newSwipes];
        });
      })
      .catch(() => {});

    // Listen to cross-component workspace updates (e.g. when targeted on Feed)
    const onWorkspaceUpdate = () => {
      fetchTargetedTrends()
        .then((targeted) => {
          if (!isMounted || !Array.isArray(targeted)) return;
          setSavedAudios(targeted.map(toDeckTrend));
        })
        .catch(() => {});
    };
    window.addEventListener('trendrop:workspace_updated', onWorkspaceUpdate);

    return () => {
      isMounted = false;
      window.removeEventListener('trendrop:workspace_updated', onWorkspaceUpdate);
    };
  }, []);

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
        audio_id: currentCard.audio_id,
        audio_title: currentCard.audio_title,
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

      // If 'use', add to saved audios & unified workspace (Targeted)
      if (action === 'use') {
        saveAudioToWorkspace(currentCard);
        setSavedAudios((prev) => [currentCard, ...prev.filter((c) => c.id !== currentCard.id)]);
        queryClient.invalidateQueries({ queryKey: ["trends-targeted"] });

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

  // Unswiped count remaining in rawPool
  const remainingCandidatesCount = useMemo(() => {
    const swipedIds = new Set(swipes.map((s) => s.trend_id));
    const swipedAudios = new Set(swipes.map((s) => s.audio_id).filter(Boolean));
    return rawPool.filter((c) => !swipedIds.has(c.id) && !(c.audio_id && swipedAudios.has(c.audio_id))).length;
  }, [rawPool, swipes]);

  // Deal Next 15 Candidates with continuous batching & bulletproof redeal
  const handleDealMore = useCallback(async () => {
    setIsDealingMore(true);
    try {
      // 1. Keep saved audios ('use'), clear passed skips so catalog loops seamlessly
      let activeSwipes = swipes.filter((s) => s.action === 'use');
      setSwipes(activeSwipes);
      if (typeof window !== 'undefined') {
        localStorage.setItem('trendrop_local_swipes', JSON.stringify(activeSwipes));
      }

      // 2. Fetch fresh pool from backend
      let poolToUse = rawPool;
      try {
        const params = new URLSearchParams({
          mode,
          limit: '120',
          fresh: 'true',
          _t: Date.now().toString(),
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
        const res = await fetch(`${API_URL}/api/deck?${params.toString()}`, {
          headers: { 'Cache-Control': 'no-cache, no-store', 'Pragma': 'no-cache' },
        });
        if (res.ok) {
          const data = await res.json();
          const freshTrends: DeckTrend[] = data.trends || [];
          if (freshTrends.length > 0) {
            setRawPool(freshTrends);
            poolToUse = freshTrends;
          }
        }
      } catch (fetchErr) {
        console.warn('Could not replenish deck pool:', fetchErr);
      }

      // 3. Rank deck from poolToUse
      let nextRanked = rankDeck(poolToUse, activeSwipes, 15);
      if (nextRanked.length === 0 && poolToUse.length > 0) {
        nextRanked = rankDeck(poolToUse, [], 15);
      }

      if (nextRanked.length > 0) {
        setDeck(nextRanked);
        setCurrentIndex(0);
        setBatchCount((prev) => prev + 1);
        toast.success(`Redealt catalog with ${nextRanked.length} trending audios`);
      } else {
        toast.error('No trending audios found');
      }
    } finally {
      setIsDealingMore(false);
    }
  }, [rawPool, swipes, mode, selectedLanguages, selectedNiches, includeExpiredDeck]);

  // Re-shuffle passed tracks (keeps saved audios safe, resets skips)
  const handleReshufflePassed = useCallback(() => {
    const keptSwipes = swipes.filter((s) => s.action === 'use');
    setSwipes(keptSwipes);
    if (typeof window !== 'undefined') {
      localStorage.setItem('trendrop_local_swipes', JSON.stringify(keptSwipes));
    }
    let freshRanked = rankDeck(rawPool, keptSwipes, 15);
    if (freshRanked.length === 0 && rawPool.length > 0) {
      freshRanked = rankDeck(rawPool, [], 15);
    }
    if (freshRanked.length > 0) {
      setDeck(freshRanked);
      setCurrentIndex(0);
      setBatchCount((prev) => prev + 1);
      toast.success('Catalog reshuffled with fresh priority');
    }
  }, [rawPool, swipes]);

  return (
    <div
      className="flex flex-col w-full h-[calc(100dvh-4.5rem)] max-h-[calc(100dvh-4.5rem)] md:h-[100dvh] md:max-h-[100dvh] overflow-hidden font-sans select-none relative bg-background text-foreground"
    >
      {/* Animated background */}
      <VinylBackground />

      {/* Top Header Bar */}
      <header
        className="flex flex-col gap-2 px-3 sm:px-4 pt-2.5 pb-2 border-b border-border/40 z-40 sticky top-0 bg-background/85 backdrop-blur-xl"
      >
        {/* Top Controls Row */}
        <div className="flex items-center justify-between w-full min-w-0 gap-2">
          {/* Left: Mode Switcher & Niche Filter & Guide */}
          <div className="flex items-center gap-1.5 min-w-0 shrink">
            <button
              onClick={() => handleSwitchMode(mode === 'india' ? 'global' : 'india')}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-full text-xs font-semibold shrink-0 transition-all active:scale-95 cursor-pointer shadow-xs"
              style={{
                background: '#FF4D3D',
                color: '#fff',
                border: 'none',
                boxShadow: '0 2px 8px rgba(255,77,61,0.3)',
              }}
              title={`Switch to ${mode === 'india' ? 'Global' : 'India'} trends`}
            >
              <span>{mode === 'india' ? '🇮🇳 India' : '🌍 Global'}</span>
            </button>

            <button
              onClick={() => setIsOnboardingOpen(true)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-full text-xs transition-all active:scale-95 shrink min-w-0 cursor-pointer"
              style={{
                background: 'rgba(255,77,61,0.08)',
                border: '1px solid rgba(255,77,61,0.2)',
                color: '#FF4D3D',
              }}
              title="Filter by niche"
            >
              <span className="truncate max-w-[76px] sm:max-w-[120px] font-medium">
                {selectedNiches.length > 0 ? selectedNiches.join(', ') : 'All Niches'}
              </span>
              <ChevronDown className="w-3 h-3 shrink-0" />
            </button>

            {/* Guide Button */}
            <button
              onClick={() => setIsOnboardingOpen(true)}
              className="flex items-center gap-1 px-2 py-1.5 rounded-full text-xs transition-all active:scale-95 shrink-0 cursor-pointer"
              style={{
                background: 'rgba(255,77,61,0.08)',
                border: '1px solid rgba(255,77,61,0.22)',
                color: '#FF4D3D',
              }}
              title="Deck Walkthrough & Guide"
              aria-label="Deck Walkthrough & Guide"
            >
              <HelpCircle className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Guide</span>
            </button>
          </div>

          {/* Right: Sync & Progress */}
          {activeTab === 'deck' && (
            <div className="flex items-center gap-1.5 shrink-0">
              <button
                onClick={handleRefreshDeckFromStart}
                disabled={isRefreshing}
                title="Sync latest live breakout audios"
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-full text-xs font-semibold transition-all active:scale-95 bg-background border border-[#FF4D3D]/30 text-[#FF4D3D] hover:bg-[#FF4D3D]/10 shadow-xs cursor-pointer shrink-0"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                <span>Sync</span>
              </button>
              <span
                className="text-xs font-mono font-medium px-2 py-1 rounded-full shrink-0"
                style={{ background: 'rgba(255,77,61,0.08)', color: '#FF4D3D', border: '1px solid rgba(255,77,61,0.15)' }}
              >
                {Math.min(currentIndex + 1, deck.length || 15)}/{deck.length || 15}
              </span>
            </div>
          )}
        </div>

        {/* Sub-view Switcher & Expired Chip Row */}
        <div className="flex items-center justify-between gap-2 max-w-sm mx-auto w-full">
          <div
            className="flex-1 flex items-center justify-center p-1 rounded-full"
            style={{ background: 'var(--surface-2)', border: '1px solid var(--border)' }}
          >
            <button
              onClick={() => setActiveTab('deck')}
              className="flex-1 py-1.5 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-1 cursor-pointer"
              style={activeTab === 'deck'
                ? { background: '#FF4D3D', color: '#fff', boxShadow: '0 2px 8px rgba(255,77,61,0.35)' }
                : { color: '#9A9AA8' }
              }
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Deck</span>
            </button>
            <button
              onClick={() => navigate({ to: '/', search: { tab: 'feed' } as any })}
              className="flex-1 py-1.5 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-1 active:scale-95 cursor-pointer"
              style={{ color: '#9A9AA8' }}
            >
              <Compass className="w-3.5 h-3.5" />
              <span>Feed</span>
            </button>
            <button
              onClick={() => setActiveTab('picks')}
              className="flex-1 py-1.5 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-1 relative cursor-pointer"
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

          {activeTab === 'deck' && (
            <button
              onClick={() => setIncludeExpiredDeck((prev) => !prev)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-full text-[11px] transition-all active:scale-95 shrink-0 cursor-pointer"
              style={{
                background: includeExpiredDeck ? 'rgba(100,116,139,0.18)' : 'rgba(0,0,0,0.05)',
                border: `1px solid ${includeExpiredDeck ? 'rgba(100,116,139,0.35)' : 'rgba(0,0,0,0.08)'}`,
                color: includeExpiredDeck ? '#334155' : '#9A9AA8',
                fontWeight: includeExpiredDeck ? 700 : 500,
              }}
              title="Toggle including expired tracks in deck"
            >
              <span>{includeExpiredDeck ? '⛔ +Expired' : 'Active'}</span>
            </button>
          )}
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
            // Milestone Celebration Card with 1-Tap Deal More & Session Recap
            <MilestoneRecapCard
              batchCount={batchCount}
              sessionSwipesCount={swipes.length}
              savedAudios={savedAudios}
              streakDays={streakDays}
              freshnessMinutes={freshnessMinutes}
              remainingCandidatesCount={remainingCandidatesCount}
              onDealMore={handleDealMore}
              onViewPicks={() => setActiveTab('picks')}
              onGoToFeed={() => navigate({ to: '/', search: { tab: 'feed' } as any })}
              onReshufflePassed={handleReshufflePassed}
              onSelectTrend={(t) => setSelectedVinyl(t)}
              isLoadingMore={isDealingMore}
            />
          ) : (
            // Vinyl stack + action buttons
            <div className="w-full max-w-[390px] flex flex-col items-center h-full justify-between py-1">
              {/* Single Vinyl Showcase (one at a time) */}
              <div className="w-full flex-1 min-h-0 relative flex items-center justify-center">
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
              <div className="w-full shrink-0 flex items-center justify-center gap-4 py-2 sm:py-3 px-2">
                {/* Undo */}
                <button
                  onClick={handleUndo}
                  disabled={currentIndex === 0}
                  className="w-11 h-11 sm:w-12 sm:h-12 rounded-full flex items-center justify-center disabled:opacity-30 disabled:pointer-events-none active:scale-90 transition-all"
                  style={{ background: 'rgba(0,0,0,0.06)', border: '1px solid rgba(0,0,0,0.08)', color: '#9A9AA8' }}
                  aria-label="Undo"
                >
                  <RotateCcw className="w-4 h-4 sm:w-5 sm:h-5" />
                </button>

                {/* Pass (down) */}
                <button
                  onClick={() => handleSwipe('skip')}
                  className="w-13 h-13 sm:w-16 sm:h-16 shrink-0 rounded-full flex items-center justify-center active:scale-90 transition-all"
                  style={{
                    background: 'rgba(255,77,61,0.08)',
                    border: '1.5px solid rgba(255,77,61,0.25)',
                    color: '#FF4D3D',
                  }}
                  aria-label="Pass (flick down)"
                >
                  <X className="w-6 h-6 sm:w-7 sm:h-7" />
                </button>

                {/* Use It (up) */}
                <button
                  onClick={() => handleSwipe('use')}
                  className="w-13 h-13 sm:w-16 sm:h-16 shrink-0 rounded-full text-white flex items-center justify-center active:scale-90 transition-all"
                  style={{
                    background: '#FF4D3D',
                    boxShadow: '0 6px 20px rgba(255,77,61,0.4)',
                  }}
                  aria-label="Use It (flick up)"
                >
                  <Check className="w-6 h-6 sm:w-8 sm:h-8 stroke-[3]" />
                </button>
              </div>

              {/* Swipe hint label */}
              <p className="text-[10px] sm:text-[11px] shrink-0 pb-1" style={{ color: '#C7A09A', fontFamily: 'Inter, sans-serif' }}>
                Flick up to use · Flick down to pass · Tap to open
              </p>
            </div>
          )
        ) : (
          <DeckPicks
            savedAudios={savedAudios}
            swipes={swipes}
            onRemove={(id) => {
              removeAudioFromWorkspace(id);
              setSavedAudios((prev) => prev.filter((a) => a.id !== id));
              setSwipes((prev) => prev.filter((s) => s.trend_id !== id));
              queryClient.invalidateQueries({ queryKey: ["trends-targeted"] });
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
          if (typeof window !== 'undefined') {
            localStorage.setItem('trendrop_deck_onboarded', 'true');
          }
          setIsOnboardingOpen(false);
        }}
        onClose={() => {
          if (typeof window !== 'undefined') {
            localStorage.setItem('trendrop_deck_onboarded', 'true');
          }
          setIsOnboardingOpen(false);
        }}
        initialMode={mode}
        initialLanguages={selectedLanguages}
        initialNiches={selectedNiches}
      />
    </div>
  );
}
