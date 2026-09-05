import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Music2, Clock, Zap, Shield, Play, Volume2, VolumeX, AlertTriangle, ExternalLink } from "lucide-react";
import { supabase } from "@/lib/supabase";
import type { UiTrend } from "@/lib/api";
import { TrendCardVideo } from "./TrendCardVideo";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

interface TrendPreviewModalProps {
  trend: UiTrend | null;
  isOpen: boolean;
  onClose: () => void;
}

export function TrendPreviewModal({ trend, isOpen, onClose }: TrendPreviewModalProps) {
  const [playlist, setPlaylist] = useState<string[]>([]);
  const [playlistIndex, setPlaylistIndex] = useState(0);
  const [isPlayingPlaylist, setIsPlayingPlaylist] = useState(false);
  const [playlistLoading, setPlaylistLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setIsPlayingPlaylist(false);
      setPlaylist([]);
    }
  }, [isOpen]);

  if (!trend) return null;

  const audioUrl = trend.audioId
    ? `https://www.instagram.com/reels/audio/${trend.audioId}/`
    : `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(trend.song || "")}`;

  const globalPct = trend.globalSaturationPct ?? 0;
  const indiaPct = trend.indiaSaturationPct ?? 0;
  const nicheTag = trend.nicheTag ?? "general";
  const hookBrief = trend.hookBrief ?? [];
  const primaryHook = hookBrief[0] ?? null;

  const handlePlayPlaylist = async () => {
    if (!trend.audioId) {
      toast.error("No Audio ID found for this trend.");
      return;
    }
    setPlaylistLoading(true);
    try {
      const { data, error } = await supabase
        .from("reels")
        .select("reel_id")
        .eq("audio_id", trend.audioId)
        .eq("video_storage_status", "stored")
        .order("view_count", { ascending: false })
        .limit(3);

      if (error) throw error;

      const validUrls = (data || [])
        .map((r: any) => r.reel_id)
        .filter(Boolean)
        .map((reelId: string) => /^\d+$/.test(reelId)
          ? `https://www.instagram.com/reels/audio/${reelId}/`
          : `https://www.instagram.com/reel/${reelId}/`) as string[];

      if (validUrls.length === 0) {
        toast.error("No Instagram deep-links are currently available for this audio trend yet.");
        return;
      }

      setPlaylist(validUrls);
      setPlaylistIndex(0);
      setIsPlayingPlaylist(true);
      window.open(validUrls[0], "_blank", "noopener,noreferrer");
      toast.success(`Opened the top ${validUrls.length} reel deep-link(s) on Instagram.`);
    } catch (err) {
      console.error("Failed to load playlist reels:", err);
      toast.error("Failed to fetch Instagram deep-links.");
    } finally {
      setPlaylistLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-zinc-950 border-zinc-800 text-zinc-100 overflow-y-auto max-h-[90vh] rounded-2xl p-6">
        <DialogHeader className="border-b border-zinc-800 pb-4 mb-4">
          <DialogTitle className="text-xl font-display font-extrabold text-white flex items-center justify-between gap-4">
            <span className="truncate">{trend.song}</span>
            <span className="text-xs font-semibold text-zinc-400 font-sans tracking-normal shrink-0">
              by {trend.artist}
            </span>
          </DialogTitle>
        </DialogHeader>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Left Column: Video Preview / Playlist Autoplay */}
          <div className="space-y-4">
            <div className="relative w-full rounded-2xl overflow-hidden bg-black/60 border border-zinc-800 flex items-center justify-center p-1">
              <TrendCardVideo
                reel={{
                  id: trend.id,
                  audio_title: trend.song,
                  audio_artist: trend.artist,
                  audio_use_count: trend.audioUseCount,
                  audio_id: trend.audioId,
                }}
                trendId={trend.id}
                opportunityScore={trend.opportunityScore}
              />
            </div>

            {trend.audioId && (
              <Button
                onClick={handlePlayPlaylist}
                disabled={playlistLoading}
                className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold py-2.5 rounded-xl shadow-lg transition-all"
              >
                {playlistLoading ? "⏳ Loading Instagram links..." : "Open Top Reel on Instagram"}
              </Button>
            )}
          </div>

          {/* Right Column: Trend intelligence information */}
          <div className="space-y-5">
            {/* Header badges */}
            <div className="flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 text-xs font-bold text-emerald-400">
                <Clock className="w-3.5 h-3.5" /> {trend.hoursLeft}h remaining
              </span>
              {!trend.isClassificationVerified && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 border border-amber-500/20 px-2.5 py-0.5 text-xs font-bold text-amber-300">
                  ⏳ Classifying
                </span>
              )}
              {nicheTag && nicheTag !== "general" && (
                <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/10 border border-blue-500/20 px-2.5 py-0.5 text-xs font-bold text-blue-400">
                  #{nicheTag}
                </span>
              )}
            </div>

            {/* Hook Brief details */}
            {primaryHook && (
              <div className="rounded-xl border border-teal-500/20 bg-teal-500/[0.03] p-4 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-teal-400">🎬 Hook Brief</h4>
                {primaryHook.hook_brief_one_line && (
                  <p className="text-sm font-medium leading-relaxed italic text-zinc-200">
                    "{primaryHook.hook_brief_one_line}"
                  </p>
                )}
                {primaryHook.dominant_hook_type && (
                  <p className="text-xs text-zinc-400">
                    Dominant Hook: <span className="font-semibold text-zinc-200 capitalize">{primaryHook.dominant_hook_type.replace(/_/g, " ")}</span>
                  </p>
                )}
              </div>
            )}

            {/* Saturation section */}
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400">📊 Saturation</h4>
              
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-zinc-400">🌍 Global Saturation</span>
                  <span className="text-white">{Math.round(globalPct)}%</span>
                </div>
                <svg viewBox="0 0 100 8" className="h-2 w-full overflow-hidden rounded-full bg-zinc-800" aria-hidden="true">
                  <rect x="0" y="0" width={Math.max(0, Math.min(100, globalPct))} height="8" rx="4" fill="#f97316" />
                </svg>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-xs font-medium">
                  <span className="text-zinc-400">🇮🇳 India Saturation</span>
                  <span className="text-white flex items-center gap-1.5">
                    {indiaPct < 30 && (
                      <span className="rounded bg-emerald-500/10 text-emerald-400 text-[10px] px-1 py-0.2 font-bold">
                        Opportunity
                      </span>
                    )}
                    {Math.round(indiaPct)}%
                  </span>
                </div>
                <svg viewBox="0 0 100 8" className="h-2 w-full overflow-hidden rounded-full bg-zinc-800" aria-hidden="true">
                  <rect x="0" y="0" width={Math.max(0, Math.min(100, indiaPct))} height="8" rx="4" fill="#10b981" />
                </svg>
              </div>
            </div>

            {/* Action buttons */}
            <div className="pt-2 space-y-3">
              <a
                href={audioUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold py-3 text-sm shadow-md transition-all duration-200"
              >
                <Music2 className="w-4 h-4" />
                <span>Save Audio on Instagram →</span>
                <ExternalLink className="w-3.5 h-3.5 opacity-80" />
              </a>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
