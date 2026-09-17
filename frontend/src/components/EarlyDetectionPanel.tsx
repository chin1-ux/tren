import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Sparkles, TrendingUp, Clock, AlertCircle, Zap,
  Music2, ExternalLink, RefreshCw, Info
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { PlanGate } from "./PlanGate";
import { apiFetch } from "@/lib/api";
import { useUserStore } from "@/store/useAppStore";

interface SpotifyTrack {
  id: string;
  audio_title: string;
  audio_artist: string;
  spotify_id?: string;
  market: string;
  market_label: string;
  rank: number;
  popularity?: number;
  release_date?: string;
  data_source?: string;
  prediction: {
    combined_score: number;
    prediction: string;
    optimal_timing: string;
    reach_multiplier: string;
    recommended_action: string;
  };
}

// Map raw API shape (emerging trend) → SpotifyTrack shape
function mapEarlyTrend(t: any): SpotifyTrack | null {
  if (!t || t.id == null) return null;
  // Already in correct shape (from /api/spotify/viral)
  if (t?.prediction?.combined_score != null && t.audio_title) return t as SpotifyTrack;
  // Map from /api/trends/emerging shape
  if (t.status !== "emerging" && t.status !== "rising") return null;
  const fit = typeof t.creator_fit_score === "number" ? t.creator_fit_score : null;
  const hook = typeof t.hook_retention_score === "number" ? t.hook_retention_score : null;
  const sat = typeof t.saturation_penalty === "number" ? t.saturation_penalty : null;
  if (fit == null || hook == null || sat == null) return null;
  const score = Math.round(100 * Math.min(1, Math.max(0, 0.4 * fit + 0.35 * hook + 0.25 * (1 - sat))));
  const hoursLeft = Number.isFinite(t.window_hours_remaining)
    ? Math.max(0, Math.round(t.window_hours_remaining))
    : null;
  const timing = Number.isFinite(t.optimal_post_hour_ist)
    ? `${String(Math.floor(t.optimal_post_hour_ist)).padStart(2, "0")}:00 IST`
    : "N/A";
  return {
    id: t.id,
    audio_title: t.audio_title ?? "Unknown audio",
    audio_artist: t.audio_artist ?? "",
    market: "IN",
    market_label: "🇮🇳 India",
    rank: 0,
    prediction: {
      combined_score: score,
      prediction: t.status ?? "",
      optimal_timing: timing,
      reach_multiplier: `${score}%`,
      recommended_action:
        hoursLeft == null || hoursLeft <= 0
          ? "WINDOW CLOSED"
          : hoursLeft < 12
          ? "POST SOON"
          : "CREATE CONTENT NOW",
    },
  };
}

// Filter: only show tracks that are not clearly vintage (>= 3 years old)
function isRecentEnough(track: SpotifyTrack): boolean {
  if (!track.release_date) return true; // unknown date — let it through
  try {
    const releaseYear = parseInt(track.release_date.split("-")[0], 10);
    const currentYear = new Date().getFullYear();
    return currentYear - releaseYear <= 3;
  } catch {
    return true;
  }
}

const ACTION_COLOR: Record<string, string> = {
  "POST NOW": "text-green-400",
  "POST SOON": "text-yellow-400",
  "EARLY ENTRY WINDOW": "text-blue-400",
  "CREATE CONTENT NOW": "text-green-400",
  "WINDOW CLOSED": "text-muted-foreground line-through",
};

export function EarlyDetectionPanel() {
  const [tracks, setTracks] = useState<SpotifyTrack[]>([]);
  const [loading, setLoading] = useState(true);
  const [fallbackReason, setFallbackReason] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<string>("none");
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  const userPlan = useUserStore((s) => s.plan) || "free";

  useEffect(() => {
    fetchTracks();
  }, []);

  const fetchTracks = async () => {
    setLoading(true);
    setFallbackReason(null);
    try {
      const res = await apiFetch("/api/spotify/viral");

      // Read quality headers
      const fallback = res.headers.get("X-Fallback-Reason");
      const source = res.headers.get("X-Data-Source") ?? "search";
      setDataSource(source);
      if (fallback) setFallbackReason(fallback);

      if (res.ok) {
        const data: SpotifyTrack[] = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          const filtered = data.filter(isRecentEnough);
          setTracks(filtered);
          setLastRefreshed(new Date());
          setLoading(false);
          return;
        }
      }
    } catch (err) {
      console.error("spotify/viral fetch error:", err);
    }

    // Fallback: try /api/trends/emerging
    try {
      const res2 = await apiFetch("/api/trends/emerging");
      if (res2.ok) {
        const data2 = await res2.json();
        const mapped = (data2 || []).map(mapEarlyTrend).filter(Boolean) as SpotifyTrack[];
        setTracks(mapped.filter(isRecentEnough));
        setDataSource("emerging");
        setLastRefreshed(new Date());
      }
    } catch (err2) {
      console.error("trends/emerging fetch error:", err2);
    }

    setLoading(false);
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "text-green-400";
    if (score >= 65) return "text-yellow-400";
    return "text-orange-400";
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return "bg-green-500/10 border-green-500/20";
    if (score >= 65) return "bg-yellow-500/10 border-yellow-500/20";
    return "bg-orange-500/10 border-orange-500/20";
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 bg-card/50 border border-border/50 animate-pulse rounded-2xl" />
        ))}
      </div>
    );
  }

  return (
    <PlanGate
      feature="Early Detection"
      requiredPlan="pro"
      currentPlan={userPlan}
      onUpgrade={() => (window.location.href = "/pricing")}
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold font-display flex items-center gap-2">
              <Music2 className="h-5 w-5 text-green-500" />
              Spotify Viral Tracks
              {/* Live / stale indicator */}
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                  fallbackReason
                    ? "bg-yellow-500/10 border-yellow-500/30 text-yellow-400"
                    : "bg-green-500/10 border-green-500/30 text-green-400"
                }`}
              >
                {fallbackReason ? "⚠ Cached" : "🟢 Live"}
              </span>
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {tracks.length > 0
                ? `${tracks.length} trending audios — use before they saturate`
                : "No tracks available right now"}
              {lastRefreshed && (
                <span className="ml-2 opacity-60">
                  · refreshed {lastRefreshed.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                </span>
              )}
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="rounded-full gap-1.5 text-xs h-8 shrink-0"
            onClick={fetchTracks}
          >
            <RefreshCw className="h-3 w-3" />
            Refresh
          </Button>
        </div>

        {/* Fallback warning banner */}
        {fallbackReason && (
          <div className="flex items-start gap-3 p-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
            <AlertCircle className="h-4 w-4 text-yellow-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-yellow-300">Spotify data temporarily unavailable</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                {fallbackReason === "spotify_credentials_error"
                  ? "API credentials need renewal. Showing cached tracks from trends database."
                  : fallbackReason === "spotify_search_empty"
                  ? "Spotify returned no results for current queries. Check back in a few minutes."
                  : "Spotify connection issue. Data may be slightly delayed."}
              </p>
            </div>
          </div>
        )}

        {/* Empty state */}
        {tracks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Music2 className="h-12 w-12 text-muted-foreground mb-3" />
            <p className="text-sm font-semibold text-muted-foreground">No viral tracks right now</p>
            <p className="text-xs text-muted-foreground mt-1 max-w-xs">
              Our Spotify pipeline refreshes every hour. Try refreshing or check back soon.
            </p>
            <Button
              size="sm"
              variant="outline"
              className="mt-4 rounded-full gap-1.5 text-xs"
              onClick={fetchTracks}
            >
              <RefreshCw className="h-3 w-3" />
              Try Again
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {tracks.map((track, index) => {
              const score = track.prediction?.combined_score ?? 0;
              return (
                <motion.div
                  key={track.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.06 }}
                  className="bg-card border border-border p-4 rounded-2xl hover:border-primary/30 transition-all hover:shadow-md"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      {/* Title + badges row */}
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <h3 className="text-sm font-semibold font-display truncate">
                          {track.audio_title}
                        </h3>
                        {track.market_label && (
                          <span className="px-2 py-0.5 text-[10px] font-bold bg-primary/10 text-primary border border-primary/20 rounded-full shrink-0">
                            {track.market_label}
                          </span>
                        )}
                        <span
                          className={`px-2 py-0.5 text-[10px] font-bold ${getScoreBg(score)} ${getScoreColor(score)} rounded-full border`}
                        >
                          {score}% viral score
                        </span>
                      </div>

                      {/* Artist */}
                      <p className="text-xs text-muted-foreground mb-2 truncate">
                        {track.audio_artist}
                        {track.release_date && (
                          <span className="ml-2 opacity-60">· {track.release_date.split("-")[0]}</span>
                        )}
                      </p>

                      {/* Timing */}
                      <div className="flex items-center gap-3 text-[10px] text-muted-foreground flex-wrap">
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          Best time: {track.prediction?.optimal_timing ?? "N/A"}
                        </span>
                        {track.popularity != null && (
                          <span className="flex items-center gap-1">
                            <TrendingUp className="h-3 w-3" />
                            Spotify popularity: {track.popularity}/100
                          </span>
                        )}
                        {track.spotify_id && (
                          <a
                            href={`https://open.spotify.com/track/${track.spotify_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-green-500 hover:text-green-400 transition-colors"
                          >
                            <ExternalLink className="h-3 w-3" />
                            Open in Spotify
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Right panel */}
                    <div className="flex flex-col items-end gap-2 shrink-0">
                      <div
                        className={`w-12 h-12 rounded-full ${getScoreBg(score)} border flex items-center justify-center ${getScoreColor(score)} font-bold text-sm`}
                      >
                        {score}
                      </div>
                      <span
                        className={`text-[9px] font-bold text-right ${
                          ACTION_COLOR[track.prediction?.recommended_action] ?? "text-muted-foreground"
                        }`}
                      >
                        {track.prediction?.recommended_action}
                      </span>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        )}

        {/* Info banner */}
        <div className="bg-gradient-to-r from-green-500/5 to-primary/5 border border-green-500/10 p-4 rounded-2xl">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-green-500/15 flex items-center justify-center text-green-500 shrink-0">
              <Zap className="h-4 w-4" />
            </div>
            <div>
              <h4 className="text-sm font-semibold font-display mb-1">Why use trending audio early?</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Reels that use audio in the first 48h of virality get{" "}
                <span className="text-green-400 font-semibold">3–5× more reach</span> than those who
                join after saturation. These are real Spotify viral searches — not curated suggestions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </PlanGate>
  );
}