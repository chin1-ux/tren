/**
 * Audio Resolver Service
 * 
 * Provides fast, zero-server-cost resolution for trending audio previews.
 * Uses official Apple Music / iTunes Search CDN preview endpoints with in-memory + local storage caching.
 * Employs Strict Multi-Candidate Fuzzy Verification to prevent incorrect artist/song audio mismatches.
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

import { API_URL } from "./api";

// In-memory runtime cache
const memoryCache = new Map<string, ResolvedAudio>();

// Storage cache key (v7: strictly genuine audio streams, purged all video CDN URLs)
const CACHE_STORAGE_KEY = "trendrop_resolved_audio_cache_v7_clean";

/**
 * Detect expired Instagram CDN URLs by parsing the hexadecimal oe= timestamp
 */
export function isInstagramCdnUrlExpired(url?: string | null): boolean {
  if (!url || typeof url !== "string") return false;
  if (!url.includes(".cdninstagram.com") && !url.includes("fbcdn.net")) return false;
  const match = url.match(/[?&]oe=([0-9a-fA-F]+)/);
  if (!match) return false;
  try {
    const expirySec = parseInt(match[1], 16);
    const nowSec = Math.floor(Date.now() / 1000);
    // Expired or expiring within 60 seconds
    return nowSec >= expirySec - 60;
  } catch {
    return false;
  }
}

/**
 * Check if a URL is an actual audio stream file (m4a, mp3, aac) and NOT an HTML page or Instagram video CDN URL
 */
export function isAudioStreamUrl(url?: string | null): boolean {
  if (!url || typeof url !== "string") return false;
  if (isInstagramCdnUrlExpired(url)) return false;
  const u = url.toLowerCase();
  // Reject web pages and raw Instagram video chunks that 403 on client audio tags
  if (
    u.includes("instagram.com") ||
    u.includes(".cdninstagram.com") ||
    u.includes("fbcdn.net") ||
    u.endsWith(".mp4")
  ) {
    return false;
  }
  return (
    u.endsWith(".m4a") ||
    u.endsWith(".mp3") ||
    u.endsWith(".aac") ||
    u.endsWith(".ogg") ||
    u.includes("audio-ssl.itunes.apple.com") ||
    u.includes("mzstatic.com")
  );
}

/**
 * Load persisted audio resolutions from localStorage
 */
function getStorageCache(): Record<string, ResolvedAudio> {
  if (typeof window === "undefined") return {};
  try {
    // Purge legacy caches that may contain cross-artist mismatches or 403 CDN URLs
    localStorage.removeItem("trendrop_resolved_audio_cache_v1");
    localStorage.removeItem("trendrop_resolved_audio_cache_v2");
    localStorage.removeItem("trendrop_resolved_audio_cache_v3");
    localStorage.removeItem("trendrop_resolved_audio_cache_v4_strict");
    localStorage.removeItem("trendrop_resolved_audio_cache_v6_unexpired");

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
    // Cap cache at 300 tracks to preserve storage space
    const keys = Object.keys(cache);
    if (keys.length > 300) {
      delete cache[keys[0]];
    }
    localStorage.setItem(CACHE_STORAGE_KEY, JSON.stringify(cache));
  } catch {
    // Ignore storage quota or disabled errors
  }
}

/**
 * Clean and normalize text strings for tokenization (strips diacritics e.g. ROSÉ -> rose)
 */
function normalizeString(s?: string | null): string {
  if (!s) return "";
  return s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "") // Strip diacritics / accents: ROSÉ -> ROSE
    .toLowerCase()
    .replace(/[\(\[].*?[\)\]]/g, "") // remove parenthetical content like (feat. ...)
    .replace(/[^a-z0-9\s]/g, " ")     // keep alphanumeric
    .replace(/\s+/g, " ")
    .trim();
}

/**
 * Clean song title and artist for iTunes query string.
 * Preserves artists with commas like "Tyler, The Creator".
 */
export function cleanMusicQuery(title: string, artist?: string): { cleanTitle: string; cleanArtist: string; fullQuery: string } {
  let cleanTitle = (title || "")
    // Remove (feat. ...), [feat. ...], (ft. ...)
    .replace(/\s*[\(\[](feat\.|ft\.|featuring).*?[\)\]]/gi, "")
    // Remove movie/album references like (From "Bad Newz"), (From the Movie ...)
    .replace(/\s*[\(\[](from|soundtrack|ost|audio).*?[\)\]]/gi, "")
    // Remove video/reverb modifiers like [Official Video], (Slowed + Reverb)
    .replace(/\s*[\(\[](official|video|music video|lyric|lyrics|slowed|reverb|remix|version).*?[\)\]]/gi, "")
    .replace(/[—–\-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  let cleanArtist = (artist || "")
    .replace(/\s*[\(\[](feat\.|ft\.|featuring).*?[\)\]]/gi, "")
    // Only strip trailing collaboration tokens after & or 'with', NOT commas (to protect "Tyler, The Creator")
    .replace(/\s*(&|\bwith\b)\s*.*$/gi, "")
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
 * Calculate match confidence between requested track and iTunes candidate.
 * STRICT:
 * 1. Title must match at least 65% of words (prevents matching 1 word out of 3).
 * 2. Artist overlap is balanced across both target and candidate.
 */
export function calculateMatchConfidence(
  targetTitle: string,
  targetArtist: string,
  candidateTitle: string,
  candidateArtist: string
): number {
  const normTargetTitle = normalizeString(targetTitle);
  const normTargetArtist = normalizeString(targetArtist);
  const normCandTitle = normalizeString(candidateTitle);
  const normCandArtist = normalizeString(candidateArtist);

  const titleWords = normTargetTitle.split(" ").filter((w) => w.length > 0);
  const candTitleWords = new Set(normCandTitle.split(" ").filter((w) => w.length > 0));

  if (titleWords.length === 0 || candTitleWords.size === 0) {
    return 0;
  }

  // Calculate title overlap
  const matchedTitleWords = titleWords.filter((w) => candTitleWords.has(w));
  const titleScore = matchedTitleWords.length / titleWords.length;

  // STRICT TITLE VETO: Reject if fewer than 65% of title words match!
  if (titleScore < 0.65) {
    return 0;
  }

  // Stopwords for artist matching
  const artistStopwords = new Set(["the", "feat", "ft", "and", "official", "music", "audio", "records"]);
  const artistWords = normTargetArtist.split(" ").filter((w) => w.length > 1 && !artistStopwords.has(w));
  const candArtistList = normCandArtist.split(" ").filter((w) => w.length > 1 && !artistStopwords.has(w));
  const candArtistWords = new Set(candArtistList);

  let artistScore = 0.5; // Neutral if no artist provided

  if (artistWords.length > 0) {
    const matchedArtistWords = artistWords.filter((w) => candArtistWords.has(w));
    if (matchedArtistWords.length === 0) {
      return 0; // Absolute veto: target artist was not found in candidate
    }

    // Overlap relative to both target and candidate (prevents matching 1 name in 5 artists)
    const targetOverlap = matchedArtistWords.length / artistWords.length;
    const candOverlap = matchedArtistWords.length / Math.max(1, candArtistList.length);
    artistScore = (targetOverlap * 0.7) + (candOverlap * 0.3);
  }

  // 60% Title weight, 40% Artist weight
  return titleScore * 0.6 + artistScore * 0.4;
}

/**
 * Fetch top candidate tracks from iTunes Search API (request 10 to rank by confidence)
 */
async function fetchItunesCandidates(query: string, country?: string): Promise<any[]> {
  try {
    const countryParam = country ? `&country=${country}` : "";
    const itunesUrl = `https://itunes.apple.com/search?term=${encodeURIComponent(query)}&entity=song&limit=10${countryParam}`;
    const res = await fetch(itunesUrl, { mode: "cors" });
    if (!res.ok) return [];
    const data = await res.json();
    return (data.results || []).filter((r: any) => Boolean(r && r.previewUrl));
  } catch {
    return [];
  }
}

/**
 * Find best candidate matching target song and artist
 */
function findBestCandidate(candidates: any[], targetTitle: string, targetArtist: string): { candidate: any | null; confidence: number } {
  let bestCandidate: any | null = null;
  let bestScore = 0;

  for (const cand of candidates) {
    const score = calculateMatchConfidence(
      targetTitle,
      targetArtist,
      cand.trackName || "",
      cand.artistName || ""
    );

    if (score > bestScore && score >= 0.60) {
      bestScore = score;
      bestCandidate = cand;
    }
  }

  return { candidate: bestCandidate, confidence: bestScore };
}

/**
 * Resolve audio playback source with Strict Multi-Candidate Fuzzy Verification.
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

  // 5. Query Apple Music / iTunes Search API with Strict Scoring
  const { cleanTitle, cleanArtist, fullQuery } = cleanMusicQuery(params.song, params.artist);

  try {
    let match: any = null;

    // Step 5A+5B: Fire IN store and Global store in PARALLEL — halves latency vs sequential
    const [inCandidates, globalCandidates] = await Promise.all([
      fetchItunesCandidates(fullQuery, "IN"),
      fetchItunesCandidates(fullQuery),
    ]);

    let result = findBestCandidate(inCandidates, cleanTitle, cleanArtist);
    if (!result.candidate) {
      result = findBestCandidate(globalCandidates, cleanTitle, cleanArtist);
    }

    // Step 5C: If still no match and artist was present, search title alone BUT strictly verify candidate artist
    // Also fire both stores in parallel
    if (!result.candidate && cleanTitle && cleanArtist) {
      const [titleIN, titleGlobal] = await Promise.all([
        fetchItunesCandidates(cleanTitle, "IN"),
        fetchItunesCandidates(cleanTitle),
      ]);
      result = findBestCandidate(titleIN, cleanTitle, cleanArtist);
      if (!result.candidate) {
        result = findBestCandidate(titleGlobal, cleanTitle, cleanArtist);
      }
    }

    match = result.candidate;

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

  // Step 5D: If iTunes has no match, fetch reel audio stream from backend
  if (params.id) {
    try {
      const streamRes = await fetch(`${API_URL}/api/deck/${params.id}/stream`);
      if (streamRes.ok) {
        const streamData = await streamRes.json();
        if (streamData.audio_url && isAudioStreamUrl(streamData.audio_url)) {
          const resolved: ResolvedAudio = {
            previewUrl: streamData.audio_url,
            title: params.song,
            artist: params.artist,
            coverUrl: null,
            sourceType: "stream",
            viralStartSec: 0,
            viralDurationSec: 15,
            durationSec: 30,
            externalUrl: params.audioId ? `https://www.instagram.com/reels/audio/${params.audioId}/` : null,
          };
          memoryCache.set(cacheKey, resolved);
          saveToStorageCache(cacheKey, resolved);
          return resolved;
        }
      }
    } catch {}
  }

  // Fallback: unresolved (never serve an incorrect artist)
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
