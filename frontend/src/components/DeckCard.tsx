import React, { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Heart, X, RotateCcw, Info, ExternalLink, Copy, Check, Play, Volume2, VolumeX } from "lucide-react";
import type { UiTrend } from "@/lib/api";
import { formatRelativeTime } from "@/lib/time";
import { toast } from "sonner";

interface DeckCardProps {
  trend: UiTrend;
  isTop5?: boolean;
  onSwipe: (action: "like" | "skip" | "save") => void;
  canUndo?: boolean;
  onUndo?: () => void;
  nextDropTime?: string;
}

export const DeckCard: React.FC<DeckCardProps> = ({
  trend,
  isTop5 = false,
  onSwipe,
  canUndo = false,
  onUndo,
}) => {
  const [showInfo, setShowInfo] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [copied, setCopied] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Stage Badge helper
  const getStageMeta = (stage?: string, status?: string) => {
    const s = stage || status || "Rising";
    switch (s.toLowerCase()) {
      case "just starting":
        return { label: "Just starting", icon: "🌱", color: "text-pink-400 bg-pink-500/15 border-pink-500/30" };
      case "blowing up":
        return { label: "Blowing up", icon: "🚀", color: "text-amber-400 bg-amber-500/15 border-amber-500/30" };
      case "comeback":
        return { label: "Comeback", icon: "🔁", color: "text-violet-400 bg-violet-500/15 border-violet-500/30" };
      case "fading":
        return { label: "Fading", icon: "📉", color: "text-orange-400 bg-orange-500/15 border-orange-500/30" };
      case "expired":
        return { label: "Expired", icon: "⏱️", color: "text-slate-400 bg-slate-500/15 border-slate-500/30" };
      case "still going":
      default:
        return { label: "Still going", icon: "✨", color: "text-emerald-400 bg-emerald-500/15 border-emerald-500/30" };
    }
  };

  const stage = getStageMeta(trend.stage, trend.status);
  const creators = trend.reelCount || 1;
  const hoursAgo = trend.firstDetectedAt ? formatRelativeTime(trend.firstDetectedAt) : "recently";

  // Grounded note: strictly uses used_for_note or clean template (never hallucinating)
  const groundedLine = trend.used_for_note
    ? `High retention format: ${trend.used_for_note}`
    : trend.idealContentDescription || `Trending sound for creator reels across ${trend.category || "creative niches"}.`;

  const instagramAudioUrl = trend.id
    ? `https://www.instagram.com/reels/audio/${trend.id}/`
    : `https://www.instagram.com/`;

  const togglePlayback = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
        setIsPlaying(false);
      } else {
        videoRef.current.play().then(() => setIsPlaying(true)).catch(() => {});
      }
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const copyCaption = () => {
    const caption = trend.sampleCaptions && trend.sampleCaptions.length > 0
      ? trend.sampleCaptions[0]
      : `${trend.song} by ${trend.artist} #trending #viral`;
    navigator.clipboard.writeText(caption);
    setCopied(true);
    toast.success("Caption copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative w-full max-w-[420px] h-[calc(100vh-140px)] max-h-[680px] min-h-[520px] mx-auto flex flex-col rounded-3xl overflow-hidden border border-white/10 bg-zinc-950 shadow-2xl select-none">
      {/* ── CARD FACE ──────────────────────────────────────────────────────────── */}
      {/* 1. Reel Media Area (Tap to play inline with sound) */}
      <div
        id="card-media-tap"
        onClick={togglePlayback}
        className="relative flex-1 w-full bg-zinc-900 overflow-hidden cursor-pointer flex items-center justify-center group"
      >
        {trend.previewUrl ? (
          <video
            ref={videoRef}
            src={trend.previewUrl}
            loop
            muted={isMuted}
            playsInline
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-zinc-900 via-zinc-950 to-zinc-900 p-6 text-center">
            <div className="h-16 w-16 rounded-full bg-primary/10 border border-primary/30 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
              <Play className="h-7 w-7 text-primary ml-1" />
            </div>
            <p className="text-xs text-zinc-400 font-medium">Tap to play preview</p>
          </div>
        )}

        {/* Top Floating Badges */}
        <div className="absolute top-4 left-4 right-4 flex items-center justify-between pointer-events-none">
          <div className="flex items-center gap-1.5">
            {isTop5 && (
              <span className="px-2.5 py-1 rounded-full text-[11px] font-black uppercase tracking-wider bg-amber-500 text-black shadow-lg">
                🔥 Top 5
              </span>
            )}
            <span className={`px-2.5 py-1 rounded-full text-[11px] font-bold border flex items-center gap-1 shadow-md ${stage.color}`}>
              <span>{stage.icon}</span>
              <span>{stage.label}</span>
            </span>
          </div>

          <button
            type="button"
            id="card-info-btn"
            onClick={(e) => {
              e.stopPropagation();
              setShowInfo(true);
            }}
            className="pointer-events-auto h-8 w-8 rounded-full bg-black/60 backdrop-blur-md border border-white/20 text-white flex items-center justify-center hover:bg-black/80 transition-all cursor-pointer shadow-lg"
            aria-label="Audio Details"
          >
            <Info className="h-4 w-4" />
          </button>
        </div>

        {/* Sound toggle indicator on media */}
        {trend.previewUrl && (
          <button
            type="button"
            id="card-mute-toggle"
            onClick={(e) => {
              e.stopPropagation();
              setIsMuted(!isMuted);
            }}
            className="absolute bottom-3 right-3 h-7 w-7 rounded-full bg-black/60 backdrop-blur-md border border-white/20 text-white flex items-center justify-center hover:bg-black/80 transition-all cursor-pointer"
          >
            {isMuted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>

      {/* 2. Card Bottom Meta (Title, Proof line, Grounded line) */}
      <div className="p-4 bg-zinc-950/95 border-t border-white/10 flex flex-col gap-2">
        <div className="flex flex-col">
          <h2 className="text-base font-extrabold text-white truncate leading-tight">
            {trend.song}
          </h2>
          <p className="text-xs text-zinc-400 truncate">
            {trend.artist}
          </p>
        </div>

        {/* Proof Line */}
        <p className="text-xs font-semibold text-emerald-400 flex items-center gap-1.5">
          <span>👥</span>
          <span>{creators} creator{creators > 1 ? "s" : ""} · caught {hoursAgo}</span>
        </p>

        {/* Grounded Line */}
        <p className="text-[11px] text-zinc-300 line-clamp-2 leading-relaxed bg-zinc-900/60 p-2 rounded-xl border border-white/5">
          {groundedLine}
        </p>

        {/* 3. Action Controls: X (Skip), Heart (Use it), Undo */}
        <div className="flex items-center justify-between pt-1 mt-1">
          {/* Undo Button */}
          <button
            type="button"
            id="card-undo-btn"
            disabled={!canUndo}
            onClick={onUndo}
            className={`h-11 w-11 rounded-full flex items-center justify-center border transition-all cursor-pointer ${
              canUndo
                ? "bg-zinc-900 border-white/20 text-zinc-300 hover:text-white hover:border-white/40"
                : "opacity-30 border-transparent text-zinc-600 cursor-not-allowed"
            }`}
            aria-label="Undo last swipe"
          >
            <RotateCcw className="h-4 w-4" />
          </button>

          {/* Main Swipe Buttons */}
          <div className="flex items-center gap-4">
            {/* Skip (Left) */}
            <button
              type="button"
              id="card-skip-btn"
              onClick={() => onSwipe("skip")}
              className="h-13 w-13 rounded-full bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-400 flex items-center justify-center shadow-lg hover:scale-105 active:scale-95 transition-all cursor-pointer"
              aria-label="Skip audio"
            >
              <X className="h-6 w-6" />
            </button>

            {/* Use It (Right) */}
            <button
              type="button"
              id="card-save-btn"
              onClick={() => onSwipe("save")}
              className="h-13 w-13 rounded-full bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-400 flex items-center justify-center shadow-lg hover:scale-105 active:scale-95 transition-all cursor-pointer"
              aria-label="Use and save audio"
            >
              <Heart className="h-6 w-6 fill-emerald-400/20" />
            </button>
          </div>
        </div>
      </div>

      {/* ── INFO SHEET (SLIDING DRAWER) ────────────────────────────────────────── */}
      <AnimatePresence>
        {showInfo && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-50 bg-black/80 backdrop-blur-md flex flex-col justify-end"
          >
            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", stiffness: 350, damping: 30 }}
              className="w-full bg-zinc-900 border-t border-white/15 rounded-t-3xl p-5 flex flex-col gap-3.5 max-h-[85%] overflow-y-auto no-scrollbar shadow-2xl"
            >
              {/* Sheet Header */}
              <div className="flex items-center justify-between pb-2 border-b border-white/10">
                <div>
                  <h3 className="text-sm font-extrabold text-white">{trend.song}</h3>
                  <p className="text-xs text-zinc-400">{trend.artist}</p>
                </div>
                <button
                  type="button"
                  id="info-sheet-close"
                  onClick={() => setShowInfo(false)}
                  className="h-8 w-8 rounded-full bg-zinc-800 text-zinc-300 hover:text-white flex items-center justify-center cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Discovery Timeline */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2.5 rounded-xl bg-zinc-950/60 border border-white/5">
                  <span className="text-[10px] text-zinc-400 uppercase font-bold block">First Caught</span>
                  <span className="font-semibold text-zinc-200">{hoursAgo}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-zinc-950/60 border border-white/5">
                  <span className="text-[10px] text-zinc-400 uppercase font-bold block">Proof Creators</span>
                  <span className="font-semibold text-emerald-400">{creators} verified</span>
                </div>
              </div>

              {/* Niche & Language */}
              <div className="flex items-center gap-2 text-xs">
                <span className="px-2.5 py-1 rounded-lg bg-zinc-800 text-zinc-200 border border-white/10 font-medium">
                  {trend.category || "General"}
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-zinc-800 text-zinc-200 border border-white/10 font-medium">
                  {trend.languageLabel || trend.language || "Global"}
                </span>
              </div>

              {/* Caption Copy Section */}
              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] text-zinc-400 uppercase font-bold">Suggested Caption Copy</span>
                <div className="p-3 rounded-xl bg-zinc-950 border border-white/10 text-xs text-zinc-300 flex items-start justify-between gap-2">
                  <p className="line-clamp-3">
                    {trend.sampleCaptions && trend.sampleCaptions.length > 0
                      ? trend.sampleCaptions[0]
                      : `Syncing with '${trend.song}' for maximum engagement. Save this sound before it peaks!`}
                  </p>
                  <button
                    type="button"
                    onClick={copyCaption}
                    className="p-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 flex-shrink-0 cursor-pointer"
                    aria-label="Copy caption"
                  >
                    {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              {/* The ONLY Outbound Link: Open on Instagram */}
              <a
                href={instagramAudioUrl}
                target="_blank"
                rel="noopener noreferrer"
                id="outbound-instagram-link"
                className="w-full py-3 rounded-xl bg-gradient-to-r from-pink-600 via-rose-600 to-purple-600 text-white font-bold text-xs flex items-center justify-center gap-2 shadow-lg hover:opacity-95 transition-opacity cursor-pointer mt-1"
              >
                <span>Open on Instagram</span>
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
