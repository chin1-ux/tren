import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, CheckCircle2, AlertTriangle, RefreshCw, Layers } from "lucide-react";
import type { UiTrend } from "@/lib/api";
import { DeckCard } from "./DeckCard";
import { recordSwipe } from "@/lib/learning-engine";
import { toast } from "sonner";

interface DeckViewProps {
  trends: UiTrend[];
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  nextDropTime?: string;
  isDataDelayed?: boolean;
  onSavePick: (trend: UiTrend) => void;
}

const SKIP_REASONS = ["Wrong niche", "Too saturated", "Not my vibe", "Already used"];

export const DeckView: React.FC<DeckViewProps> = ({
  trends,
  isLoading,
  isError,
  onRetry,
  nextDropTime = "in 2 hours",
  isDataDelayed = false,
  onSavePick,
}) => {
  // Filter for deck: Tier A/B and >= 2 creators, max 15 cards/day
  const deckCards = React.useMemo(() => {
    return trends
      .filter((t) => (t.reelCount || 1) >= 2 && t.status !== "expired" && t.stage !== "Expired")
      .slice(0, 15);
  }, [trends]);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [history, setHistory] = useState<{ index: number; action: "like" | "skip" | "save"; trend: UiTrend }[]>([]);
  const [showSkipChips, setShowSkipChips] = useState(false);
  const [skipTimer, setSkipTimer] = useState<NodeJS.Timeout | null>(null);

  const currentTrend = deckCards[currentIndex];
  const isCaughtUp = currentIndex >= deckCards.length && deckCards.length > 0;

  const handleSwipe = (action: "like" | "skip" | "save") => {
    if (!currentTrend) return;

    recordSwipe(action, {
      niche: currentTrend.category,
      language: currentTrend.language,
      category: currentTrend.category,
    });

    if (action === "save") {
      onSavePick(currentTrend);
      toast.success("Saved to Picks!");
    } else if (action === "skip") {
      // Show optional 3-second reason chips
      setShowSkipChips(true);
      if (skipTimer) clearTimeout(skipTimer);
      const timer = setTimeout(() => setShowSkipChips(false), 3000);
      setSkipTimer(timer);
    }

    setHistory((prev) => [...prev, { index: currentIndex, action, trend: currentTrend }]);
    setCurrentIndex((prev) => prev + 1);
  };

  const handleUndo = () => {
    if (history.length === 0) return;
    const last = history[history.length - 1];
    setHistory((prev) => prev.slice(0, -1));
    setCurrentIndex(last.index);
    setShowSkipChips(false);
    toast.info("Swipe reverted");
  };

  const handleSelectSkipReason = (reason: string) => {
    setShowSkipChips(false);
    toast.info(`Feedback noted: ${reason}`);
  };

  // 1. Loading State
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] w-full px-4 text-center">
        <div className="relative w-full max-w-[380px] h-[540px] rounded-3xl bg-zinc-900/60 border border-white/5 animate-pulse flex flex-col justify-between p-6">
          <div className="flex justify-between">
            <div className="h-6 w-20 bg-zinc-800 rounded-full" />
            <div className="h-8 w-8 bg-zinc-800 rounded-full" />
          </div>
          <div className="flex flex-col gap-3">
            <div className="h-6 w-3/4 bg-zinc-800 rounded-lg" />
            <div className="h-4 w-1/2 bg-zinc-800 rounded-lg" />
            <div className="h-10 w-full bg-zinc-800 rounded-xl mt-2" />
          </div>
        </div>
        <p className="text-xs text-zinc-400 mt-4 font-medium">Curating today's audio deck...</p>
      </div>
    );
  }

  // 2. Error State with Retry
  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[460px] w-full px-4 text-center">
        <div className="h-14 w-14 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-center mb-4">
          <AlertTriangle className="h-7 w-7" />
        </div>
        <h3 className="text-base font-bold text-white mb-1">Failed to load deck</h3>
        <p className="text-xs text-zinc-400 max-w-xs mb-4">We encountered an issue loading today's cards.</p>
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-2 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-white font-semibold text-xs flex items-center gap-1.5 transition-all cursor-pointer"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Retry</span>
        </button>
      </div>
    );
  }

  // 3. Empty State (no trends qualify)
  if (deckCards.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[460px] w-full px-4 text-center">
        <div className="h-14 w-14 rounded-2xl bg-zinc-800 text-zinc-400 flex items-center justify-center mb-4">
          <Layers className="h-7 w-7" />
        </div>
        <h3 className="text-base font-bold text-white mb-1">No audio cards today</h3>
        <p className="text-xs text-zinc-400 max-w-xs">New multi-creator audios will drop after the next scrape cycle.</p>
      </div>
    );
  }

  // 4. End of List (Caught up state)
  if (isCaughtUp) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px] w-full px-4 text-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", stiffness: 350, damping: 25 }}
          className="relative w-full max-w-[380px] p-8 rounded-3xl bg-zinc-950 border border-white/10 shadow-2xl flex flex-col items-center text-center"
        >
          <div className="h-16 w-16 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mb-4">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <h2 data-testid="deck-caught-up-header" className="text-xl font-extrabold text-white mb-2">You're caught up!</h2>
          <p className="text-xs text-zinc-400 leading-relaxed mb-6">
            You've reviewed all 15 top sounds for today. Next drop scheduled for <span className="text-emerald-400 font-bold">{nextDropTime}</span>.
          </p>
          <button
            type="button"
            onClick={() => setCurrentIndex(0)}
            className="w-full py-2.5 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-white font-semibold text-xs transition-all cursor-pointer"
          >
            Review Deck Again
          </button>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="relative w-full flex flex-col items-center pb-6">
      {/* Delayed Data Warning Banner */}
      {isDataDelayed && (
        <div className="w-full max-w-[420px] mb-3 px-3 py-2 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          <span>Scraper schedule delayed. Serving latest verified audio drop.</span>
        </div>
      )}

      {/* Main Deck Stack */}
      <div className="relative w-full max-w-[420px] flex items-center justify-center">
        {currentTrend && (
          <DeckCard
            key={currentTrend.id}
            trend={currentTrend}
            isTop5={currentIndex < 5}
            onSwipe={handleSwipe}
            canUndo={history.length > 0}
            onUndo={handleUndo}
          />
        )}
      </div>

      {/* Optional 3-Second Reason Chips After Skip */}
      <AnimatePresence>
        {showSkipChips && (
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="w-full max-w-[420px] mt-3 px-3 py-2 rounded-2xl bg-zinc-900/90 border border-white/10 backdrop-blur-md flex flex-col gap-1.5 shadow-xl"
          >
            <div className="flex items-center justify-between text-[11px] text-zinc-400 font-medium px-1">
              <span>Why skip? (optional)</span>
              <span className="text-[10px] text-zinc-500">Auto-dismissing...</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {SKIP_REASONS.map((reason) => (
                <button
                  key={reason}
                  type="button"
                  onClick={() => handleSelectSkipReason(reason)}
                  className="px-2.5 py-1 rounded-full bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-[11px] font-medium border border-white/5 transition-colors cursor-pointer"
                >
                  {reason}
                </button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
