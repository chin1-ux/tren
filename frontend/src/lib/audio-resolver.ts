/**
 * Audio Resolver Service
 * 
 * Provides fast, zero-server-cost resolution for trending audio previews.
 * Uses official Apple Music / iTunes Search CDN preview endpoints with in-memory + local storage caching.
 * Resolves viral drop segments and handles original/custom audio fallbacks.
 */

export interface ResolvedAudio {
  previewUrl: string | null;
  title: string;
  artist: string;
  coverUrl: string | null;
  sourceType: "catalog" | "original" | "stream";
  viralStartSec: number;
  viralDurationSec: number;
  durationSec: number;
  externalUrl?: string | null;
}

// In-memory runtime cache
const memoryCache = new Map<string, ResolvedAudio>();

// Storage cache key
const CACHE_STORAGE_KEY = "trendrop_resolved_audio_cache_v2";

/**
 * Check if a URL is an actual audio stream file (m4a, mp3, aac) and NOT an HTML page
 */
export function isAudioStreamUrl(url?: string | null): boolean {
  if (!url || typeof url !== "string") return false;
  const u = url.toLowerCase();
  // Reject web pages
  if (
    u.includes("instagram.com/reels/audio") ||
    u.includes("instagram.com/explore") ||
    u.includes("instagram.com/p/") ||
    u.includes("instagram.com/reel/")
  ) {
    return false;
  }
  return (
    u.endsWith(".m4a") ||
    u.endsWith(".mp3") ||
    u.endsWith(".aac") ||
    u.endsWith(".ogg") ||
    u.includes("audio-ssl.itunes.apple.com") ||
    u.includes("mzstatic.com") ||
    u.includes(".cdninstagram.com")
  );
}

/**
 * Load persisted audio resolutions from localStorage
 */
function getStorageCache(): Record<string, ResolvedAudio> {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(CACHE_STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

/**
 * Save audio resolution to localStorage
 */
function saveToStorageCache(key: string, data: ResolvedAudio) {
  if (typeof window === "undefined") return;
  try {
    const cache = getStorageCache();
    cache[key] = data;
    // Cap cache at 200 tracks to preserve storage space
    const keys = Object.keys(cache);
    if (keys.length > 200) {
      delete cache[keys[0]];
    }
    localStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(cache));
  } catch {
    // Ignore storage quota or disabled errors
  }
}

/**
 * Clean and normalize song titles to maximize search hit rate on music catalogs.
 * Strips out tags like (From "..."), [Official Music Video], (feat. ...), [Slowed], etc.
 */
export function cleanMusicQuery(title: string, artist?: string): { cleanTitle: string; cleanArtist: string; fullQuery: string } {
  let cleanTitle = (title || "")
    // Remove (feat. ...), [feat. ...], (ft. ...)
    .replace(/\s*[\(\[](feat\.|ft\.|featuring).*?[\)\]]/gi, "")
    // Remove movie/album references like (From "Bad Newz"), (From the Movie ...)
    .replace(/\s*[\(\[](from|soundtrack|ost|audio).*?[\)\]]/gi, "")
    // Remove video/reverb modifiers like [Official Video], (Slowed + Reverb)
    .replace(/\s*[\(\[](official|video|music video|lyric|lyrics|slowed|reverb|remix|version).*?[\)\]]/gi, "")
    // Remove extra punctuation
    .replace(/[—–\-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  let cleanArtist = (artist || "")
    .replace(/\s*[\(\[](feat\.|ft\.|featuring).*?[\)\]]/gi, "")
    .replace(/\s*,\s*.*$/, "") // Pick first artist if comma-separated
    .replace(/\s*&\s*.*$/, "") // Pick first artist before &
    .replace(/\s+/g, " ")
    .trim();

  // If artist is unknown or generic placeholder, ignore artist
  if (!cleanArtist || cleanArtist.toLowerCase().includes("unknown") || cleanArtist.toLowerCase().includes("original audio")) {
    cleanArtist = "";
  }

  const fullQuery = cleanArtist ? `${cleanTitle} ${cleanArtist}`.trim() : cleanTitle;
  return { cleanTitle, cleanArtist, fullQuery };
}

/**
 * Check if the audio is an original creator audio (dialogue, skit, voiceover)
 */
export function isOriginalCreatorAudio(title?: string, artist?: string): boolean {
  const t = (title || "").toLowerCase();
  const a = (artist || "").toLowerCase();
  return (
    t.includes("original audio") ||
    a.includes("original audio") ||
    t.includes("original sound") ||
    a.includes("original sound")
  );
}

/**
 * Helper to fetch and parse from iTunes Search API
 */
async function fetchItunes(query: string, country?: string): Promise<any | null> {
  const countryParam = country ? `&country=${country}` : "";
  const itunesUrl = `https://itunes.apple.com/search?term=${encodeURIComponent(query)}&entity=song&limit=1${countryParam}`;
  const res = await fetch(itunesUrl, { mode: "cors" });
  if (!res.ok) return null;
  const data = await res.json();
  if (data.results && data.results.length > 0 && data.results[0].previewUrl) {
    return data.results[0];
  }
  return null;
}

/**
 * Resolve audio playback source using iTunes Search API.
 * High-speed Akamai CDN delivery, zero authentication required, fully licensed 30s clips.
 */
export async function resolveAudioTrack(params: {
  id: string | number;
  song: string;
  artist: string;
  audioId?: string | null;
  previewUrl?: string | null;
  offsetMs?: number | null;
}): Promise<ResolvedAudio> {
  const cacheKey = `${params.song}:::${params.artist}`.toLowerCase().trim();

  // 1. Check in-memory cache
  if (memoryCache.has(cacheKey)) {
    return memoryCache.get(cacheKey)!;
  }

  // 2. Check localStorage cache
  const storageCache = getStorageCache();
  if (storageCache[cacheKey]) {
    const cached = storageCache[cacheKey];
    memoryCache.set(cacheKey, cached);
    return cached;
  }

  // 3. If direct preview URL was already provided and is a VALID AUDIO STREAM (not a webpage)
  if (isAudioStreamUrl(params.previewUrl)) {
    const viralStartSec = params.offsetMs ? Math.floor(params.offsetMs / 1000) : 0;
    const resolved: ResolvedAudio = {
      previewUrl: params.previewUrl!,
      title: params.song,
      artist: params.artist,
      coverUrl: null,
      sourceType: "catalog",
      viralStartSec,
      viralDurationSec: 15,
      durationSec: 30,
      externalUrl: params.audioId ? `https://www.instagram.com/reels/audio/${params.audioId}/` : null,
    };
    memoryCache.set(cacheKey, resolved);
    saveToStorageCache(cacheKey, resolved);
    return resolved;
  }

  // 4. If it's an original audio (creator skit/voiceover)
  if (isOriginalCreatorAudio(params.song, params.artist)) {
    const originalResolved: ResolvedAudio = {
      previewUrl: null,
      title: params.song || "Original Audio",
      artist: params.artist || "Instagram Creator",
      coverUrl: null,
      sourceType: "original",
      viralStartSec: 0,
      viralDurationSec: 15,
      durationSec: 15,
      externalUrl: params.audioId ? `https://www.instagram.com/reels/audio/${params.audioId}/` : null,
    };
    memoryCache.set(cacheKey, originalResolved);
    return originalResolved;
  }

  // 5. Query Apple Music / iTunes Search API with multi-step fallback
  const { cleanTitle, cleanArtist, fullQuery } = cleanMusicQuery(params.song, params.artist);

  try {
    // Step 5A: Try full query in India store
    let match = await fetchItunes(fullQuery, "IN");

    // Step 5B: If no hit and artist was present, try title alone in India store
    if (!match && cleanTitle) {
      match = await fetchItunes(cleanTitle, "IN");
    }

    // Step 5C: Try global iTunes store
    if (!match) {
      match = await fetchItunes(fullQuery);
    }

    // Step 5D: Try title alone in global store
    if (!match && cleanTitle) {
      match = await fetchItunes(cleanTitle);
    }

    if (match) {
      const resolved: ResolvedAudio = {
        previewUrl: match.previewUrl || null,
        title: match.trackName || params.song,
        artist: match.artistName || params.artist,
        coverUrl: match.artworkUrl100 ? match.artworkUrl100.replace("100x100bb.jpg", "300x300bb.jpg") : null,
        sourceType: "catalog",
        viralStartSec: 0,
        viralDurationSec: 15,
        durationSec: 30,
        externalUrl: match.trackViewUrl || (params.audioId ? `https://www.instagram.com/reels/audio/${params.audioId}/` : null),
      };

      memoryCache.set(cacheKey, resolved);
      saveToStorageCache(cacheKey, resolved);
      return resolved;
    }
  } catch (err) {
    console.warn(`[audio-resolver] Failed to resolve "${fullQuery}":`, err);
  }

  // Fallback: unresolved
  const fallbackResolved: ResolvedAudio = {
    previewUrl: null,
    title: params.song,
    artist: params.artist,
    coverUrl: null,
    sourceType: "catalog",
    viralStartSec: 0,
    viralDurationSec: 15,
    durationSec: 30,
    externalUrl: params.audioId ? `https://www.instagram.com/reels/audio/${params.audioId}/` : null,
  };

  memoryCache.set(cacheKey, fallbackResolved);
  return fallbackResolved;
}
