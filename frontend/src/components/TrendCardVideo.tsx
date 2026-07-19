import { useState, useEffect, useRef } from "react";
import { ExternalLink } from "lucide-react";

interface TrendCardVideoProps {
  reel: {
    id: string;
    thumbnail_url?: string | null;
    reel_id?: string;
  };
}

export const TrendCardVideo = ({ reel }: TrendCardVideoProps) => {
  const reelId = reel.reel_id?.trim();
  const instagramUrl = reelId
    ? `https://www.instagram.com/reel/${reelId}/`
    : null;

  return (
    <div className="group/video relative block w-full overflow-hidden rounded-xl border border-white/10 bg-black/40">
      <div className="relative aspect-[9/16] w-full">
        {reel.thumbnail_url ? (
          <img
            src={reel.thumbnail_url}
            alt="Reel thumbnail"
            className="h-full w-full object-cover transition-transform duration-300 group-hover/video:scale-[1.02]"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-white/5 to-white/0 text-xs font-semibold text-white/60">
            Open on Instagram
          </div>
        )}

        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/15 to-transparent" />

        <div className="absolute inset-x-0 bottom-0 flex items-center justify-between gap-2 p-3">
          {instagramUrl ? (
            <a
              href={instagramUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-full bg-black/50 px-2.5 py-1 text-[10px] font-semibold text-white/90 backdrop-blur"
              aria-label="Open reel on Instagram"
            >
              Open on Instagram
            </a>
          ) : (
            <span className="rounded-full bg-black/50 px-2.5 py-1 text-[10px] font-semibold text-white/60 backdrop-blur">
              Instagram unavailable
            </span>
          )}
          <ExternalLink className="h-4 w-4 text-white/90" />
        </div>
      </div>
    </div>
  );
};
