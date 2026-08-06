


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
  velocity_score?: number;
  opportunity_score?: number;
  is_regional_crossover?: boolean;
  crossover_from_language?: string | null;
  crossover_message?: string | null;
  views_delta_last_run?: number;
  likes_delta_last_run?: number;
  audio_delta_last_run?: number;
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
  global_discovery: { emoji: "🌍", category: "Global" },
  india_vernacular: { emoji: "🇮🇳", category: "Regional" },
  GLOBAL_DISCOVERY: { emoji: "🌍", category: "Global" },
  INDIA_VERNACULAR: { emoji: "🇮🇳", category: "Regional" },
  other:          { emoji: "🔥", category: "Viral" },
  viral:          { emoji: "🔥", category: "Viral" },
};

const LANGUAGE_INFO: Record<string, { emoji: string; label: string }> = {
  hi: { emoji: "🇮🇳", label: "Hindi" },
  pa: { emoji: "🎺", label: "Punjabi" },
  kn: { emoji: "🎯", label: "Kannada" },
  ta: { emoji: "🌴", label: "Tamil" },
  te: { emoji: "🌟", label: "Telugu" },
  bn: { emoji: "🐯", label: "Bengali" },
  mr: { emoji: "🦁", label: "Marathi" },
  ml: { emoji: "🌴", label: "Malayalam" },
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
  // Trend classification fields for display differentiation
  trendClassification?: string;
  velocityPattern?: string;
  isEvergreen?: boolean;
  trendAgeHours?: number;
  audioReleaseDate?: string;
  audioOriginalReleaseYear?: number;
  audioGenre?: string;
  audioLabel?: string;
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
  reelId?: string;

  // opportunity and crossover fields
  opportunityScore?: number;
  nicheFitScore?: number;
  isRegionalCrossover?: boolean;
  crossoverFromLanguage?: string | null;
  crossoverMessage?: string | null;
  viewsDelta?: number;
  likesDelta?: number;
}

export function adaptTrend(t: ApiTrend): UiTrend {
  const key = (t.content_type || "viral").toLowerCase();
  const meta = CATEGORY_EMOJI[key] ?? { emoji: "🔥", category: "Viral" as TrendCategory };
  const hours = Math.max(0, Number(t.window_hours_remaining) || 0);
  let rawLang = (t.language ?? "").toLowerCase().trim();
  // Map legacy text values to proper ISO codes
  if (rawLang === "hindi" || rawLang === "bhojpuri") rawLang = "hi";
  else if (rawLang === "tamil") rawLang = "ta";
  else if (rawLang === "telugu") rawLang = "te";
  else if (rawLang === "punjabi") rawLang = "pa";
  else if (rawLang === "kannada") rawLang = "kn";
  else if (rawLang === "marathi") rawLang = "mr";
  else if (rawLang === "malayalam") rawLang = "ml";
  else if (rawLang === "bengali") rawLang = "bn";
  else if (rawLang === "english") rawLang = "en";

  const langInfo = LANGUAGE_INFO[rawLang] ?? null;
  const classificationStatus = (t.llm_classification_status || (t.reel_id ? "completed" : "pending")).toLowerCase();
  const VERIFIED_STATUSES = new Set(["completed", "not_needed", "verified"]);
  const isVerified = VERIFIED_STATUSES.has(classificationStatus);
  const isUnverified = !isVerified;

  return {
    id: String(t.id),
    song: t.song || t.audio_title || "Unknown Song",
    artist: t.artist || t.audio_artist || "Unknown Artist",
    hoursLeft: Math.round(hours),
    expiresAt: Date.now() + hours * 3600 * 1000,
    viralMultiplier: Math.min(99.9, Math.round((Number(t.velocity_avg) || Number(t.velocity_score) || 0) / VIRAL_SCALE_FACTOR * VIRAL_DISPLAY_MULTIPLIER) / 10),
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
    reelId: t.reel_id,
    opportunityScore: t.opportunity_score,
    nicheFitScore: t.niche_fit_score !== undefined ? t.niche_fit_score : undefined,
    isRegionalCrossover: t.is_regional_crossover ?? false,
    crossoverFromLanguage: t.crossover_from_language,
    crossoverMessage: t.crossover_message,
    viewsDelta: t.views_delta_last_run,
    likesDelta: t.likes_delta_last_run,
    // Trend classification fields for display differentiation
    trendClassification: t.trend_classification ?? "new_viral",
    velocityPattern: t.velocity_pattern ?? "sudden_spike",
    isEvergreen: t.is_evergreen ?? false,
    trendAgeHours: t.trend_age_hours ?? 0,
    audioReleaseDate: t.audio_release_date,
    audioOriginalReleaseYear: t.audio_original_release_year,
    audioGenre: t.audio_genre,
    audioLabel: t.audio_label,
  };
}

// ── HTTP helper ────────────────────────────────────────────────────────────────

// NOTE: These must match backend VIRAL_MULTIPLIER_SCALE_FACTOR and VIRAL_MULTIPLIER_DISPLAY_MULTIPLIER
// TODO: Expose these via API to avoid manual sync
const VIRAL_SCALE_FACTOR = 10000;
const VIRAL_DISPLAY_MULTIPLIER = 10;

import { supabase } from "./supabase";

let inMemoryToken: string | null = null;

export const createDefaultPreferences = async (userId: string) => {
  // Graceful no-op since user_preferences table does not exist in backend schema
};

if (typeof window !== "undefined") {
  supabase.auth.getSession().then(({ data: { session } }) => {
    inMemoryToken = session?.access_token || null;
  });

  supabase.auth.onAuthStateChange(async (event, session) => {
    inMemoryToken = session?.access_token || null;
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

export async function fetchAudioHistory(trendId: string | number): Promise<Array<{ snapshotted_at: string; audio_use_count: number }>> {
  return http<Array<{ snapshotted_at: string; audio_use_count: number }>>(`/api/trends/${encodeURIComponent(trendId)}/audio-history`);
}

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

export async function fetchPeakedTrends(language?: string): Promise<UiTrend[]> {
  const qs = language && language !== "all" ? `?language=${language}` : "";
  const data = await http<ApiTrend[]>(`/api/trends/peaked${qs}`);
  return data.map(adaptTrend);
}

export async function fetchExpiredTrends(language?: string): Promise<UiTrend[]> {
  const qs = language && language !== "all" ? `?language=${language}` : "";
  const data = await http<ApiTrend[]>(`/api/trends/expired${qs}`);
  return data.map(adaptTrend);
}

// ── Instagram Algorithm Insights API ─────────────────────────────────────

export interface ContentAnalysisData {
  views?: number;
  likes?: number;
  comments?: number;
  shares?: number;
  saves?: number;
  duration?: number;
  niche?: string;
  uses_trending_audio?: boolean;
}

export interface AlgorithmAnalysis {
  virality_score: number;
  viral_potential: string;
  factor_scores: Record<string, number>;
  engagement_metrics: {
    engagement_rate: number;
    like_rate: number;
    comment_rate: number;
    share_rate: number;
    save_rate: number;
  };
  recommendations: Array<{
    category: string;
    priority: string;
    title: string;
    description: string;
    expected_impact: string;
    difficulty: string;
  }>;
  algorithm_explanation: string;
}

export async function analyzeContentForVirality(contentData: ContentAnalysisData): Promise<AlgorithmAnalysis> {
  const params = new URLSearchParams();
  if (contentData.views !== undefined) params.set('views', contentData.views.toString());
  if (contentData.likes !== undefined) params.set('likes', contentData.likes.toString());
  if (contentData.comments !== undefined) params.set('comments', contentData.comments.toString());
  if (contentData.shares !== undefined) params.set('shares', contentData.shares.toString());
  if (contentData.saves !== undefined) params.set('saves', contentData.saves.toString());
  if (contentData.duration !== undefined) params.set('duration', contentData.duration.toString());
  if (contentData.niche) params.set('niche', contentData.niche);
  if (contentData.uses_trending_audio !== undefined) params.set('uses_trending_audio', contentData.uses_trending_audio.toString());
  
  const qs = params.toString() ? `?${params}` : "";
  return http<AlgorithmAnalysis>(`/api/algorithm/analyze${qs}`);
}

export async function getOptimalPostingTimes(niche: string = "general", targetAudience: string = "india"): Promise<{
  niche: string;
  target_audience: string;
  optimal_times: string[];
}> {
  const params = new URLSearchParams();
  params.set('niche', niche);
  params.set('target_audience', targetAudience);
  return http(`/api/algorithm/posting-times?${params}`);
}

export async function getHashtagStrategy(niche: string = "general", contentType: string = "reel"): Promise<{
  niche: string;
  content_type: string;
  hashtag_strategy: Record<string, string[]>;
}> {
  const params = new URLSearchParams();
  params.set('niche', niche);
  params.set('content_type', contentType);
  return http(`/api/algorithm/hashtag-strategy?${params}`);
}

// ── Event Monitoring API ─────────────────────────────────────────────────────

export interface SocialMediaEvent {
  id: string;
  name: string;
  type: string;
  impact: string;
  start_date: string;
  end_date: string;
  hashtags: string[];
  content_themes: string[];
  creator_opportunities: string[];
  target_audiences: string[];
  platform_relevance: Record<string, number>;
  viral_potential: number;
  trending_now: boolean;
  estimated_creator_participation: number;
  days_until_start: number;
}

export async function getActiveEvents(daysAhead: number = 30, daysBehind: number = 7): Promise<{
  events: SocialMediaEvent[];
  total_events: number;
  query_params: { days_ahead: number; days_behind: number };
}> {
  const params = new URLSearchParams();
  params.set('days_ahead', daysAhead.toString());
  params.set('days_behind', daysBehind.toString());
  return http(`/api/events/active?${params}`);
}

export async function getEventOpportunities(eventId: string): Promise<any> {
  return http(`/api/events/${eventId}/opportunities`);
}

export async function detectHashtagSpikes(hoursWindow: number = 24): Promise<{
  spikes: Array<{
    hashtag: string;
    event_name: string;
    usage_count: number;
    velocity_score: number;
    spike_detected: boolean;
    trend_direction: string;
  }>;
  hours_window: number;
  total_spikes: number;
}> {
  const params = new URLSearchParams();
  params.set('hours_window', hoursWindow.toString());
  return http(`/api/events/hashtag-spikes?${params}`);
}

// ── Hashtag Velocity Tracking API ───────────────────────────────────────────

export interface HashtagVelocity {
  hashtag: string;
  current_count: number;
  previous_count: number;
  velocity_score: number;
  trend_direction: string;
  acceleration: number;
  usage_frequency: number;
  niche_relevance: string;
  estimated_total_creators: number;
  peak_24h_usage: number;
  discovered_at: string;
}

export async function getHashtagVelocity(hoursWindow: number = 24): Promise<{
  hashtag_velocities: HashtagVelocity[];
  total_hashtags: number;
  hours_window: number;
}> {
  const params = new URLSearchParams();
  params.set('hours_window', hoursWindow.toString());
  return http(`/api/hashtags/velocity?${params}`);
}

export interface HashtagTrend {
  hashtag: string;
  velocity_score: number;
  trend_direction: string;
  related_hashtags: string[];
  content_themes: string[];
  target_audiences: string[];
  optimal_content_types: string[];
  estimated_lifespan_hours: number;
  competition_level: string;
  platform_performance: Record<string, number>;
}

export async function getTrendingHashtags(hoursWindow: number = 24, minVelocity: number = 20.0): Promise<{
  trending_hashtags: HashtagTrend[];
  total_trending: number;
  query_params: { hours_window: number; min_velocity: number };
}> {
  const params = new URLSearchParams();
  params.set('hours_window', hoursWindow.toString());
  params.set('min_velocity', minVelocity.toString());
  return http(`/api/hashtags/trending?${params}`);
}

// ── Topic Clustering API ─────────────────────────────────────────────────────

export interface TopicCluster {
  topic_id: string;
  topic_name: string;
  topic_keywords: string[];
  topic_category: string;
  content_samples: string[];
  creator_count: number;
  total_engagement: number;
  avg_velocity: number;
  viral_potential: number;
  trending_since: string;
  estimated_lifespan_hours: number;
  related_topics: string[];
  target_audiences: string[];
  content_opportunities: string[];
}

export async function getTopicClusters(hoursWindow: number = 48, minClusterSize: number = 5): Promise<{
  topic_clusters: TopicCluster[];
  total_clusters: number;
  query_params: { hours_window: number; min_cluster_size: number };
}> {
  const params = new URLSearchParams();
  params.set('hours_window', hoursWindow.toString());
  params.set('min_cluster_size', minClusterSize.toString());
  return http(`/api/topics/clusters?${params}`);
}

export interface Conversation {
  conversation_id: string;
  conversation_name: string;
  conversation_type: string;
  template_structure: string;
  participation_count: number;
  velocity_score: number;
  engagement_rate: number;
  viral_potential: number;
  platform_performance: Record<string, number>;
  optimal_content_types: string[];
  example_captions: string[];
  creator_opportunities: string[];
}

export async function detectConversations(hoursWindow: number = 48): Promise<{
  conversations: Conversation[];
  total_conversations: number;
  hours_window: number;
}> {
  const params = new URLSearchParams();
  params.set('hours_window', hoursWindow.toString());
  return http(`/api/conversations/detect?${params}`);
}

// ── Creator Analytics API ─────────────────────────────────────────────────────

export interface CreatorMetrics {
  creator_email: string;
  total_reels_analyzed: number;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  avg_engagement_rate: number;
  avg_velocity_score: number;
  top_performing_content: Array<{
    id: string;
    views: number;
    likes: number;
    velocity: number;
    category: string;
  }>;
  content_categories: Record<string, number>;
  trend_adoption_rate: number;
  viral_content_count: number;
  growth_trend: string;
  peak_performance_hours: number[];
  optimal_posting_times: string[];
}

export async function getCreatorMetrics(daysBack: number = 30): Promise<CreatorMetrics> {
  const params = new URLSearchParams();
  params.set('days_back', daysBack.toString());
  return http(`/api/creator/metrics?${params}`);
}

export interface TrendAdoption {
  trend_id: number;
  trend_name: string;
  adoption_date: string;
  content_created: number;
  avg_performance: number;
  success_score: number;
  timing_score: number;
  category_fit: string;
}

export async function getTrendAdoptionHistory(daysBack: number = 90): Promise<{
  trend_adoption: TrendAdoption[];
  total_adoptions: number;
}> {
  const params = new URLSearchParams();
  params.set('days_back', daysBack.toString());
  return http(`/api/creator/trend-adoption?${params}`);
}

export async function getContentPerformanceOverTime(daysBack: number = 30): Promise<{
  performance_data: Array<{
    date: string;
    total_views: number;
    total_likes: number;
    total_comments: number;
    content_count: number;
    avg_views: number;
  }>;
  days_analyzed: number;
}> {
  const params = new URLSearchParams();
  params.set('days_back', daysBack.toString());
  return http(`/api/creator/performance-over-time?${params}`);
}

export async function getSuccessRecommendations(): Promise<{
  recommendations: Array<{
    type: string;
    title: string;
    description: string;
    action: string;
  }>;
  total_recommendations: number;
}> {
  return http(`/api/creator/recommendations`);
}

// ── AI Content Generation API ───────────────────────────────────────────────

export interface GeneratedCaption {
  caption: string;
  hashtags: string[];
  tone: string;
  target_audience: string;
  cta: string;
  emoji_usage: string;
}

export async function generateCaption(trendName: string, tone: string = "casual", niche: string = "general"): Promise<GeneratedCaption> {
  const params = new URLSearchParams();
  params.set('trend_name', trendName);
  params.set('tone', tone);
  params.set('niche', niche);
  return http(`/api/ai/generate-caption?${params}`);
}

export interface ContentIdea {
  title: string;
  description: string;
  content_type: string;
  niche: string;
  difficulty: string;
  estimated_engagement: string;
  required_resources: string[];
  script_outline: string[];
  suggested_hashtags: string[];
}

export async function generateContentIdeas(niche: string = "general", count: number = 5): Promise<{
  content_ideas: ContentIdea[];
  total_ideas: number;
}> {
  const params = new URLSearchParams();
  params.set('niche', niche);
  params.set('count', count.toString());
  return http(`/api/ai/content-ideas?${params}`);
}

export interface HookSuggestion {
  hook_text: string;
  hook_type: string;
  estimated_retention: number;
  best_for_content: string[];
}

export async function generateAIHooks(topic: string, count: number = 5): Promise<{
  hooks: HookSuggestion[];
  total_hooks: number;
}> {
  const params = new URLSearchParams();
  params.set('topic', topic);
  params.set('count', count.toString());
  return http(`/api/ai/generate-hooks?${params}`);
}

export async function generateScriptOutline(contentType: string = "reel", topic: string = "general", durationSeconds: number = 30): Promise<{
  script_outline: string[];
  content_type: string;
  topic: string;
  duration_seconds: number;
}> {
  const params = new URLSearchParams();
  params.set('content_type', contentType);
  params.set('topic', topic);
  params.set('duration_seconds', durationSeconds.toString());
  return http(`/api/ai/script-outline?${params}`);
}

// ── India-Specific Features API ───────────────────────────────────────────

export interface RegionalTrend {
  region: string;
  city: string;
  language: string;
  trend_name: string;
  viral_score: number;
  cultural_context: string;
  peak_hours: number[];
  hashtags: string[];
  content_themes: string[];
}

export async function getRegionalTrends(region?: string): Promise<{
  regional_trends: RegionalTrend[];
  total_trends: number;
}> {
  const params = new URLSearchParams();
  if (region) params.set('region', region);
  return http(`/api/india/regional-trends?${params}`);
}

export async function getRegionalTimingOptimization(region: string = "north"): Promise<{
  region: string;
  city: string;
  peak_hours: number[];
  secondary_hours: number[];
  best_days: string[];
  timezone_offset: string;
  cultural_considerations: string[];
}> {
  const params = new URLSearchParams();
  params.set('region', region);
  return http(`/api/india/regional-timing?${params}`);
}

export interface CulturalEvent {
  event_name: string;
  event_date: string;
  region: string;
  content_automation: string[];
  hashtag_strategy: string[];
  timing_recommendations: string[];
  content_themes: string[];
  creator_opportunities: string[];
}

export async function getCulturalEventAutomation(daysAhead: number = 30): Promise<{
  cultural_events: CulturalEvent[];
  total_events: number;
}> {
  const params = new URLSearchParams();
  params.set('days_ahead', daysAhead.toString());
  return http(`/api/india/cultural-events?${params}`);
}

export async function detectLanguageCrossover(content: string): Promise<{
  detected_languages: Record<string, number>;
  content: string;
}> {
  return http('/api/india/detect-language', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  });
}

export async function getRegionalHashtagStrategy(region: string = "north", contentType: string = "general"): Promise<{
  regional: string[];
  city_specific: string[];
  language_specific: string[];
  cultural: string[];
}> {
  const params = new URLSearchParams();
  params.set('region', region);
  params.set('content_type', contentType);
  return http(`/api/india/hashtag-strategy?${params}`);
}

export async function getCreatorPatternAnalysis(creatorRegion: string = "north"): Promise<{
  region: string;
  peak_content_hours: number[];
  popular_languages: string[];
  cultural_themes: string[];
  content_preferences: {
    video_length: string;
    music_preference: string;
    caption_style: string;
    posting_frequency: string;
  };
  audience_insights: {
    primary_age_group: string;
    gender_distribution: string;
    engagement_pattern: string;
    content_type_preference: string;
  };
  success_factors: string[];
}> {
  const params = new URLSearchParams();
  params.set('creator_region', creatorRegion);
  return http(`/api/india/creator-patterns?${params}`);
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

// ── Admin API Functions ───────────────────────────────────────────────────────────

export async function getAdminUsers(search?: string, planFilter?: string): Promise<any> {
  const params = new URLSearchParams();
  if (search) params.append("search", search);
  if (planFilter && planFilter !== "all") params.append("plan_filter", planFilter);
  
  return http<any>(`/api/admin/users?${params.toString()}`, {
    headers: {
      "X-Admin-Key": import.meta.env.VITE_ADMIN_KEY || "trendrop_dev_admin_secret_key_2026"
    }
  });
}

export async function getAdminUserDetails(email: string): Promise<any> {
  return http<any>(`/api/admin/users/${encodeURIComponent(email)}`, {
    headers: {
      "X-Admin-Key": import.meta.env.VITE_ADMIN_KEY || "trendrop_dev_admin_secret_key_2026"
    }
  });
}

export async function updateAdminUserPlan(email: string, newPlan: string, reason?: string): Promise<any> {
  return http<any>(`/api/admin/users/${encodeURIComponent(email)}/plan`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": import.meta.env.VITE_ADMIN_KEY || "trendrop_dev_admin_secret_key_2026"
    },
    body: JSON.stringify({ new_plan: newPlan, reason }),
  });
}

export async function lockAdminUserAccount(email: string, reason?: string): Promise<any> {
  return http<any>(`/api/admin/users/${encodeURIComponent(email)}/lock`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": import.meta.env.VITE_ADMIN_KEY || "trendrop_dev_admin_secret_key_2026"
    },
    body: JSON.stringify({ reason }),
  });
}

export async function unlockAdminUserAccount(email: string, reason?: string): Promise<any> {
  return http<any>(`/api/admin/users/${encodeURIComponent(email)}/unlock`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": import.meta.env.VITE_ADMIN_KEY || "trendrop_dev_admin_secret_key_2026"
    },
    body: JSON.stringify({ reason }),
  });
}

export async function getAdminBusinessMetrics(days: number = 30): Promise<any> {
  return http<any>(`/api/admin/business-metrics?days=${days}`, {
    headers: {
      "X-Admin-Key": import.meta.env.VITE_ADMIN_KEY || "trendrop_dev_admin_secret_key_2026"
    }
  });
}

export async function getAdminSuspiciousActivity(days: number = 7): Promise<any> {
  return http<any>(`/api/admin/suspicious-activity?days=${days}`, {
    headers: {
      "X-Admin-Key": import.meta.env.VITE_ADMIN_KEY || "trendrop_dev_admin_secret_key_2026"
    }
  });
}

export async function resolveAdminSuspiciousActivity(activityId: number, resolution?: string): Promise<any> {
  return http<any>(`/api/admin/suspicious-activity/${activityId}/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": import.meta.env.VITE_ADMIN_KEY || "trendrop_dev_admin_secret_key_2026"
    },
    body: JSON.stringify({ resolution }),
  });
}

export async function getAdminPlanFeatures(): Promise<any> {
  return http<any>("/api/admin/plan-features", {
    headers: {
      "X-Admin-Key": import.meta.env.VITE_ADMIN_KEY || "trendrop_dev_admin_secret_key_2026"
    }
  });
}

export async function createAdminPlanFeature(data: any): Promise<any> {
  return http<any>("/api/admin/plan-features", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": import.meta.env.VITE_ADMIN_KEY || "trendrop_dev_admin_secret_key_2026"
    },
    body: JSON.stringify(data),
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
  audio_id?: string | null;
  audio_use_count?: number;
  hashtags: string[];
  caption: string;
  velocity_score: number;
  video_url?: string;
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



