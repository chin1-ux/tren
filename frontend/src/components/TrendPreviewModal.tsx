import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Music2, Clock, ExternalLink, Play, Image } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { getCleanAnalysis, type UiTrend } from "@/lib/api";

interface TrendPreviewModalProps {
  trend: UiTrend | null;
  isOpen: boolean;
  onClose: () => void;
}

interface ReelPreview {
  reel_id: string;
  owner_username?: string;
  view_count?: number;
  caption?: string;
  thumbnail_url?: string | null;
}

export function TrendPreviewModal({ trend, isOpen, onClose }: TrendPreviewModalProps) {
  const [reels, setReels] = useState<ReelPreview[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen || !trend?.audioId) {
      setReels([]);
      return;
    }
    setLoading(true);
    supabase
      .from("reels")
      .select("reel_id, owner_username, view_count, caption, thumbnail_url")
      .eq("audio_id", trend.audioId)
      .order("view_count", { ascending: false })
      .limit(3)
      .then(({ data, error }) => {
        if (!error && data) setReels(data as ReelPreview[]);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [isOpen, trend?.audioId]);

  if (!trend) return null;

  const audioUrl = trend.audioId
    ? `https://www.instagram.com/reels/audio/${trend.audioId}/`
    : `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(trend.song || "")}`;

  const globalPct = trend.globalSaturationPct ?? 0;
  const indiaPct  = trend.indiaSaturationPct  ?? 0;

  const formatViews = (v?: number) => {
    if (!v) return "—";
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
    return v.toString();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg bg-zinc-950 border-zinc-800 text-zinc-100 overflow-y-auto max-h-[90vh] rounded-2xl p-5">
        <DialogHeader className="border-b border-zinc-800 pb-3 mb-3">
          <DialogTitle className="text-lg font-extrabold text-white flex items-center justify-between gap-3">
            <span className="truncate">{trend.song}</span>
            <span className="text-xs font-semibold text-zinc-400 font-sans shrink-0">by {trend.artist}</span>
          </DialogTitle>
        </DialogHeader>

        {/* Quick stats row */}
        <div className="flex flex-wrap gap-2 mb-4">
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 text-xs font-bold text-emerald-400">
            <Clock className="w-3 h-3" /> {trend.hoursLeft}h window
          </span>
          {globalPct > 0 && (
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold border ${
              globalPct < 30 ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              : globalPct < 65 ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
              : "bg-red-500/10 border-red-500/20 text-red-400"
            }`}>
              🌍 Global {Math.round(globalPct)}%
            </span>
          )}
          {indiaPct > 0 && (
            <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold border ${
              indiaPct < 30 ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              : "bg-amber-500/10 border-amber-500/20 text-amber-400"
            }`}>
              🇮🇳 India {Math.round(indiaPct)}%
            </span>
          )}
        </div>

        {/* ── Reel thumbnail grid ────────────────────────────────────────────
            Fix #4: Instagram thumbnails fetched from Supabase reels table by
            audio_id. Served by Instagram CDN — zero Supabase storage cost.
        ─────────────────────────────────────────────────────────────────── */}
        <div className="mb-4">
          <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-2 flex items-center gap-1.5">
            <Image className="h-3 w-3" /> Top Reels Using This Audio
          </p>
          {loading ? (
            <div className="grid grid-cols-3 gap-2">
              {[0, 1, 2].map((i) => (
                <div key={i} className="aspect-[9/16] rounded-xl bg-zinc-800 animate-pulse" />
              ))}
            </div>
          ) : reels.length > 0 ? (
            <div className="grid grid-cols-3 gap-2">
              {reels.map((reel) => {
                const reelUrl = `https://www.instagram.com/reel/${reel.reel_id}/`;
                // Instagram's public CDN thumbnail — no auth needed, no storage cost
                const thumbSrc =
                  reel.thumbnail_url ||
                  `https://www.instagram.com/p/${reel.reel_id}/media/?size=m`;
                return (
                  <a
                    key={reel.reel_id}
                    href={reelUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="relative group block aspect-[9/16] rounded-xl overflow-hidden bg-zinc-800 border border-zinc-700 hover:border-rose-500/60 transition-all"
                    title={`@${reel.owner_username || "creator"} — ${formatViews(reel.view_count)} views`}
                  >
                    <img
                      src={thumbSrc}
                      alt={`Reel by @${reel.owner_username}`}
                      className="w-full h-full object-cover"
                      loading="lazy"
                      onError={(e) => {
                        // hide broken img, show gradient fallback
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                    {/* Play overlay on hover */}
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-1">
                      <Play className="h-6 w-6 text-white" fill="white" />
                      <span className="text-[9px] text-white font-bold">Open on IG</span>
                    </div>
                    {/* Creator + views bar */}
                    <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-1.5">
                      <p className="text-[9px] text-white font-bold truncate">@{reel.owner_username || "creator"}</p>
                      {reel.view_count ? (
                        <p className="text-[8px] text-zinc-300">{formatViews(reel.view_count)} views</p>
                      ) : null}
                    </div>
                  </a>
                );
              })}
            </div>
          ) : (
            <div className="rounded-xl bg-zinc-900 border border-zinc-800 p-4 text-center">
              <p className="text-xs text-zinc-500">No indexed reels yet — open the audio directly on Instagram to browse.</p>
            </div>
          )}
        </div>

        {/* Why this works */}
        {(() => {
          const cleanWhy = getCleanAnalysis(trend.whyThisWorks);
          if (!cleanWhy) return null;
          return (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-3 mb-4">
              <p className="text-[9px] font-bold uppercase tracking-wider text-zinc-500 mb-1">💡 Why this works</p>
              <p className="text-xs text-zinc-300 leading-relaxed">{cleanWhy}</p>
            </div>
          );
        })()}

        {/* CTA */}
        <a
          href={audioUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 w-full rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold py-3 text-sm shadow-md transition-all duration-200"
        >
          <Music2 className="w-4 h-4" />
          <span>{trend.audioId ? "Save Audio on Instagram →" : "Search Audio on Instagram →"}</span>
          <ExternalLink className="w-3.5 h-3.5 opacity-80" />
        </a>
      </DialogContent>
    </Dialog>
  );
}
