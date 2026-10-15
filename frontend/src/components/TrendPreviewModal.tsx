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
  AppWindow,
  Play,
  Sparkles,
  Info,
} from "lucide-react";
import type { UiTrend } from "@/lib/api";

interface TrendPreviewModalProps {
  trend: UiTrend | null;
  isOpen: boolean;
  onClose: () => void;
}

export function TrendPreviewModal({ trend, isOpen, onClose }: TrendPreviewModalProps) {
  // Extract all available reel IDs from trend object (Zero database query cost!)
  const topReels = trend?.top_reels || [];
  const initialReelId =
    trend?.reelId ||
    topReels[0]?.reel_id ||
    "";

  const [selectedReelId, setSelectedReelId] = useState<string>(initialReelId);
  const [iframeLoading, setIframeLoading] = useState(true);

  // Sync selected reel when modal opens or trend changes
  useEffect(() => {
    if (trend) {
      const bestId = trend.reelId || trend.top_reels?.[0]?.reel_id || "";
      setSelectedReelId(bestId);
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

  const globalPct = trend.globalSaturationPct ?? 0;
  const indiaPct = trend.indiaSaturationPct ?? 0;
  const totalUses = trend.audioUseCount ?? 0;

  const formatUses = (count: number) => {
    if (!count) return "Early Signal";
    if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M reels`;
    if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K reels`;
    return `${count} reels`;
  };

  // Opens a phone-sized companion popup window directly on Instagram without leaving the app
  const openCompanionWindow = (url: string) => {
    const width = 440;
    const height = 780;
    const left = window.screen.width ? (window.screen.width - width) / 2 : 100;
    const top = window.screen.height ? (window.screen.height - height) / 2 : 100;
    window.open(
      url,
      "InstagramPreviewWindow",
      `width=${width},height=${height},top=${top},left=${left},scrollbars=yes,resizable=yes`
    );
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl bg-zinc-950 border-zinc-800/80 text-zinc-100 overflow-y-auto max-h-[92vh] rounded-3xl p-5 sm:p-6 shadow-2xl backdrop-blur-xl">
        {/* Instagram-Authentic Audio Banner */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-zinc-900/90 via-zinc-900/50 to-zinc-950 border border-zinc-800/80 p-4 mb-4">
          <div className="flex items-start gap-3.5">
            {/* Spinning Vinyl Record Visual */}
            <div className="relative shrink-0 w-14 h-14 rounded-full bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600 p-[2px] shadow-lg shadow-rose-500/20">
              <div className="w-full h-full rounded-full bg-zinc-950 flex items-center justify-center relative overflow-hidden">
                <Music2 className="w-6 h-6 text-rose-400 animate-spin" style={{ animationDuration: "6s" }} />
                <div className="absolute w-3 h-3 rounded-full bg-zinc-900 border border-zinc-700" />
              </div>
            </div>

            {/* Song + Artist + Meta */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/15 border border-rose-500/30 px-2 py-0.5 text-[10px] font-bold text-rose-300">
                  <Flame className="w-2.5 h-2.5" /> Trending Audio
                </span>
                <span className="text-[11px] font-semibold text-zinc-400">
                  {formatUses(totalUses)}
                </span>
              </div>
              <h2 className="text-base font-extrabold text-white truncate leading-tight">
                {trend.song}
              </h2>
              <p className="text-xs text-zinc-400 truncate">
                {trend.artist || "Original Audio"}
              </p>
            </div>
          </div>

          {/* Quick Stats Badges */}
          <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-zinc-800/60">
            <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[11px] font-bold text-emerald-400">
              <Clock className="w-3 h-3" /> {trend.hoursLeft}h peak window left
            </span>
            {globalPct > 0 && (
              <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold border ${
                globalPct < 30 ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                : globalPct < 65 ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
                : "bg-red-500/10 border-red-500/20 text-red-400"
              }`}>
                🌍 Global Saturation {Math.round(globalPct)}%
              </span>
            )}
            {indiaPct > 0 && (
              <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-bold border ${
                indiaPct < 30 ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                : "bg-amber-500/10 border-amber-500/20 text-amber-400"
              }`}>
                🇮🇳 India {Math.round(indiaPct)}%
              </span>
            )}
          </div>
        </div>

        {/* Live Instagram In-App Window / Player */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                <AppWindow className="h-3.5 w-3.5 text-rose-400" /> Live Instagram Preview
              </span>
              <span className="text-[10px] text-zinc-500">
                (Zero storage • Directly from Instagram)
              </span>
            </div>

            {/* Launch Companion Popup Button */}
            <button
              onClick={() => openCompanionWindow(currentReelUrl)}
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-400 hover:text-rose-300 transition-colors"
              title="Open a companion phone-sized Instagram window on your screen"
            >
              <span>Pop-out Mini Window</span>
              <ExternalLink className="h-3 w-3" />
            </button>
          </div>

          {/* Reel Switcher Chips (if multiple top reels exist) */}
          {topReels.length > 1 && (
            <div className="flex items-center gap-2 mb-2.5 overflow-x-auto pb-1">
              <span className="text-[10px] font-semibold text-zinc-500 shrink-0">Sample Reels:</span>
              {topReels.map((r, idx) => {
                const rid = r.reel_id;
                if (!rid) return null;
                const isSelected = selectedReelId === rid;
                return (
                  <button
                    key={rid}
                    onClick={() => {
                      setSelectedReelId(rid);
                      setIframeLoading(true);
                    }}
                    className={`text-[10px] font-bold px-2.5 py-1 rounded-lg border transition-all shrink-0 ${
                      isSelected
                        ? "bg-rose-500/20 border-rose-500/60 text-rose-300 shadow-sm"
                        : "bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
                    }`}
                  >
                    @{r.owner_username || `Reel #${idx + 1}`}
                  </button>
                );
              })}
            </div>
          )}

          {/* Instagram Official Embed Player Container */}
          {selectedReelId ? (
            <div className="relative w-full rounded-2xl overflow-hidden bg-zinc-900 border border-zinc-800/80 shadow-inner flex flex-col items-center justify-center min-h-[480px]">
              {iframeLoading && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-zinc-950/80 backdrop-blur-sm gap-2">
                  <div className="w-8 h-8 rounded-full border-2 border-rose-500/20 border-t-rose-500 animate-spin" />
                  <p className="text-xs font-semibold text-zinc-400">Loading Instagram Player...</p>
                </div>
              )}
              <iframe
                key={selectedReelId}
                src={`https://www.instagram.com/reel/${selectedReelId}/embed/`}
                className="w-full max-w-[380px] h-[480px] border-none"
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
                No single reel post is attached to this scraped audio yet.
              </p>
              <button
                onClick={() => openCompanionWindow(audioUrl)}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-xs font-bold text-white border border-zinc-700"
              >
                <AppWindow className="w-3.5 h-3.5" />
                Launch Instagram Audio Window
              </button>
            </div>
          )}
        </div>

        {/* Why this works & Content Idea */}
        {trend.whyThisWorks && (
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-3.5 mb-4">
            <p className="text-[10px] font-bold uppercase tracking-wider text-amber-400 mb-1 flex items-center gap-1">
              <Sparkles className="w-3 h-3" /> Creator Strategy
            </p>
            <p className="text-xs text-zinc-300 leading-relaxed">
              {trend.whyThisWorks}
            </p>
            {trend.used_for_note && (
              <p className="text-[11px] text-zinc-400 mt-2 pt-2 border-t border-zinc-800/60">
                <span className="font-semibold text-zinc-300">Format note: </span>
                {trend.used_for_note}
              </p>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {/* Button 1: Mini Companion Window (doesn't leave app) */}
          <button
            onClick={() => openCompanionWindow(audioUrl)}
            className="flex items-center justify-center gap-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-100 font-bold py-3 text-xs border border-zinc-700/80 transition-all duration-200"
          >
            <AppWindow className="w-4 h-4 text-rose-400" />
            <span>Open Audio in Mini Window</span>
          </button>

          {/* Button 2: Direct Instagram Audio Page */}
          <a
            href={audioUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-rose-600 to-pink-600 hover:from-rose-500 hover:to-pink-500 text-white font-bold py-3 text-xs shadow-lg shadow-rose-600/25 transition-all duration-200"
          >
            <Music2 className="w-4 h-4" />
            <span>Use / Save on Instagram →</span>
            <ExternalLink className="w-3.5 h-3.5 opacity-80" />
          </a>
        </div>
      </DialogContent>
    </Dialog>
  );
}
