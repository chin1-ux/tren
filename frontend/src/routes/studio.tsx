import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Sparkles, Trophy, Lightbulb, Target, Info, Check, Share2, ClipboardList, PenTool, MessageSquarePlus, Flame, Zap, Clock, Music, Copy, RefreshCw, TrendingUp, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { apiFetch, getAuthToken } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { useUserStore } from "@/store/useAppStore";
import { PlanGate } from "@/components/PlanGate";
import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";

export const Route = createFileRoute("/studio")({
  head: () => ({
    meta: [
      { title: "Creator Studio & Post-Mortem — Trendrop" },
      { name: "description", content: "Post-Mortem Flop Diagnosis, Pre-Post Score, Hook Generator, and SEO Caption Optimizer." },
    ],
  }),
  errorComponent: RouteErrorBoundary,
  component: StudioPage,
});

interface FlopDiagnosisResult {
  overall_grade: string;
  headline_diagnosis: string;
  primary_bottleneck: string;
  audio_timing: {
    grade: string;
    saturation_pct: number;
    verdict: string;
  };
  hook_strength: {
    grade: string;
    archetype_detected: string;
    retention_verdict: string;
    rewritten_viral_hook: string;
  };
  posting_timing: {
    grade: string;
    optimal_window: string;
    verdict: string;
  };
  hashtag_health?: {
    grade: string;
    verdict: string;
  };
  actionable_playbook: string[];
  replacement_audio?: {
    title: string;
    artist: string;
    saturation: string;
    velocity: string;
    status: string;
  };
  is_fallback?: boolean;
}

interface AnalysisResult {
  overall_score: number;
  breakdown: {
    hook_strength: number;
    audio_match: number;
    seo_and_caption: number;
    hashtags: number;
    timing: number;
  };
  fixes: string[];
  estimated_reach_multiplier: string;
  /** True when the LLM call failed and the backend returned rule-based defaults */
  is_simulated?: boolean;
}

interface Hook {
  style: string;
  text: string;
  why_it_works: string;
  on_screen_keyword?: string;
}

interface HookResponse {
  hooks: Hook[];
}

interface CaptionResponse {
  caption: string;
  keywords_targeted: string[];
  alt_text: string;
  hashtag_strategy: string;
}

import { useEffectivePlan } from '@/lib/plan';

function StudioPage() {
  const { user } = useAuth();
  const userPlan = useEffectivePlan();
  const [activeTool, setActiveTool] = useState<"flop" | "prepost" | "hooks" | "seo">("flop");

  // Post-Mortem Flop Diagnosis States
  const [flopNiche, setFlopNiche] = useState("Fitness");
  const [flopAudio, setFlopAudio] = useState("");
  const [flopDate, setFlopDate] = useState(() => new Date().toISOString().split("T")[0]);
  const [flopTime, setFlopTime] = useState("18:30");
  const [flopViews, setFlopViews] = useState("");
  const [flopHookCaption, setFlopHookCaption] = useState("");
  const [flopTags, setFlopTags] = useState("");
  const [loadingFlop, setLoadingFlop] = useState(false);
  const [flopResult, setFlopResult] = useState<FlopDiagnosisResult | null>(null);

  // Pre-Post States
  const [niche, setNiche] = useState("");
  const [hook, setHook] = useState("");
  const [audio, setAudio] = useState("");
  const [caption, setCaption] = useState("");
  const [tags, setTags] = useState("");
  const [postTime, setPostTime] = useState("18:30");
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);

  // Hook Generator States
  const [hookNiche, setHookNiche] = useState("");
  const [hookTopic, setHookTopic] = useState("");
  const [loadingHooks, setLoadingHooks] = useState(false);
  const [hooksResult, setHooksResult] = useState<HookResponse | null>(null);

  // SEO Caption States
  const [seoDesc, setSeoDesc] = useState("");
  const [seoPlatform, setSeoPlatform] = useState("instagram");
  const [loadingSeo, setLoadingSeo] = useState(false);
  const [seoResult, setSeoResult] = useState<CaptionResponse | null>(null);

  const handleDiagnoseFlop = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!flopAudio.trim()) {
      toast.error("Please enter the Audio / Song used!");
      return;
    }
    if (!flopHookCaption.trim()) {
      toast.error("Please enter your Hook or Caption!");
      return;
    }
    setLoadingFlop(true);
    const token = getAuthToken();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    try {
      const res = await apiFetch("/api/diagnose-flop", {
        method: "POST",
        headers,
        body: JSON.stringify({
          audio_title: flopAudio.trim(),
          posted_date: flopDate,
          posted_time: flopTime,
          views_count: flopViews.trim(),
          hook_or_caption: flopHookCaption.trim(),
          niche: flopNiche,
          hashtags: flopTags.split(",").map(t => t.trim()).filter(Boolean)
        })
      });
      if (res.ok) {
        const data = await res.json();
        setFlopResult(data);
        toast.success("Post-mortem diagnosis generated!");
      } else {
        throw new Error(`Server returned ${res.status}`);
      }
    } catch (err: any) {
      toast.error(err?.message || "Failed to generate flop diagnosis.");
    } finally {
      setLoadingFlop(false);
    }
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!niche || !hook || !audio) {
      toast.error("Please fill in Niche, Hook, and Audio fields!");
      return;
    }
    setLoadingAnalysis(true);
    const token = getAuthToken();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    try {
      const res = await apiFetch("/api/prepost-score", {
        method: "POST",
        headers,
        body: JSON.stringify({
          niche,
          hook,
          audio_title: audio,
          caption,
          hashtags: tags.split(",").map(t => t.trim()).filter(Boolean),
          post_time: postTime
        })
      });
      if (res.ok) {
        const data = await res.json();
        setAnalysisResult(data);
        toast.success("Analysis complete!");
      } else {
        throw new Error(`Server returned ${res.status}`);
      }
    } catch (err: any) {
      toast.error(err?.message || "Failed to generate analysis. Check your backend status.");
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleGenerateHooks = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hookNiche || !hookTopic) {
      toast.error("Please fill in Niche and Topic!");
      return;
    }
    setLoadingHooks(true);
    const token = getAuthToken();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    try {
      const res = await apiFetch("/api/generate-hooks", {
        method: "POST",
        headers,
        body: JSON.stringify({
          niche: hookNiche,
          topic: hookTopic
        })
      });
      if (res.ok) {
        const data = await res.json();
        setHooksResult(data);
        toast.success("Hooks generated!");
      } else {
        throw new Error(`Server returned ${res.status}`);
      }
    } catch (err: any) {
      toast.error(err?.message || "Failed to generate hooks.");
    } finally {
      setLoadingHooks(false);
    }
  };

  const handleGenerateSeo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!seoDesc) {
      toast.error("Please provide a description!");
      return;
    }
    setLoadingSeo(true);
    const token = getAuthToken();
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    try {
      const res = await apiFetch("/api/seo-caption", {
        method: "POST",
        headers,
        body: JSON.stringify({
          description: seoDesc,
          platform: seoPlatform
        })
      });
      if (res.ok) {
        const data = await res.json();
        setSeoResult(data);
        toast.success("SEO Caption generated!");
      } else {
        throw new Error(`Server returned ${res.status}`);
      }
    } catch (err: any) {
      toast.error(err?.message || "Failed to generate SEO Caption.");
    } finally {
      setLoadingSeo(false);
    }
  };

  return (
    <PlanGate
      feature="Creator Studio"
      requiredPlan="pro"
      currentPlan={userPlan}
      onUpgrade={() => window.location.href = '/pricing'}
    >
    <div className="flex flex-col gap-6 px-4 pb-28 pt-6">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 text-white text-xl font-bold shadow-lg shadow-teal-500/20">
          <PenTool className="h-6 w-6" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold text-text">Creator Studio</h1>
          <p className="text-xs text-muted-foreground">Post-mortem flop diagnosis & pre-publish content intelligence</p>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-muted p-1">
        <button
          onClick={() => setActiveTool("flop")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-bold uppercase tracking-wide transition-all ${
            activeTool === "flop" ? "bg-rose-500 text-white shadow-sm shadow-rose-500/30" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Flame className="h-3.5 w-3.5 text-rose-300" />
          <span>Flop Audit</span>
          <span className="hidden sm:inline-block ml-0.5 px-1 py-0.2 rounded bg-white/20 text-[9px] font-black">NEW</span>
        </button>
        <button
          onClick={() => setActiveTool("prepost")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-bold uppercase tracking-wide transition-all ${
            activeTool === "prepost" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Trophy className="h-3.5 w-3.5" />
          Pre-Post Score
        </button>
        <button
          onClick={() => setActiveTool("hooks")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-bold uppercase tracking-wide transition-all ${
            activeTool === "hooks" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <MessageSquarePlus className="h-3.5 w-3.5" />
          Hooks
        </button>
        <button
          onClick={() => setActiveTool("seo")}
          className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2.5 text-xs font-bold uppercase tracking-wide transition-all ${
            activeTool === "seo" ? "bg-primary text-white shadow-sm" : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <Target className="h-3.5 w-3.5" />
          SEO Caption
        </button>
      </div>

      {/* 0. Flop Diagnosis */}
      {activeTool === "flop" && (
        <div className="space-y-5">
          <form onSubmit={handleDiagnoseFlop} className="glass-card p-5 rounded-2xl border border-rose-500/20 space-y-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="flex items-center gap-2">
                  <span className="px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 text-[10px] font-black uppercase tracking-wider border border-rose-500/20">
                    Post-Mortem Engine
                  </span>
                  <span className="text-[11px] text-muted-foreground font-medium">Empirical Saturation + Hook Audit</span>
                </div>
                <h3 className="font-display font-bold text-lg text-text mt-1">Why Did My Reel Flop?</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Cross-reference your audio's velocity, historical saturation, and hook retention to pinpoint the exact failure point.
                </p>
              </div>
            </div>

            <div className="space-y-3 pt-2">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] uppercase font-bold text-muted-foreground">Your Niche</label>
                  <input
                    type="text"
                    placeholder="e.g. Fitness, Tech, Fashion, Food, Comedy"
                    value={flopNiche}
                    onChange={(e) => setFlopNiche(e.target.value)}
                    className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-rose-500/50"
                  />
                </div>
                <div>
                  <label className="text-[10px] uppercase font-bold text-muted-foreground">Audio / Song Used</label>
                  <input
                    type="text"
                    placeholder="e.g. Kesariya, Chaleya, Espresso"
                    value={flopAudio}
                    onChange={(e) => setFlopAudio(e.target.value)}
                    className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-rose-500/50"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="text-[10px] uppercase font-bold text-muted-foreground">Date Posted</label>
                  <input
                    type="date"
                    value={flopDate}
                    onChange={(e) => setFlopDate(e.target.value)}
                    className="w-full mt-1 rounded-xl bg-muted/60 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-rose-500/50"
                  />
                </div>
                <div>
                  <label className="text-[10px] uppercase font-bold text-muted-foreground">Time Posted (IST)</label>
                  <input
                    type="time"
                    value={flopTime}
                    onChange={(e) => setFlopTime(e.target.value)}
                    className="w-full mt-1 rounded-xl bg-muted/60 px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-rose-500/50"
                  />
                </div>
                <div>
                  <label className="text-[10px] uppercase font-bold text-muted-foreground">Views Reached</label>
                  <input
                    type="text"
                    placeholder="e.g. 380 views"
                    value={flopViews}
                    onChange={(e) => setFlopViews(e.target.value)}
                    className="w-full mt-1 rounded-xl bg-muted/60 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-rose-500/50"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Your Hook (First 3 Seconds) & Caption</label>
                <textarea
                  placeholder="Paste what was spoken/shown on screen in the first 3 seconds, plus your caption..."
                  value={flopHookCaption}
                  onChange={(e) => setFlopHookCaption(e.target.value)}
                  rows={3}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-rose-500/50 resize-none"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Hashtags Used (Optional)</label>
                <input
                  type="text"
                  placeholder="#fitness, #workout, #gymmotivation"
                  value={flopTags}
                  onChange={(e) => setFlopTags(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-rose-500/50"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={loadingFlop}
              className="w-full bg-gradient-to-r from-rose-500 to-amber-500 hover:from-rose-600 hover:to-amber-600 text-white font-bold h-11 shadow-lg shadow-rose-500/20"
            >
              {loadingFlop ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Running Post-Mortem Audit...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Flame className="h-4 w-4" />
                  Diagnose My Flop
                </span>
              )}
            </Button>
          </form>

          {/* Diagnosis Results Card */}
          {flopResult && (
            <div className="glass-card p-5 border border-rose-500/30 rounded-2xl space-y-5 animate-in fade-in duration-300">
              {/* Header Banner */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-gradient-to-r from-rose-950/40 via-surface to-amber-950/30 border border-rose-500/20">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 text-[10px] font-black uppercase tracking-wider">
                      PRIMARY BOTTLENECK
                    </span>
                    <span className="text-xs font-bold text-amber-400">
                      {flopResult.primary_bottleneck?.replace(/_/g, " ")}
                    </span>
                  </div>
                  <h4 className="text-sm sm:text-base font-bold text-white leading-snug">
                    "{flopResult.headline_diagnosis}"
                  </h4>
                </div>
                <div className="flex sm:flex-col items-center justify-center px-4 py-2 rounded-xl bg-black/40 border border-white/10 shrink-0">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground sm:block">Grade</span>
                  <span className={`text-3xl font-black ${
                    flopResult.overall_grade?.startsWith("A") ? "text-emerald-400" :
                    flopResult.overall_grade?.startsWith("B") ? "text-teal-400" :
                    flopResult.overall_grade?.startsWith("C") ? "text-amber-400" : "text-rose-400"
                  }`}>
                    {flopResult.overall_grade}
                  </span>
                </div>
              </div>

              {/* 3 Core Diagnosis Columns */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* Audio Timing */}
                <div className="p-4 rounded-xl bg-surface-2 border border-border/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
                      <Music className="h-3 w-3 text-rose-400" /> Audio Timing
                    </span>
                    <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 text-xs font-black">
                      {flopResult.audio_timing?.grade}
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-text">
                    Saturation: <span className="text-rose-400 font-bold">{flopResult.audio_timing?.saturation_pct}%</span>
                  </div>
                  <p className="text-xs text-text-muted leading-relaxed">
                    {flopResult.audio_timing?.verdict}
                  </p>
                </div>

                {/* Hook Strength */}
                <div className="p-4 rounded-xl bg-surface-2 border border-border/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
                      <Zap className="h-3 w-3 text-amber-400" /> Hook Retention
                    </span>
                    <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 text-xs font-black">
                      {flopResult.hook_strength?.grade}
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-text">
                    Type: <span className="text-amber-400 font-bold">{flopResult.hook_strength?.archetype_detected}</span>
                  </div>
                  <p className="text-xs text-text-muted leading-relaxed">
                    {flopResult.hook_strength?.retention_verdict}
                  </p>
                </div>

                {/* Posting Timing */}
                <div className="p-4 rounded-xl bg-surface-2 border border-border/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3 text-emerald-400" /> Niche Peak
                    </span>
                    <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-xs font-black">
                      {flopResult.posting_timing?.grade}
                    </span>
                  </div>
                  <div className="text-xs font-semibold text-text">
                    Optimal: <span className="text-emerald-400 font-bold">{flopResult.posting_timing?.optimal_window}</span>
                  </div>
                  <p className="text-xs text-text-muted leading-relaxed">
                    {flopResult.posting_timing?.verdict}
                  </p>
                </div>
              </div>

              {/* Hook Rewrite Card */}
              {flopResult.hook_strength?.rewritten_viral_hook && (
                <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] uppercase font-black text-amber-400 tracking-wider flex items-center gap-1">
                      <Sparkles className="h-3.5 w-3.5" /> High-Retention Hook Rewrite
                    </span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(flopResult.hook_strength.rewritten_viral_hook);
                        toast.success("Viral hook copied!");
                      }}
                      className="text-xs text-amber-300 font-bold hover:underline flex items-center gap-1"
                    >
                      <Copy className="h-3 w-3" /> Copy Rewrite
                    </button>
                  </div>
                  <p className="text-sm font-semibold text-white italic">
                    "{flopResult.hook_strength.rewritten_viral_hook}"
                  </p>
                  <p className="text-[11px] text-amber-300/80">
                    Use this Contrarian / Curiosity angle to halt viewer scroll in the first 1.5 seconds.
                  </p>
                </div>
              )}

              {/* Actionable Playbook */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Next Reel Action Playbook
                </span>
                <div className="space-y-1.5">
                  {flopResult.actionable_playbook?.map((step, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 p-2.5 rounded-lg bg-surface border border-border text-xs text-foreground">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-rose-500/20 text-rose-400 font-bold text-[10px]">
                        {idx + 1}
                      </span>
                      <span className="leading-snug pt-0.5">{step}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Suggested Replacement Audio */}
              {flopResult.replacement_audio && (
                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="space-y-1">
                    <span className="text-[10px] font-black uppercase tracking-wider text-emerald-400 flex items-center gap-1">
                      <TrendingUp className="h-3.5 w-3.5" /> Don't Reuse Peaked Audios — Use This Instead
                    </span>
                    <div className="text-sm font-bold text-white">
                      "{flopResult.replacement_audio.title}" {flopResult.replacement_audio.artist && `— ${flopResult.replacement_audio.artist}`}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-emerald-300">
                      <span>Saturation: <strong>{flopResult.replacement_audio.saturation}</strong></span>
                      <span>•</span>
                      <span>Velocity: <strong>{flopResult.replacement_audio.velocity}</strong></span>
                      <span>•</span>
                      <span className="uppercase text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 font-bold">
                        {flopResult.replacement_audio.status}
                      </span>
                    </div>
                  </div>
                  <Button
                    onClick={() => {
                      setAudio(flopResult.replacement_audio!.title);
                      setNiche(flopNiche);
                      setActiveTool("prepost");
                      toast.success(`Loaded "${flopResult.replacement_audio!.title}" into Pre-Post auditor!`);
                    }}
                    size="sm"
                    className="bg-emerald-500 hover:bg-emerald-600 text-white font-bold text-xs shrink-0"
                  >
                    Test in Pre-Post Score →
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 1. Pre-Post Score */}
      {activeTool === "prepost" && (
        <div className="space-y-4">
          <form onSubmit={handleAnalyze} className="glass-card p-5 rounded-2xl space-y-4">
            <h3 className="font-display font-bold text-base text-text">Audit Your Post</h3>
            
            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Niche</label>
                <input
                  type="text"
                  placeholder="e.g., Finance, Fitness, Tech, Fashion"
                  value={niche}
                  onChange={(e) => setNiche(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Hook Text / Video Opener</label>
                <input
                  type="text"
                  placeholder="What is the first text seen on screen?"
                  value={hook}
                  onChange={(e) => setHook(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Audio / Song Name</label>
                <input
                  type="text"
                  placeholder="e.g., Espresso - Sabrina Carpenter"
                  value={audio}
                  onChange={(e) => setAudio(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Caption</label>
                <textarea
                  placeholder="Write your planned caption..."
                  value={caption}
                  onChange={(e) => setCaption(e.target.value)}
                  rows={3}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 resize-none"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Hashtags (comma separated)</label>
                <input
                  type="text"
                  placeholder="e.g., #growth, #coding, #tutorial"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Planned Posting Time</label>
                <input
                  type="time"
                  value={postTime}
                  onChange={(e) => setPostTime(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>
            </div>

            <Button type="submit" disabled={loadingAnalysis} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white font-bold h-11">
              {loadingAnalysis ? "Auditing Post..." : "Get Pre-Post Score"}
            </Button>
          </form>

          {analysisResult && (
            <div className="glass-card p-5 border border-emerald-500/40 rounded-2xl space-y-4 animate-in fade-in">
              {/* Simulated-data warning — shown only when backend LLM call failed */}
              {analysisResult.is_simulated && (
                <div className="flex items-start gap-2 rounded-xl bg-amber-500/10 border border-amber-500/30 px-3 py-2.5">
                  <Info className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
                  <p className="text-xs text-amber-300">
                    <span className="font-bold">Estimated result</span> — AI scoring is temporarily unavailable.
                    These numbers are rule-based defaults, not personalised analysis.
                    Results will update automatically once the AI service recovers.
                  </p>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="font-bold text-emerald-400 text-sm">Analysis Results</span>
                <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded-full font-bold">Est. Reach: {analysisResult.estimated_reach_multiplier}</span>
              </div>

              <div className="flex items-center gap-4 py-2">
                <div className="text-5xl font-extrabold text-white">{analysisResult.overall_score}</div>
                <div className="text-xs text-muted-foreground">
                  <span className="font-bold text-foreground block">Overall Score</span>
                  Based on current algorithm weights.
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-[10px] font-bold uppercase text-muted-foreground">Breakdown</span>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-white/5 p-2 rounded-lg flex justify-between">
                    <span className="text-gray-400">Hook:</span>
                    <span className="font-bold">{analysisResult.breakdown.hook_strength}/100</span>
                  </div>
                  <div className="bg-white/5 p-2 rounded-lg flex justify-between">
                    <span className="text-gray-400">Audio:</span>
                    <span className="font-bold">{analysisResult.breakdown.audio_match}/100</span>
                  </div>
                  <div className="bg-surface-2 p-2 rounded-lg flex justify-between border border-border">
                    <span className="text-text-muted">SEO:</span>
                    <span className="font-bold">{analysisResult.breakdown.seo_and_caption}/100</span>
                  </div>
                  <div className="bg-surface-2 p-2 rounded-lg flex justify-between border border-border">
                    <span className="text-text-muted">Hashtags:</span>
                    <span className="font-bold">{analysisResult.breakdown.hashtags}/100</span>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <span className="text-[10px] font-bold uppercase text-muted-foreground">Specific Fixes Required</span>
                <ul className="space-y-1.5 text-xs text-text-muted">
                  {analysisResult.fixes.map((fix, i) => (
                    <li key={i} className="flex gap-2 items-start">
                      <span className="text-emerald-400 font-bold">•</span>
                      <span>{fix}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2. Hook Generator */}
      {activeTool === "hooks" && (
        <div className="space-y-4">
          <form onSubmit={handleGenerateHooks} className="glass-card p-5 rounded-2xl space-y-4">
            <h3 className="font-display font-bold text-base text-text">Generate High-Converting Hooks</h3>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Niche</label>
                <input
                  type="text"
                  placeholder="e.g., Tech, Beauty, Comedy"
                  value={hookNiche}
                  onChange={(e) => setHookNiche(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Topic/Theme</label>
                <input
                  type="text"
                  placeholder="What is your video about?"
                  value={hookTopic}
                  onChange={(e) => setHookTopic(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                />
              </div>
            </div>
            <Button type="submit" disabled={loadingHooks} className="w-full bg-primary hover:bg-primary text-white font-bold h-11">
              {loadingHooks ? "Generating Hooks..." : "Create 5 Hook Formulas"}
            </Button>
          </form>

          {hooksResult && (
            <div className="space-y-3">
              <h4 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Your Tailored Hooks</h4>
              {hooksResult.hooks.map((h, i) => (
                <div key={i} className="glass-card p-4 rounded-xl space-y-2 border border-border">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-primary">{h.style} Hook</span>
                    <button 
                      onClick={() => {
                        navigator.clipboard.writeText(h.text);
                        toast.success("Hook copied!");
                      }} 
                      className="text-[10px] text-muted-foreground hover:text-text"
                    >
                      Copy
                    </button>
                  </div>
                  <p className="text-sm text-text font-semibold">"{h.text}"</p>
                  {h.on_screen_keyword && (
                    <p className="text-xs font-bold text-amber-400">📺 On-screen text: {h.on_screen_keyword}</p>
                  )}
                  <p className="text-xs text-muted-foreground">{h.why_it_works}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 3. SEO Caption Generator */}
      {activeTool === "seo" && (
        <div className="space-y-4">
          <form onSubmit={handleGenerateSeo} className="glass-card p-5 rounded-2xl space-y-4">
            <h3 className="font-display font-bold text-base text-text">SEO Caption Generator</h3>
            <div className="space-y-3">
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Video Description</label>
                <textarea
                  placeholder="Describe your video in detail..."
                  value={seoDesc}
                  onChange={(e) => setSeoDesc(e.target.value)}
                  rows={4}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 resize-none"
                />
              </div>
              <div>
                <label className="text-[10px] uppercase font-bold text-muted-foreground">Platform</label>
                <select
                  value={seoPlatform}
                  onChange={(e) => setSeoPlatform(e.target.value)}
                  className="w-full mt-1 rounded-xl bg-muted/60 px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                >
                  <option value="instagram" className="bg-surface text-text">Instagram Reels</option>
                  <option value="youtube_shorts" className="bg-surface text-text">YouTube Shorts</option>
                </select>
              </div>
            </div>
            <Button type="submit" disabled={loadingSeo} className="w-full bg-emerald-500 hover:bg-emerald-600 text-white font-bold h-11">
              {loadingSeo ? "Optimizing..." : "Generate SEO Caption"}
            </Button>
          </form>

          {seoResult && (
            <div className="glass-card p-5 rounded-2xl border border-emerald-500/30 space-y-4 animate-in fade-in">
              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold uppercase text-muted-foreground">Generated Caption</span>
                  <button 
                    onClick={() => {
                      navigator.clipboard.writeText(seoResult.caption);
                      toast.success("Caption copied!");
                    }} 
                    className="text-xs text-primary font-bold hover:underline"
                  >
                    Copy Caption
                  </button>
                </div>
                <div className="bg-surface p-3 rounded-xl text-xs whitespace-pre-wrap text-text border border-border">
                  {seoResult.caption}
                </div>
              </div>

              <div className="space-y-1.5">
                <span className="text-[10px] font-bold uppercase text-muted-foreground">Targeted Keywords (Google/In-app)</span>
                <div className="flex flex-wrap gap-1.5">
                  {seoResult.keywords_targeted.map((kw, i) => (
                    <span key={i} className="px-2 py-0.5 rounded bg-muted text-emerald-400 text-xs font-semibold">{kw}</span>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-bold uppercase text-muted-foreground">Accessibility Alt Text</span>
                  <button 
                    onClick={() => {
                      navigator.clipboard.writeText(seoResult.alt_text);
                      toast.success("Alt text copied!");
                    }} 
                    className="text-[10px] text-muted-foreground hover:text-text"
                  >
                    Copy
                  </button>
                </div>
                <p className="text-xs text-text-muted italic">"{seoResult.alt_text}"</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
    </PlanGate>
  );
}

