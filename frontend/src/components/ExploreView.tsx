import React, { useState, useMemo } from "react";
import { Search, Globe, ChevronDown, Check, Sparkles, ExternalLink, Play } from "lucide-react";
import type { UiTrend } from "@/lib/api";
import { fetchAskSearch } from "@/lib/api";

interface ExploreViewProps {
  trends: UiTrend[];
  onSelectTrend: (trend: UiTrend) => void;
  onSavePick: (trend: UiTrend) => void;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  onLoadMore?: () => void;
}

const STAGE_PILLS = [
  { id: "all", label: "All Active" },
  { id: "Just starting", label: "🌱 Just starting" },
  { id: "Blowing up", label: "🚀 Blowing up" },
  { id: "Still going", label: "✨ Still going" },
  { id: "Comeback", label: "🔁 Comeback" },
];

const NICHE_CHIPS = [
  "all", "Fitness", "Fashion", "Dance", "Beauty", "POV", "Travel", "Food", "Comedy", "Music"
];

const INDIA_LANGUAGES = [
  { id: "all", label: "All India" },
  { id: "hi", label: "🇮🇳 Hindi" },
  { id: "pa", label: "🎺 Punjabi" },
  { id: "ta", label: "🌴 Tamil" },
  { id: "te", label: "🌟 Telugu" },
  { id: "mr", label: "🦁 Marathi" },
  { id: "bn", label: "🐯 Bengali" },
  { id: "instrumental", label: "🎹 Instrumental" },
];

const GLOBAL_LANGUAGES = [
  { id: "all", label: "All Global" },
  { id: "en", label: "🇺🇸 English" },
  { id: "pt", label: "🇧🇷 Brazilian" },
  { id: "ko", label: "🇰🇷 Korean" },
  { id: "ru", label: "🇷🇺 Russian" },
  { id: "es", label: "🇪🇸 Spanish" },
  { id: "instrumental", label: "🎹 Instrumental" },
];

const SEARCH_SUGGESTIONS = [
  "Gym workout beat drop",
  "Fashion outfit transition",
  "GRWM aesthetic",
  "Viral dance choreography",
  "POV relatable acting",
];

export const ExploreView: React.FC<ExploreViewProps> = ({
  trends,
  onSelectTrend,
  onSavePick,
  hasMore = false,
  isLoadingMore = false,
  onLoadMore,
}) => {
  // Controls
  const [selectedStage, setSelectedStage] = useState<string>("all");
  const [selectedNiche, setSelectedNiche] = useState<string>("all");
  const [selectedRegion, setSelectedRegion] = useState<"all" | "india" | "global">("all");
  const [selectedIndiaLang, setSelectedIndiaLang] = useState<string>("all");
  const [selectedGlobalLang, setSelectedGlobalLang] = useState<string>("all");
  const [includeExpired, setIncludeExpired] = useState<boolean>(false);

  // AI / Catalog Search Box
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [askResult, setAskResult] = useState<{ intent: string; count_line?: string; chips?: Array<{ key: string; label: string }>; results: UiTrend[] } | null>(null);

  const executeSearch = async (queryText: string) => {
    const q = queryText.trim();
    if (!q) {
      setAskResult(null);
      return;
    }
    setSearchQuery(q);
    setIsSearching(true);
    try {
      const res = await fetchAskSearch(q);
      setAskResult(res);
    } catch {
      setAskResult(null);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    executeSearch(searchQuery);
  };

  const resolveLanguageCode = (t: UiTrend): string => {
    const raw = (t.rawLanguage || t.languageFinal || t.fallbackLanguage || t.language || "").toLowerCase().trim();
    const map: Record<string, string> = {
      hindi: "hi",
      punjabi: "pa",
      tamil: "ta",
      telugu: "te",
      marathi: "mr",
      bengali: "bn",
      kannada: "kn",
      malayalam: "ml",
      gujarati: "gu",
      nepali: "ne",
      english: "en",
      portuguese: "pt",
      brazilian: "pt",
      korean: "ko",
      russian: "ru",
      spanish: "es",
      instrumental: "instrumental",
    };
    return map[raw] || raw;
  };

  // Filter trends for Catalog Feed
  const { radarAudios, mainList } = useMemo(() => {
    let base = askResult ? askResult.results : trends;

    // Filter by Stage
    if (selectedStage !== "all") {
      base = base.filter((t) => (t.stage || t.status || "").toLowerCase() === selectedStage.toLowerCase());
    }

    // Filter by Niche (checks category, semantic_niches, AND why_this_works!)
    if (selectedNiche !== "all") {
      const nLow = selectedNiche.toLowerCase();
      base = base.filter((t) => {
        const cat = (t.category || "").toLowerCase();
        const why = (t.whyThisWorks || (t as any).why_this_works || "").toLowerCase();
        const note = (t.used_for_note || "").toLowerCase();
        return cat.includes(nLow) || why.includes(nLow) || note.includes(nLow);
      });
    }

    // Strict Region & Language Filtering (Zero Leaks)
    const indianLangs = ["hi", "pa", "ta", "te", "ml", "kn", "bn", "mr", "gu", "ne", "bho", "hne", "or"];
    const globalLangs = ["en", "es", "pt", "ko", "ja", "ru", "fr", "de", "it"];

    if (selectedRegion === "global") {
      // Must be a global language or instrumental, strictly exclude Indian regional
      base = base.filter((t) => {
        const langCode = resolveLanguageCode(t);
        if (indianLangs.includes(langCode)) return false;
        if (selectedGlobalLang !== "all") {
          return langCode === selectedGlobalLang;
        }
        return globalLangs.includes(langCode) || langCode === "global" || langCode === "instrumental" || !langCode;
      });
    } else if (selectedRegion === "india") {
      // India mode: Must be Indian language or instrumental, strictly exclude foreign pop/phonk/k-pop
      base = base.filter((t) => {
        const langCode = resolveLanguageCode(t);
        if (globalLangs.includes(langCode)) return false;
        if (selectedIndiaLang !== "all") {
          return langCode === selectedIndiaLang;
        }
        return indianLangs.includes(langCode) || langCode === "india" || langCode === "instrumental" || !langCode;
      });
    }

    // Include Expired filter
    if (!includeExpired) {
      base = base.filter((t) => t.status !== "expired" && t.stage !== "Expired");
    }

    // Radar tracks are early signals (1 creator)
    const radar = base.filter((t) => (t.reelCount ?? 1) === 1);

    // Full catalog list includes all matching audios
    return { radarAudios: radar.slice(0, 10), mainList: base };
  }, [trends, askResult, selectedStage, selectedNiche, selectedRegion, selectedIndiaLang, selectedGlobalLang, includeExpired]);

  return (
    <div className="w-full flex flex-col gap-4 pb-16">
      {/* ── 1. Catalog / AI Search Box ────────────────────────────────────────── */}
      <form onSubmit={handleSearch} className="relative w-full">
        <input
          type="text"
          id="explore-ai-search"
          placeholder="Search 2,000+ viral audios ('Gym beat drop', 'Fashion transition', 'POV')..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-10 pr-20 py-3 rounded-2xl bg-zinc-900/90 border border-white/10 text-xs text-white placeholder-zinc-500 focus:outline-none focus:border-primary/60 shadow-inner"
        />
        <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-zinc-400" />
        <button
          type="submit"
          disabled={isSearching}
          className="absolute right-2 top-2 px-3 py-1.5 rounded-xl bg-primary text-white text-[11px] font-bold hover:bg-primary/90 transition-all cursor-pointer disabled:opacity-50"
        >
          {isSearching ? "Searching..." : "Search"}
        </button>
      </form>

      {/* Quick Search Suggestion Pills */}
      {!askResult && (
        <div className="flex gap-1.5 overflow-x-auto no-scrollbar -mt-2 pb-1">
          {SEARCH_SUGGESTIONS.map((sug) => (
            <button
              key={sug}
              type="button"
              onClick={() => executeSearch(sug)}
              className="flex-shrink-0 px-2.5 py-1 rounded-full bg-zinc-900 border border-white/10 text-[11px] text-zinc-300 hover:text-white hover:border-primary/40 transition-all cursor-pointer"
            >
              {sug}
            </button>
          ))}
        </div>
      )}

      {askResult && (
        <div className="flex flex-col gap-1.5 -mt-2">
          <div className="flex items-center justify-between text-[11px] text-zinc-300 bg-zinc-900/90 border border-white/10 px-3 py-2 rounded-xl">
            <span id="search-count-line" className="font-semibold text-emerald-400">{askResult.count_line || askResult.intent}</span>
            <button
              type="button"
              id="clear-search-btn"
              onClick={() => {
                setAskResult(null);
                setSearchQuery("");
              }}
              className="text-[10px] text-zinc-400 hover:text-white underline cursor-pointer"
            >
              Clear Search
            </button>
          </div>
          {askResult.chips && askResult.chips.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-0.5">
              {askResult.chips.map((chip, idx) => (
                <span
                  key={idx}
                  data-testid="search-chip"
                  className="px-2 py-0.5 rounded-md bg-primary/20 border border-primary/40 text-primary text-[10px] font-bold flex items-center gap-1"
                >
                  <span>{chip.label}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── 2. CONTROLS: Stage, Niche, Region Tabs, Language ───────────────────── */}
      <div className="flex flex-col gap-2.5">
        {/* Stage Pills */}
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

        {/* Niche Chips */}
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

        {/* Region & Language Selector (Zero Leakage) */}
        <div className="flex items-center justify-between gap-2 pt-1.5 border-t border-white/5 text-xs flex-wrap">
          <div className="flex items-center gap-2">
            {/* Region Switcher: All | India | Global */}
            <div className="inline-flex rounded-xl bg-zinc-900 p-0.5 border border-white/10">
              <button
                type="button"
                id="lane-toggle-all"
                onClick={() => {
                  setSelectedRegion("all");
                  setSelectedIndiaLang("all");
                  setSelectedGlobalLang("all");
                }}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  selectedRegion === "all"
                    ? "bg-white text-black shadow-sm font-black"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                🌐 All
              </button>
              <button
                type="button"
                id="lane-toggle-india"
                onClick={() => {
                  setSelectedRegion("india");
                  setSelectedIndiaLang("all");
                }}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  selectedRegion === "india"
                    ? "bg-white text-black shadow-sm font-black"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                🇮🇳 India
              </button>
              <button
                type="button"
                id="lane-toggle-global"
                onClick={() => {
                  setSelectedRegion("global");
                  setSelectedGlobalLang("all");
                }}
                className={`px-3 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  selectedRegion === "global"
                    ? "bg-white text-black shadow-sm font-black"
                    : "text-zinc-400 hover:text-white"
                }`}
              >
                🌍 Global
              </button>
            </div>

            {/* Language Dropdown for India Mode */}
            {selectedRegion === "india" && (
              <select
                id="language-select-india"
                value={selectedIndiaLang}
                onChange={(e) => setSelectedIndiaLang(e.target.value)}
                className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-white/10 text-zinc-200 text-xs font-medium cursor-pointer focus:outline-none"
              >
                {INDIA_LANGUAGES.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.label}
                  </option>
                ))}
              </select>
            )}

            {/* Language Dropdown for Global Mode (Russian, Brazilian, Korean, Spanish, English) */}
            {selectedRegion === "global" && (
              <select
                id="language-select-global"
                value={selectedGlobalLang}
                onChange={(e) => setSelectedGlobalLang(e.target.value)}
                className="px-2.5 py-1 rounded-lg bg-zinc-900 border border-white/10 text-zinc-200 text-xs font-medium cursor-pointer focus:outline-none"
              >
                {GLOBAL_LANGUAGES.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.label}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Include Expired Checkbox */}
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

      {/* ── 3. RADAR ROW: Single-creator Audios ───────────────────────────────── */}
      {radarAudios.length > 0 && (
        <div className="flex flex-col gap-2 mt-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-bold text-zinc-300 flex items-center gap-1.5">
              <span>📡</span>
              <span>Radar: 1 creator early breakout</span>
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
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
            Trending Catalog ({mainList.length} audios)
          </span>
          {trends.length > mainList.length && (
            <span className="text-[10px] text-zinc-500">
              Filtered from {trends.length} active
            </span>
          )}
        </div>

        {mainList.length === 0 ? (
          <div className="p-8 text-center bg-zinc-900/40 rounded-2xl border border-white/5 text-xs text-zinc-500">
            No audios match the current filter selection. Try switching between India/Global or clear niche filter.
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {mainList.map((t) => (
              <div
                key={t.id}
                onClick={() => onSelectTrend(t)}
                data-testid="trend-card"
                className="p-3.5 rounded-2xl bg-zinc-950 border border-white/10 hover:border-white/20 transition-all cursor-pointer flex items-center justify-between gap-3 shadow-md"
              >
                <div className="flex flex-col min-w-0">
                  <h3 className="text-xs font-bold text-white truncate">{t.song}</h3>
                  <p className="text-[11px] text-zinc-400 truncate">{t.artist}</p>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className="text-[10px] text-emerald-400 font-semibold">
                      👥 {t.reelCount || 2} creators
                    </span>
                    {t.stage && (
                      <span className="text-[10px] text-zinc-400 bg-zinc-900 px-1.5 py-0.5 rounded border border-white/5">
                        {t.stage}
                      </span>
                    )}
                    {t.language && (
                      <span className="text-[10px] text-primary bg-primary/10 px-1.5 py-0.5 rounded uppercase font-bold">
                        {t.language}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSavePick(t);
                  }}
                  className="px-3 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-200 text-[11px] font-semibold border border-white/10 flex-shrink-0 cursor-pointer"
                >
                  Save Pick
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Load More Button for Infinite Catalog */}
        {hasMore && onLoadMore && (
          <div className="flex justify-center pt-4">
            <button
              type="button"
              id="load-more-trends-btn"
              onClick={onLoadMore}
              disabled={isLoadingMore}
              className="w-full sm:w-auto px-6 py-2.5 rounded-xl bg-zinc-900 border border-white/10 hover:bg-zinc-800 text-xs text-white font-bold transition-all cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoadingMore ? "Loading more audios..." : `Load More Audios (Showing ${mainList.length}) ⬇️`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
