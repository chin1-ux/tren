import React, { useEffect, useState, useRef } from "react";
import { Music, ExternalLink, Volume2, Play, Pause, Loader2, Sparkles } from "lucide-react";
import { SparklineChart } from "./SparklineChart";
import { fetchAudioHistory } from "../lib/api";
import { useAudioStore, primeAudio } from "../store/useAudioStore";
import { resolveAudioTrack } from "../lib/audio-resolver";

interface AudioIdentityCardProps {
  audioId?: string | null;
  audioTitle?: string | null;
  audioArtist?: string | null;
  audioUseCount?: number | null;
  reelCount?: number | null;
  trendId?: string | number | null;
  opportunityScore?: number;
  previewUrl?: string | null;
  index?: number;
}

export const AudioIdentityCard = ({
  audioId,
  audioTitle,
  audioArtist,
  audioUseCount,
  reelCount,
  trendId,
  opportunityScore = 50,
  previewUrl = null,
  index = 0,
}: AudioIdentityCardProps) => {
  const [history, setHistory] = useState<number[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [isResolving, setIsResolving] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  const { currentTrack, isPlaying, playTrack, togglePlay } = useAudioStore();

  const trackIdentifier = String(trendId || audioId || audioTitle);
  const isCurrentTrack = currentTrack && String(currentTrack.id) === trackIdentifier;
  const isThisPlaying = isCurrentTrack && isPlaying;

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "100px" }
    );
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (trendId && isVisible) {
      const delay = Math.min(1000, (index || 0) * 120);
      const timer = setTimeout(() => {
        setLoadingHistory(true);
        fetchAudioHistory(trendId)
          .then((data) => {
            const counts = data.map((d: any) => d.audio_use_count);
            setHistory(counts);
          })
          .catch(() => {})
          .finally(() => setLoadingHistory(false));
      }, delay);
      return () => clearTimeout(timer);
    }
  }, [trendId, isVisible, index]);

  const handlePlayDrop = async (e: React.MouseEvent) => {
    e.stopPropagation();

    // Synchronously prime audio element within user gesture
    primeAudio();

    if (isCurrentTrack) {
      togglePlay();
      return;
    }

    setIsResolving(true);
    try {
      const resolved = await resolveAudioTrack({
        id: trackIdentifier,
        song: audioTitle || "Unknown",
        artist: audioArtist || "Unknown",
        audioId: audioId,
        previewUrl: previewUrl,
      });

      playTrack({
        id: trackIdentifier,
        title: resolved.title,
        artist: resolved.artist,
        coverUrl: resolved.coverUrl || undefined,
        instagramAudioId: audioId || undefined,
        viralStartSec: resolved.viralStartSec,
        viralDurationSec: resolved.viralDurationSec,
        previewUrl: resolved.previewUrl,
        sourceType: resolved.sourceType,
      });
    } finally {
      setIsResolving(false);
    }
  };

  const instagramUrl = audioId
    ? `https://www.instagram.com/reels/audio/${audioId}/`
    : audioTitle
    ? `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(audioTitle)}`
    : null;

  const getWaveformColor = () => {
    if (isThisPlaying) return "bg-amber-400";
    if (opportunityScore >= 80) return "bg-emerald-400";
    if (opportunityScore >= 60) return "bg-amber-400";
    if (opportunityScore >= 40) return "bg-orange-400";
    return "bg-red-400";
  };

  const getSparklineColor = () => {
    if (opportunityScore >= 80) return "green" as const;
    if (opportunityScore >= 60) return "amber" as const;
    return "red" as const;
  };

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden rounded-xl border p-4 transition-all duration-300 ${
        isThisPlaying
          ? "border-amber-500/50 bg-amber-500/[0.04] shadow-[0_0_24px_rgba(245,158,11,0.18)]"
          : "border-white/10 bg-black/60 hover:border-white/20"
      }`}
    >
      {/* Top ambient highlight when playing */}
      {isThisPlaying && (
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-amber-400 via-rose-400 to-amber-400 animate-pulse" />
      )}

      {/* Header Row: Play Trigger & Waveform & Sparkline */}
      <div className="mb-3.5 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {/* 1-Tap Play Viral Drop Button */}
          <button
            onClick={handlePlayDrop}
            disabled={isResolving}
            className={`group flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold transition-all ${
              isThisPlaying
                ? "bg-amber-500 text-black shadow-[0_0_12px_rgba(245,158,11,0.4)] scale-105"
                : "bg-primary text-primary-foreground hover:bg-primary/90 hover:scale-105 active:scale-95"
            }`}
            title="Listen to the viral hook segment of this audio"
            aria-label="Play audio drop"
          >
            {isResolving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : isThisPlaying ? (
              <>
                <Pause className="h-3.5 w-3.5 fill-current" />
                <span>Playing Hook</span>
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current ml-0.5" />
                <span>Play Drop</span>
              </>
            )}
          </button>

          {/* Equalizer Bars (animated when playing) */}
          <div className="flex items-center gap-1 h-6 px-1">
            {[40, 70, 90, 60, 100, 50, 80].map((baseHeight, idx) => (
              <div
                key={idx}
                className={`w-0.5 rounded-full transition-all duration-200 ${getWaveformColor()}`}
                style={{
                  height: isThisPlaying
                    ? `${25 + ((idx * 27) % 75)}%`
                    : `${baseHeight * 0.4}%`,
                  animation: isThisPlaying
                    ? `audioBarBounce 0.8s ease-in-out infinite alternate ${idx * 0.12}s`
                    : "none",
                }}
              />
            ))}
          </div>
        </div>

        {/* Sparkline integration */}
        {!loadingHistory && history.length > 0 && (
          <div className="flex flex-col items-end gap-0.5">
            <span className="text-[9px] font-semibold tracking-wider text-white/40 uppercase">Growth</span>
            <SparklineChart data={history} color={getSparklineColor()} />
          </div>
        )}
      </div>

      <div className="space-y-1">
        <div className="flex items-center justify-between gap-2">
          <h3 className="line-clamp-1 font-bold text-white text-sm" title={audioTitle || "Unknown"}>
            {audioTitle || "Original Audio"}
          </h3>
          {isThisPlaying && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 text-[9px] font-extrabold text-amber-500 dark:text-amber-400 shrink-0">
              <Sparkles className="h-2.5 w-2.5" /> 15s Drop
            </span>
          )}
        </div>
        <p className="line-clamp-1 text-xs text-white/60">
          by {audioArtist || "Unknown Artist"}
        </p>
      </div>

      <div className="mt-3.5 flex items-center justify-between border-t border-white/5 pt-3">
        <span className="text-xs font-medium text-white/60 flex items-center gap-1">
          <Volume2 className="h-3 w-3 text-muted-foreground" />
          {audioUseCount && audioUseCount > 0
            ? `${audioUseCount >= 1000 ? `${(audioUseCount / 1000).toFixed(0)}K` : audioUseCount.toString()} IG uses · ${reelCount || 1} tracked`
            : `${reelCount || 1} reel tracked`}
        </span>

        {instagramUrl && (
          <a
            href={instagramUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 text-[11px] font-semibold text-sky-400 hover:text-sky-300 transition-colors"
          >
            Open on IG
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>

      <style>{`
        @keyframes audioBarBounce {
          0% { height: 20%; }
          50% { height: 95%; }
          100% { height: 35%; }
        }
      `}</style>
    </div>
  );
};
