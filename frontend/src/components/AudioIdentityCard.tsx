import React, { useEffect, useState, useRef } from "react";
import { Music, ExternalLink, Volume2 } from "lucide-react";
import { SparklineChart } from "./SparklineChart";
import { fetchAudioHistory } from "../lib/api";

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
  const containerRef = useRef<HTMLDivElement | null>(null);

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

  const instagramUrl = audioId
    ? `https://www.instagram.com/reels/audio/${audioId}/`
    : audioTitle
    ? `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(audioTitle)}`
    : null;

  const formatReelCount = (num?: number | null, fallbackCount?: number | null) => {
    const countToUse = num && num > 0 ? num : (fallbackCount && fallbackCount > 0 ? fallbackCount : 0);
    if (!countToUse) return "— reels";
    if (countToUse >= 1000000) return `${(countToUse / 1000000).toFixed(1)}M reels`;
    if (countToUse >= 1000) return `${(countToUse / 1000).toFixed(1)}K reels`;
    return `${countToUse} reels`;
  };

  const getWaveformColor = () => {
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
    <div ref={containerRef} className="relative overflow-hidden rounded-xl border border-white/10 bg-black/60 p-4 transition-all duration-300 hover:border-white/20">
      {/* Header Row: Waveform & Growth Sparkline */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Audio Icon Badge */}
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary border border-primary/20">
            <Music className="h-4 w-4" />
          </div>

          {/* Equalizer Bars */}
          <div className="flex items-center gap-1 h-6">
            {[1.2, 0.6, 1.5, 0.9, 1.4, 0.7, 1.1].map((_, idx) => (
              <div
                key={idx}
                className={`w-0.5 rounded-full ${getWaveformColor()}`}
                style={{
                  height: `${30 + (idx % 4) * 20}%`,
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
        <h3 className="line-clamp-1 font-bold text-white text-sm" title={audioTitle || "Unknown"}>
          {audioTitle || "Original Audio"}
        </h3>
        <p className="line-clamp-1 text-xs text-white/60">
          by {audioArtist || "Unknown Artist"}
        </p>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-white/5 pt-3">
        <span className="text-xs font-medium text-white/60 flex items-center gap-1">
          <Volume2 className="h-3 w-3 text-muted-foreground" />
          {audioUseCount && audioUseCount > 0 ? `${audioUseCount >= 1000 ? `${(audioUseCount / 1000).toFixed(0)}K` : audioUseCount.toString()} IG uses · ${reelCount || 1} tracked` : `${reelCount || 1} reel tracked`}
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
        @keyframes pulse {
          0%, 100% { transform: scaleY(0.3); }
          50% { transform: scaleY(1); }
        }
      `}</style>
    </div>
  );
};

