/**
 * Learning Engine v1 (Order 81 Phase 3)
 * Tracks user taste profile (niches, languages, mood) from swipes with 14-day half-life.
 * Personal multiplier bounded [0.6, 1.4] with ~20% exploration.
 */

export interface UserTasteProfile {
  niches: Record<string, number>;
  languages: Record<string, number>;
  updatedAt: number;
}

const STORAGE_KEY = "trendrop_user_taste_v1";
const HALF_LIFE_MS = 14 * 24 * 60 * 60 * 1000; // 14 days

export function getLocalUserTaste(): UserTasteProfile {
  if (typeof window === "undefined") {
    return { niches: {}, languages: {}, updatedAt: Date.now() };
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { niches: {}, languages: {}, updatedAt: Date.now() };
    const parsed = JSON.parse(raw);
    return applyDecay(parsed);
  } catch {
    return { niches: {}, languages: {}, updatedAt: Date.now() };
  }
}

function applyDecay(profile: UserTasteProfile): UserTasteProfile {
  const now = Date.now();
  const elapsed = now - (profile.updatedAt || now);
  if (elapsed <= 0) return profile;

  // Exponential decay factor: e^(-ln(2) * elapsed / half_life)
  const factor = Math.pow(0.5, elapsed / HALF_LIFE_MS);
  const newNiches: Record<string, number> = {};
  const newLangs: Record<string, number> = {};

  for (const [k, v] of Object.entries(profile.niches || {})) {
    const decayed = v * factor;
    if (Math.abs(decayed) > 0.05) newNiches[k] = decayed;
  }
  for (const [k, v] of Object.entries(profile.languages || {})) {
    const decayed = v * factor;
    if (Math.abs(decayed) > 0.05) newLangs[k] = decayed;
  }

  return {
    niches: newNiches,
    languages: newLangs,
    updatedAt: now,
  };
}

export function recordSwipe(action: "like" | "skip" | "save", trend: { niche?: string; language?: string; category?: string }): UserTasteProfile {
  const profile = getLocalUserTaste();
  const weight = action === "save" ? 1.0 : action === "like" ? 0.6 : -0.5;

  const niche = (trend.niche || trend.category || "").toLowerCase().trim();
  if (niche && niche !== "all" && niche !== "viral") {
    profile.niches[niche] = (profile.niches[niche] || 0) + weight;
  }

  const lang = (trend.language || "").toLowerCase().trim();
  if (lang && lang !== "all") {
    profile.languages[lang] = (profile.languages[lang] || 0) + weight;
  }

  profile.updatedAt = Date.now();
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
  }
  return profile;
}

/**
 * Calculates a personal taste multiplier for a candidate trend bounded in [0.6, 1.4].
 * 20% exploration factor allows serendipitous discovery.
 */
export function getPersonalScoreMultiplier(trend: { niche?: string; language?: string; category?: string }): number {
  // ~20% exploration: return neutral 1.0
  if (Math.random() < 0.2) {
    return 1.0;
  }

  const profile = getLocalUserTaste();
  let score = 0;

  const niche = (trend.niche || trend.category || "").toLowerCase().trim();
  if (niche && profile.niches[niche]) {
    score += profile.niches[niche];
  }

  const lang = (trend.language || "").toLowerCase().trim();
  if (lang && profile.languages[lang]) {
    score += profile.languages[lang] * 0.5;
  }

  // Bound to [0.6, 1.4]
  const multiplier = 1.0 + Math.tanh(score) * 0.4;
  return Math.max(0.6, Math.min(1.4, multiplier));
}
