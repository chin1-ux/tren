import React, { useState } from "react";
import { ExternalLink, Check, Sparkles, BookmarkCheck, ThumbsUp, Flame, ThumbsDown } from "lucide-react";
import type { UiTrend } from "@/lib/api";
import { toast } from "sonner";

interface PicksViewProps {
  picks: UiTrend[];
  onRemovePick: (trendId: string) => void;
}

interface PickStatus {
  posted: boolean;
  postedAt?: number;
  feedback?: string;
}

export const PicksView: React.FC<PicksViewProps> = ({ picks, onRemovePick }) => {
  const [pickStatuses, setPickStatuses] = useState<Record<string, PickStatus>>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("trendrop_user_picks_status");
        if (saved) return JSON.parse(saved);
      } catch {}
    }
    return {};
  });

  const handleMarkPosted = (id: string) => {
    const updated = {
      ...pickStatuses,
      [id]: { posted: true, postedAt: Date.now() },
    };
    setPickStatuses(updated);
    if (typeof window !== "undefined") {
      localStorage.setItem("trendrop_user_picks_status", JSON.stringify(updated));
    }
    toast.success("Marked as posted! We'll check in soon.");
  };

  const handleFeedback = (id: string, feedback: string) => {
    const updated = {
      ...pickStatuses,
      [id]: { ...pickStatuses[id], feedback },
    };
    setPickStatuses(updated);
    if (typeof window !== "undefined") {
      localStorage.setItem("trendrop_user_picks_status", JSON.stringify(updated));
    }
    toast.success("Feedback recorded! Thanks for rating.");
  };

  if (picks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[460px] w-full px-4 text-center">
        <div className="h-14 w-14 rounded-2xl bg-zinc-900 border border-white/10 text-zinc-400 flex items-center justify-center mb-4">
          <BookmarkCheck className="h-7 w-7 text-primary" />
        </div>
        <h3 className="text-base font-bold text-white mb-1">No picks saved yet</h3>
        <p className="text-xs text-zinc-400 max-w-xs">
          Swipe right on the Deck or tap 'Use It' in Explore to save sounds for your upcoming reels.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col gap-3 pb-16">
      <div className="flex items-center justify-between pb-2 border-b border-white/10">
        <h2 className="text-sm font-extrabold text-white">Your Saved Picks ({picks.length})</h2>
        <span className="text-[11px] text-zinc-400">Ready to film & post</span>
      </div>

      <div className="flex flex-col gap-3">
        {picks.map((p) => {
          const status = pickStatuses[p.id] || { posted: false };
          const instagramUrl = p.id ? `https://www.instagram.com/reels/audio/${p.id}/` : `https://www.instagram.com/`;

          return (
            <div
              key={p.id}
              className="p-3.5 rounded-2xl bg-zinc-950 border border-white/10 flex flex-col gap-2.5 shadow-lg"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex flex-col min-w-0">
                  <h3 className="text-xs font-bold text-white truncate">{p.song}</h3>
                  <p className="text-[11px] text-zinc-400 truncate">{p.artist}</p>
                  <span className="text-[10px] text-emerald-400 font-semibold mt-0.5">
                    {p.stage || p.status || "Rising"} · {p.reelCount || 1} creators
                  </span>
                </div>
                <a
                  href={instagramUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-2.5 py-1.5 rounded-xl bg-gradient-to-r from-pink-600 to-purple-600 text-white text-[11px] font-bold flex items-center gap-1 shadow-md flex-shrink-0 cursor-pointer"
                >
                  <span>Open Audio</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>

              {/* Status Action: 'I posted it' vs Feedback prompt */}
              <div className="pt-2 border-t border-white/5 flex items-center justify-between">
                {!status.posted ? (
                  <button
                    type="button"
                    onClick={() => handleMarkPosted(p.id)}
                    className="px-3 py-1.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-300 hover:text-white text-xs font-semibold border border-white/10 transition-colors cursor-pointer"
                  >
                    I posted it
                  </button>
                ) : !status.feedback ? (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-[11px] text-zinc-400 font-medium">How did it go?</span>
                    <button
                      type="button"
                      onClick={() => handleFeedback(p.id, "viral")}
                      className="px-2 py-1 rounded-lg bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 text-[11px] font-bold hover:bg-emerald-500/25 flex items-center gap-1 cursor-pointer"
                    >
                      <Flame className="h-3 w-3" /> Blew up
                    </button>
                    <button
                      type="button"
                      onClick={() => handleFeedback(p.id, "good")}
                      className="px-2 py-1 rounded-lg bg-blue-500/15 text-blue-400 border border-blue-500/30 text-[11px] font-bold hover:bg-blue-500/25 flex items-center gap-1 cursor-pointer"
                    >
                      <ThumbsUp className="h-3 w-3" /> Good
                    </button>
                    <button
                      type="button"
                      onClick={() => handleFeedback(p.id, "flop")}
                      className="px-2 py-1 rounded-lg bg-zinc-800 text-zinc-400 border border-white/10 text-[11px] font-medium hover:text-zinc-200 flex items-center gap-1 cursor-pointer"
                    >
                      <ThumbsDown className="h-3 w-3" /> Flop
                    </button>
                  </div>
                ) : (
                  <span className="text-[11px] text-zinc-400 font-medium">
                    Rated: <strong className="text-white capitalize">{status.feedback}</strong>
                  </span>
                )}

                <button
                  type="button"
                  onClick={() => onRemovePick(p.id)}
                  className="text-[11px] text-zinc-500 hover:text-zinc-300 cursor-pointer"
                >
                  Remove
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
