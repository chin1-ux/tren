import React, { useEffect, useState } from "react";
import { Music, ExternalLink, Activity } from "lucide-react";
import { SparklineChart } from "./SparklineChart";
import { fetchAudioHistory } from "../lib/api";

interface AudioIdentityCardProps {
  audioId?: string | null;
  audioTitle?: string | null;
  audioArtist?: string | null;
  audioUseCount?: number | null;
  trendId?: string | number | null;
  opportunityScore?: number;
}

export const AudioIdentityCard = ({
  audioId,
  audioTitle,
  audioArtist,
  audioUseCount,
  trendId,
  opportunityScore = 50,
}: AudioIdentityCardProps) => {
  const [history, setHistory] = useState<number[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    if (trendId) {
      setLoadingHistory(true);
      fetchAudioHistory(trendId)
        .then((data) => {
          const counts = data.map((d: any) => d.audio_use_count);
          setHistory(counts);
        })
        .catch(() => {})
        .finally(() => setLoadingHistory(false));
    }
  }, [trendId]);

  const instagramUrl = audioId
    ? `https://www.instagram.com/reels/audio/${audioId}/`
    : audioTitle
    ? `https://www.instagram.com/explore/search/keyword/?q=${encodeURIComponent(audioTitle)}`
    : null;

  const formatReelCount = (num?: number | null) => {
    if (!num) return "0 reels";
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M reels`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K reels`;
    return `${num} reels`;
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
    <div className="relative overflow-hidden rounded-xl border border-white/10 bg-black/60 p-4 transition-all duration-300 hover:border-white/20">
      {/* Waveform Visualization */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-1.5 h-6">
          <Music className="h-4 w-4 text-white/60 mr-1" />
          {[1.2, 0.6, 1.5, 0.9, 1.4, 0.7, 1.1].map((delay, idx) => (
            <div
              key={idx}
              className={`w-0.5 rounded-full ${getWaveformColor()}`}
              style={{
                height: "100%",
                animation: `pulse 1.2s ease-in-out infinite`,
                animationDelay: `${delay}s`,
              }}
            />
          ))}
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
        <span className="text-xs font-medium text-white/60">
          {formatReelCount(audioUseCount)}
        </span>
        
        {instagramUrl && (
          <a
            href={instagramUrl}
            target="_blank"
            rel="noopener noreferrer"
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
