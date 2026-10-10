import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Sparkles, TrendingUp, Clock, AlertCircle, Zap,
  Music2, ExternalLink, RefreshCw, Flame, Disc, Radio
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PlanGate } from "./PlanGate";
import { apiFetch } from "@/lib/api";
import { useUserStore } from "@/store/useAppStore";
import { useEffectivePlan } from "@/lib/plan";

interface AlreadyTrendingTrack {
  id: number | string;
  audio_title: string;
  audio_artist: string;
  instagram_audio_id?: string;
  instagram_audio_url?: string;
  status?: string;
  velocity_avg?: number;
  window_hours_remaining?: number;
  language?: string;
  data_source?: string;
}

interface NewOnSpotifyTrack {
  id: number | string;
  audio_title: string;
  audio_artist: string;
  spotify_id?: string;
  spotify_url?: string;
  cover_art_url?: string;
  release_date?: string;
  ig_reel_count?: number;
  popularity?: number;
  data_source?: string;
}

interface SpotifyApiResponse {
  already_trending?: AlreadyTrendingTrack[];
  new_on_spotify?: NewOnSpotifyTrack[];
}

export function EarlyDetectionPanel() {
  const [alreadyTrending, setAlreadyTrending] = useState<AlreadyTrendingTrack[]>([]);
  const [newOnSpotify, setNewOnSpotify] = useState<NewOnSpotifyTrack[]>([]);
  const [loading, setLoading] = useState(true);
  const [fallbackReason, setFallbackReason] = useState<string | null>(null);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);

  // Order 70 Part 1.1: Early signals flag reset to false
  const SHOW_EARLY_SIGNALS = false;
  const [earlySignals, setEarlySignals] = useState<any[]>([]);

  const userPlan = useEffectivePlan();

  useEffect(() => {
    fetchTracks();
  }, []);

  const fetchTracks = async () => {
    setLoading(true);
    setFallbackReason(null);
    try {
      const res = await apiFetch("/api/spotify/viral");
      const fallback = res.headers.get("X-Fallback-Reason");
      if (fallback) setFallbackReason(fallback);

      if (res.ok) {
        const data: SpotifyApiResponse = await res.json();
        if (data && (Array.isArray(data.already_trending) || Array.isArray(data.new_on_spotify))) {
          setAlreadyTrending(data.already_trending || []);
          setNewOnSpotify(data.new_on_spotify || []);
          setLastRefreshed(new Date());
        }
      }

      if (SHOW_EARLY_SIGNALS) {
        try {
          const wlRes = await apiFetch("/api/trends/watchlist?limit=10");
          if (wlRes.ok) {
            const wlData = await wlRes.json();
            setEarlySignals(wlData || []);
          }
        } catch (e) {
          console.debug("watchlist fetch error:", e);
        }
      }
    } catch (err) {
      console.error("spotify/viral fetch error:", err);
    }

    setLoading(false);
  };

  const getStatusBadge = (status?: string) => {
    switch (status?.toLowerCase()) {
      case "rising":
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-green-500/10 text-green-400 border border-green-500/20 rounded-full flex items-center gap-1"><Flame className="w-3 h-3" /> Rising</span>;
      case "emerging":
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-full flex items-center gap-1"><Sparkles className="w-3 h-3" /> Emerging</span>;
      case "resurging":
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded-full flex items-center gap-1"><RefreshCw className="w-3 h-3" /> Resurging</span>;
      default:
        return <span className="px-2 py-0.5 text-[10px] font-bold bg-secondary text-muted-foreground border border-border rounded-full">Active</span>;
    }
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

  const totalCount = alreadyTrending.length + newOnSpotify.length;

  return (
    <PlanGate
      feature="Early Detection"
      requiredPlan="pro"
      currentPlan={userPlan}
      onUpgrade={() => (window.location.href = "/pricing")}
    >
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-border/40 pb-5">
          <div>
            <h2 className="text-xl font-bold font-display flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-500/10 border border-green-500/30 flex items-center justify-center text-green-400">
                <Radio className="h-4 w-4 animate-pulse" />
              </div>
              Spotify Radar & IG Virality
              <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full border bg-green-500/10 border-green-500/30 text-green-400">
                🟢 Live Search Ingested
              </span>
            </h2>
            <p className="text-xs text-muted-foreground mt-1">
              Catch songs on Spotify before they hit Instagram Reels virality
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
            className="rounded-full gap-1.5 text-xs h-8 shrink-0 hover:bg-green-500/10 hover:text-green-400 hover:border-green-500/30 transition-all"
            onClick={fetchTracks}
          >
            <RefreshCw className="h-3 w-3" />
            Refresh
          </Button>
        </div>

        {/* Fallback warning banner if any */}
        {fallbackReason && (
          <div className="flex items-start gap-3 p-3.5 rounded-xl bg-yellow-500/10 border border-yellow-500/20">
            <AlertCircle className="h-4 w-4 text-yellow-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-yellow-300">Spotify Data Notice</p>
              <p className="text-[11px] text-muted-foreground mt-0.5">
                {fallbackReason}
              </p>
            </div>
          </div>
        )}

        {totalCount === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Music2 className="h-12 w-12 text-muted-foreground/60 mb-3" />
            <p className="text-sm font-semibold text-muted-foreground">No Spotify tracks available right now</p>
            <p className="text-xs text-muted-foreground mt-1 max-w-xs">
              Our Spotify ingester updates regularly. Click below to try fetching again.
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
          <div className="space-y-8">
            {/* SECTION 1: ALREADY TRENDING ON INSTAGRAM */}
            {alreadyTrending.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Flame className="h-4 w-4 text-orange-500" />
                    <h3 className="text-sm font-bold font-display tracking-tight text-foreground uppercase">
                      Already Trending on Instagram
                    </h3>
                    <span className="text-[11px] font-semibold text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded-full border border-orange-500/20">
                      {alreadyTrending.length} Active
                    </span>
                  </div>
                  <span className="text-[11px] text-muted-foreground">Top active IG Audio trends</span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {alreadyTrending.map((track, idx) => (
                    <motion.div
                      key={`trending_${track.id}_${idx}`}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.04 }}
                      className="bg-card/80 border border-border/80 hover:border-orange-500/40 p-4 rounded-xl transition-all hover:shadow-md group relative overflow-hidden"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            {getStatusBadge(track.status)}
                            {track.window_hours_remaining != null && (
                              <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                                <Clock className="w-3 h-3 text-amber-400" />
                                {track.window_hours_remaining}h window left
                              </span>
                            )}
                          </div>
                          <h4 className="text-sm font-semibold font-display truncate text-foreground group-hover:text-orange-400 transition-colors">
                            {track.audio_title}
                          </h4>
                          <p className="text-xs text-muted-foreground truncate mt-0.5">
                            {track.audio_artist}
                          </p>
                        </div>
                        {track.instagram_audio_url && (
                          <a
                            href={track.instagram_audio_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-gradient-to-r from-purple-500/10 to-pink-500/10 hover:from-purple-500/20 hover:to-pink-500/20 text-pink-400 border border-pink-500/30 transition-all shrink-0"
                          >
                            <ExternalLink className="h-3 w-3" />
                            Use on IG
                          </a>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </div>
            )}

            {/* SECTION 2: NEW ON SPOTIFY (PRE-INSTAGRAM VIRALITY) */}
            {newOnSpotify.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Disc className="h-4 w-4 text-green-500 animate-spin-slow" />
                    <h3 className="text-sm font-bold font-display tracking-tight text-foreground uppercase">
                      New on Spotify
                    </h3>
                    <span className="text-[11px] font-semibold text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full border border-green-500/20">
                      {newOnSpotify.length} Tracks
                    </span>
                  </div>
                  <span className="text-[11px] text-muted-foreground">Pre-virality Spotify releases (Zero IG overlap)</span>
                </div>

                <div className="space-y-2.5">
                  {newOnSpotify.map((track, idx) => (
                    <motion.div
                      key={`spotify_${track.id}_${idx}`}
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: idx * 0.03 }}
                      className="bg-card border border-border/70 p-3.5 rounded-xl hover:border-green-500/40 transition-all hover:shadow-md flex items-center justify-between gap-4 group"
                    >
                      <div className="flex items-center gap-3.5 min-w-0 flex-1">
                        {track.cover_art_url ? (
                          <img
                            src={track.cover_art_url}
                            alt={track.audio_title}
                            className="w-11 h-11 rounded-lg object-cover border border-border/60 shrink-0 group-hover:scale-105 transition-transform"
                          />
                        ) : (
                          <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-950/40 border border-green-500/30 flex items-center justify-center text-green-400 shrink-0">
                            <Music2 className="h-5 w-5" />
                          </div>
                        )}

                        <div className="min-w-0 flex-1">
                          <h4 className="text-sm font-semibold font-display truncate text-foreground group-hover:text-green-400 transition-colors">
                            {track.audio_title}
                          </h4>
                          <div className="flex items-center gap-2.5 text-xs text-muted-foreground mt-0.5 flex-wrap">
                            <span className="truncate">{track.audio_artist}</span>
                            {track.release_date && (
                              <span className="opacity-60 text-[11px]">
                                · Released {track.release_date}
                              </span>
                            )}
                            {track.popularity != null && track.popularity > 0 && (
                              <span className="inline-flex items-center gap-1 text-[10px] text-green-400/90 font-medium">
                                <TrendingUp className="h-3 w-3" /> {track.popularity}/100 pop
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {track.spotify_url && (
                        <a
                          href={track.spotify_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-green-500/10 hover:bg-green-500/20 text-green-400 border border-green-500/30 transition-all shrink-0"
                        >
                          <ExternalLink className="h-3 w-3" />
                          Spotify
                        </a>
                      )}
                    </motion.div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Order 65 Part 7.1: Minimal read-only 'Early signals' section behind feature flag */}
        {SHOW_EARLY_SIGNALS && earlySignals.length > 0 && (
          <div className="space-y-4 pt-4 border-t border-border/40">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <h3 className="text-sm font-semibold font-display text-foreground">Early Signals (Watchlist)</h3>
            </div>
            <div className="grid gap-2">
              {earlySignals.map((item, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 rounded-xl bg-card/60 border border-border/50 text-xs">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-foreground truncate">{item.song_key || item.audio_id}</p>
                    <p className="text-muted-foreground text-[11px]">Score: {item.score} · Creators: {item.first_creators || 0} · Reels: {item.first_reels || 0}</p>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-medium uppercase tracking-wide">
                    {item.status || "active"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Informational banner */}
        <div className="bg-gradient-to-r from-green-500/5 to-primary/5 border border-green-500/10 p-4 rounded-2xl">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-green-500/15 flex items-center justify-center text-green-400 shrink-0">
              <Zap className="h-4 w-4" />
            </div>
            <div>
              <h4 className="text-sm font-semibold font-display mb-1">Spotify Early Detection Strategy</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Tracks in <strong className="text-green-400">New on Spotify</strong> are fresh releases scanned directly from Spotify search queries (`tag:new year:2025-2026`). 
                They have <strong className="text-foreground">0 overlap</strong> with existing Instagram trends, enabling you to discover breakout tracks before they hit saturated Instagram audio rails.
              </p>
            </div>
          </div>
        </div>
      </div>
    </PlanGate>
  );
}