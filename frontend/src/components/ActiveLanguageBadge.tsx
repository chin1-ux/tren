import React from "react";
import { X, Globe } from "lucide-react";

interface ActiveLanguageBadgeProps {
  activeLanguages?: string[];
  languagesMap: Array<{ code: string; label: string }>;
  onClear: () => void;
}

export function ActiveLanguageBadge({
  activeLanguages,
  languagesMap,
  onClear,
}: ActiveLanguageBadgeProps) {
  if (!activeLanguages || activeLanguages.length === 0) {
    return null;
  }

  const selectedLabels = activeLanguages.map((code) => {
    const match = languagesMap.find((l) => l.code === code);
    return match ? match.label.replace(/^[^\s]+\s/, "") : code;
  });

  return (
    <div
      id="active-language-filter-badge"
      className="flex items-center justify-between gap-2 rounded-xl border border-primary/25 bg-primary/10 px-3.5 py-2 text-xs font-medium text-foreground backdrop-blur-md transition-all"
    >
      <div className="flex items-center gap-1.5 flex-wrap">
        <Globe className="h-3.5 w-3.5 text-primary shrink-0" />
        <span className="text-primary font-semibold">Filtering:</span>
        <span className="text-foreground/90 font-medium">
          {selectedLabels.join(", ")}
        </span>
      </div>
      <button
        id="clear-language-filter-btn"
        onClick={onClear}
        className="flex items-center gap-1 rounded-md bg-background/60 hover:bg-background px-2 py-1 text-[11px] font-semibold text-muted-foreground hover:text-foreground transition-all active:scale-95 border border-border/40"
        aria-label="Clear active language filter"
      >
        <span>Clear</span>
        <X className="h-3 w-3 text-muted-foreground" />
      </button>
    </div>
  );
}
