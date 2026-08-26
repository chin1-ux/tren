import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Sparkles, Trophy, Lightbulb, Target, Info, Check, Share2, ClipboardList, PenTool, MessageSquarePlus } from "lucide-react";
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
      { title: "Creator Studio — Trendrop" },
      { name: "description", content: "Pre-Post Score, Hook Generator, and SEO Caption Optimizer." },
    ],
  }),
  errorComponent: RouteErrorBoundary,
  component: StudioPage,
});

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

function StudioPage() {
  const { user } = useAuth();
  const userPlan = useUserStore((s) => s.plan) || 'free';
  const [activeTool, setActiveTool] = useState<"prepost" | "hooks" | "seo">("prepost");

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
          <p className="text-xs text-muted-foreground">Level up your posts before publishing</p>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-muted p-1">
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

