import { toggleTrendTarget, fetchTargetedTrends, type UiTrend } from './api';
import { type DeckTrend, type UserSwipe } from './deck-ranking';

export const TARGETED_STORAGE_KEY = 'trendrop_saved_targets';
export const LOCAL_SWIPES_KEY = 'trendrop_local_swipes';

/**
 * Normalizes any trend (UiTrend, DeckTrend, or DB row) into a DeckTrend
 */
export function toDeckTrend(t: any): DeckTrend {
  return {
    id: typeof t.id === 'string' ? parseInt(t.id, 10) || 0 : Number(t.id) || 0,
    audio_id: t.audioId || t.audio_id || null,
    audio_title: t.audio_title || t.song || 'Trending Audio',
    audio_artist: t.audio_artist || t.artist || 'Original Audio',
    status: (t.status || 'emerging').toLowerCase(),
    stage_label: (t.status || 'emerging').toUpperCase(),
    first_detected_at: t.firstDetectedAt || t.first_detected_at || null,
    last_seen_at: t.lastSeenAt || t.last_seen_at || null,
    creator_count: t.creatorCount || t.creator_count || 0,
    reel_count: t.reelCount || t.reel_count || 0,
    audio_use_count: t.audioUseCount || t.audio_use_count || 0,
    language: t.language || 'en',
    niche: t.niche || null,
    used_for: t.used_for || null,
    used_for_note: t.used_for_note || null,
    why_this_works: t.why_this_works || null,
    ideal_content_description: t.ideal_content_description || null,
    hook_brief: t.hook_brief || null,
  };
}

/**
 * Normalizes any trend into a UiTrend for the Feed
 */
export function toUiTrend(t: any): UiTrend {
  return {
    id: String(t.id),
    song: t.audio_title || t.song || 'Trending Audio',
    artist: t.audio_artist || t.artist || 'Original Audio',
    audioId: t.audioId || t.audio_id || null,
    status: (t.status || 'emerging').toLowerCase(),
    niche: t.niche || null,
    language: t.language || 'en',
    creatorCount: t.creatorCount || t.creator_count || 0,
    reelCount: t.reelCount || t.reel_count || 0,
    audioUseCount: t.audioUseCount || t.audio_use_count || 0,
    used_for: t.used_for || null,
    used_for_note: t.used_for_note || null,
    why_this_works: t.why_this_works || null,
    ideal_content_description: t.ideal_content_description || null,
    firstDetectedAt: t.firstDetectedAt || t.first_detected_at || null,
    lastSeenAt: t.lastSeenAt || t.last_seen_at || null,
    saturationScore: t.saturationScore || 0,
    opportunityScore: t.opportunityScore || t.score || 0,
    contentType: t.contentType || t.content_type || 'Reel Audio',
    windowHoursRemaining: t.windowHoursRemaining || 48,
    velocityAvg: t.velocityAvg || 0,
  } as UiTrend;
}

/**
 * Retrieves all locally saved targets
 */
export function getLocalTargeted(): DeckTrend[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(TARGETED_STORAGE_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr.map(toDeckTrend) : [];
  } catch {
    return [];
  }
}

/**
 * Saves an audio to the unified creator workspace (Targeted on Feed & Picks on Deck)
 */
export async function saveAudioToWorkspace(trend: DeckTrend | UiTrend | any): Promise<void> {
  if (!trend) return;
  const numId = typeof trend.id === 'string' ? parseInt(trend.id, 10) || 0 : Number(trend.id) || 0;
  const idStr = String(trend.id);

  // 1. Save to local targets storage
  if (typeof window !== 'undefined') {
    try {
      const current = getLocalTargeted();
      if (!current.some((t) => String(t.id) === idStr)) {
        const deckForm = toDeckTrend(trend);
        const updated = [deckForm, ...current].slice(0, 300);
        localStorage.setItem(TARGETED_STORAGE_KEY, JSON.stringify(updated));
      }

      // Also ensure it is recorded as a 'use' swipe in local swipes for taste learning & deck exclusion
      const rawSwipes = localStorage.getItem(LOCAL_SWIPES_KEY);
      const swipes: UserSwipe[] = rawSwipes ? JSON.parse(rawSwipes) : [];
      if (!swipes.some((s) => s.trend_id === numId && s.action === 'use')) {
        const newSwipe: UserSwipe = {
          trend_id: numId,
          action: 'use',
          updated_at: new Date().toISOString(),
          niche: trend.niche,
          language: trend.language,
          artist: trend.audio_artist || trend.artist,
          audio_id: trend.audio_id || trend.audioId,
          audio_title: trend.audio_title || trend.song,
        };
        const updatedSwipes = [newSwipe, ...swipes.filter((s) => s.trend_id !== numId)].slice(0, 500);
        localStorage.setItem(LOCAL_SWIPES_KEY, JSON.stringify(updatedSwipes));
      }

      window.dispatchEvent(new CustomEvent('trendrop:workspace_updated', { detail: { trendId: numId, action: 'target' } }));
    } catch (e) {
      console.warn('Could not save to local workspace:', e);
    }
  }

  // 2. Sync to server backend
  try {
    await toggleTrendTarget(numId, 'target');
  } catch (err) {
    // Guest or offline: safe in local storage
  }
}

/**
 * Removes an audio from the unified creator workspace (Untargeted from Feed & removed from Picks)
 */
export async function removeAudioFromWorkspace(trendId: number | string): Promise<void> {
  const numId = typeof trendId === 'string' ? parseInt(trendId, 10) || 0 : Number(trendId) || 0;
  const idStr = String(trendId);

  // 1. Remove from local storage
  if (typeof window !== 'undefined') {
    try {
      const current = getLocalTargeted();
      const updated = current.filter((t) => String(t.id) !== idStr);
      localStorage.setItem(TARGETED_STORAGE_KEY, JSON.stringify(updated));

      // Remove from local swipes
      const rawSwipes = localStorage.getItem(LOCAL_SWIPES_KEY);
      const swipes: UserSwipe[] = rawSwipes ? JSON.parse(rawSwipes) : [];
      const updatedSwipes = swipes.filter((s) => s.trend_id !== numId);
      localStorage.setItem(LOCAL_SWIPES_KEY, JSON.stringify(updatedSwipes));

      window.dispatchEvent(new CustomEvent('trendrop:workspace_updated', { detail: { trendId: numId, action: 'untarget' } }));
    } catch (e) {
      console.warn('Could not remove from local workspace:', e);
    }
  }

  // 2. Sync to server backend
  try {
    await toggleTrendTarget(numId, 'untarget');
  } catch (err) {
    // Guest or offline: safe in local storage
  }
}
