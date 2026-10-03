import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, RotateCcw, Check, Sparkles, Clock, Flame, ShieldCheck, Film, Globe2 } from "lucide-react";

export interface FilterState {
  lifecycle: string; // 'all' | 'emerging' | 'rising' | 'resurging' | 'peaked' | 'expired'
  urgency: string;   // 'all' | 'under6' | 'under12' | 'under24' | 'under48'
  minOpportunityScore: number; // 0 | 70 | 80 | 90
  minVelocity: number; // 0 | 10 | 25 | 50
  outlierOnly: boolean;
  goldenHourOnly: boolean;
  niches: string[]; // ['all'] or array of niche IDs
  language: string; // 'all' | 'global' | 'hi' | 'pa' | ...
  format: string; // 'all' | 'dance' | 'narrative' | 'faceless'
}

interface TrendFiltersModalProps {
  isOpen: boolean;
  onClose: () => void;
  filters: FilterState;
  onChange: (updated: Partial<FilterState>) => void;
  onReset: () => void;
  nichesList: Array<{ id: string; label: string }>;
  languagesList: Array<{ code: string; label: string }>;
  totalResultsCount: number;
}

export function TrendFiltersModal({
  isOpen,
  onClose,
  filters,
  onChange,
  onReset,
  nichesList,
  languagesList,
  totalResultsCount,
}: TrendFiltersModalProps) {
  if (!isOpen) return null;

  const handleToggleNiche = (nicheId: string) => {
    if (nicheId === "all") {
      onChange({ niches: ["all"] });
      return;
    }
    const current = filters.niches.filter((n) => n !== "all");
    if (current.includes(nicheId)) {
      const next = current.filter((n) => n !== nicheId);
      onChange({ niches: next.length === 0 ? ["all"] : next });
    } else {
      onChange({ niches: [...current, nicheId] });
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-background/80 backdrop-blur-md"
        />

        {/* Modal Sheet */}
        <motion.div
          initial={{ y: "100%", opacity: 0.5 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: "100%", opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 280 }}
          className="relative w-full max-w-xl max-h-[88vh] flex flex-col bg-card border border-border/80 rounded-t-[1.75rem] sm:rounded-2xl shadow-2xl overflow-hidden z-10"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-5 py-4 border-b border-border/60 bg-muted/20">
            <div className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-primary">
                <Sparkles className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                  Intelligence Filters
                  <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-semibold">
                    {totalResultsCount} Audios
                  </span>
                </h3>
                <p className="text-xs text-muted-foreground">Tailor your viral discovery stream</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onReset}
                className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-muted-foreground hover:text-foreground rounded-lg hover:bg-muted/80 transition-colors"
              >
                <RotateCcw className="h-3 w-3" />
                Reset
              </button>
              <button
                type="button"
                onClick={onClose}
                className="h-8 w-8 rounded-full flex items-center justify-center hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Close filters"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          {/* Scrollable Filter Body */}
          <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6 no-scrollbar">
            
            {/* 1. Lifecycle Stage */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 block">
                Lifecycle Stage
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: "all", label: "All Stages", desc: "Every active track" },
                  { id: "emerging", label: "🚨 Emerging", desc: "Early signal, high upside" },
                  { id: "rising", label: "📈 Rising", desc: "Viral momentum spike" },
                  { id: "resurging", label: "🔄 Comeback", desc: "Evergreen resurgence" },
                  { id: "peaked", label: "📉 Peaked", desc: "High saturation" },
                  { id: "expired", label: "⛔ Expired", desc: "Historical archive" },
                ].map((st) => {
                  const isSelected = filters.lifecycle === st.id;
                  return (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => onChange({ lifecycle: st.id })}
                      className={`flex flex-col text-left p-2.5 rounded-xl border transition-all ${
                        isSelected
                          ? "border-primary bg-primary/10 text-primary ring-1 ring-primary/40 font-bold"
                          : "border-border/60 bg-muted/30 text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                      }`}
                    >
                      <span className="text-xs font-semibold">{st.label}</span>
                      <span className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">{st.desc}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 2. Urgency & Time to Act */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-primary" />
                Urgency / Creation Window
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: "all", label: "Any Window" },
                  { id: "under6", label: "🚨 < 6h Left", tag: "Critical" },
                  { id: "under12", label: "⚡ < 12h Left", tag: "Urgent" },
                  { id: "under24", label: "🕒 < 24h Left", tag: "Prime" },
                ].map((u) => {
                  const isSelected = filters.urgency === u.id;
                  return (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => onChange({ urgency: u.id })}
                      className={`flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium border transition-all ${
                        isSelected
                          ? "border-primary bg-primary/10 text-primary font-bold"
                          : "border-border/60 bg-muted/30 text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                      }`}
                    >
                      <span>{u.label}</span>
                      {isSelected && <Check className="h-3 w-3 text-primary" />}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 3. Virality Confidence & Predictive Signals */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                Confidence & Predictive Signals
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {/* Min Opportunity Score */}
                <div className="p-3 rounded-xl border border-border/60 bg-muted/20">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-xs font-semibold text-foreground">Opportunity Score</span>
                    <span className="text-xs font-bold text-primary">
                      {filters.minOpportunityScore > 0 ? `${filters.minOpportunityScore}+` : "Any"}
                    </span>
                  </div>
                  <div className="flex gap-1.5">
                    {[0, 70, 80, 85].map((score) => (
                      <button
                        key={score}
                        type="button"
                        onClick={() => onChange({ minOpportunityScore: score })}
                        className={`flex-1 py-1 text-[11px] rounded-lg border font-medium transition-all ${
                          filters.minOpportunityScore === score
                            ? "bg-primary text-white border-primary"
                            : "bg-muted/50 border-border/50 text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        {score === 0 ? "All" : `${score}+`}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Min Velocity Multiplier */}
                <div className="p-3 rounded-xl border border-border/60 bg-muted/20">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-xs font-semibold text-foreground">Viral Velocity</span>
                    <span className="text-xs font-bold text-amber-500">
                      {filters.minVelocity > 0 ? `${filters.minVelocity}x+` : "Any"}
                    </span>
                  </div>
                  <div className="flex gap-1.5">
                    {[0, 15, 30, 50].map((vel) => (
                      <button
                        key={vel}
                        type="button"
                        onClick={() => onChange({ minVelocity: vel })}
                        className={`flex-1 py-1 text-[11px] rounded-lg border font-medium transition-all ${
                          filters.minVelocity === vel
                            ? "bg-amber-500 text-white border-amber-500"
                            : "bg-muted/50 border-border/50 text-muted-foreground hover:text-foreground"
                        }`}
                      >
                        {vel === 0 ? "All" : `${vel}x+`}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Creator Outlier Toggle */}
                <button
                  type="button"
                  onClick={() => onChange({ outlierOnly: !filters.outlierOnly })}
                  className={`flex items-center justify-between p-3 rounded-xl border transition-all text-left ${
                    filters.outlierOnly
                      ? "border-emerald-500 bg-emerald-500/10 text-emerald-400 font-bold"
                      : "border-border/60 bg-muted/20 text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <div>
                    <span className="text-xs font-semibold block text-foreground">⭐ Creator Outliers Only</span>
                    <span className="text-[10px] text-muted-foreground">Blew up from small creators (high intrinsic audio power)</span>
                  </div>
                  <div className={`h-4 w-4 rounded-full border flex items-center justify-center ${
                    filters.outlierOnly ? "border-emerald-500 bg-emerald-500" : "border-border"
                  }`}>
                    {filters.outlierOnly && <Check className="h-2.5 w-2.5 text-white" />}
                  </div>
                </button>

                {/* Golden Hour Toggle */}
                <button
                  type="button"
                  onClick={() => onChange({ goldenHourOnly: !filters.goldenHourOnly })}
                  className={`flex items-center justify-between p-3 rounded-xl border transition-all text-left ${
                    filters.goldenHourOnly
                      ? "border-amber-500 bg-amber-500/10 text-amber-500 font-bold"
                      : "border-border/60 bg-muted/20 text-muted-foreground hover:text-foreground"
                  }`}
                >
                  <div>
                    <span className="text-xs font-semibold block text-foreground flex items-center gap-1">
                      <Flame className="h-3 w-3 text-amber-500" />
                      Golden Hour Window
                    </span>
                    <span className="text-[10px] text-muted-foreground">&lt;28% Saturation + High Velocity</span>
                  </div>
                  <div className={`h-4 w-4 rounded-full border flex items-center justify-center ${
                    filters.goldenHourOnly ? "border-amber-500 bg-amber-500" : "border-border"
                  }`}>
                    {filters.goldenHourOnly && <Check className="h-2.5 w-2.5 text-white" />}
                  </div>
                </button>
              </div>
            </div>

            {/* 4. Creator Niches */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Creator Niche
                </label>
                {filters.niches.length > 0 && !filters.niches.includes("all") && (
                  <span className="text-[11px] text-primary font-semibold">
                    {filters.niches.length} selected
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-1.5">
                {nichesList.map((n) => {
                  const isSelected = n.id === "all" ? filters.niches.includes("all") : filters.niches.includes(n.id);
                  return (
                    <button
                      key={n.id}
                      type="button"
                      onClick={() => handleToggleNiche(n.id)}
                      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                        isSelected
                          ? "bg-primary text-white shadow-sm ring-1 ring-primary/40 font-bold"
                          : "bg-muted/70 border border-border/50 text-muted-foreground hover:text-foreground hover:bg-muted"
                      }`}
                    >
                      {n.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 5. Language & Region */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                <Globe2 className="h-3.5 w-3.5 text-primary" />
                Language & Regional Cluster
              </label>
              <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto no-scrollbar p-1">
                {languagesList.map((l) => {
                  const isSelected = filters.language === l.code;
                  return (
                    <button
                      key={l.code}
                      type="button"
                      onClick={() => onChange({ language: l.code })}
                      className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                        isSelected
                          ? "bg-secondary text-secondary-foreground shadow-sm ring-1 ring-secondary/50 font-bold"
                          : "bg-muted/60 border border-border/40 text-muted-foreground hover:text-foreground hover:bg-muted"
                      }`}
                    >
                      {l.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 6. Video Format & Production Type */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                <Film className="h-3.5 w-3.5 text-primary" />
                Content Format / Style
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { id: "all", label: "All Formats" },
                  { id: "dance", label: "💃 Dance / Routine" },
                  { id: "narrative", label: "🎞️ Cinematic Edit" },
                  { id: "faceless", label: "🎭 Faceless / Text" },
                ].map((f) => {
                  const isSelected = filters.format === f.id;
                  return (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => onChange({ format: f.id })}
                      className={`px-2.5 py-2 rounded-xl text-xs font-medium border text-center transition-all ${
                        isSelected
                          ? "border-primary bg-primary/10 text-primary font-bold"
                          : "border-border/60 bg-muted/30 text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                      }`}
                    >
                      {f.label}
                    </button>
                  );
                })}
              </div>
            </div>

          </div>

          {/* Footer Action */}
          <div className="p-4 border-t border-border/60 bg-muted/30 flex items-center justify-between">
            <span className="text-xs text-muted-foreground">
              Showing <strong className="text-foreground">{totalResultsCount}</strong> matching trends
            </span>
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2 rounded-xl bg-primary text-white font-bold text-xs shadow-md shadow-primary/25 hover:bg-primary/90 transition-all cursor-pointer"
            >
              Apply Filters
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
