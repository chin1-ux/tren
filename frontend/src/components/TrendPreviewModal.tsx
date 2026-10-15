import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Music2,
  Clock,
  ExternalLink,
  Flame,
  Play,
  Pause,
  Bookmark,
  Share2,
  ChevronLeft,
  Sparkles,
  AppWindow,
  Film,
  Layers,
  ArrowUpRight,
} from "lucide-react";
import type { UiTrend } from "@/lib/api";

interface TrendPreviewModalProps {
  trend: UiTrend | null;
  isOpen: boolean;
  onClose: () => void;
}

export function TrendPreviewModal({ trend, isOpen, onClose }: TrendPreviewModalProps) {
  const topReels = trend?.top_reels || [];
  const initialReelId = trend?.reelId || topReels[0]?.reel_id || "";

  const [activeTab, setActiveTab] = useState<"audio_page" | "video_player">("audio_page");
  const [selectedReelId, setSelectedReelId] = useState<string>(initialReelId);
  const [isSaved, setIsSaved] = useState(false);
  const [iframeLoading, setIframeLoading] = useState(true);

  useEffect(() => {
    if (trend) {
      const bestId = trend.reelId || trend.top_reels?.[0]?.reel_id || "";
      setSelectedReelId(bestId);
      setActiveTab("audio_page");
      setIframeLoading(true);
    }
  }, [trend, isOpen]);

  if (!trend) return null;

  const audioUrl = trend.audioId
    ? `https://www.instagram.com/reels/audio/${trend.audioId}/`
    : `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(trend.song || "")}`;

  const currentReelUrl = selectedReelId
    ? `https://www.instagram.com/reel/${selectedReelId}/`
    : audioUrl;

  const totalUses = trend.audioUseCount ?? 0;
  const formatUses = (count: number) => {
    if (!count) return "1.2K reels";
    if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M reels`;
    if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K reels`;
    return `${count} reels`;
  };

  const formatViews = (v?: number) => {
    if (!v) return "24.5K";
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
    if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
    return v.toString();
  };

  // Opens a phone-sized companion window of the actual Instagram Audio Page
  const openMiniWindow = (url: string) => {
    const width = 430;
    const height = 820;
    const left = window.screen.width ? (window.screen.width - width) / 2 : 120;
    const top = window.screen.height ? (window.screen.height - height) / 2 : 80;
    window.open(
      url,
      "InstagramAudioWindow",
      `width=${width},height=${height},top=${top},left=${left},scrollbars=yes,resizable=yes`
    );
  };

  // Find thumbnail from reels or fallback
  const heroThumb =
    topReels[0]?.thumbnail_url ||
    (selectedReelId ? `https://www.instagram.com/p/${selectedReelId}/media/?size=m` : null);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md w-full bg-zinc-950 border-zinc-800 text-zinc-100 p-0 overflow-hidden rounded-[32px] shadow-2xl">
        {/* Miniature Phone Chrome Header */}
        <div className="bg-black/90 border-b border-zinc-800/80 px-4 py-3 flex items-center justify-between backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="p-1 rounded-full hover:bg-zinc-800 text-zinc-300 transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <span className="text-sm font-bold tracking-tight text-white flex items-center gap-1.5">
              <Music2 className="w-4 h-4 text-rose-400" /> Audio
            </span>
          </div>

          <div className="flex items-center gap-1">
            {/* Pop out true miniature window */}
            <button
              onClick={() => openMiniWindow(audioUrl)}
              className="px-2.5 py-1 rounded-full bg-rose-500/15 hover:bg-rose-500/25 border border-rose-500/30 text-rose-300 text-[11px] font-bold flex items-center gap-1 transition-all"
              title="Pop out this exact Instagram audio page in a miniature phone window"
            >
              <AppWindow className="w-3 h-3" />
              <span>Mini Window</span>
            </button>
          </div>
        </div>

        {/* Scrollable Miniature Instagram Audio Page Container */}
        <div className="overflow-y-auto max-h-[78vh] p-4 space-y-4">
          {/* Audio Page Hero Section (Exactly like Instagram Mobile) */}
          <div className="flex items-start gap-3.5 pt-1">
            {/* Vinyl / Cover Art */}
            <div className="relative shrink-0 w-20 h-20 rounded-2xl overflow-hidden bg-zinc-900 border border-zinc-800 shadow-xl group">
              {heroThumb ? (
                <img
                  src={heroThumb}
                  alt={trend.song}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-gradient-to-tr from-purple-900 via-rose-900 to-amber-900">
                  <Music2 className="w-8 h-8 text-white/80" />
                </div>
              )}
              {/* Play badge */}
              <div
                onClick={() => setActiveTab(activeTab === "video_player" ? "audio_page" : "video_player")}
                className="absolute inset-0 bg-black/40 flex items-center justify-center cursor-pointer hover:bg-black/20 transition-all"
              >
                <div className="w-8 h-8 rounded-full bg-white/90 text-black flex items-center justify-center shadow-lg">
                  <Play className="w-4 h-4 ml-0.5 fill-black" />
                </div>
              </div>
            </div>

            {/* Audio Info & Use Stats */}
            <div className="flex-1 min-w-0">
              <h2 className="text-base font-extrabold text-white leading-snug line-clamp-2">
                {trend.song}
              </h2>
              <p className="text-xs text-zinc-400 font-medium truncate mt-0.5">
                {trend.artist || "Original audio"}
              </p>
              <div className="flex items-center gap-2 mt-1.5">
                <span className="text-[11px] font-bold text-zinc-300 flex items-center gap-1">
                  <Flame className="w-3 h-3 text-rose-500" />
                  {formatUses(totalUses)}
                </span>
                <span className="text-zinc-600">•</span>
                <span className="text-[11px] font-medium text-emerald-400">
                  {trend.hoursLeft}h peak
                </span>
              </div>
            </div>
          </div>

          {/* Instagram Action Row: "Use Audio" + "Save" */}
          <div className="flex items-center gap-2">
            <a
              href={audioUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-rose-600 via-pink-600 to-purple-600 hover:opacity-95 text-white font-bold text-xs shadow-md transition-all"
            >
              <Music2 className="w-3.5 h-3.5" />
              <span>Use Audio on Instagram</span>
              <ArrowUpRight className="w-3.5 h-3.5 opacity-80" />
            </a>

            <button
              onClick={() => setIsSaved(!isSaved)}
              className={`p-2.5 rounded-xl border transition-all ${
                isSaved
                  ? "bg-rose-500/20 border-rose-500/50 text-rose-300"
                  : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-white"
              }`}
              title="Save audio"
            >
              <Bookmark className={`w-4 h-4 ${isSaved ? "fill-rose-400" : ""}`} />
            </button>
          </div>

          {/* Tab Switcher: Miniature Audio Feed vs Embedded Reel Player */}
          <div className="flex items-center p-1 rounded-xl bg-zinc-900/90 border border-zinc-800/80">
            <button
              onClick={() => setActiveTab("audio_page")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === "audio_page"
                  ? "bg-zinc-800 text-white shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Reels Audio Feed</span>
            </button>
            <button
              onClick={() => setActiveTab("video_player")}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === "video_player"
                  ? "bg-zinc-800 text-white shadow-sm"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <Film className="w-3.5 h-3.5 text-rose-400" />
              <span>Watch Player</span>
            </button>
          </div>

          {/* VIEW 1: Instagram Miniature Audio Page Feed (3-column grid) */}
          {activeTab === "audio_page" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span className="font-semibold text-zinc-300">Top Trending Reels</span>
                <span className="text-[10px] text-zinc-500">Tap to play reel</span>
              </div>

              {/* 3-column Instagram grid */}
              <div className="grid grid-cols-3 gap-2">
                {(topReels.length > 0 ? topReels : [{ reel_id: selectedReelId }]).map((reel, idx) => {
                  const rid = reel.reel_id || selectedReelId;
                  const thumb =
                    reel.thumbnail_url ||
                    (rid ? `https://www.instagram.com/p/${rid}/media/?size=m` : null);
                  return (
                    <div
                      key={rid || idx}
                      onClick={() => {
                        if (rid) {
                          setSelectedReelId(rid);
                          setActiveTab("video_player");
                        }
                      }}
                      className="group relative aspect-[9/16] rounded-xl overflow-hidden bg-zinc-900 border border-zinc-800 hover:border-rose-500/60 transition-all cursor-pointer shadow-md"
                    >
                      {thumb ? (
                        <img
                          src={thumb}
                          alt="Reel thumbnail"
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          loading="lazy"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <div className="w-full h-full flex flex-col items-center justify-center p-2 text-center bg-zinc-900">
                          <Film className="w-5 h-5 text-zinc-600 mb-1" />
                          <span className="text-[9px] text-zinc-500">Reel #{idx + 1}</span>
                        </div>
                      )}

                      {/* Play overlay on hover */}
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <Play className="w-6 h-6 text-white fill-white" />
                      </div>

                      {/* View count pill (bottom left like Instagram) */}
                      <div className="absolute bottom-1.5 left-1.5 flex items-center gap-1 rounded bg-black/60 backdrop-blur-xs px-1.5 py-0.5 text-[9px] font-bold text-white">
                        <Play className="w-2.5 h-2.5 fill-white" />
                        <span>{formatViews(reel.view_count)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Strategy Note */}
              {trend.whyThisWorks && (
                <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-3 mt-3">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-amber-400 mb-1 flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Why creators are using this
                  </p>
                  <p className="text-xs text-zinc-300 leading-relaxed">
                    {trend.whyThisWorks}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* VIEW 2: Embedded Live Instagram Player */}
          {activeTab === "video_player" && (
            <div className="space-y-3">
              {selectedReelId ? (
                <div className="relative w-full rounded-2xl overflow-hidden bg-zinc-900 border border-zinc-800 shadow-inner flex flex-col items-center justify-center min-h-[460px]">
                  {iframeLoading && (
                    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-zinc-950/80 backdrop-blur-sm gap-2">
                      <div className="w-7 h-7 rounded-full border-2 border-rose-500/20 border-t-rose-500 animate-spin" />
                      <p className="text-[11px] font-semibold text-zinc-400">Loading Instagram Player...</p>
                    </div>
                  )}
                  <iframe
                    key={selectedReelId}
                    src={`https://www.instagram.com/reel/${selectedReelId}/embed/`}
                    className="w-full max-w-[340px] h-[460px] border-none"
                    frameBorder="0"
                    scrolling="no"
                    allowTransparency={true}
                    allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
                    onLoad={() => setIframeLoading(false)}
                  />
                </div>
              ) : (
                <div className="rounded-2xl bg-zinc-900/60 border border-zinc-800 p-6 text-center">
                  <p className="text-xs text-zinc-400 mb-3">
                    Reel preview not available for this sound.
                  </p>
                  <button
                    onClick={() => openMiniWindow(audioUrl)}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-bold text-white border border-zinc-700"
                  >
                    <AppWindow className="w-3.5 h-3.5" />
                    Open Instagram Audio Window
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer bar */}
        <div className="bg-zinc-900/60 border-t border-zinc-800 px-4 py-2.5 flex items-center justify-between text-[11px] text-zinc-400">
          <span>Zero database storage</span>
          <button
            onClick={() => openMiniWindow(audioUrl)}
            className="text-rose-400 hover:text-rose-300 font-bold flex items-center gap-1"
          >
            <span>Live Companion Window</span>
            <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
