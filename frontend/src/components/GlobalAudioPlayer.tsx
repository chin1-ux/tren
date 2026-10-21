import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  Pause,
  RotateCcw,
  X,
  Music,
  ExternalLink,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useAudioStore } from "../store/useAudioStore";

export const GlobalAudioPlayer: React.FC = () => {
  const {
    currentTrack,
    isPlaying,
    isLoading,
    currentTime,
    duration,
    isLooping,
    error,
    togglePlay,
    seek,
    toggleLoop,
    stop,
  } = useAudioStore();

  if (!currentTrack) return null;

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const targetTime = parseFloat(e.target.value);
    seek(targetTime);
  };

  const formatSeconds = (sec: number) => {
    if (isNaN(sec) || sec < 0) return "0:00";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  const instagramUrl = currentTrack.instagramAudioId
    ? `https://www.instagram.com/reels/audio/${currentTrack.instagramAudioId}/`
    : `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(currentTrack.title)}`;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: 90, opacity: 0, scale: 0.95 }}
        animate={{ y: 0, opacity: 1, scale: 1 }}
        exit={{ y: 90, opacity: 0, scale: 0.95 }}
        transition={{ type: "spring", stiffness: 350, damping: 28 }}
        className="fixed z-[75] bottom-[76px] left-3 right-3 sm:left-auto sm:right-6 sm:bottom-[82px] sm:w-[430px]"
      >
        <div className="relative overflow-hidden rounded-2xl border border-white/20 dark:border-white/10 bg-surface/95 dark:bg-zinc-950/95 backdrop-blur-2xl p-3.5 shadow-[0_16px_45px_rgba(0,0,0,0.35)] dark:shadow-[0_20px_55px_rgba(0,0,0,0.7)]">
          {/* Top Amber Glowing Bar for Viral Drop Window */}
          <div className="absolute top-0 left-0 right-0 h-[2.5px] bg-gradient-to-r from-amber-500 via-rose-500 to-amber-500 animate-pulse" />

          <div className="flex items-center gap-3">
            {/* Cover Art / Spinning Vinyl Disc */}
            <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-xl border border-white/10 bg-black/40 shadow-inner">
              {currentTrack.coverUrl ? (
                <img
                  src={currentTrack.coverUrl}
                  alt={currentTrack.title}
                  className={`h-full w-full object-cover transition-transform duration-700 ${isPlaying ? "scale-105" : "scale-100"}`}
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-amber-500/20 to-primary/20 text-primary">
                  <Music className="h-5 w-5" />
                </div>
              )}
              {isPlaying && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/35 backdrop-blur-[1px]">
                  <span className="flex items-end gap-0.5 h-3.5">
                    <span className="w-0.5 h-3 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-0.5 h-2 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-0.5 h-3.5 bg-amber-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </span>
                </div>
              )}
            </div>

            {/* Title & Artist & Viral Pill */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="inline-flex items-center gap-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 px-1.5 py-0.2 text-[9px] font-extrabold text-amber-500 dark:text-amber-400">
                  <Sparkles className="h-2.5 w-2.5" /> VIRAL DROP
                </span>
                {currentTrack.sourceType === "original" && (
                  <span className="text-[9px] text-muted-foreground font-semibold">
                    (IG Original)
                  </span>
                )}
              </div>
              <h4 className="truncate text-xs font-bold text-foreground mt-0.5" title={currentTrack.title}>
                {currentTrack.title}
              </h4>
              <p className="truncate text-[11px] text-muted-foreground">
                {currentTrack.artist}
              </p>
            </div>

            {/* Playback Controls */}
            <div className="flex items-center gap-1.5 shrink-0">
              {/* Loop Toggle */}
              <button
                onClick={toggleLoop}
                className={`rounded-lg p-2 transition-colors ${
                  isLooping
                    ? "bg-amber-500/15 text-amber-500 dark:text-amber-400 border border-amber-500/30"
                    : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                }`}
                title={isLooping ? "Looping viral drop (Active)" : "Loop disabled"}
                aria-label="Toggle loop"
              >
                <RotateCcw className="h-4 w-4" />
              </button>

              {/* Play / Pause / Load */}
              <button
                onClick={togglePlay}
                disabled={isLoading || !currentTrack.previewUrl}
                className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-md hover:scale-105 active:scale-95 transition-all disabled:opacity-50"
                aria-label={isPlaying ? "Pause" : "Play"}
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : isPlaying ? (
                  <Pause className="h-4 w-4 fill-current" />
                ) : (
                  <Play className="h-4 w-4 fill-current ml-0.5" />
                )}
              </button>

              {/* Use on IG Deep Link */}
              <a
                href={instagramUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 px-2.5 py-2 text-[11px] font-bold text-white shadow-sm hover:opacity-90 transition-opacity"
                title="Open this audio directly in Instagram Reels camera"
              >
                <span>Use</span>
                <ExternalLink className="h-3 w-3" />
              </a>

              {/* Close Player */}
              <button
                onClick={stop}
                className="rounded-lg p-1.5 text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors ml-0.5"
                aria-label="Close audio player"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Scrubber Progress Bar & Timestamps */}
          {currentTrack.previewUrl && (
            <div className="mt-2.5 space-y-1">
              <div className="relative flex items-center">
                <input
                  type="range"
                  min={0}
                  max={duration || 30}
                  step={0.1}
                  value={currentTime}
                  onChange={handleSeek}
                  className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-white/10 accent-amber-500 focus:outline-none"
                />
              </div>
              <div className="flex items-center justify-between text-[10px] font-mono tabular-nums text-muted-foreground">
                <span>{formatSeconds(currentTime)}</span>
                <span className="text-[9px] text-amber-500 dark:text-amber-400 font-sans font-bold">
                  {isLooping ? "🔁 15s Hook Loop" : "30s Preview"}
                </span>
                <span>{formatSeconds(duration || 30)}</span>
              </div>
            </div>
          )}

          {/* Notice if Audio has no direct CDN preview */}
          {!currentTrack.previewUrl && (
            <div className="mt-2 rounded-lg bg-white/5 border border-white/10 px-2.5 py-1.5 text-[11px] text-muted-foreground flex items-center justify-between">
              <span>Original audio not in public catalog.</span>
              <a
                href={instagramUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary font-semibold hover:underline flex items-center gap-1"
              >
                Listen on Instagram <ExternalLink className="h-2.5 w-2.5" />
              </a>
            </div>
          )}

          {/* Error Notice */}
          {error && (
            <p className="mt-1 text-[10px] text-rose-400 font-medium text-center">
              {error}
            </p>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
