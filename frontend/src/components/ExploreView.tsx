import React, { useState, useMemo } from "react";
import { Search, Globe, ChevronDown, Check, Sparkles, ExternalLink, Play } from "lucide-react";
import type { UiTrend } from "@/lib/api";
import { fetchAskSearch } from "@/lib/api";

interface ExploreViewProps {
  trends: UiTrend[];
  onSelectTrend: (trend: UiTrend) => void;
  onSavePick: (trend: UiTrend) => void;
}

const STAGE_PILLS = [
  { id: "all", label: "All Active" },
  { id: "Just starting", label: "🌱 Just starting" },
  { id: "Blowing up", label: "🚀 Blowing up" },
  { id: "Still going", label: "✨ Still going" },
  { id: "Comeback", label: "🔁 Comeback" },
];

const NICHE_CHIPS = [
  "all", "Fashion", "Dance", "Comedy", "Fitness", "Travel", "Food", "Beauty", "Music"
];

const LANGUAGES = [
  { id: "all", label: "All Languages" },
  { id: "hi", label: "🇮🇳 Hindi" },
  { id: "pa", label: "🎺 Punjabi" },
  { id: "ta", label: "🌴 Tamil" },
  { id: "te", label: "🌟 Telugu" },
  { id: "en", label: "🌐 English" },
  { id: "es", label: "🇪🇸 Spanish" },
  { id: "pt", label: "🇧🇷 Portuguese" },
  { id: "ko", label: "🇰🇷 Korean" },
];

export const ExploreView: React.FC<ExploreViewProps> = ({
  trends,
  onSelectTrend,
  onSavePick,
}) => {
  // FOUR Controls Only
  const [selectedStage, setSelectedStage] = useState<string>("all");
  const [selectedNiche, setSelectedNiche] = useState<string>("all");
  const [isGlobalMode, setIsGlobalMode] = useState<boolean>(false);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("all");
  const [includeExpired, setIncludeExpired] = useState<boolean>(false);

  // AI Search Box
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [askResult, setAskResult] = useState<{ intent: string; results: UiTrend[] } | null>(null);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) {
      setAskResult(null);
      return;
    }
    setIsSearching(true);
    try {
      const res = await fetchAskSearch(searchQuery.trim());
      setAskResult(res);
    } catch {
      setAskResult(null);
    } finally {
      setIsSearching(false);
    }
  };

  // Separate single-creator audios into Radar row (only if >=1 creator and not expired)
  const { radarAudios, mainList } = useMemo(() => {
    let base = askResult ? askResult.results : trends;

    // Filter by Stage
    if (selectedStage !== "all") {
      base = base.filter((t) => (t.stage || t.status || "").toLowerCase() === selectedStage.toLowerCase());
    }

    // Filter by Niche
    if (selectedNiche !== "all") {
      base = base.filter((t) => (t.category || "").toLowerCase() === selectedNiche.toLowerCase());
    }

    // Filter by Mode & Language
    if (isGlobalMode) {
      base = base.filter((t) => {
        const lang = (t.language || "").toLowerCase();
        return ["en", "es", "pt", "ko", "global"].includes(lang);
      });
    } else if (selectedLanguage !== "all") {
      base = base.filter((t) => (t.language || "").toLowerCase().includes(selectedLanguage));
    }

    // Include Expired filter
    if (!includeExpired) {
      base = base.filter((t) => t.status !== "expired" && t.stage !== "Expired");
    }

    const radar = base.filter((t) => (t.reelCount || 1) === 1);
    const main = base.filter((t) => (t.reelCount || 1) >= 2);

    return { radarAudios: radar.slice(0, 8), mainList: main };
  }, [trends, askResult, selectedStage, selectedNiche, isGlobalMode, selectedLanguage, includeExpired]);

  return (
    <div className="w-full flex flex-col gap-4 pb-12">
      {/* ── 1. AI Search Box ──────────────────────────────────────────────────── */}
      <form onSubmit={handleSearch} className="relative w-full">
        <input
          type="text"
          id="explore-ai-search"
          placeholder="Ask for audio ideas ('Rising fashion audios in India')..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-2xl bg-zinc-900 border border-white/10 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/50"
        />
        <Search className="absolute left-3.5 top-3 h-4 w-4 text-zinc-500" />
      </form>

      {/* ── 2. FOUR CONTROLS ONLY ──────────────────────────────────────────────── */}
      <div className="flex flex-col gap-2.5">
        {/* Control 1: Stage (4 Pills) */}
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar pb-0.5">
          {STAGE_PILLS.map((st) => (
            <button
              key={st.id}
              type="button"
              id={`stage-pill-${st.id.replace(/\s+/g, "-").toLowerCase()}`}
              onClick={() => setSelectedStage(st.id)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
                selectedStage === st.id
                  ? "bg-white text-black border-white"
                  : "bg-zinc-900 text-zinc-400 border-white/10 hover:text-white"
              }`}
            >
              {st.label}
            </button>
          ))}
        </div>

        {/* Control 2: Niche (Chips) */}
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar pb-0.5">
          {NICHE_CHIPS.map((niche) => (
            <button
              key={niche}
              type="button"
              id={`niche-chip-${niche.toLowerCase()}`}
              onClick={() => setSelectedNiche(niche)}
              className={`flex-shrink-0 px-2.5 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                selectedNiche === niche
                  ? "bg-primary text-white"
                  : "bg-zinc-900 text-zinc-400 hover:text-white"
              }`}
            >
              {niche === "all" ? "All Niches" : niche}
            </button>
          ))}
        </div>

        {/* Control 3 & 4: India/Global Toggle + Language + Include Expired */}
        <div className="flex items-center justify-between gap-2 pt-1 border-t border-white/5 text-xs">
          <div className="flex items-center gap-2">
            {/* India ⇄ Global Toggle */}
            <button
              type="button"
              id="lane-toggle-btn"
              onClick={() => setIsGlobalMode(!isGlobalMode)}
              className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-white/10 text-zinc-200 font-bold hover:bg-zinc-800 transition-colors cursor-pointer"
            >
              {isGlobalMode ? "🌍 Global" : "🇮🇳 India"}
            </button>

            {/* Language Dropdown */}
            {!isGlobalMode && (
              <select
                id="language-select-dropdown"
                value={selectedLanguage}
                onChange={(e) => setSelectedLanguage(e.target.value)}
                className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-white/10 text-zinc-300 font-medium cursor-pointer focus:outline-none"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.label}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Control 4: Include Expired Checkbox */}
          <label className="flex items-center gap-1.5 text-zinc-400 cursor-pointer text-[11px] select-none">
            <input
              type="checkbox"
              id="include-expired-checkbox"
              checked={includeExpired}
              onChange={(e) => setIncludeExpired(e.target.checked)}
              className="rounded bg-zinc-900 border-white/20 text-primary focus:ring-0"
            />
            <span>Include expired</span>
          </label>
        </div>
      </div>

      {/* ── 3. RADAR ROW: Single-creator Audios (1 creator so far) ───────────── */}
      {radarAudios.length > 0 && (
        <div className="flex flex-col gap-2 mt-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-zinc-300 flex items-center gap-1.5">
              <span>📡</span>
              <span>Radar: 1 creator so far</span>
            </span>
            <span className="text-[10px] text-zinc-500">{radarAudios.length} early signals</span>
          </div>
          <div className="flex gap-2.5 overflow-x-auto no-scrollbar pb-1">
            {radarAudios.map((t) => (
              <div
                key={t.id}
                onClick={() => onSelectTrend(t)}
                className="flex-shrink-0 w-44 p-2.5 rounded-xl bg-zinc-900/80 border border-white/10 hover:border-white/20 transition-all cursor-pointer flex flex-col justify-between"
              >
                <div>
                  <h4 className="text-xs font-bold text-white truncate">{t.song}</h4>
                  <p className="text-[10px] text-zinc-400 truncate">{t.artist}</p>
                </div>
                <div className="flex items-center justify-between mt-2 pt-1 border-t border-white/5 text-[10px] text-zinc-400">
                  <span className="text-pink-400 font-semibold">🌱 Early</span>
                  <span>1 creator</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 4. MAIN MULTI-CREATOR LIST ────────────────────────────────────────── */}
      <div className="flex flex-col gap-2.5 mt-2">
        <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
          Multi-Creator Trends ({mainList.length})
        </span>

        {mainList.length === 0 ? (
          <div className="p-8 text-center bg-zinc-900/40 rounded-2xl border border-white/5 text-xs text-zinc-500">
            No audios match the current filter selection.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {mainList.map((t) => (
              <div
                key={t.id}
                onClick={() => onSelectTrend(t)}
                className="p-3 rounded-2xl bg-zinc-950 border border-white/10 hover:border-white/20 transition-all cursor-pointer flex items-center justify-between gap-3"
              >
                <div className="flex flex-col min-w-0">
                  <h3 className="text-xs font-bold text-white truncate">{t.song}</h3>
                  <p className="text-[11px] text-zinc-400 truncate">{t.artist}</p>
                  <p className="text-[10px] text-emerald-400 font-semibold mt-1">
                    👥 {t.reelCount || 2} creators
                  </p>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSavePick(t);
                  }}
                  className="px-2.5 py-1.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-300 text-[11px] font-semibold border border-white/10 flex-shrink-0 cursor-pointer"
                >
                  Use It
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
