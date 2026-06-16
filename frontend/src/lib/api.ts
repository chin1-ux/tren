import type { Trend, TrendCategory } from "./mock-trends";

export const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

// ── API types ──────────────────────────────────────────────────────────────────

export interface ApiTrend {
  id: string | number;
  song?: string;
  artist?: string;
  audio_title?: string;
  audio_artist?: string;
  content_type: string;
  window_hours_remaining: number;
  velocity_avg: number;
  language?: string | null;
  is_dance?: boolean;
  narrative_edit?: boolean;
  ideal_content_description?: string;
  camera_style?: string;
  hashtags?: string[];
  status?: string;         // "emerging" | "rising" | "peaked" | "expired"
  saturation_score?: number;
  optimal_post_hour_ist?: number;
  best_platform_first?: string;
  why_this_works?: string;
  audio_cue_second?: number;
  platform?: string;
  trend_type?: string;
  reel_count?: number;
  peak_velocity?: number;
  created_at?: string;
}

export interface ApiCaptionKit {
  captions: Array<{ vibe: string; text: string }>;
  hashtags: string[];
  audio_cue: string;
  posting_strategy: {
    best_hour_ist: number;
    best_days: string[];
    platform_first: string;
    reasoning: string;
  };
  saturation_alert: string;
}

// ── Category metadata ──────────────────────────────────────────────────────────

const CATEGORY_EMOJI: Record<string, { emoji: string; category: TrendCategory }> = {
  dance:          { emoji: "💃", category: "Dance" },
  scenic:         { emoji: "🎬", category: "Scenic" },
  fashion:        { emoji: "👗", category: "Fashion" },
  travel:         { emoji: "✈️", category: "Travel" },
  food:           { emoji: "🍳", category: "Food" },
  comedy:         { emoji: "😂", category: "Comedy" },
  devotional:     { emoji: "🙏", category: "Devotional" },
  festival:       { emoji: "🪔", category: "Festival" },
  motivation:     { emoji: "💪", category: "Motivation" },
  fitness:        { emoji: "🏋️", category: "Fitness" },
  study:          { emoji: "📚", category: "Study" },
  narrative_edit: { emoji: "🎞️", category: "Narrative" },
  text_overlay:   { emoji: "✏️", category: "Text Overlay" },
  other:          { emoji: "🔥", category: "Viral" },
  viral:          { emoji: "🔥", category: "Viral" },
};

const LANGUAGE_INFO: Record<string, { emoji: string; label: string }> = {
  hi: { emoji: "🇮🇳", label: "Hindi" },
  kn: { emoji: "🎯", label: "Kannada" },
  ta: { emoji: "🌴", label: "Tamil" },
  te: { emoji: "🌟", label: "Telugu" },
  bn: { emoji: "🐯", label: "Bengali" },
  mr: { emoji: "🦁", label: "Marathi" },
  en: { emoji: "🌐", label: "English" },
};

// ── UiTrend adapter ────────────────────────────────────────────────────────────

export interface UiTrend extends Trend {
  expiresAt: number;
  status?: string;
  saturationScore?: number;
  optimalPostHourIst?: number;
  bestPlatformFirst?: string;
  whyThisWorks?: string;
  audioCueSecond?: number;
  reelCount?: number;
  languageLabel?: string;
  isEmerging?: boolean;
}

export function adaptTrend(t: ApiTrend): UiTrend {
  const key = (t.content_type || "viral").toLowerCase();
  const meta = CATEGORY_EMOJI[key] ?? { emoji: "🔥", category: "Viral" as TrendCategory };
  const hours = Math.max(0, Number(t.window_hours_remaining) || 0);
  const langInfo = LANGUAGE_INFO[(t.language ?? "").toLowerCase()] ?? null;

  return {
    id: String(t.id),
    song: t.song || t.audio_title || "Unknown Song",
    artist: t.artist || t.audio_artist || "Unknown Artist",
    hoursLeft: Math.round(hours),
    expiresAt: Date.now() + hours * 3600 * 1000,
    viralMultiplier: Math.round((Number(t.velocity_avg) || 0) * 10) / 10,
    contentType: meta.category,
    contentTypeEmoji: meta.emoji,
    category: meta.category,
    language: langInfo?.label ?? t.language ?? undefined,
    languageEmoji: langInfo?.emoji ?? (t.language ? "🌍" : undefined),
    languageLabel: langInfo?.label,
    isDance: !!t.is_dance,
    isNarrativeEdit: !!t.narrative_edit,
    idealContentDescription: t.ideal_content_description ?? "",
    cameraStyle: t.camera_style ?? "",
    hashtags: t.hashtags ?? [],
    // New v2 fields
    status: t.status ?? "rising",
    saturationScore: t.saturation_score ?? 0,
    optimalPostHourIst: t.optimal_post_hour_ist,
    bestPlatformFirst: t.best_platform_first ?? "instagram",
    whyThisWorks: t.why_this_works,
    audioCueSecond: t.audio_cue_second,
    reelCount: t.reel_count,
    isEmerging: t.status === "emerging",
  };
}

// ── HTTP helper ────────────────────────────────────────────────────────────────

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

// ── Trend fetch functions ──────────────────────────────────────────────────────

export async function fetchTrends(language?: string, sort?: string): Promise<UiTrend[]> {
  const params = new URLSearchParams();
  if (language && language !== "all") params.set("language", language);
  if (sort) params.set("sort", sort);
  const qs = params.toString() ? `?${params}` : "";
  const data = await http<ApiTrend[] | { trends: ApiTrend[] }>(`/api/trends${qs}`);
  const list = Array.isArray(data) ? data : (data as { trends: ApiTrend[] }).trends ?? [];
  return list.map(adaptTrend);
}

export async function fetchEmergingTrends(language?: string): Promise<UiTrend[]> {
  const qs = language && language !== "all" ? `?language=${language}` : "";
  const data = await http<ApiTrend[]>(`/api/trends/emerging${qs}`);
  return data.map(adaptTrend);
}

export async function fetchAllActiveTrends(): Promise<UiTrend[]> {
  const data = await http<ApiTrend[]>("/api/trends/all-active");
  return data.map(adaptTrend);
}

export async function fetchTrendById(id: string): Promise<UiTrend> {
  const data = await http<ApiTrend>(`/api/trends/${encodeURIComponent(id)}`);
  return adaptTrend(data);
}

export async function fetchSimilarTrends(trendId: string): Promise<UiTrend[]> {
  const data = await http<ApiTrend[]>(`/api/trends/${encodeURIComponent(trendId)}/similar`);
  return data.map(adaptTrend);
}

export async function fetchCaptionKit(trendId: string): Promise<ApiCaptionKit> {
  return http<ApiCaptionKit>(`/api/trends/${encodeURIComponent(trendId)}/caption`);
}

export async function fetchTrendReels(trendId: string): Promise<ApiReel[]> {
  return http<ApiReel[]>(`/api/trends/${encodeURIComponent(trendId)}/reels`);
}

// ── Reel generation ────────────────────────────────────────────────────────────

export interface GenerateResponse { job_id: string }
export interface StatusResponse {
  status: "queued" | "processing" | "complete" | "failed" | string;
  progress: number;
  output_url?: string;
  error?: string;
  error_message?: string;
}

export async function generateReel(args: {
  files: File[];
  trendId: string;
  userEmail: string;
}): Promise<GenerateResponse> {
  const fd = new FormData();
  args.files.forEach((f) => fd.append("files", f));
  fd.append("trend_id", args.trendId);
  fd.append("user_email", args.userEmail);
  return http<GenerateResponse>("/api/generate-reel", { method: "POST", body: fd });
}

export async function reelStatus(jobId: string): Promise<StatusResponse> {
  return http<StatusResponse>(`/api/reel-status/${encodeURIComponent(jobId)}`);
}

export function resolveOutputUrl(outputUrl: string): string {
  if (/^https?:\/\//i.test(outputUrl)) return outputUrl;
  return `${API_URL}/${outputUrl.replace(/^\//, "")}`;
}

// ── User ───────────────────────────────────────────────────────────────────────

export async function subscribe(body: {
  email: string;
  niche: string;
  language: string;
}): Promise<void> {
  await http<unknown>("/api/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function submitFeedback(body: {
  trend_id: number;
  feedback_type: string;
  comment?: string;
  user_email?: string;
}): Promise<void> {
  await http<unknown>("/api/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ── ApiReel type ───────────────────────────────────────────────────────────────

export interface ApiReel {
  id: number;
  platform: string;
  reel_id: string;
  view_count: number;
  like_count: number;
  comment_count: number;
  share_count?: number;
  posted_at: string;
  owner_username: string;
  owner_follower_count?: number;
  audio_title: string;
  audio_artist: string;
  hashtags: string[];
  caption: string;
  velocity_score: number;
  video_url?: string;
  thumbnail_url?: string;
}
