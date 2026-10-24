/**
 * Client-side Deck Ranking & Taste Learning (Order 100 Section D)
 * Deterministic ranking with no ML dependencies.
 */

export interface DeckTrend {
  id: number;
  audio_id?: string | null;
  audio_title: string;
  audio_artist: string;
  status: string;
  stage_label: string;
  first_detected_at: string | null;
  last_seen_at?: string | null;
  age_hours?: number;
  is_new_today?: boolean;
  creator_count: number;
  reel_count: number;
  audio_use_count: number;
  language: string;
  niche: string | null;
  used_for?: string | null;
  used_for_note?: string | null;
  why_this_works?: string | null;
  ideal_content_description?: string | null;
  hook_brief?: string | null;
  optimal_post_hour_ist?: number | null;
  score?: number;
  is_top_5?: boolean;
  is_exploration?: boolean;
}


export interface UserSwipe {
  trend_id: number;
  action: 'use' | 'skip';
  reason?: string | null;
  updated_at: string;
  niche?: string | null;
  language?: string | null;
  artist?: string | null;
  audio_id?: string | null;
  audio_title?: string | null;
}

export interface AffinityProfile {
  nicheLikes: Record<string, number>;
  nicheSkips: Record<string, number>;
  langLikes: Record<string, number>;
  langSkips: Record<string, number>;
  artistLikes: Record<string, number>;
  artistSkips: Record<string, number>;
}

/**
 * Calculates base score from hard facts:
 * base = statusWeight (rising 1.0, emerging 0.9)
 *      x freshness decay (half-life 24h from first_detected_at)
 *      x (1 + ln(1 + creator_count))
 *      x (1 + 0.1 ln(1 + reel_count))
 */
export function calculateBaseScore(trend: DeckTrend, nowMs: number = Date.now()): number {
  const st = (trend.status || '').toLowerCase().trim();
  const isExpired = st === 'expired';
  const statusWeight = st === 'rising' ? 1.0 : st === 'emerging' ? 0.9 : st === 'resurging' ? 0.85 : st === 'peaked' ? 0.8 : 0.75;

  let ageHours = trend.age_hours;
  if (ageHours === undefined || ageHours === null) {
    if (trend.first_detected_at) {
      const dt = new Date(trend.first_detected_at).getTime();
      ageHours = Math.max(0, (nowMs - dt) / (1000 * 3600));
    } else {
      ageHours = 24.0;
    }
  }

  // 24h half-life for active; bounded decay for historical/expired so they remain rankable in filtered pools
  const freshnessDecay = isExpired
    ? Math.max(0.25, Math.pow(0.5, ageHours / (24.0 * 14)))
    : Math.pow(0.5, ageHours / 24.0);

  const creators = Math.max(0, trend.creator_count || 1);
  const reels = Math.max(0, trend.reel_count || 0);

  const creatorFactor = 1.0 + Math.log(1.0 + creators);
  const reelFactor = 1.0 + 0.1 * Math.log(1.0 + reels);

  return statusWeight * freshnessDecay * creatorFactor * reelFactor;
}

/**
 * Build decay-weighted user affinity profile from swipe history.
 * 14-day half life for historical swipes.
 */
export function buildAffinityProfile(swipes: UserSwipe[], nowMs: number = Date.now()): AffinityProfile {
  const profile: AffinityProfile = {
    nicheLikes: {},
    nicheSkips: {},
    langLikes: {},
    langSkips: {},
    artistLikes: {},
    artistSkips: {}
  };

  const msPerDay = 1000 * 3600 * 24;

  for (const s of swipes) {
    const swipeTime = s.updated_at ? new Date(s.updated_at).getTime() : nowMs;
    const ageDays = Math.max(0, (nowMs - swipeTime) / msPerDay);
    // 14-day half-life decay
    const decay = Math.pow(0.5, ageDays / 14.0);

    const isUse = s.action === 'use';
    const reason = (s.reason || '').toLowerCase();

    // Niche weights
    if (s.niche && s.niche.toLowerCase() !== 'other') {
      const k = s.niche.toLowerCase();
      if (isUse) {
        profile.nicheLikes[k] = (profile.nicheLikes[k] || 0) + 1.0 * decay;
      } else {
        const weight = reason.includes('vibe') ? 1.5 : 1.0;
        profile.nicheSkips[k] = (profile.nicheSkips[k] || 0) + weight * decay;
      }
    }

    // Language weights
    if (s.language) {
      const k = s.language.toLowerCase();
      if (isUse) {
        profile.langLikes[k] = (profile.langLikes[k] || 0) + 1.0 * decay;
      } else {
        const weight = reason.includes('language') ? 1.5 : 1.0;
        profile.langSkips[k] = (profile.langSkips[k] || 0) + weight * decay;
      }
    }

    // Artist weights
    if (s.artist) {
      const k = s.artist.toLowerCase();
      if (isUse) {
        profile.artistLikes[k] = (profile.artistLikes[k] || 0) + 1.0 * decay;
      } else {
        profile.artistSkips[k] = (profile.artistSkips[k] || 0) + 1.0 * decay;
      }
    }
  }

  return profile;
}

/**
 * Calculates smoothed user affinity for a trend [0.0, 1.0].
 * Cold start affinity defaults to 0.5.
 */
export function calculateAffinity(trend: DeckTrend, profile: AffinityProfile): number {
  const getSmoothedRatio = (likes: number = 0, skips: number = 0): number => {
    // Bayesian Laplace smoothing: prior = 1 / (1 + 1) = 0.5
    return (likes + 1.0) / (likes + skips + 2.0);
  };

  const nicheKey = trend.niche ? trend.niche.toLowerCase() : null;
  const langKey = trend.language ? trend.language.toLowerCase() : null;
  const artistKey = trend.audio_artist ? trend.audio_artist.toLowerCase() : null;

  const nicheAffinity = nicheKey
    ? getSmoothedRatio(profile.nicheLikes[nicheKey], profile.nicheSkips[nicheKey])
    : 0.5;

  const langAffinity = langKey
    ? getSmoothedRatio(profile.langLikes[langKey], profile.langSkips[langKey])
    : 0.5;

  const artistAffinity = artistKey
    ? getSmoothedRatio(profile.artistLikes[artistKey], profile.artistSkips[artistKey])
    : 0.5;

  // Weighted combination
  return 0.4 * nicheAffinity + 0.4 * langAffinity + 0.2 * artistAffinity;
}

/**
 * Personal multiplier = 0.6 + 0.8 * affinity, bounded to [0.6, 1.4].
 */
export function calculatePersonalMultiplier(affinity: number): number {
  const raw = 0.6 + 0.8 * affinity;
  return Math.min(1.4, Math.max(0.6, raw));
}

/**
 * Rank and select the daily 15-card deck:
 * - 20% exploration share (outside top affinity)
 * - Diversity: no same artist within 5 cards
 * - At most 3 consecutive cards of same language
 * - Never re-show a swiped audio
 * - First 5 labeled "Top 5"
 */
export function rankDeck(
  candidates: DeckTrend[],
  swipes: UserSwipe[] = [],
  deckSize: number = 15,
  nowMs: number = Date.now()
): DeckTrend[] {
  // 1. Exclude already swiped audios by trend_id, audio_id, or normalized title+artist
  const swipedTrendIds = new Set(swipes.map(s => s.trend_id).filter(Boolean));
  const swipedAudioIds = new Set(swipes.map(s => s.audio_id).filter(Boolean));
  const swipedKeys = new Set(
    swipes
      .map(s => `${(s.audio_title || '').toLowerCase().trim()}|${(s.artist || '').toLowerCase().trim()}`)
      .filter(k => k !== '|')
  );

  const unswiped = candidates.filter(c => {
    if (swipedTrendIds.has(c.id)) return false;
    if (c.audio_id && swipedAudioIds.has(c.audio_id)) return false;
    const key = `${(c.audio_title || '').toLowerCase().trim()}|${(c.audio_artist || '').toLowerCase().trim()}`;
    if (key !== '|' && swipedKeys.has(key)) return false;
    return true;
  });

  if (unswiped.length === 0) {
    return [];
  }

  // 2. Build user taste profile
  const profile = buildAffinityProfile(swipes, nowMs);

  // 3. Score all candidates
  const scored = unswiped.map(item => {
    const base = calculateBaseScore(item, nowMs);
    const affinity = calculateAffinity(item, profile);
    const multiplier = calculatePersonalMultiplier(affinity);
    const finalScore = base * multiplier;
    return {
      ...item,
      score: finalScore,
      _affinity: affinity
    };
  });

  // Sort descending: strictly NEWEST to OLDEST (discovery date / creation date, fallback to id desc)
  scored.sort((a, b) => {
    const timeA = Math.max(
      a.first_detected_at ? new Date(a.first_detected_at).getTime() : 0,
      (a as any).created_at ? new Date((a as any).created_at).getTime() : 0
    );
    const timeB = Math.max(
      b.first_detected_at ? new Date(b.first_detected_at).getTime() : 0,
      (b as any).created_at ? new Date((b as any).created_at).getTime() : 0
    );
    if (timeB !== timeA) {
      return timeB - timeA;
    }
    if ((b.id || 0) !== (a.id || 0)) {
      return (b.id || 0) - (a.id || 0);
    }
    return (b.score || 0) - (a.score || 0);
  });

  // Exploration partition: 20% of deckSize (e.g. 3 cards in a 15-card deck)
  const exploreTargetCount = Math.floor(deckSize * 0.20);
  const exploitedTargetCount = deckSize - exploreTargetCount;

  // Split into high-affinity pool and exploration pool
  const topAffinityThreshold = 0.52; // slightly above neutral cold-start
  const exploitedPool = scored.filter(s => s._affinity >= topAffinityThreshold);
  const explorationPool = scored.filter(s => s._affinity < topAffinityThreshold);

  // Fallbacks if one pool is depleted
  const primaryPool = exploitedPool.length >= exploitedTargetCount ? exploitedPool : scored;
  const secondaryPool = explorationPool.length >= exploreTargetCount ? explorationPool : scored;

  const result: DeckTrend[] = [];
  const usedIds = new Set<number>();

  const isCardDiverse = (card: DeckTrend, currentDeck: DeckTrend[]): boolean => {
    // No same artist within 5 cards
    const artist = (card.audio_artist || '').toLowerCase().trim();
    if (artist) {
      const recent5 = currentDeck.slice(-5);
      for (const r of recent5) {
        if ((r.audio_artist || '').toLowerCase().trim() === artist) {
          return false;
        }
      }
    }

    // At most 3 consecutive cards of same language
    const lang = (card.language || '').toLowerCase().trim();
    if (lang && currentDeck.length >= 3) {
      const recent3 = currentDeck.slice(-3);
      const allSame = recent3.every(r => (r.language || '').toLowerCase().trim() === lang);
      if (allSame) {
        return false;
      }
    }

    return true;
  };

  const pickFromPool = (pool: typeof scored, isExploration: boolean = false): boolean => {
    for (const card of pool) {
      if (usedIds.has(card.id)) continue;
      if (isCardDiverse(card, result)) {
        usedIds.add(card.id);
        result.push({
          ...card,
          is_exploration: isExploration
        });
        return true;
      }
    }
    // If strict diversity can't find a match, relax diversity to avoid starving
    for (const card of pool) {
      if (usedIds.has(card.id)) continue;
      usedIds.add(card.id);
      result.push({
        ...card,
        is_exploration: isExploration
      });
      return true;
    }
    return false;
  };

  // Interleave exploited and exploration cards
  for (let i = 0; i < deckSize; i++) {
    // Position 4, 9, 14 as exploration slots (20% share)
    const isExploreSlot = (i % 5 === 4) && (exploreTargetCount > 0);
    if (isExploreSlot && secondaryPool.length > 0) {
      const picked = pickFromPool(secondaryPool, true);
      if (!picked) {
        pickFromPool(primaryPool, false);
      }
    } else {
      const picked = pickFromPool(primaryPool, false);
      if (!picked) {
        pickFromPool(scored, false);
      }
    }
    if (result.length >= deckSize) break;
  }

  // Mark the first 5 cards as "Top 5"
  return result.slice(0, deckSize).map((card, idx) => ({
    ...card,
    is_top_5: idx < 5
  }));
}
