import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { 
  Lightbulb, 
  Calendar as CalendarIcon, 
  Sparkles, 
  Clock, 
  Music, 
  CheckCircle2, 
  RefreshCw, 
  Flame, 
  Award, 
  Gauge, 
  Wrench, 
  Copy, 
  Check, 
  ChevronRight,
  HelpCircle,
  Hash,
  Compass
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { 
  fetchDailyIdeas, 
  scoreReel, 
  generateHooks, 
  generateCalendar, 
  ApiDailyIdea, 
  ScoreReelResponse, 
  GeneratedHook, 
  CalendarDay 
} from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { FEATURES } from "@/lib/features";
import { PlanGate } from "@/components/PlanGate";
import { useUserStore } from "@/store/useAppStore";
import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";

export const Route = createFileRoute("/ideas")({
  head: () => ({
    meta: [
      { title: "Ideation & Scoring Hub — Trendrop" },
      { name: "description", content: "Personalized daily ideas, reel scoring gauge, hook generator, and content calendar." },
    ],
  }),
  errorComponent: RouteErrorBoundary,
  component: IdeasPage,
});

function IdeasPage() {
  const { user } = useAuth();
  const userPlan = useUserStore((s) => s.plan) || 'free';
  
  // Feature disabled check
  if (!FEATURES.IDEAS_ENABLED) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4 pb-28 pt-6">
        <div className="text-center space-y-4">
          <div className="h-16 w-16 rounded-2xl bg-muted/60 flex items-center justify-center text-muted-foreground mx-auto">
            <Lightbulb className="h-8 w-8" />
          </div>
          <h1 className="text-xl font-bold text-foreground">Feature Temporarily Disabled</h1>
          <p className="text-sm text-muted-foreground max-w-xs">
            The Ideation Hub is currently unavailable. Focus on the core trend detection dashboard for now.
          </p>
        </div>
      </div>
    );
  }

  const [activeTab, setActiveTab] = useState<"daily" | "score" | "hooks" | "calendar">("daily");

  // Hide calendar tab if feature disabled
  const availableTabs = FEATURES.CALENDAR_ENABLED 
    ? ["daily", "score", "hooks", "calendar"] as const
    : ["daily", "score", "hooks"] as const;
  const [userEmail, setUserEmail] = useState("anonymous@trendrop.app");
  const [userNiche, setUserNiche] = useState("dance");

  // Section 1: Daily Idea Drop States
  const [ideas, setIdeas] = useState<ApiDailyIdea[]>([]);
  const [loadingIdeas, setLoadingIdeas] = useState(false);
  const [usingFallbackIdeas, setUsingFallbackIdeas] = useState(false);

  // Section 2: Pre-Post Reel Score States
  const [scoreAudio, setScoreAudio] = useState("");
  const [scoreCaption, setScoreCaption] = useState("");
  const [scorePostingTime, setScorePostingTime] = useState("18:30");
  const [scoreNiche, setScoreNiche] = useState("dance");
  const [scoringResult, setScoringResult] = useState<ScoreReelResponse | null>(null);
  const [loadingScore, setLoadingScore] = useState(false);

  // Section 3: Hook Generator States
  const [hookTrend, setHookTrend] = useState("");
  const [hookDescription, setHookDescription] = useState("");
  const [generatedHooks, setGeneratedHooks] = useState<GeneratedHook[]>([]);
  const [loadingHooks, setLoadingHooks] = useState(false);

  // Section 4: Content Calendar States
  const [calendar, setCalendar] = useState<CalendarDay[]>([]);
  const [loadingCalendar, setLoadingCalendar] = useState(false);
  const [selectedDay, setSelectedDay] = useState<CalendarDay | null>(null);

  // Clipboard tracking
  const [copiedText, setCopiedText] = useState<string | null>(null);

  useEffect(() => {
    const email = user?.email || localStorage.getItem("trendrop_user_email") || "anonymous@trendrop.app";
    const niche = localStorage.getItem("trendrop_niche") || "dance";
    setUserEmail(email);
    setUserNiche(niche);
    setScoreNiche(niche);
    
    // Load daily ideas
    getIdeas(email);
    // Load saved calendar from local storage or DB
    loadSavedCalendar(email);
  }, [user]);

  const getIdeas = async (email: string) => {
    setLoadingIdeas(true);
    setUsingFallbackIdeas(false);
    try {
      const data = await fetchDailyIdeas(email);
      setIdeas(data);
      // Detect server-side fallback: any idea with is_fallback means LLM failed
      const isServerFallback = Array.isArray(data) && data.length > 0 && data.some(i => i.is_fallback);
      setUsingFallbackIdeas(isServerFallback);
    } catch (err) {
      console.error("Failed to load daily ideas", err);
      toast.error("Could not load personalized ideas. Check your connection.");
      setUsingFallbackIdeas(true);
      setIdeas([]);
    } finally {
      setLoadingIdeas(false);
    }
  };

  const loadSavedCalendar = async (email: string) => {
    try {
      const saved = localStorage.getItem(`trendrop_calendar_${email}`);
      if (saved) {
        setCalendar(JSON.parse(saved));
      }
    } catch {}
  };

  const handleCopy = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    toast.success(`${label} copied to clipboard!`);
    setTimeout(() => setCopiedText(null), 2000);
  };

  // Section 1 Action
  const handleUseIdea = (idea: ApiDailyIdea) => {
    setScoreAudio(idea.audio_suggestion);
    setScoreCaption(`${idea.hook}\n\nHere's how to do it...\n\n#${userNiche} #trend #viral`);
    setScoreNiche(userNiche);
    
    // Smooth scroll/transition to score tab
    setActiveTab("score");
    toast.success("Idea pre-filled into Pre-Post Reel Scorer!");
  };

  // Section 2 Action
  const handleScoreReel = async () => {
    if (!scoreAudio || !scoreCaption || !scoreNiche) {
      toast.error("Please fill in all inputs to score your reel.");
      return;
    }
    setLoadingScore(true);
    setScoringResult(null);
    try {
      const result = await scoreReel({
        audio: scoreAudio,
        caption: scoreCaption,
        posting_time: scorePostingTime,
        niche: scoreNiche
      });
      setScoringResult(result);
      if (result.is_fallback) {
        toast.warning(result.fallback_reason || "Showing fallback score — LLM unavailable");
      } else {
        toast.success("Reel scored successfully!");
      }
    } catch (err) {
      console.error("Failed to score reel", err);
      toast.error("Failed to score your reel. Using fallback score.");
      // Set fallback score
      setScoringResult({
        overall_score: 75,
        grade: "B",
        hook_score: 70,
        audio_score: 70,
        caption_score: 70,
        hashtag_score: 70,
        timing_score: 70,
        top_fixes: ["Keep the first 3 seconds extremely fast-paced.", "Optimize the caption with target keywords."],
        is_fallback: true,
        fallback_reason: "Server error — showing generic score"
      });
    } finally {
      setLoadingScore(false);
    }
  };

  // Section 3 Action
  const handleGenerateHooks = async () => {
    if (!hookTrend || !hookDescription) {
      toast.error("Please enter a trend/topic and content description.");
      return;
    }
    setLoadingHooks(true);
    setGeneratedHooks([]);
    try {
      const data = await generateHooks({
        trend: hookTrend,
        content_description: hookDescription
      });
      setGeneratedHooks(data.hooks);
      toast.success("5 high-converting hooks generated!");
    } catch (err) {
      console.error("Failed to generate hooks", err);
      toast.error("Failed to generate hooks. Using fallback hooks.");
      // Set fallback hooks
      setGeneratedHooks([
        { style: "Curiosity", text: `Why nobody is talking about ${hookDescription}`, why_it_works: "Intrigue" },
        { style: "Authority", text: `The only guide you need for ${hookDescription}`, why_it_works: "Establishes immediate value" },
        { style: "Relatable", text: "I was today years old when I learned this about " + hookDescription, why_it_works: "Humor & connection" }
      ]);
    } finally {
      setLoadingHooks(false);
    }
  };

  // Section 4 Action
  const handleGenerateCalendar = async () => {
    setLoadingCalendar(true);
    try {
      const res = await generateCalendar(userEmail);
      setCalendar(res.calendar);
      localStorage.setItem(`trendrop_calendar_${userEmail}`, JSON.stringify(res.calendar));
      if (res.is_fallback) {
        toast.warning(res.fallback_reason || "Showing generic calendar — LLM unavailable");
      } else {
        toast.success("Your 30-Day starter template is ready!");
      }
    } catch (err) {
      console.error("Failed to generate calendar", err);
      toast.error("Failed to generate your 30-Day calendar. Using fallback calendar.");
      
      // Seeded fallback calendar with built-in major Indian holidays and festivals
      const holidays: Record<number, string> = {
        6: "🇮🇳 Independence Day Special",
        19: "✨ Raksha Bandhan special",
        26: "🙏 Janmashtami Celebrations",
        30: "🎯 Month End Goal Tracking"
      };

      const fallbackCalendar = Array.from({ length: 30 }, (_, i) => {
        const dayNum = i + 1;
        const festivalName = holidays[dayNum];
        return {
          day: dayNum,
          topic: festivalName 
            ? `${festivalName}: Post regional transitions matching the celebration vibe!`
            : `Challenge Day ${dayNum}: Publish a 15-second key tip in ${userNiche}`,
          hook: festivalName
            ? `Happy ${festivalName.replace(/[^a-zA-Z\s]/g, "").trim()}! Here is how we celebrate...`
            : `If you are struggling with this, watch until the end...`,
          audio_style: festivalName ? "Festive traditional fusion beat" : "Trending aesthetic lofi",
          hashtags: festivalName ? ["#festivalseason", "#festivevibes"] : ["#creatorcommunity", "#contenttips"],
          posting_time: "6:30 PM"
        };
      });

      setCalendar(fallbackCalendar);
      localStorage.setItem(`trendrop_calendar_${userEmail}`, JSON.stringify(fallbackCalendar));
    } finally {
      setLoadingCalendar(false);
    }
  };

  // Difficulty styling
  const getDifficultyBadge = (difficulty: string) => {
    switch ((difficulty ?? "").toLowerCase()) {
      case "easy":
        return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      case "medium":
        return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
      case "hard":
        return "bg-primary/10 text-primary border border-primary/20";
      default:
        return "bg-primary/10 text-primary border border-primary/20";
    }
  };

  return (
    <PlanGate
      feature="Ideation Hub"
      requiredPlan="pro"
      currentPlan={userPlan}
      onUpgrade={() => window.location.href = '/pricing'}
    >
    <div className="flex flex-col gap-6 px-4 pb-28 pt-6 max-w-2xl mx-auto w-full">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-purple-600 text-white text-xl font-bold shadow-lg shadow-primary/20 animate-pulse">
          <Lightbulb className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold bg-clip-text bg-gradient-to-r from-text via-text to-primary text-transparent">Ideation Hub</h1>
          <p className="text-xs text-muted-foreground">AI-powered trend scoring, hook generators, and daily schedules</p>
        </div>
      </header>

      {/* Modern High-End Tab Swapper */}
      <div className={`grid gap-1 rounded-xl bg-surface-2 border border-border p-1 backdrop-blur-md ${FEATURES.CALENDAR_ENABLED ? 'grid-cols-4' : 'grid-cols-3'}`}>
        <button
          onClick={() => setActiveTab("daily")}
          className={`flex flex-col md:flex-row items-center justify-center gap-1.5 rounded-lg py-2.5 text-[10px] font-bold uppercase tracking-wider transition-all duration-300 ${
            activeTab === "daily" 
              ? "bg-gradient-to-r from-primary to-purple-600 text-white shadow-lg" 
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Idea Drop</span>
          <span className="sm:hidden">Daily</span>
        </button>

        <button
          onClick={() => setActiveTab("score")}
          className={`flex flex-col md:flex-row items-center justify-center gap-1.5 rounded-lg py-2.5 text-[10px] font-bold uppercase tracking-wider transition-all duration-300 ${
            activeTab === "score" 
              ? "bg-gradient-to-r from-primary to-purple-600 text-white shadow-lg" 
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Gauge className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Reel Score</span>
          <span className="sm:hidden">Score</span>
        </button>

        <button
          onClick={() => setActiveTab("hooks")}
          className={`flex flex-col md:flex-row items-center justify-center gap-1.5 rounded-lg py-2.5 text-[10px] font-bold uppercase tracking-wider transition-all duration-300 ${
            activeTab === "hooks" 
              ? "bg-gradient-to-r from-primary to-purple-600 text-white shadow-lg" 
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Flame className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Hook Gen</span>
          <span className="sm:hidden">Hooks</span>
        </button>

        {FEATURES.CALENDAR_ENABLED && (
          <button
            onClick={() => setActiveTab("calendar")}
            className={`flex flex-col md:flex-row items-center justify-center gap-1.5 rounded-lg py-2.5 text-[10px] font-bold uppercase tracking-wider transition-all duration-300 ${
              activeTab === "calendar" 
                ? "bg-gradient-to-r from-primary to-purple-600 text-white shadow-lg" 
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <CalendarIcon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Calendar</span>
            <span className="sm:hidden">Calendar</span>
          </button>
        )}
      </div>

      {/* Main Tab Contents */}
      <div className="mt-2 min-h-[450px]">
        <AnimatePresence mode="wait">
          {/* TAB 1: DAILY IDEA DROP */}
          {activeTab === "daily" && (
            <motion.div 
              key="daily"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.2 }}
              className="space-y-5"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-text">Daily Idea Drop</h2>
                  <p className="text-xs text-muted-foreground">3 fresh trend-backed ideas customized for your niche</p>
                </div>
                <Button 
                  onClick={() => getIdeas(userEmail)} 
                  disabled={loadingIdeas}
                  variant="outline"
                  size="sm"
                  className="h-8 border-border hover:bg-surface-2 flex items-center gap-1.5 text-xs text-text"
                >
                  <RefreshCw className={`h-3 w-3 ${loadingIdeas ? 'animate-spin' : ''}`} /> 
                  Refresh
                </Button>
              </div>

              {usingFallbackIdeas && !loadingIdeas && ideas.length > 0 && (
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3.5 mb-4 text-xs text-amber-400 leading-relaxed">
                  ⚠️ <strong>Personalized Ideas Offline:</strong> We couldn't load custom ideas tailored to your niche. Showing generic fallback starting points instead.
                </div>
              )}

              {loadingIdeas ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3 text-muted-foreground">
                  <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                  <span className="text-sm font-semibold animate-pulse">Curating personalized ideas...</span>
                </div>
              ) : ideas.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center gap-4">
                  <div className="h-16 w-16 rounded-2xl bg-muted/50 flex items-center justify-center">
                    <Lightbulb className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <div>
                    <h3 className="font-bold text-foreground">No ideas available</h3>
                    <p className="text-sm text-muted-foreground mt-1 max-w-xs">
                      We couldn't generate personalized ideas right now. Tap Refresh to try again.
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="rounded-xl text-xs"
                    onClick={() => getIdeas(userEmail)}
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Try Again
                  </Button>
                </div>
              ) : (
                <div className="grid gap-4">
                  {ideas.map((idea, index) => (
                    <div 
                      key={index} 
                      className="relative p-5 border border-border hover:border-primary/30 transition-all duration-300 rounded-2xl bg-surface-2 shadow-xl space-y-4"
                    >
                      <div className="flex justify-between items-start gap-4">
                        <span className={`text-[10px] font-extrabold uppercase px-2.5 py-1 rounded-full ${getDifficultyBadge(idea.difficulty)}`}>
                          {idea.difficulty || "Medium"} Difficulty
                        </span>
                        <span className="text-xs font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-md">
                          Idea #{index + 1}
                        </span>
                      </div>

                      <div className="space-y-2">
                        <h3 className="font-display font-bold text-lg text-text leading-tight">{idea.title}</h3>
                        <p className="text-sm text-text-muted leading-relaxed">{idea.description}</p>
                      </div>

                      {/* Hook & Details */}
                      <div className="bg-surface rounded-xl border border-border p-4 space-y-3">
                        <div className="flex items-start gap-2.5">
                          <span className="text-primary text-xs font-black uppercase tracking-wider pt-0.5">Hook:</span>
                          <p className="text-sm text-primary dark:text-primary italic font-medium">"{idea.hook}"</p>
                        </div>
                        
                        <div className="h-px bg-border" />
                        
                        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-text-muted">
                          <div className="flex items-center gap-1.5 bg-surface-2 border border-border px-2.5 py-1 rounded-lg">
                            <Music className="h-3.5 w-3.5 text-primary" />
                            <span className="truncate max-w-[150px]">{idea.audio_suggestion}</span>
                          </div>
                          <div className="flex items-center gap-1.5 bg-surface-2 border border-border px-2.5 py-1 rounded-lg">
                            <Clock className="h-3.5 w-3.5 text-primary" />
                            <span>Post: {idea.posting_time}</span>
                          </div>
                        </div>
                      </div>

                      {/* Use Idea Button */}
                      <div className="flex gap-2">
                        <Button 
                          onClick={() => handleUseIdea(idea)}
                          className="flex-1 bg-gradient-to-r from-primary to-purple-600 hover:from-primary hover:to-purple-700 text-white font-bold rounded-xl h-10 transition-all shadow-md shadow-primary/10"
                        >
                          Use This Idea
                          <ChevronRight className="ml-1.5 h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => handleCopy(`Title: ${idea.title}\nHook: ${idea.hook}\nAudio: ${idea.audio_suggestion}\nTime: ${idea.posting_time}`, "Idea details")}
                          className="h-10 w-10 border-border rounded-xl hover:bg-surface-2"
                        >
                          {copiedText === `Title: ${idea.title}\nHook: ${idea.hook}\nAudio: ${idea.audio_suggestion}\nTime: ${idea.posting_time}` ? (
                             <Check className="h-4 w-4 text-emerald-400" />
                          ) : (
                            <Copy className="h-4 w-4 text-text-muted" />
                          )}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* TAB 2: PRE-POST REEL SCORE */}
          {activeTab === "score" && (
            <motion.div 
              key="score"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.2 }}
              className="space-y-6"
            >
              <div>
                <h2 className="text-lg font-bold text-text">Pre-Post Reel Scorer</h2>
                <p className="text-xs text-muted-foreground">Test your post content, audio, and schedule to forecast performance</p>
              </div>

              {/* Form Input Section */}
              <div className="p-5 border border-border rounded-2xl bg-surface-2 space-y-4 shadow-xl">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[10px] uppercase font-bold text-text-muted tracking-wider flex items-center gap-1">
                      <Music className="h-3 w-3 text-primary" /> Audio Title
                    </label>
                    <input 
                      type="text" 
                      placeholder="e.g. Trending Remix, Chill Beat"
                      value={scoreAudio} 
                      onChange={(e) => setScoreAudio(e.target.value)}
                      className="w-full h-10 px-3 bg-surface border border-border rounded-xl text-sm text-text placeholder-text-muted focus:outline-none focus:border-primary transition-colors"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[10px] uppercase font-bold text-text-muted tracking-wider flex items-center gap-1">
                      <Compass className="h-3 w-3 text-primary" /> Niche
                    </label>
                    <input 
                      type="text" 
                      placeholder="e.g. dance, finance, tech"
                      value={scoreNiche} 
                      onChange={(e) => setScoreNiche(e.target.value)}
                      className="w-full h-10 px-3 bg-surface border border-border rounded-xl text-sm text-text placeholder-text-muted focus:outline-none focus:border-primary transition-colors"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[10px] uppercase font-bold text-text-muted tracking-wider flex items-center gap-1">
                      <Clock className="h-3 w-3 text-primary" /> Posting Time (IST)
                    </label>
                    <input 
                      type="time" 
                      value={scorePostingTime} 
                      onChange={(e) => setScorePostingTime(e.target.value)}
                      className="w-full h-10 px-3 bg-surface border border-border rounded-xl text-sm text-text focus:outline-none focus:border-primary transition-colors"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-text-muted tracking-wider flex items-center gap-1">
                    <Hash className="h-3 w-3 text-primary" /> Caption & Hashtags
                  </label>
                  <textarea 
                    placeholder="Write your reel caption here... Don't forget to include hashtags!"
                    value={scoreCaption} 
                    onChange={(e) => setScoreCaption(e.target.value)}
                    rows={4}
                    className="w-full p-3 bg-surface border border-border rounded-xl text-sm text-text placeholder-text-muted focus:outline-none focus:border-primary transition-colors resize-none"
                  />
                </div>

                <Button 
                  onClick={handleScoreReel}
                  disabled={loadingScore}
                  className="w-full bg-gradient-to-r from-primary via-primary to-purple-600 hover:from-primary hover:to-purple-700 text-white font-bold h-11 rounded-xl shadow-lg transition-all"
                >
                  {loadingScore ? (
                    <span className="flex items-center gap-2 justify-center">
                      <RefreshCw className="h-4 w-4 animate-spin" /> Scoring Reel...
                    </span>
                  ) : "Score My Reel"}
                </Button>
              </div>

              {/* Scoring Results Gauge & Details */}
              {scoringResult && (
                <motion.div 
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="glass-card p-6 border border-border rounded-2xl bg-surface-2 space-y-6 shadow-2xl relative overflow-hidden"
                >
                  {scoringResult.is_fallback && (
                    <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg px-4 py-2 text-amber-400 text-sm font-medium">
                      {scoringResult.fallback_reason || "Showing fallback score — LLM unavailable"}
                    </div>
                  )}

                  {/* Glowing background decor */}
                  <div className="absolute -top-16 -right-16 w-32 h-32 bg-primary/10 rounded-full blur-3xl" />

                  <div className="flex flex-col sm:flex-row items-center gap-6 pb-2">
                    {/* Score Gauge Circle */}
                    <div className="relative flex items-center justify-center w-32 h-32 shrink-0">
                      <svg className="w-full h-full transform -rotate-90">
                        <circle 
                          cx="64" 
                          cy="64" 
                          r="54" 
                          className="stroke-border fill-transparent" 
                          strokeWidth="10"
                        />
                        <motion.circle 
                          cx="64" 
                          cy="64" 
                          r="54" 
                          className="fill-transparent" 
                          strokeWidth="10"
                          stroke={scoringResult.overall_score >= 85 ? "#10b981" : scoringResult.overall_score >= 70 ? "#f59e0b" : "#ef4444"}
                          strokeDasharray={2 * Math.PI * 54}
                          initial={{ strokeDashoffset: 2 * Math.PI * 54 }}
                          animate={{ strokeDashoffset: 2 * Math.PI * 54 * (1 - scoringResult.overall_score / 100) }}
                          transition={{ duration: 1.5, ease: "easeOut" }}
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute flex flex-col items-center justify-center">
                        <span className="text-3xl font-extrabold text-text">{scoringResult.overall_score}</span>
                        <span className="text-[10px] text-primary font-bold uppercase tracking-wider">Score</span>
                      </div>
                    </div>

                    <div className="space-y-2 text-center sm:text-left flex-1">
                      <div className="flex items-center justify-center sm:justify-start gap-2.5">
                        <h3 className="font-display font-extrabold text-xl text-text">Reel Health Grade</h3>
                        <span className="bg-gradient-to-br from-primary to-purple-600 text-white text-base font-black px-3 py-1 rounded-lg border border-primary/20 shadow-md">
                          {scoringResult.grade}
                        </span>
                      </div>
                      <p className="text-xs text-text-muted leading-relaxed">
                        Overall score <span className="text-primary font-bold">{scoringResult.overall_score}/100</span>. Fix the identified areas below to boost engagement.
                      </p>
                    </div>
                  </div>

                  {/* Score breakdown metrics */}
                  <div className="space-y-4 pt-4 border-t border-border">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                      <Award className="h-4 w-4 text-primary" /> Detail Score Breakdown
                    </h4>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      {/* Hook Score */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-xs">
                          <span className="text-text-muted">Hook Score</span>
                          <span className="text-text font-bold">{scoringResult.hook_score}/100</span>
                        </div>
                        <div className="h-1.5 bg-surface rounded-full overflow-hidden">
                          <motion.div 
                            className="h-full bg-gradient-to-r from-purple-500 to-primary rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${scoringResult.hook_score}%` }}
                            transition={{ duration: 0.8 }}
                          />
                        </div>
                      </div>

                      {/* Audio Score */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-xs">
                          <span className="text-text-muted">Audio Score</span>
                          <span className="text-text font-bold">{scoringResult.audio_score}/100</span>
                        </div>
                        <div className="h-1.5 bg-surface rounded-full overflow-hidden">
                          <motion.div 
                            className="h-full bg-gradient-to-r from-purple-500 to-primary rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${scoringResult.audio_score}%` }}
                            transition={{ duration: 0.8 }}
                          />
                        </div>
                      </div>

                      {/* Caption Score */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-xs">
                          <span className="text-text-muted">Caption SEO Score</span>
                          <span className="text-text font-bold">{scoringResult.caption_score}/100</span>
                        </div>
                        <div className="h-1.5 bg-surface rounded-full overflow-hidden">
                          <motion.div 
                            className="h-full bg-gradient-to-r from-purple-500 to-primary rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${scoringResult.caption_score}%` }}
                            transition={{ duration: 0.8 }}
                          />
                        </div>
                      </div>

                      {/* Hashtag Score */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-xs">
                          <span className="text-text-muted">Hashtag Score</span>
                          <span className="text-text font-bold">{scoringResult.hashtag_score}/100</span>
                        </div>
                        <div className="h-1.5 bg-surface rounded-full overflow-hidden">
                          <motion.div 
                            className="h-full bg-gradient-to-r from-purple-500 to-primary rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${scoringResult.hashtag_score}%` }}
                            transition={{ duration: 0.8 }}
                          />
                        </div>
                      </div>

                      {/* Timing Score */}
                      <div className="space-y-1.5">
                        <div className="flex justify-between text-xs">
                          <span className="text-text-muted">Timing Score</span>
                          <span className="text-text font-bold">{scoringResult.timing_score}/100</span>
                        </div>
                        <div className="h-1.5 bg-surface rounded-full overflow-hidden">
                          <motion.div 
                            className="h-full bg-gradient-to-r from-purple-500 to-primary rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${scoringResult.timing_score}%` }}
                            transition={{ duration: 0.8 }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Top Fixes */}
                  <div className="space-y-3 pt-4 border-t border-border bg-primary/[0.02] -mx-6 px-6 pb-2 rounded-b-2xl">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                      <Wrench className="h-4 w-4" /> Top Fixes Recommended
                    </h4>
                    <ul className="space-y-2.5">
                      {scoringResult.top_fixes.map((fix, idx) => (
                        <li key={idx} className="flex gap-2.5 text-xs text-text-muted leading-relaxed items-start">
                          <span className="h-4 w-4 shrink-0 rounded-full bg-primary/10 text-primary border border-primary/20 text-[10px] font-black flex items-center justify-center">
                            {idx + 1}
                          </span>
                          <span>{fix}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </motion.div>
              )}
            </motion.div>
          )}

          {/* TAB 3: HOOK GENERATOR */}
          {activeTab === "hooks" && (
            <motion.div 
              key="hooks"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.2 }}
              className="space-y-6"
            >
              <div>
                <h2 className="text-lg font-bold text-text">Scroll-Stopping Hook Generator</h2>
                <p className="text-xs text-muted-foreground">Generate 5 psychological high-performing hook options</p>
              </div>

              {/* Hooks Input Box */}
              <div className="p-5 border border-border rounded-2xl bg-surface-2 space-y-4 shadow-xl">
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-text-muted tracking-wider">Trend or Core Topic</label>
                  <input 
                    type="text" 
                    placeholder="e.g. 5 AM Morning Routine, Transition edits"
                    value={hookTrend} 
                    onChange={(e) => setHookTrend(e.target.value)}
                    className="w-full h-10 px-3 bg-surface border border-border rounded-xl text-sm text-text placeholder-text-muted focus:outline-none focus:border-primary transition-colors"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-bold text-text-muted tracking-wider">Video Content Description</label>
                  <textarea 
                    placeholder="e.g. Showing step-by-step how I set up my planner and work productively without getting distracted."
                    value={hookDescription} 
                    onChange={(e) => setHookDescription(e.target.value)}
                    rows={3}
                    className="w-full p-3 bg-surface border border-border rounded-xl text-sm text-text placeholder-text-muted focus:outline-none focus:border-primary transition-colors resize-none"
                  />
                </div>

                <Button 
                  onClick={handleGenerateHooks}
                  disabled={loadingHooks}
                  className="w-full bg-gradient-to-r from-primary via-primary to-purple-600 hover:from-primary hover:to-purple-700 text-white font-bold h-11 rounded-xl shadow-lg transition-all"
                >
                  {loadingHooks ? (
                    <span className="flex items-center gap-2 justify-center">
                      <RefreshCw className="h-4 w-4 animate-spin" /> Generating Hooks...
                    </span>
                  ) : "Generate 5 hooks"}
                </Button>
              </div>

              {/* Hook Cards Output */}
              {generatedHooks.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Your Tailored Hooks</h3>
                  
                  <div className="grid gap-3">
                    {generatedHooks.map((hook, idx) => (
                      <div 
                        key={idx}
                        className="glass-card p-4 border border-white/5 hover:border-primary/20 transition-all rounded-xl bg-gradient-to-r from-white/[0.02] to-transparent flex gap-4 items-start"
                      >
                        <div className="flex-1 space-y-2">
                          <div className="flex gap-2 items-center">
                            <span className="text-[9px] font-black uppercase bg-primary/10 text-primary border border-primary/20 px-2 py-0.5 rounded">
                              {hook.style} Style
                            </span>
                          </div>
                          <p className="text-sm font-semibold text-white">"{hook.text}"</p>
                          <p className="text-xs text-muted-foreground italic"><strong className="text-primary font-bold not-italic">Why it works:</strong> {hook.why_it_works}</p>
                        </div>

                        <Button 
                          variant="ghost" 
                          size="icon"
                          onClick={() => handleCopy(hook.text, "Hook text")}
                          className="h-8 w-8 hover:bg-white/5 rounded-lg border border-white/5"
                        >
                          {copiedText === hook.text ? (
                            <Check className="h-3.5 w-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="h-3.5 w-3.5 text-gray-400" />
                          )}
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* TAB 4: CONTENT CALENDAR */}
          {FEATURES.CALENDAR_ENABLED && activeTab === "calendar" && (
            <PlanGate
              feature="30-Day Starter Calendar"
              requiredPlan="pro"
              currentPlan={userPlan}
              onUpgrade={() => window.location.href = '/pricing'}
            >
            <motion.div 
              key="calendar"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.2 }}
              className="space-y-6"
            >
              <div className="flex justify-between items-start gap-4">
                <div>
                  <h2 className="text-lg font-bold text-white">30-Day Starter Template</h2>
                  <p className="text-xs text-muted-foreground">A generic posting schedule to build the habit — personalized calendars are coming soon</p>
                </div>
                <Button 
                  onClick={handleGenerateCalendar} 
                  disabled={loadingCalendar}
                  className="bg-primary hover:bg-primary text-white font-bold h-9 px-3 rounded-lg text-xs"
                >
                  {loadingCalendar ? "Generating..." : calendar.length > 0 ? "Re-generate" : "Generate Plan"}
                </Button>
              </div>

              {calendar.length === 0 && !loadingCalendar && (
                <div className="glass-card p-8 text-center border border-white/5 rounded-2xl space-y-4 shadow-xl">
                  <CalendarIcon className="h-10 w-10 text-primary mx-auto" />
                  <div>
                    <h3 className="font-bold text-white text-base">Plan Your 30-Day Calendar</h3>
                    <p className="text-xs text-muted-foreground max-w-sm mx-auto mt-1 leading-relaxed">
                      Generates a full schedule of posts for the next month complete with topics, trending audio configurations, and optimum target posting hours.
                    </p>
                  </div>
                  <Button 
                    onClick={handleGenerateCalendar} 
                    className="bg-primary hover:bg-primary text-white font-bold h-10 px-6 rounded-xl text-xs"
                  >
                    Generate 30-Day Plan
                  </Button>
                </div>
              )}

              {loadingCalendar && (
                <div className="flex flex-col items-center justify-center py-20 gap-3 text-muted-foreground">
                  <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                  <span className="text-sm font-semibold animate-pulse animate-duration-1000">Structuring your 30-Day scheduler...</span>
                </div>
              )}

              {/* Monthly calendar view grid */}
              {calendar.length > 0 && !loadingCalendar && (
                <div className="space-y-4">
                  <div className="grid grid-cols-5 sm:grid-cols-6 gap-2">
                    {calendar.map((item) => (
                      <button
                        key={item.day}
                        onClick={() => setSelectedDay(item)}
                        className={`aspect-square rounded-xl border flex flex-col justify-center items-center transition-all duration-300 relative overflow-hidden ${
                          selectedDay?.day === item.day 
                            ? 'border-primary bg-primary/20 text-primary dark:text-primary shadow-lg shadow-primary/10' 
                            : 'border-border bg-surface-2 dark:bg-card/40 text-foreground/80 hover:border-primary/50 hover:bg-surface-2/80'
                        }`}
                      >
                        <span className="text-[8px] font-bold uppercase tracking-wider text-muted-foreground opacity-60">Day</span>
                        <span className="text-base font-extrabold text-foreground">{item.day}</span>
                        {/* Status marker / Festival indicator */}
                        {item.topic.includes("Special") || item.topic.includes("special") || item.topic.includes("Celebrations") ? (
                          <div className="absolute top-1 right-1 w-2 h-2 rounded-full bg-amber shadow-[0_0_6px_#EF9F27]" title="Special Holiday / Festival" />
                        ) : (
                          <div className="absolute bottom-1 w-1.5 h-1.5 rounded-full bg-primary" />
                        )}
                      </button>
                    ))}
                  </div>

                  {/* Day Details View Panel */}
                  <AnimatePresence mode="wait">
                    {selectedDay ? (
                      <motion.div 
                        key={selectedDay.day}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="p-5 border border-primary/30 rounded-2xl bg-primary/[0.01] space-y-4 shadow-xl"
                      >
                        <div className="flex justify-between items-center">
                          <span className="text-primary font-extrabold text-xs tracking-wider uppercase bg-primary/10 px-2.5 py-1 rounded-md">
                            Day {selectedDay.day} Agenda
                          </span>
                          <button 
                            onClick={() => setSelectedDay(null)} 
                            className="text-xs text-muted-foreground hover:text-text"
                          >
                            Close
                          </button>
                        </div>
 
                        <div className="space-y-1">
                          <h4 className="font-display text-base font-bold text-text">{selectedDay.topic}</h4>
                        </div>
 
                        <div className="space-y-3">
                          {/* Recommended Hook */}
                          <div className="p-3.5 bg-surface rounded-xl border border-border relative group">
                            <span className="block font-bold text-[9px] text-primary uppercase tracking-widest mb-1.5">RECOMMENDED HOOK</span>
                            <span className="text-sm text-text font-medium">"{selectedDay.hook}"</span>
                            <button
                              onClick={() => handleCopy(selectedDay.hook, "Hook text")}
                              className="absolute top-3 right-3 h-6 w-6 hover:bg-surface-2 rounded-md flex items-center justify-center border border-border opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                              {copiedText === selectedDay.hook ? (
                                <Check className="h-3 w-3 text-emerald-400" />
                              ) : (
                                <Copy className="h-3 w-3 text-text-muted" />
                              )}
                            </button>
                          </div>
 
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                            <div className="flex items-center gap-2 bg-surface p-2.5 rounded-xl border border-border text-text">
                              <Music className="h-4 w-4 text-primary shrink-0" />
                              <span className="truncate">Audio: {selectedDay.audio_style}</span>
                            </div>
                            <div className="flex items-center gap-2 bg-surface p-2.5 rounded-xl border border-border text-text">
                              <Clock className="h-4 w-4 text-primary shrink-0" />
                              <span>Optimal Time: {selectedDay.posting_time}</span>
                            </div>
                          </div>
 
                          {/* Hashtags */}
                          <div className="flex flex-wrap gap-1.5 pt-1">
                            {selectedDay.hashtags.map((h, i) => (
                              <span key={i} className="px-2.5 py-1 rounded-lg bg-surface border border-border text-primary dark:text-primary text-[10px] font-bold">
                                {h}
                              </span>
                            ))}
                          </div>
                        </div>
                      </motion.div>
                    ) : (
                      <div className="text-center py-6 text-xs text-muted-foreground border border-dashed border-border rounded-2xl">
                        Select any Day above to view details and hook copy options
                      </div>
                    )}
                  </AnimatePresence>
                </div>
              )}
            </motion.div>
            </PlanGate>
          )}
        </AnimatePresence>
      </div>
    </div>
    </PlanGate>
  );
}
