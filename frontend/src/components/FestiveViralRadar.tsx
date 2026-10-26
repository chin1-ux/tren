import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Flame, 
  Sparkles, 
  Calendar, 
  Clock, 
  Copy, 
  Check, 
  Zap, 
  Music, 
  ShieldCheck, 
  Share2, 
  AlertCircle, 
  ChevronRight,
  TrendingUp,
  Tag,
  Compass,
  ArrowRight,
  Layers,
  BarChart2,
  Info,
  SlidersHorizontal,
  Video,
  Target,
  FileText
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { 
  fetchFestiveRadar, 
  generateFestiveIdeas, 
  fetchFestiveQuota,
  FestiveRadarResponse, 
  FestiveEvent, 
  FestiveIdeasResponse,
  FestiveReelConcept,
  FestiveQuotaInfo 
} from "@/lib/api";
import { useUserStore } from "@/store/useAppStore";

const NICHE_OPTIONS = [
  { id: "all", label: "All Niches", emoji: "🌐" },
  { id: "fitness", label: "Fitness & Gym", emoji: "💪" },
  { id: "fashion", label: "Fashion & Beauty", emoji: "👗" },
  { id: "food", label: "Food & Recipes", emoji: "🍽️" },
  { id: "comedy", label: "Comedy & Memes", emoji: "😂" },
  { id: "tech", label: "Tech & Gadgets", emoji: "📱" },
  { id: "finance", label: "Finance & Money", emoji: "💰" },
  { id: "travel", label: "Travel & Culture", emoji: "✈️" },
  { id: "dance", label: "Dance & Choreo", emoji: "💃" },
];

const CATEGORY_OPTIONS = [
  { id: "all", label: "All Events", emoji: "🌐" },
  { id: "cultural_in", label: "Indian Cultural", emoji: "🪔" },
  { id: "global_pop", label: "Global Pop & Viral", emoji: "🎃" },
  { id: "commercial_tech", label: "Shopping & Sales", emoji: "🛍️" },
  { id: "sports_entertainment", label: "Sports & Cricket", emoji: "🏏" },
];

const FORMAT_OPTIONS = [
  { id: "grwm", label: "GRWM & Talking Head", emoji: "🎬", desc: "Face-to-camera personal commentary, prep routine & relatable chatting" },
  { id: "faceless", label: "Faceless B-Roll & Aesthetic", emoji: "📸", desc: "Cinematic flatlays, hands, atmospheric lighting, mood cuts" },
  { id: "hack", label: "Fast 3-Step Actionable Hack", emoji: "⚡", desc: "Speedy tactical advice, problem-to-solution structure" },
  { id: "skit", label: "Relatable POV Skit / Comedy", emoji: "😂", desc: "POV situational comedy, relatable festival chaos & irony" },
  { id: "transformation", label: "Audio-Synced Transformation", emoji: "🔄", desc: "Satisfying before/after reveal snapped to audio beat drop" },
];

const TONE_OPTIONS = [
  { id: "relatable", label: "Relatable & Humorous", emoji: "☕" },
  { id: "aesthetic", label: "Aesthetic & Luxury", emoji: "✨" },
  { id: "hype", label: "High-Energy Hype", emoji: "🔥" },
  { id: "educational", label: "Authoritative & Tactical", emoji: "🧠" },
  { id: "emotional", label: "Heartfelt & Nostalgic", emoji: "💖" },
];

const GOAL_OPTIONS = [
  { id: "viral_reach", label: "Mass Reach & DM Shares", emoji: "🚀" },
  { id: "saves", label: "High Saves & Bookmarks", emoji: "💾" },
  { id: "engagement", label: "Comment Debate & Community", emoji: "💬" },
];

const QUICK_ANGLES = [
  "Last-minute prep panic",
  "Budget vs Luxury hack",
  "3 Mistakes everyone makes",
  "5-Minute quick glow-up",
  "What nobody tells you",
];

export function FestiveViralRadar() {
  const storeNiche = useUserStore((s) => s.niche) || "all";
  const [selectedNiche, setSelectedNiche] = useState<string>(storeNiche);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");

  // Creator Customization Options
  const [selectedFormat, setSelectedFormat] = useState<string>("grwm");
  const [selectedTone, setSelectedTone] = useState<string>("relatable");
  const [selectedGoal, setSelectedGoal] = useState<string>("viral_reach");
  const [customAngle, setCustomAngle] = useState("");
  const [isOptionsOpen, setIsOptionsOpen] = useState(true);

  // Radar Data
  const { data: radarData = null, isLoading: loadingRadar } = useQuery<FestiveRadarResponse | null>({
    queryKey: ["festive-radar", selectedNiche, selectedCategory],
    queryFn: () => fetchFestiveRadar(selectedNiche, selectedCategory),
    staleTime: 10 * 60_000,
  });

  // Daily AI Quota Data
  const { data: quotaData, refetch: refetchQuota } = useQuery<FestiveQuotaInfo>({
    queryKey: ["festive-quota"],
    queryFn: fetchFestiveQuota,
    staleTime: 30_000,
  });

  // Idea Generation State
  const [generatingForSlug, setGeneratingForSlug] = useState<string | null>(null);
  const [activeIdeas, setActiveIdeas] = useState<FestiveIdeasResponse | null>(null);
  const [copiedHook, setCopiedHook] = useState<string | null>(null);
  const [copiedFlow, setCopiedFlow] = useState<number | null>(null);
  const [filterPhase, setFilterPhase] = useState<"all" | "golden" | "peak">("all");

  const handleGenerateIdeas = async (eventSlug: string, angleOverride?: string) => {
    if (quotaData && quotaData.remaining <= 0) {
      toast.error("Daily AI Blueprint quota reached (10/10). Resets at 00:00 UTC. Repeat requests still load instantly from cache!");
    }

    setGeneratingForSlug(eventSlug);
    try {
      const result = await generateFestiveIdeas(eventSlug, selectedNiche, {
        customAngle: angleOverride !== undefined ? angleOverride : customAngle,
        tone: selectedTone,
        formatStyle: selectedFormat,
        targetGoal: selectedGoal,
      });

      setActiveIdeas(result);
      if (result.quota) {
        refetchQuota();
      }

      toast.success(
        result.is_cached
          ? `⚡ Loaded cached concept for ${result.event_name} (0 quota used)`
          : `✨ Generated 3 bespoke viral blueprints for ${result.event_name}!`
      );

      const el = document.getElementById("festive-blueprints-view");
      if (el) el.scrollIntoView({ behavior: "smooth" });
    } catch (err: any) {
      console.error("Error generating festive ideas:", err);
      const msg = err?.message || err?.detail || "Failed to generate festive concepts.";
      toast.error(msg);
    } finally {
      setGeneratingForSlug(null);
    }
  };

  const copyToClipboard = (text: string, label: string = "Hook") => {
    navigator.clipboard.writeText(text);
    setCopiedHook(text);
    toast.success(`${label} copied to clipboard!`);
    setTimeout(() => setCopiedHook(null), 2500);
  };

  const copyFullFlow = (concept: FestiveReelConcept, idx: number) => {
    const text = `Title: ${concept.concept_title}\n` +
      `3s Hook: "${concept.hook_3s}"\n` +
      `Format: ${concept.format_archetype} | Tone: ${selectedTone.toUpperCase()}\n\n` +
      `Script Flow:\n` +
      concept.blueprint_flow.map((s) => `• ${s}`).join("\n") +
      `\n\nOptimal Time: ${concept.optimal_post_window}\nAlgorithm Edge: ${concept.why_algorithm_favors}`;
    navigator.clipboard.writeText(text);
    setCopiedFlow(idx);
    toast.success(`Full script & visual flow for Concept #${idx + 1} copied!`);
    setTimeout(() => setCopiedFlow(null), 2500);
  };

  const allFestivals = [
    ...(radarData?.active_wave_festivals || []),
    ...(radarData?.upcoming_radar_festivals || [])
  ];

  const filteredFestivals = allFestivals.filter(f => {
    if (filterPhase === "golden") return f.wave_phase?.phase === "PRE_FESTIVE_SURGE";
    if (filterPhase === "peak") return f.wave_phase?.phase === "PEAK_HYPE" || f.wave_phase?.phase === "DAY_OF";
    return true;
  });

  const remainingQuota = quotaData?.remaining ?? 10;
  const totalLimit = quotaData?.limit ?? 10;

  return (
    <div className="space-y-8">
      {/* Hero Header */}
      <div className="rounded-3xl border border-primary/20 bg-gradient-to-br from-amber-500/10 via-orange-500/5 to-card p-6 md:p-8 relative overflow-hidden shadow-sm">
        <div className="absolute top-0 right-0 w-80 h-80 bg-orange-500/10 rounded-full blur-3xl pointer-events-none -mr-20 -mt-20" />
        
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-orange-500/15 text-orange-400 border border-orange-500/30">
              <Flame className="w-3.5 h-3.5 animate-pulse text-orange-500" />
              Seasonal, Festive & Viral Radar (India & Global)
            </div>
            <h2 className="text-2xl md:text-3xl font-bold font-display tracking-tight text-foreground">
              Film the Pre-Festive Surge <span className="text-orange-400">Before Feeds Flood</span>
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Instagram's algorithm distributes festive curiosity, styling, prep, & shopping <strong className="text-foreground">5 to 14 days before</strong> the event. Posting on the festival day means competing with 50M+ personal greeting clips.
            </p>
          </div>

          {/* AI Quota & Stat Pill Group */}
          <div className="shrink-0 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            {/* Strict Daily Quota Guard */}
            <div className="bg-background/90 backdrop-blur border border-amber-500/40 rounded-2xl p-4 flex flex-col items-center justify-center text-center min-w-[170px] shadow-sm">
              <span className="text-[10px] uppercase font-bold text-amber-500 tracking-wider flex items-center gap-1">
                <Zap className="w-3 h-3" /> AI Daily Quota
              </span>
              <span className="text-2xl font-extrabold text-foreground mt-0.5">
                {remainingQuota} <span className="text-xs font-normal text-muted-foreground">/ {totalLimit} left</span>
              </span>
              <span className="text-[10px] text-muted-foreground mt-1">
                Resets at 00:00 UTC
              </span>
            </div>

            {/* Quick Stat Pill */}
            <div className="bg-background/80 backdrop-blur border border-border/80 rounded-2xl p-4 flex flex-col items-center justify-center text-center min-w-[150px] shadow-sm">
              <span className="text-xs uppercase font-bold text-muted-foreground tracking-wider">Active Waves</span>
              <span className="text-2xl font-extrabold text-foreground mt-0.5">
                {radarData?.active_wave_festivals?.length ?? 2} <span className="text-xs font-medium text-orange-400">Waves</span>
              </span>
              <span className="text-[11px] text-emerald-400 font-semibold mt-1 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block" />
                Golden Filming Open
              </span>
            </div>
          </div>
        </div>

        {/* 4-Phase Wave Infographic Strip */}
        <div className="mt-6 pt-6 border-t border-border/40 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-2.5 rounded-xl bg-background/50 border border-border/40">
            <div className="font-semibold text-blue-400 flex items-center gap-1">
              <span>🔭 Horizon</span>
              <span className="text-[10px] text-muted-foreground">(19d+)</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">Scout props & concepts</p>
          </div>
          <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
            <div className="font-semibold text-emerald-400 flex items-center gap-1">
              <span>🔥 Pre-Surge</span>
              <span className="text-[10px] text-emerald-500 font-bold">(4-18d)</span>
            </div>
            <p className="text-[11px] text-emerald-300 font-medium mt-1">FILM & POST (Max Reach)</p>
          </div>
          <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30">
            <div className="font-bold text-amber-500 dark:text-amber-400 flex items-center gap-1">
              <span>⚡ Peak Hype</span>
              <span className="text-[10px] text-muted-foreground font-semibold">(1-3d)</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">GRWM & fast hacks</p>
          </div>
          <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30">
            <div className="font-semibold text-rose-400 flex items-center gap-1">
              <span>⚠️ Day Of</span>
              <span className="text-[10px] text-rose-500">(Day 0)</span>
            </div>
            <p className="text-[11px] text-muted-foreground mt-1">Feed flood / High saturation</p>
          </div>
        </div>
      </div>

      {/* Scope / Category Filter Rail */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-border/40 pb-4">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Event Scope</h3>
          <p className="text-[11px] text-muted-foreground">Filter by Indian cultural traditions or global pop-culture viral spikes.</p>
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto max-w-full pb-1 no-scrollbar">
          {CATEGORY_OPTIONS.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setSelectedCategory(cat.id)}
              className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 border ${
                selectedCategory === cat.id
                  ? "bg-foreground text-background border-foreground shadow-sm font-bold"
                  : "bg-muted/40 text-muted-foreground border-border/50 hover:text-foreground hover:bg-muted"
              }`}
            >
              <span>{cat.emoji}</span>
              <span>{cat.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Niche Selector Filter */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Select Your Creator Niche</h3>
          <p className="text-xs text-muted-foreground">Reel concepts and compatibility scores adapt to your category.</p>
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto max-w-full pb-2 no-scrollbar">
          {NICHE_OPTIONS.map((n) => (
            <button
              key={n.id}
              onClick={() => setSelectedNiche(n.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all flex items-center gap-1.5 border ${
                selectedNiche === n.id
                  ? "bg-primary text-primary-foreground border-primary shadow-sm font-bold"
                  : "bg-card/70 text-muted-foreground border-border/60 hover:text-foreground hover:bg-muted"
              }`}
            >
              <span>{n.emoji}</span>
              <span>{n.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Interactive Creator Blueprint Studio Customizer */}
      <div className="rounded-2xl border border-primary/20 bg-card/60 backdrop-blur p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-bold font-display text-foreground">
              Creator Blueprint Options
            </h3>
            <span className="text-[10px] text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
              Customizes AI tone, script flow & hook style
            </span>
          </div>
          <button
            onClick={() => setIsOptionsOpen(!isOptionsOpen)}
            className="text-xs text-primary font-semibold hover:underline"
          >
            {isOptionsOpen ? "Collapse Options" : "Customize Strategy"}
          </button>
        </div>

        {isOptionsOpen && (
          <div className="space-y-4 pt-2 border-t border-border/40 text-xs">
            {/* 1. Format Style */}
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1.5 flex items-center gap-1">
                <Video className="w-3.5 h-3.5 text-orange-400" />
                1. Video Format / Style
              </label>
              <div className="flex items-center gap-2 flex-wrap">
                {FORMAT_OPTIONS.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setSelectedFormat(f.id)}
                    className={`px-3 py-1.5 rounded-xl border transition-all text-left flex items-center gap-1.5 ${
                      selectedFormat === f.id
                        ? "bg-orange-500/15 border-orange-500/50 text-foreground font-semibold shadow-sm"
                        : "bg-muted/40 border-border/50 text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <span>{f.emoji}</span>
                    <span>{f.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* 2. Tone & Vibe + 3. Viral Goal in 2 columns */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Tone */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1.5 flex items-center gap-1">
                  <span>☕</span> 2. Tone & Voice
                </label>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {TONE_OPTIONS.map((t) => (
                    <button
                      key={t.id}
                      onClick={() => setSelectedTone(t.id)}
                      className={`px-2.5 py-1 rounded-lg border transition-all text-xs flex items-center gap-1 ${
                        selectedTone === t.id
                          ? "bg-primary/15 border-primary/50 text-primary font-bold shadow-sm"
                          : "bg-muted/30 border-border/50 text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <span>{t.emoji}</span>
                      <span>{t.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Goal */}
              <div>
                <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1.5 flex items-center gap-1">
                  <Target className="w-3.5 h-3.5 text-emerald-400" /> 3. Primary Viral Metric
                </label>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {GOAL_OPTIONS.map((g) => (
                    <button
                      key={g.id}
                      onClick={() => setSelectedGoal(g.id)}
                      className={`px-2.5 py-1 rounded-lg border transition-all text-xs flex items-center gap-1 ${
                        selectedGoal === g.id
                          ? "bg-emerald-500/15 border-emerald-500/50 text-emerald-400 font-bold shadow-sm"
                          : "bg-muted/30 border-border/50 text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <span>{g.emoji}</span>
                      <span>{g.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* 4. Quick Angles & Custom Creator Note */}
            <div>
              <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1.5">
                4. Custom Angle or Quick Theme Idea
              </label>
              <div className="flex items-center gap-1.5 flex-wrap mb-2">
                {QUICK_ANGLES.map((angle) => (
                  <button
                    key={angle}
                    onClick={() => setCustomAngle(angle)}
                    className="px-2.5 py-0.5 rounded-full bg-muted/60 hover:bg-muted text-[11px] text-muted-foreground hover:text-foreground transition-colors border border-border/40"
                  >
                    + {angle}
                  </button>
                ))}
              </div>
              <input
                type="text"
                value={customAngle}
                onChange={(e) => setCustomAngle(e.target.value)}
                placeholder="Optional: Describe your product, specific joke, outfit, or specific hook idea..."
                className="w-full bg-background border border-border/70 rounded-xl px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          </div>
        )}
      </div>

      {/* Active Golden Opportunity Spotlight */}
      {radarData?.golden_opportunity && (
        <div className="rounded-3xl border-2 border-emerald-500/40 bg-gradient-to-r from-emerald-500/10 via-card to-background p-6 shadow-md relative overflow-hidden">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <Flame className="w-3.5 h-3.5" />
                  GOLDEN FILMING WINDOW OPEN
                </span>
                <span className="text-xs font-semibold text-muted-foreground px-2 py-0.5 rounded-md bg-muted/60">
                  {radarData.golden_opportunity.days_until} days until festival
                </span>
                {radarData.golden_opportunity.category_label && (
                  <span className="text-xs font-medium text-muted-foreground px-2 py-0.5 rounded-md bg-muted/50 border border-border/40">
                    {radarData.golden_opportunity.category_label}
                  </span>
                )}
                <span className="text-xs font-bold text-amber-500 dark:text-amber-400 bg-amber-500/15 border border-amber-500/30 px-2 py-0.5 rounded-md">
                  ★ {radarData.golden_opportunity.niche_fit_score ?? 95}% Match for {selectedNiche}
                </span>
              </div>

              <div>
                <h3 className="text-2xl font-bold font-display text-foreground flex items-baseline gap-2">
                  {radarData.golden_opportunity.name}
                  {radarData.golden_opportunity.local_name && (
                    <span className="text-base text-muted-foreground font-normal">
                      ({radarData.golden_opportunity.local_name})
                    </span>
                  )}
                </h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Event Date: <strong className="text-foreground">{new Date(radarData.golden_opportunity.date).toLocaleDateString("en-IN", { month: "long", day: "numeric", year: "numeric" })}</strong>
                </p>
              </div>

              <p className="text-sm text-foreground/90 max-w-2xl bg-background/60 backdrop-blur p-3 rounded-xl border border-border/60">
                💡 <strong className="text-emerald-400">Viral Strategy:</strong> {radarData.golden_opportunity.wave_phase.filming_action}
              </p>

              {radarData.golden_opportunity.audio_vibe && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Music className="w-3.5 h-3.5 text-primary shrink-0" />
                  <span>Trending Sound Archetype: <strong className="text-foreground">{radarData.golden_opportunity.audio_vibe}</strong></span>
                </div>
              )}
            </div>

            <div className="shrink-0 flex flex-col gap-2.5">
              <Button
                size="lg"
                onClick={() => handleGenerateIdeas(radarData.golden_opportunity!.slug)}
                disabled={generatingForSlug === radarData.golden_opportunity.slug}
                className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold rounded-2xl gap-2 shadow-lg shadow-emerald-500/20 px-6 py-6 text-sm"
              >
                {generatingForSlug === radarData.golden_opportunity.slug ? (
                  <>
                    <Sparkles className="w-4 h-4 animate-spin" />
                    Generating Concepts...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    Generate {selectedNiche.toUpperCase()} Blueprints
                  </>
                )}
              </Button>
              <p className="text-[11px] text-muted-foreground text-center">
                Generates 3 word-for-word hooks & camera directions ({remainingQuota}/{totalLimit} daily credits left)
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Generated Ideas Spotlight Section */}
      <AnimatePresence>
        {activeIdeas && (
          <motion.div
            id="festive-blueprints-view"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="rounded-3xl border border-primary/30 bg-card p-6 md:p-8 space-y-6 shadow-xl relative"
          >
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border/60">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-primary/10 text-primary border border-primary/20">
                    {activeIdeas.is_ai_generated ? "✨ AI Generated Blueprints" : activeIdeas.is_cached ? "⚡ Instant Cached Blueprint" : "🎯 High-Converting Blueprint"}
                  </span>
                  <span className="text-xs text-muted-foreground uppercase font-bold tracking-wider">
                    {activeIdeas.niche} Niche
                  </span>
                  {activeIdeas.tone && (
                    <span className="text-[11px] text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-500/20">
                      {activeIdeas.tone}
                    </span>
                  )}
                  {activeIdeas.format_style && (
                    <span className="text-[11px] text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-md border border-purple-500/20">
                      {activeIdeas.format_style}
                    </span>
                  )}
                </div>
                <h3 className="text-xl md:text-2xl font-bold font-display text-foreground mt-1">
                  Viral Concepts for {activeIdeas.event_name}
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Optimal posting window: <strong className="text-foreground">{activeIdeas.wave_phase.phase_name}</strong> ({activeIdeas.wave_phase.days_until} days out)
                </p>
              </div>

              {/* Sound recommendation badge */}
              {activeIdeas.audio_recommendation && (
                <div className="bg-muted/60 p-3 rounded-2xl border border-border/60 max-w-sm text-xs">
                  <div className="font-semibold text-foreground flex items-center gap-1.5 mb-1">
                    <Music className="w-3.5 h-3.5 text-orange-400" />
                    Audio Mood Match
                  </div>
                  <p className="text-muted-foreground text-[11px]">{activeIdeas.audio_recommendation}</p>
                </div>
              )}
            </div>

            {/* 3 Concepts Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {activeIdeas.concepts.map((concept, idx) => (
                <div
                  key={idx}
                  className="rounded-2xl border border-border/80 bg-background/70 hover:border-primary/50 transition-all p-5 flex flex-col justify-between space-y-4 shadow-sm relative group"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-orange-400 bg-orange-400/10 px-2.5 py-0.5 rounded-full border border-orange-400/20">
                        Concept #{idx + 1}
                      </span>
                      <span className="text-xs font-bold text-emerald-400 flex items-center gap-1">
                        <TrendingUp className="w-3 h-3" />
                        {concept.virality_score}% Virality
                      </span>
                    </div>

                    <div>
                      <h4 className="font-bold text-base text-foreground leading-snug">
                        {concept.concept_title}
                      </h4>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span className="text-[10px] font-semibold text-muted-foreground bg-muted px-2 py-0.5 rounded">
                          {concept.hook_archetype}
                        </span>
                        <span className="text-[10px] font-semibold text-muted-foreground bg-muted px-2 py-0.5 rounded">
                          {concept.format_archetype}
                        </span>
                      </div>
                    </div>

                    {/* Word-for-Word Hook Box */}
                    <div className="rounded-xl bg-muted/40 border border-border/60 p-3 relative group/hook">
                      <span className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
                        3-Second Viral Hook:
                      </span>
                      <p className="text-xs font-medium text-foreground italic leading-relaxed">
                        "{concept.hook_3s}"
                      </p>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => copyToClipboard(concept.hook_3s, "Viral Hook")}
                        className="mt-2 w-full text-xs h-8 gap-1.5 rounded-lg border border-border/60"
                      >
                        {copiedHook === concept.hook_3s ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            Copy 3-Second Hook
                          </>
                        )}
                      </Button>
                    </div>

                    {/* Step-by-Step Blueprint */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground block">
                          Script & Camera Directives:
                        </span>
                        <button
                          onClick={() => copyFullFlow(concept, idx)}
                          className="text-[10px] text-primary hover:underline flex items-center gap-1 font-semibold"
                        >
                          {copiedFlow === idx ? (
                            <>
                              <Check className="w-3 h-3 text-emerald-400" /> Copied Flow
                            </>
                          ) : (
                            <>
                              <FileText className="w-3 h-3" /> Copy Full Flow
                            </>
                          )}
                        </button>
                      </div>
                      {concept.blueprint_flow.map((step, sIdx) => (
                        <div key={sIdx} className="text-xs text-muted-foreground flex items-start gap-1.5 leading-relaxed bg-muted/20 p-2 rounded-lg">
                          <span className="text-primary font-bold text-[11px] shrink-0">•</span>
                          <span>{step}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Footer Meta */}
                  <div className="pt-3 border-t border-border/50 text-[11px] space-y-1 text-muted-foreground">
                    <div>
                      📅 <strong className="text-foreground">Optimal Time:</strong> {concept.optimal_post_window}
                    </div>
                    <div>
                      🧠 <strong className="text-foreground">Algorithm Edge:</strong> {concept.why_algorithm_favors}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Recommended Hashtags */}
            {activeIdeas.recommended_hashtags && (
              <div className="pt-4 border-t border-border/50 flex items-center justify-between flex-wrap gap-2 text-xs">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-muted-foreground font-semibold flex items-center gap-1">
                    <Tag className="w-3 h-3" /> Recommended Tags:
                  </span>
                  {activeIdeas.recommended_hashtags.map((tag) => (
                    <span
                      key={tag}
                      onClick={() => copyToClipboard(tag, "Hashtag")}
                      className="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-mono text-[10px] cursor-pointer hover:bg-primary/20 transition-colors"
                      title="Click to copy"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    const allTags = activeIdeas.recommended_hashtags.join(" ");
                    copyToClipboard(allTags, "All Hashtags");
                  }}
                  className="text-xs h-7 gap-1"
                >
                  <Copy className="w-3 h-3" /> Copy All Tags
                </Button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Festival Radar Feed Filter Tabs */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-bold font-display text-foreground flex items-center gap-2">
              <Calendar className="w-4 h-4 text-orange-400" />
              All Monitored Cultural Waves (India)
            </h3>
            <p className="text-xs text-muted-foreground">
              Sorted by proximity and optimal viral posting window.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-muted/60 p-1 rounded-xl border border-border/60">
            <button
              onClick={() => setFilterPhase("all")}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                filterPhase === "all" ? "bg-card text-foreground shadow-sm font-bold" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All Waves ({allFestivals.length})
            </button>
            <button
              onClick={() => setFilterPhase("golden")}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all flex items-center gap-1 ${
                filterPhase === "golden" ? "bg-emerald-500/20 text-emerald-400 font-bold shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Flame className="w-3 h-3" />
              Golden Filming Window
            </button>
            <button
              onClick={() => setFilterPhase("peak")}
              className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all flex items-center gap-1 ${
                filterPhase === "peak" ? "bg-amber-500/20 text-amber-400 font-bold shadow-sm" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Zap className="w-3 h-3" />
              Peak Hype
            </button>
          </div>
        </div>

        {/* Festival Cards Grid */}
        {loadingRadar ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-44 rounded-2xl bg-card/50 border border-border/50 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredFestivals.map((festival) => {
              const isGolden = festival.wave_phase?.phase === "PRE_FESTIVE_SURGE";
              const isPeak = festival.wave_phase?.phase === "PEAK_HYPE";
              const isGenerating = generatingForSlug === festival.slug;
              const nicheScore = festival.niche_fit_score ?? Math.round((festival.niche_opportunities?.[selectedNiche] ?? 0.8) * 100);

              return (
                <div
                  key={festival.slug}
                  className={`rounded-2xl border p-5 transition-all flex flex-col justify-between space-y-4 hover:shadow-md ${
                    isGolden
                      ? "border-emerald-500/40 bg-gradient-to-br from-emerald-500/5 to-card"
                      : isPeak
                      ? "border-amber-500/40 bg-gradient-to-br from-amber-500/5 to-card"
                      : "border-border/80 bg-card hover:border-border"
                  }`}
                >
                  <div className="space-y-2.5">
                    {/* Header: Wave Badge + Days */}
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                            isGolden
                              ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                              : isPeak
                              ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                              : "bg-muted text-muted-foreground border-border/60"
                          }`}
                        >
                          {festival.wave_phase?.badge || "🔭 Radar"}
                        </span>
                        {festival.category_label && (
                          <span className="text-[10px] text-muted-foreground bg-muted/40 px-2 py-0.5 rounded-full border border-border/40">
                            {festival.category_label}
                          </span>
                        )}
                      </div>

                      <span className="text-xs font-bold text-foreground">
                        {festival.days_until === 0
                          ? "Today 🎉"
                          : festival.days_until === 1
                          ? "Tomorrow ⚡"
                          : `In ${festival.days_until} days`}
                      </span>
                    </div>

                    {/* Title + Local Name */}
                    <div>
                      <h4 className="font-bold text-base font-display text-foreground leading-snug">
                        {festival.name}
                        {festival.local_name && (
                          <span className="ml-1 text-xs text-muted-foreground font-normal">
                            ({festival.local_name})
                          </span>
                        )}
                      </h4>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {new Date(festival.date).toLocaleDateString("en-IN", {
                          month: "short",
                          day: "numeric",
                          year: "numeric"
                        })}
                        {festival.duration_days > 1 && ` • ${festival.duration_days} Days`}
                      </p>
                    </div>

                    {/* Strategy note */}
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                      {festival.wave_phase?.status_text}
                    </p>

                    {/* Niche compatibility & Tags */}
                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[11px] font-bold text-amber-500 dark:text-amber-400 flex items-center gap-1">
                        ★ {nicheScore}% {selectedNiche} fit
                      </span>

                      {festival.primary_regions && festival.primary_regions.length > 0 && (
                        <span className="text-[10px] text-muted-foreground truncate max-w-[120px]">
                          📍 {festival.primary_regions.slice(0, 2).join(", ")}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Action Button */}
                  <Button
                    size="sm"
                    variant={isGolden ? "default" : "outline"}
                    disabled={isGenerating}
                    onClick={() => handleGenerateIdeas(festival.slug)}
                    className={`w-full rounded-xl text-xs h-9 gap-1.5 font-bold ${
                      isGolden ? "bg-emerald-500 hover:bg-emerald-600 text-white shadow-sm" : ""
                    }`}
                  >
                    {isGenerating ? (
                      <>
                        <Sparkles className="w-3.5 h-3.5 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <Zap className="w-3.5 h-3.5" />
                        Generate Ideas for {selectedNiche}
                      </>
                    )}
                  </Button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
