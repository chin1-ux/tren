


const _rawApiUrl = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";
// Never use a localhost URL in production — it means the local .env was picked up by the build
const _isLocalhost = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?/i.test(_rawApiUrl);
export const API_URL = (!_isLocalhost && _rawApiUrl) || (import.meta.env.DEV ? "http://localhost:8000" : "");




// ── API types ──────────────────────────────────────────────────────────────────

export interface ApiTrend {
  id: string | number;
  song?: string;
  artist?: string;
  audio_title?: string;
  audio_artist?: string;
  audio_id?: string | null;
  audio_use_count?: number;
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
  saturation_penalty?: number;
  creator_fit_score?: number;
  hook_retention_score?: number;
  composite_score?: number;
  optimal_post_hour_ist?: number;
  best_platform_first?: string;
  why_this_works?: string;
  audio_cue_second?: number;
  platform?: string;
  trend_type?: string;
  reel_count?: number;
  peak_velocity?: number;
  created_at?: string;
  format_transferable?: boolean;
  transfer_instructions?: string | null;
  llm_classification_status?: string;
  raw_llm_response?: unknown;
  llm_classified_at?: string | null;
  // v2 new fields
  global_saturation_pct?: number;
  india_saturation_pct?: number;
  niche_tag?: string;
  hook_brief?: Array<{
    dominant_hook_type?: string;
    hook_opening_patterns?: string[];
    hook_brief_one_line?: string;
    optimal_length_seconds?: number;
  }>;
  format_patterns?: Array<{
    visual_format?: string;
    dominant_hook_type?: string;
  }>;
  is_cross_cultural?: boolean;
  trend_origin?: string;
  preview_url?: string | null;
  video_storage_status?: string;
  video_stored_at?: string;
  semantic_niches?: string[];
  discovery_source?: string;
  has_creator_outlier?: boolean;
  virality_type?: string;
  exogenous_correlation?: any;
  content_tone?: string;
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

export interface ApiTrendDecision {
  decision: "post" | "trial" | "skip" | string;
  score: number;
  rationale: string;
  test_hook: string;
  public_hook: string;
  trend: {
    creator_fit_score: number;
    hook_retention_score: number;
    saturation_penalty: number;
    composite_score: number;
    confidence: number;
  };
}

// ── Category metadata ──────────────────────────────────────────────────────────

type TrendCategory =
  | "Dance"
  | "Scenic"
  | "Fashion"
  | "Travel"
  | "Food"
  | "Comedy"
  | "Devotional"
  | "Festival"
  | "Motivation"
  | "Fitness"
  | "Study"
  | "Narrative"
  | "Text Overlay"
  | "Faceless"
  | "Regional"
  | "Viral";

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
  faceless:       { emoji: "🎭", category: "Faceless" },
  faceless_video: { emoji: "🎭", category: "Faceless" },
  face_less:      { emoji: "🎭", category: "Faceless" },
  regional:       { emoji: "🌍", category: "Regional" },
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

export interface UiTrend {
  id: string;
  song: string;
  artist: string;
  hoursLeft: number;
  viralMultiplier: number;
  contentType: string;
  contentTypeEmoji: string;
  category: string;
  language?: string;
  languageEmoji?: string;
  isDance: boolean;
  isNarrativeEdit: boolean;
  idealContentDescription: string;
  cameraStyle: string;
  hashtags: string[];

  // additional optional UI fields
  expiresAt: number;
  status?: string;
  saturationScore?: number;
  saturationPenalty?: number;
  creatorFitScore?: number;
  hookRetentionScore?: number;
  compositeScore?: number;
  optimalPostHourIst?: number;
  bestPlatformFirst?: string;
  whyThisWorks?: string;
  audioCueSecond?: number;
  reelCount?: number;
  languageLabel?: string;
  isEmerging?: boolean;
  formatTransferable?: boolean;
  transferInstructions?: string | null;
  llmClassificationStatus?: string;
  isClassificationVerified?: boolean;
  rawLlmResponse?: unknown;
  llmClassifiedAt?: string | null;

  // v2 new fields
  audioId?: string | null;
  audioUseCount?: number;
  globalSaturationPct?: number;
  indiaSaturationPct?: number;
  nicheTag?: string;
  hookBrief?: Array<{
    dominant_hook_type?: string;
    hook_opening_patterns?: string[];
    hook_brief_one_line?: string;
    optimal_length_seconds?: number;
  }>;
  formatPatterns?: Array<{
    visual_format?: string;
    dominant_hook_type?: string;
  }>;
  isCrossCultural?: boolean;
  trendOrigin?: string;
  preview_url?: string | null;
  video_storage_status?: string;
  video_stored_at?: string;
  semanticNiches?: string[];
  discoverySource?: string;
  hasCreatorOutlier?: boolean;
  viralityType?: string;
  exogenousCorrelation?: any;
  contentTone?: string;
}

export function adaptTrend(t: ApiTrend): UiTrend {
  const key = (t.content_type || "viral").toLowerCase();
  const meta = CATEGORY_EMOJI[key] ?? { emoji: "🔥", category: "Viral" as TrendCategory };
  const hours = Math.max(0, Number(t.window_hours_remaining) || 0);
  const langInfo = LANGUAGE_INFO[(t.language ?? "").toLowerCase()] ?? null;
  const classificationStatus = (t.llm_classification_status || "pending").toLowerCase();
  const isVerified = classificationStatus === "completed";
  const isUnverified = !isVerified;

  return {
    id: String(t.id),
    song: t.song || t.audio_title || "Unknown Song",
    artist: t.artist || t.audio_artist || "Unknown Artist",
    hoursLeft: Math.round(hours),
    expiresAt: Date.now() + hours * 3600 * 1000,
    viralMultiplier: Math.round((Number(t.velocity_avg) || 0) * 10) / 10,
    contentType: isUnverified ? "Classifying..." : meta.category,
    contentTypeEmoji: isUnverified ? "⏳" : meta.emoji,
    category: isUnverified ? "Classifying..." : meta.category,
    language: isVerified ? (langInfo?.label ?? t.language ?? undefined) : undefined,
    languageEmoji: isVerified ? (langInfo?.emoji ?? (t.language ? "🌍" : undefined)) : undefined,
    languageLabel: isVerified ? langInfo?.label : undefined,
    isDance: !!t.is_dance,
    isNarrativeEdit: !!t.narrative_edit,
    idealContentDescription: t.ideal_content_description ?? "",
    cameraStyle: t.camera_style ?? "",
    hashtags: t.hashtags ?? [],
    // Core v1 fields
    status: t.status ?? "rising",
    saturationScore: t.saturation_score ?? 0,
    saturationPenalty: t.saturation_penalty ?? 0,
    creatorFitScore: t.creator_fit_score ?? 0,
    hookRetentionScore: t.hook_retention_score ?? 0,
    compositeScore: t.composite_score ?? 0,
    optimalPostHourIst: t.optimal_post_hour_ist,
    bestPlatformFirst: t.best_platform_first ?? "instagram",
    whyThisWorks: t.why_this_works,
    audioCueSecond: t.audio_cue_second,
    reelCount: t.reel_count,
    isEmerging: t.status === "emerging",
    formatTransferable: t.format_transferable,
    transferInstructions: t.transfer_instructions,
    llmClassificationStatus: classificationStatus,
    isClassificationVerified: isVerified,
    rawLlmResponse: t.raw_llm_response,
    llmClassifiedAt: t.llm_classified_at ?? null,
    // v2 new fields
    audioId: t.audio_id ?? null,
    audioUseCount: t.audio_use_count ?? 0,
    globalSaturationPct: t.global_saturation_pct ?? 0,
    indiaSaturationPct: t.india_saturation_pct ?? 0,
    nicheTag: t.niche_tag ?? "general",
    hookBrief: t.hook_brief ?? [],
    formatPatterns: t.format_patterns ?? [],
    isCrossCultural: t.is_cross_cultural ?? false,
    trendOrigin: t.trend_origin ?? "unknown",
    preview_url: t.preview_url ?? null,
    video_storage_status: t.video_storage_status ?? 'pending',
    video_stored_at: t.video_stored_at,
    semanticNiches: t.semantic_niches ?? [],
    discoverySource: t.discovery_source,
    hasCreatorOutlier: t.has_creator_outlier ?? false,
    viralityType: t.virality_type ?? "unknown",
    exogenousCorrelation: t.exogenous_correlation ?? null,
    contentTone: t.content_tone ?? "unknown",
  };
}

// ── HTTP helper ────────────────────────────────────────────────────────────────

import { supabase } from "./supabase";

let inMemoryToken: string | null = null;

export const createDefaultPreferences = async (userId: string) => {
  try {
    await supabase
      .from('user_preferences')
      .upsert({
        user_id: userId,
        languages: ['english', 'hindi'],   // Phase 1 default — hardcoded
        categories: [],
        regions: ['IN'],
      }, { onConflict: 'user_id' });
  } catch (err) {
    console.error("Failed to create default preferences:", err);
  }
};

if (typeof window !== "undefined") {
  supabase.auth.getSession().then(({ data: { session } }) => {
    inMemoryToken = session?.access_token || null;
    if (session?.user?.id) {
      createDefaultPreferences(session.user.id);
    }
  });

  supabase.auth.onAuthStateChange(async (event, session) => {
    inMemoryToken = session?.access_token || null;
    if ((event === "SIGNED_IN" || event === "USER_UPDATED") && session?.user?.id) {
      await createDefaultPreferences(session.user.id);
    }
  });
}

export function setAuthToken(token: string | null) {
  inMemoryToken = token;
}

export function getAuthToken(): string | null {
  if (!inMemoryToken && typeof window !== "undefined") {
    inMemoryToken = localStorage.getItem("trendrop_token");
  }
  return inMemoryToken;
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAuthToken();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });
  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("trendrop_token");
      localStorage.removeItem("trendrop_onboarded");
      setAuthToken(null);
      import("../store/useAppStore").then(({ useUserStore }) => {
        useUserStore.getState().logout();
      });
    }
  }
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const token = getAuthToken();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });
  if (res.status === 401) {
    if (typeof window !== "undefined") {
      localStorage.removeItem("trendrop_token");
      localStorage.removeItem("trendrop_onboarded");
      setAuthToken(null);
      import("../store/useAppStore").then(({ useUserStore }) => {
        useUserStore.getState().logout();
      });
    }
  }
  return res;
}

// ── Trend fetch functions ──────────────────────────────────────────────────────

export async function fetchTrends(language?: string, sort?: string, niche?: string): Promise<UiTrend[]> {
  const params = new URLSearchParams();
  if (language && language !== "all") params.set("language", language);
  if (sort) params.set("sort", sort);
  if (niche && niche !== "all") params.set("niche", niche);
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

export async function fetchTrendDecision(trendId: string, creatorNiche?: string, creatorLanguage?: string): Promise<ApiTrendDecision> {
  const params = new URLSearchParams();
  if (creatorNiche) params.set("creator_niche", creatorNiche);
  if (creatorLanguage) params.set("creator_language", creatorLanguage);
  const qs = params.toString() ? `?${params.toString()}` : "";
  return http<ApiTrendDecision>(`/api/trends/${encodeURIComponent(trendId)}/decision${qs}`);
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

export async function generateNarrative(args: {
  files: File[];
  trendId: string;
  userEmail: string;
  narrativeType: string;
  textOverlays: string[];
}): Promise<GenerateResponse> {
  const fd = new FormData();
  args.files.forEach((f) => fd.append("files", f));
  fd.append("trend_id", args.trendId);
  fd.append("user_email", args.userEmail);
  fd.append("narrative_type", args.narrativeType);
  fd.append("text_overlays", JSON.stringify(args.textOverlays));
  return http<GenerateResponse>("/api/generate-narrative", { method: "POST", body: fd });
}

export async function generateFaceless(args: {
  trendId: string;
  userEmail: string;
  niche: string;
  contentDescription: string;
}): Promise<GenerateResponse> {
  const fd = new FormData();
  fd.append("trend_id", args.trendId);
  fd.append("user_email", args.userEmail);
  fd.append("niche", args.niche);
  fd.append("content_description", args.contentDescription);
  return http<GenerateResponse>("/api/generate-faceless", { method: "POST", body: fd });
}

export async function repurposeVideo(args: {
  file: File;
  trendId: string;
  userEmail: string;
}): Promise<GenerateResponse> {
  const fd = new FormData();
  fd.append("file", args.file);
  fd.append("trend_id", args.trendId);
  fd.append("user_email", args.userEmail);
  return http<GenerateResponse>("/api/repurpose", { method: "POST", body: fd });
}

export async function jobStatus(jobId: string): Promise<StatusResponse> {
  return http<StatusResponse>(`/api/job-status/${encodeURIComponent(jobId)}`);
}

export async function reelStatus(jobId: string): Promise<StatusResponse> {
  return jobStatus(jobId);
}

export function resolveOutputUrl(outputUrl: string): string {
  if (/^https?:\/\//i.test(outputUrl)) return outputUrl;
  return `${API_URL || ""}/${outputUrl.replace(/^\//, "")}`;
}

// ── Ideas, Score, Hook, Calendar helper functions ──────────────────────────────
export interface ApiDailyIdea {
  title: string;
  description: string;
  hook: string;
  audio_suggestion: string;
  posting_time: string;
  difficulty: "Easy" | "Medium" | "Hard" | string;
}

export interface ScoreReelResponse {
  overall_score: number;
  grade: string;
  hook_score: number;
  audio_score: number;
  caption_score: number;
  hashtag_score: number;
  timing_score: number;
  top_fixes: string[];
}

export interface GeneratedHook {
  style: string;
  text: string;
  why_it_works: string;
}

export interface GenerateHooksResponse {
  hooks: GeneratedHook[];
}

export interface CalendarDay {
  day: number;
  topic: string;
  hook: string;
  audio_style: string;
  hashtags: string[];
  posting_time: string;
}

export async function fetchDailyIdeas(userEmail: string): Promise<ApiDailyIdea[]> {
  return http<ApiDailyIdea[]>(`/api/daily-ideas/${encodeURIComponent(userEmail)}`);
}

export async function scoreReel(args: {
  audio: string;
  caption: string;
  posting_time: string;
  niche: string;
}): Promise<ScoreReelResponse> {
  return http<ScoreReelResponse>("/api/score-reel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
}

export async function generateHooks(args: {
  trend: string;
  content_description: string;
}): Promise<GenerateHooksResponse> {
  return http<GenerateHooksResponse>("/api/generate-hooks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
}

export async function generateCalendar(userEmail: string): Promise<{ calendar: CalendarDay[] }> {
  return http<{ calendar: CalendarDay[] }>(`/api/generate-calendar/${encodeURIComponent(userEmail)}`);
}

// ── User ───────────────────────────────────────────────────────────────────────


export async function subscribe(body: {
  email: string;
  niche: string;
  language: string;
}): Promise<{ success: boolean; auth_token: string; email: string }> {
  return http<{ success: boolean; auth_token: string; email: string }>("/api/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// ── Payment ────────────────────────────────────────────────────────────────────

export interface CreateOrderResponse {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
}

export async function createPaymentOrder(email: string): Promise<CreateOrderResponse> {
  return http<CreateOrderResponse>("/api/payment/create-order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
}

export async function verifyPayment(args: {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
  email: string;
}): Promise<{ success: boolean; plan: string; message: string }> {
  return http<{ success: boolean; plan: string; message: string }>("/api/payment/webhook", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(args),
  });
}

export async function getUserPlan(email: string): Promise<{ plan: string }> {
  return http<{ plan: string }>(`/api/user/plan?email=${encodeURIComponent(email)}`);
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
  audio_id?: string | null;
  audio_use_count?: number;
  hashtags: string[];
  caption: string;
  velocity_score: number;
  video_url?: string;
  thumbnail_url?: string;
  // v2 new fields
  global_saturation_pct?: number;
  india_saturation_pct?: number;
  niche_tag?: string;
  hook_brief?: unknown[];
  format_patterns?: unknown[];
  window_hours_remaining?: number;
  is_cross_cultural?: boolean;
  trend_origin?: string;
  scraped_at?: string;
  is_creator_outlier?: boolean;
}

// ── Marketplace APIs ──────────────────────────────────────────────────────────

export interface BrandDealStats {
  total_earnings: number;
  active_partnerships: number;
  pending_applications: number;
}

export interface BrandDeal {
  id: number;
  brand_name: string;
  deal_amount: number;
  commission_amount: number;
  status: string;
  details: string;
  requirements: string;
  applied: boolean;
}

export interface CollabMatch {
  instagram_username: string;
  user_email: string;
  niche: string;
  followers: number;
  engagement_rate: number;
  trend_score: number;
  compatibility_score: number;
  request_sent: boolean;
}

export async function fetchBrandDeals(userEmail: string): Promise<{ deals: BrandDeal[]; stats: BrandDealStats }> {
  return http<{ deals: BrandDeal[]; stats: BrandDealStats }>(`/api/brand-deals/${encodeURIComponent(userEmail)}`);
}

export async function applyToBrandDeal(dealId: number, userEmail: string, pitch: string): Promise<{ success: boolean; message: string }> {
  return http<{ success: boolean; message: string }>("/api/apply-deal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ deal_id: dealId, user_email: userEmail, pitch }),
  });
}

export async function fetchCollabMatches(userEmail: string): Promise<CollabMatch[]> {
  return http<CollabMatch[]>(`/api/collab-matches/${encodeURIComponent(userEmail)}`);
}

export async function sendCollabRequest(fromEmail: string, toEmail: string, message: string): Promise<{ success: boolean; message: string }> {
  return http<{ success: boolean; message: string }>("/api/send-collab-request", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from_email: fromEmail, to_email: toEmail, message }),
  });
}

export async function fetchUserFeed(): Promise<ApiReel[]> {
  return http<ApiReel[]>("/api/reels/feed");
}

export async function fetchCrossCulturalTrends(): Promise<ApiReel[]> {
  return http<ApiReel[]>("/api/reels/cross-cultural");
}

export interface FlopDiagnosticsData {
  status: string;
  message?: string;
  data?: {
    baseline_avg_plays: number;
    total_posts_analyzed: number;
    flops_detected: number;
    flops: Array<{
      media_id: string;
      permalink: string;
      caption: string;
      plays_count: number;
      engagement: number;
    }>;
    suggested_remedy_tracks: Array<{
      audio_title: string;
      audio_artist: string;
      why_this_works: string;
      transfer_instructions: string;
    }>;
  };
}

export interface NicheHealthData {
  status: string;
  message?: string;
  data?: {
    primary_niche: string;
    secondary_niches: string[];
    niche_health_score: number;
    alignment_drift_detected: boolean;
    recommendations: string[];
  };
}

export async function fetchCreatorDiagnostics(email: string): Promise<FlopDiagnosticsData> {
  return http<FlopDiagnosticsData>(`/api/creator/diagnostics?email=${encodeURIComponent(email)}`);
}

export async function fetchCreatorNicheHealth(email: string): Promise<NicheHealthData> {
  return http<NicheHealthData>(`/api/creator/niche-health?email=${encodeURIComponent(email)}`);
}

export async function logAnalyticsEvent(eventName: string): Promise<{ success: boolean }> {
  try {
    return await http<{ success: boolean }>("/api/analytics/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_name: eventName })
    });
  } catch (err) {
    console.error("Failed to log analytics: ", err);
    return { success: false };
  }
}

export async function submitCreatorFeedback(dealId: number, rating: string, comment: string): Promise<{ success: boolean }> {
  return http<{ success: boolean }>("/api/creator/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ deal_id: dealId, rating, comment })
  });
}



