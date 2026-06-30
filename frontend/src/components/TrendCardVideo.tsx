import { useState, useEffect, useRef } from "react";
import { Play, Loader2, ExternalLink } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface TrendCardVideoProps {
  reel: {
    id: string;
    preview_url?: string | null;
    video_url?: string;
    reel_id?: string;
    video_storage_status?: string;
  };
}

export const TrendCardVideo = ({ reel }: TrendCardVideoProps) => {
  const [videoUrl, setVideoUrl] = useState<string | null>(reel.preview_url ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showFallback, setShowFallback] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const instagramUrl = reel.reel_id && /^\d+$/.test(reel.reel_id)
    ? `https://www.instagram.com/reels/audio/${reel.reel_id}/`
    : `https://www.instagram.com/reel/${reel.reel_id || ""}/`;

  // Start 8 seconds timeout for fallback link
  const startLoadingTimeout = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setShowFallback(false);
    timerRef.current = setTimeout(() => {
      if (loading || !videoUrl) {
        setShowFallback(true);
      }
    }, 8000);
  };

  const handlePlay = async () => {
    if (loading) return;
    if (videoUrl) {
      setIsPlaying(true);
      videoRef.current?.play().catch(() => {});
      return;
    }

    setLoading(true);
    setError(false);
    startLoadingTimeout();

    try {
      const res = await apiFetch(`/api/reels/stream/${reel.id}`);
      if (!res.ok) throw new Error("Stream failed");
      const data = await res.json();
      if (data.videoUrl) {
        setVideoUrl(data.videoUrl);
        setIsPlaying(true);
      } else {
        throw new Error("No URL returned");
      }
    } catch (err) {
      console.error("Stream failed:", err);
      setError(true);
      setShowFallback(true);
    } finally {
      setLoading(false);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  // Desktop hover trigger: autoplay muted
  const handleMouseEnter = () => {
    // Check if not a mobile device by screen width
    if (window.innerWidth >= 1024) {
      if (videoUrl) {
        setIsPlaying(true);
        videoRef.current?.play().catch(() => {});
      } else {
        handlePlay();
      }
    }
  };

  const handleMouseLeave = () => {
    if (window.innerWidth >= 1024 && isPlaying) {
      videoRef.current?.pause();
      setIsPlaying(false);
    }
  };

  // If fallback is active, show the Instagram link
  if (showFallback) {
    return (
      <a
        href={instagramUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-1.5 w-full h-full bg-red-500/10 border border-red-500/30 text-red-400 rounded-lg p-3 text-xs font-semibold hover:bg-red-500/20 transition-all duration-200"
      >
        <span>Open on Instagram</span>
        <ExternalLink className="w-3.5 h-3.5" />
      </a>
    );
  }

  return (
    <div
      className="relative w-full aspect-[9/16] bg-black/40 rounded-xl overflow-hidden group/video flex items-center justify-center"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {videoUrl && isPlaying ? (
        <video
          ref={videoRef}
          src={videoUrl}
          autoPlay
          muted
          loop
          playsInline
          controls
          className="w-full h-full object-cover transition-opacity duration-300"
        />
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 p-4 text-center">
          <button
            onClick={handlePlay}
            disabled={loading}
            className="flex items-center justify-center w-12 h-12 rounded-full bg-white/10 border border-white/20 hover:bg-white/20 text-white transition-all duration-300 disabled:opacity-50 cursor-pointer shadow-lg hover:scale-105"
          >
            {loading ? (
              <Loader2 className="w-6 h-6 animate-spin text-white" />
            ) : (
              <Play className="w-6 h-6 fill-white text-white translate-x-0.5" />
            )}
          </button>
          <span className="text-[10px] text-white/60 font-medium tracking-wide uppercase select-none">
            {loading ? "⏳ Fetching Reel..." : "▶ Preview Reel"}
          </span>
        </div>
      )}
    </div>
  );
};
