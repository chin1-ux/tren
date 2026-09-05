import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { 
  Upload, X, Download, Share2, Flame, AlertTriangle, Play, Pause, Volume2, 
  VolumeX, Sparkles, AlignLeft, Layers, RefreshCw, Star, Info, ChevronRight, Check
} from "lucide-react";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { 
  fetchTrends, generateReel, generateNarrative, jobStatus, 
  resolveOutputUrl, scoreReel, type UiTrend 
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { PlanGate } from "@/components/PlanGate";
import { useUserStore } from "@/store/useAppStore";

import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";

const searchSchema = z.object({ trendId: z.string().optional() });

export const Route = createFileRoute("/generate")({
  validateSearch: searchSchema,
  head: () => ({
    meta: [
      { title: "Generate your viral short — Trendrop" },
      { name: "description", content: "AI-powered reel and narrative video creator." },
    ],
  }),
  component: GeneratePage,
  errorComponent: RouteErrorBoundary,
});

type Tab = "photos" | "narrative";
type Stage = "upload" | "progress" | "result" | "error";

interface PhotoItem {
  id: string;
  url: string;
  file: File;
}

const NARRATIVE_PRESETS = {
  before_after: {
    label: "Before / After",
    description: "Perfect for showing fitness, design, or lifestyle results.",
    defaultOverlays: ["Before", "After"],
  },
  transformation: {
    label: "Transformation",
    description: "Show a step-by-step progress timeline.",
    defaultOverlays: ["Start", "Progress", "Finished!"],
  },
  reveal: {
    label: "Reveal",
    description: "Build suspense and reveal a surprise.",
    defaultOverlays: ["Wait for it...", "Boom!"],
  },
  countdown: {
    label: "Countdown",
    description: "Generate high engagement using a fast countdown.",
    defaultOverlays: ["3", "2", "1", "Reveal!"],
  },
};

function GeneratePage() {
  const { trendId } = Route.useSearch();
  const navigate = useNavigate();
  const userPlan = useUserStore((s) => s.plan) || 'free';

  const { data: trends } = useQuery<UiTrend[]>({
    queryKey: ["trends"],
    queryFn: () => fetchTrends(),
    staleTime: 60_000,
  });
  
  const activeTrend = trends && Array.isArray(trends) 
    ? (trends.find((t) => t.id === trendId) ?? trends[0]) 
    : undefined;

  // Global stages & state
  const [activeTab, setActiveTab] = useState<Tab>("photos");
  const [stage, setStage] = useState<Stage>("upload");
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("Starting...");
  const [outputUrl, setOutputUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [currentJobId, setCurrentJobId] = useState<string | null>(null);
  
  // Custom interactive scoring state
  const [showScoreCard, setShowScoreCard] = useState(false);
  const [scoreDetails, setScoreDetails] = useState<any>(null);
  const [scoringLoading, setScoringLoading] = useState(false);

  // Tab 1: Photos Reel state
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [selectedStyle, setSelectedStyle] = useState("cinematic");
  const photosInputRef = useRef<HTMLInputElement>(null);

  // Tab 2: Narrative state
  const [narrativeType, setNarrativeType] = useState<keyof typeof NARRATIVE_PRESETS>("before_after");
  const [narrativePhotos, setNarrativePhotos] = useState<PhotoItem[]>([]);
  const [narrativeOverlays, setNarrativeOverlays] = useState<string[]>(NARRATIVE_PRESETS.before_after.defaultOverlays);
  const narrativeInputRef = useRef<HTMLInputElement>(null);

  // Update narrative overlays when type changes
  useEffect(() => {
    setNarrativeOverlays(NARRATIVE_PRESETS[narrativeType].defaultOverlays);
  }, [narrativeType]);

  // Draggable image uploads
  const handlePhotos = (files: FileList | null, isNarrative = false) => {
    if (!files) return;
    const limit = isNarrative ? 10 : 15;
    const currentList = isNarrative ? narrativePhotos : photos;
    const arr = Array.from(files).slice(0, limit - currentList.length);
    const next = arr.map((f) => ({ id: crypto.randomUUID(), url: URL.createObjectURL(f), file: f }));
    
    if (isNarrative) {
      setNarrativePhotos((prev) => [...prev, ...next].slice(0, limit));
    } else {
      setPhotos((prev) => [...prev, ...next].slice(0, limit));
    }
  };

  const removePhoto = (id: string, isNarrative = false) => {
    const list = isNarrative ? narrativePhotos : photos;
    const setter = isNarrative ? setNarrativePhotos : setPhotos;
    const target = list.find((x) => x.id === id);
    if (target) URL.revokeObjectURL(target.url);
    setter((prev) => prev.filter((x) => x.id !== id));
  };

  // Cleanup blob URLs on unmount
  const photosRef = useRef<PhotoItem[]>([]);
  const narrativePhotosRef = useRef<PhotoItem[]>([]);
  
  useEffect(() => { photosRef.current = photos; }, [photos]);
  useEffect(() => { narrativePhotosRef.current = narrativePhotos; }, [narrativePhotos]);
  
  useEffect(() => {
    return () => {
      photosRef.current.forEach((p) => URL.revokeObjectURL(p.url));
      narrativePhotosRef.current.forEach((p) => URL.revokeObjectURL(p.url));
    };
  }, []);

  // Polling logic
  const pollTimerRef = useRef<NodeJS.Timeout | null>(null);

  const startPolling = (jobId: string) => {
    setCurrentJobId(jobId);
    setProgress(0);
    setStage("progress");
    setStatusText("Uploading and analyzing media...");

    const checkStatus = async () => {
      try {
        const res = await jobStatus(jobId);
        const currentProgress = res.progress ?? 0;
        setProgress(currentProgress);
        
        // Dynamic status message updates based on progress percentage
        if (currentProgress < 20) {
          setStatusText("Analyzing your media beats...");
        } else if (currentProgress < 50) {
          setStatusText("Detecting visual transitions & rhythm...");
        } else if (currentProgress < 80) {
          setStatusText("Generating overlay effects and texts...");
        } else {
          setStatusText("Exporting high-definition viral MP4...");
        }

        if (res.status === "complete" && res.output_url) {
          setOutputUrl(resolveOutputUrl(res.output_url));
          // Scorecard is fetched on-demand when the user clicks "Score This Video"
          setScoreDetails(null);
          setStage("result");
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        } else if (res.status === "failed") {
          setErrorMsg(res.error_message || "Video compilation failed. Try a different format.");
          setStage("error");
          if (pollTimerRef.current) clearInterval(pollTimerRef.current);
        }
      } catch (err) {
        setErrorMsg("Failed to poll video job. Check your network connection.");
        setStage("error");
        if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      }
    };

    // Check immediately then every 2 seconds
    checkStatus();
    pollTimerRef.current = setInterval(checkStatus, 2000);
  };

  const cancelJob = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
    }
    setStage("upload");
    setProgress(0);
    setCurrentJobId(null);
  };

  // POST triggers
  const handleCreateReel = async () => {
    if (photos.length < 3 || !activeTrend) return;
    try {
      const email = localStorage.getItem("trendrop_user_email") || "anonymous@trendrop.app";
      const { job_id } = await generateReel({
        files: photos.map((p) => p.file),
        trendId: activeTrend.id,
        userEmail: email,
        style: selectedStyle,
      });
      startPolling(job_id);
    } catch {
      setErrorMsg("Failed to submit reel generation request.");
      setStage("error");
    }
  };

  const handleCreateNarrative = async () => {
    if (narrativePhotos.length < 2 || !activeTrend) return;
    try {
      const email = localStorage.getItem("trendrop_user_email") || "anonymous@trendrop.app";
      const { job_id } = await generateNarrative({
        files: narrativePhotos.map((p) => p.file),
        trendId: activeTrend.id,
        userEmail: email,
        narrativeType,
        textOverlays: narrativeOverlays,
      });
      startPolling(job_id);
    } catch {
      setErrorMsg("Failed to submit narrative generation request.");
      setStage("error");
    }
  };

  const resetAll = () => {
    setPhotos([]);
    setNarrativePhotos([]);
    setStage("upload");
    setOutputUrl(null);
    setErrorMsg(null);
    setShowScoreCard(false);
  };

  return (
    <PlanGate
      feature="AI Generation Studio"
      requiredPlan="pro"
      currentPlan={userPlan}
      onUpgrade={() => window.location.href = '/pricing'}
    >
    <div className="flex flex-col min-h-screen bg-bg text-text font-sans">
      
      {/* ── STAGE 1: UPLOAD & SETUP ── */}
      {stage === "upload" && (
        <div className="flex flex-col gap-6 px-4 pb-24 pt-6 max-w-2xl mx-auto w-full">
          <header className="relative">
            <h1 className="text-3xl font-black tracking-tight bg-gradient-to-r from-violet-400 via-pink-400 to-amber-300 bg-clip-text text-transparent">
              AI Generation Studio
            </h1>
            <p className="mt-1 text-sm text-slate-400 font-medium">
              Transform your concepts into high-engagement short-form videos.
            </p>
          </header>

          {/* Active Trend Badge */}
          {activeTrend && (
            <div className="flex items-center justify-between gap-3 rounded-2xl border border-border bg-surface-2 backdrop-blur-md p-4">
              <div className="flex items-start gap-3 min-w-0">
                <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-amber-500/20 text-amber-400 ring-1 ring-amber-500/30">
                  <Flame className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-text-muted">Locked Sound Trend</p>
                  <p className="truncate font-semibold text-text">{activeTrend.song}</p>
                  <p className="truncate text-xs text-text-muted">{activeTrend.artist}</p>
                </div>
              </div>
              <button 
                onClick={() => navigate({ to: "/" })} 
                className="text-xs font-semibold text-violet-400 hover:text-violet-300 transition-colors"
              >
                Change
              </button>
            </div>
          )}

          {/* Tab Header */}
          <div className="bg-surface border border-border rounded-xl p-1 flex gap-1">
            {(["photos", "narrative"] as Tab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-2 rounded-lg text-xs font-bold capitalize transition-all ${
                  activeTab === tab
                    ? "bg-primary text-white shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* TAB CONTENT: PHOTOS REEL */}
          {activeTab === "photos" && (
            <div className="space-y-6">
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-400">1. Select Images</label>
                <input 
                  ref={photosInputRef} 
                  type="file" 
                  accept="image/png,image/jpeg" 
                  multiple 
                  hidden 
                  onChange={(e) => handlePhotos(e.target.files)} 
                />
                
                <button
                  onClick={() => photosInputRef.current?.click()}
                  className="flex w-full flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-white/10 bg-slate-950 px-6 py-10 transition-colors hover:border-violet-500/40 hover:bg-slate-900/30 group"
                >
                  <div className="grid h-12 w-12 place-items-center rounded-xl bg-white/5 text-slate-400 group-hover:text-violet-400 group-hover:bg-violet-500/10 transition-all">
                    <Upload className="h-5 w-5" />
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-slate-200">Tap to upload photos</p>
                    <p className="text-xs text-slate-400 mt-1">Select 3–15 portrait images for optimum timing</p>
                  </div>
                </button>
              </div>

              {photos.length > 0 && (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-violet-400 bg-violet-500/10 px-2.5 py-1 rounded-full border border-violet-500/20">
                      {photos.length} photos selected
                    </span>
                    <span className="text-[10px] text-slate-500">↕ Drag to reorder</span>
                  </div>

                  <div className="grid grid-cols-3 gap-2">
                    {photos.map((p, idx) => (
                      <div
                        key={p.id}
                        draggable
                        onDragStart={(e) => e.dataTransfer.setData("text/plain", idx.toString())}
                        onDragOver={(e) => e.preventDefault()}
                        onDrop={(e) => {
                          e.preventDefault();
                          const fromIndex = parseInt(e.dataTransfer.getData("text/plain"), 10);
                          if (isNaN(fromIndex) || fromIndex === idx) return;
                          const reordered = [...photos];
                          const [moved] = reordered.splice(fromIndex, 1);
                          reordered.splice(idx, 0, moved);
                          setPhotos(reordered);
                        }}
                        className="relative aspect-[9/16] overflow-hidden rounded-xl bg-slate-900 border border-white/5 cursor-move group active:scale-95 transition-all"
                      >
                        <img src={p.url} alt="" className="h-full w-full object-cover select-none pointer-events-none" />
                        <button
                          onClick={() => removePhoto(p.id)}
                          title="Remove photo"
                          className="absolute right-1.5 top-1.5 grid h-6 w-6 place-items-center rounded-lg bg-black/60 text-slate-300 hover:bg-red-500 hover:text-white transition-all backdrop-blur-sm"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                        <div className="absolute bottom-1.5 left-1.5 bg-black/60 px-2 py-0.5 rounded-md text-[9px] font-bold text-white border border-white/10">
                          {idx + 1}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Style Selector */}
              <div className="space-y-3">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-400">2. Editing style</label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: "cinematic", title: "Cinematic", desc: "Slow drifts & flares" },
                    { id: "fast", title: "Fast Cuts", desc: "Rapid beat sync switch" },
                    { id: "glitch", title: "Urban Glitch", desc: "High energy overlays" },
                    { id: "zoom", title: "Smooth Zoom", desc: "Tension build zooms" }
                  ].map((style) => (
                    <button
                      key={style.id}
                      onClick={() => setSelectedStyle(style.id)}
                      title={`Choose ${style.title}`}
                      className={`flex flex-col items-start gap-1 p-3 rounded-xl border text-left transition-all ${
                        selectedStyle === style.id 
                          ? "border-violet-500 bg-violet-600/10" 
                          : "border-white/5 bg-slate-950 hover:bg-slate-900/60"
                      }`}
                    >
                      <span className="font-bold text-sm text-slate-200">{style.title}</span>
                      <span className="text-[10px] text-slate-400">{style.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              <Button
                onClick={handleCreateReel}
                disabled={photos.length < 3}
                className="w-full h-12 bg-gradient-to-r from-violet-600 to-primary font-bold uppercase text-white tracking-wider rounded-xl shadow-lg shadow-violet-500/20 hover:from-violet-500 hover:to-primary disabled:opacity-50"
              >
                {photos.length < 3 ? "Select at least 3 photos" : "Create Reel"}
              </Button>
            </div>
          )}

          {/* TAB CONTENT: NARRATIVE */}
          {activeTab === "narrative" && (
            <div className="space-y-6">
              {/* Type Select */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-400">1. Narrative Style</label>
                <div className="grid grid-cols-2 gap-2">
                  {(Object.keys(NARRATIVE_PRESETS) as Array<keyof typeof NARRATIVE_PRESETS>).map((type) => (
                    <button
                      key={type}
                      onClick={() => setNarrativeType(type)}
                      title={`Choose ${NARRATIVE_PRESETS[type].label}`}
                      className={`flex flex-col text-left p-3 rounded-xl border transition-all ${
                        narrativeType === type 
                          ? "border-violet-500 bg-violet-600/10" 
                          : "border-white/5 bg-slate-950 hover:bg-slate-900/60"
                      }`}
                    >
                      <span className="font-bold text-sm text-slate-200">{NARRATIVE_PRESETS[type].label}</span>
                      <span className="text-[10px] text-slate-400 mt-1 line-clamp-2">{NARRATIVE_PRESETS[type].description}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Uploads */}
              <div className="space-y-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-400">2. Narrative Assets</label>
                <input 
                  ref={narrativeInputRef} 
                  type="file" 
                  accept="image/png,image/jpeg" 
                  multiple 
                  hidden 
                  onChange={(e) => handlePhotos(e.target.files, true)} 
                />
                
                <button
                  onClick={() => narrativeInputRef.current?.click()}
                  className="flex w-full flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-white/10 bg-slate-950 px-6 py-8 transition-colors hover:border-violet-500/40 hover:bg-slate-900/30 group"
                >
                  <div className="grid h-10 w-10 place-items-center rounded-xl bg-white/5 text-slate-400 group-hover:text-violet-400 group-hover:bg-violet-500/10 transition-all">
                    <Upload className="h-5 w-5" />
                  </div>
                  <div className="text-center">
                    <p className="font-semibold text-slate-200">Upload photos</p>
                    <p className="text-xs text-slate-400 mt-0.5">Need {narrativeOverlays.length} assets minimum</p>
                  </div>
                </button>
              </div>

              {/* Asset grid */}
              {narrativePhotos.length > 0 && (
                <div className="grid grid-cols-4 gap-2">
                  {narrativePhotos.map((p, idx) => (
                    <div key={p.id} className="relative aspect-square overflow-hidden rounded-lg bg-slate-900 border border-white/5">
                      <img src={p.url} alt="" className="h-full w-full object-cover" />
                      <button
                        onClick={() => removePhoto(p.id, true)}
                        title="Remove narrative asset"
                        className="absolute right-1 top-1 grid h-5 w-5 place-items-center rounded bg-black/60 text-slate-300 hover:bg-red-500"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Editable Text Overlays */}
              <div className="space-y-3">
                <div className="flex items-center gap-1.5">
                  <AlignLeft className="h-4 w-4 text-violet-400" />
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-400">3. Edit Text Overlays</label>
                </div>
                <div className="space-y-2 bg-slate-950 p-4 rounded-xl border border-white/5">
                  {narrativeOverlays.map((overlay, index) => (
                    <div key={index} className="space-y-1">
                      <span className="text-[10px] font-bold text-slate-500">Step {index + 1} Overlay</span>
                      <input
                        type="text"
                        value={overlay}
                        onChange={(e) => {
                          const updated = [...narrativeOverlays];
                          updated[index] = e.target.value;
                          setNarrativeOverlays(updated);
                        }}
                        className="w-full bg-slate-900 border border-white/10 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-violet-500"
                        placeholder={`Text overlay ${index + 1}`}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <Button
                onClick={handleCreateNarrative}
                disabled={narrativePhotos.length < narrativeOverlays.length}
                className="w-full h-12 bg-gradient-to-r from-violet-600 to-primary font-bold uppercase text-white tracking-wider rounded-xl shadow-lg shadow-violet-500/20"
              >
                {narrativePhotos.length < narrativeOverlays.length 
                  ? `Select ${narrativeOverlays.length} photos minimum` 
                  : "Generate Narrative Reel"}
              </Button>
            </div>
          )}


        </div>
      )}

      {/* ── STAGE 2: FULL-SCREEN PROGRESS OVERLAY ── */}
      {stage === "progress" && (
        <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/95 backdrop-blur-xl px-6 text-center">
          <div className="relative flex items-center justify-center">
            {/* Animated Gradient Rotating Ring */}
            <div className="h-44 w-44 rounded-full border-4 border-slate-900" />
            <svg className="absolute h-44 w-44 -rotate-90">
              <circle
                cx="88"
                cy="88"
                r="84"
                stroke="url(#progress-gradient)"
                strokeWidth="6"
                fill="transparent"
                strokeDasharray="527"
                strokeDashoffset={527 - (527 * progress) / 100}
                className="transition-all duration-300 ease-out"
              />
              <defs>
                <linearGradient id="progress-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#8b5cf6" />
                  <stop offset="100%" stopColor="#ec4899" />
                </linearGradient>
              </defs>
            </svg>

            {/* Inner Percentage Readout */}
            <div className="absolute flex flex-col items-center justify-center">
              <span className="text-3xl font-black text-white">{Math.round(progress)}%</span>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-0.5">Progress</span>
            </div>
          </div>

          <h2 className="mt-8 text-xl font-bold text-white tracking-tight">Compiling Short Video</h2>
          <p className="mt-2 text-sm text-slate-400 h-6 font-medium animate-pulse">{statusText}</p>

          <Button
            onClick={cancelJob}
            variant="ghost"
            className="mt-12 text-slate-400 hover:text-white hover:bg-white/5 border border-white/10 rounded-xl px-6 py-2"
          >
            Cancel Generation
          </Button>
        </div>
      )}

      {/* ── STAGE 3: RESULT PREVIEW SCREEN ── */}
      {stage === "result" && (
        <div className="flex flex-col gap-6 px-4 pb-24 pt-6 max-w-2xl mx-auto w-full">
          <header className="text-center">
            <h2 className="text-2xl font-black tracking-tight text-white">Your Video is Ready! 🎉</h2>
            <p className="text-xs text-slate-400 mt-1">Ready to share, download, or score for virality.</p>
          </header>

          {/* Portrait Custom video player */}
          <div className="relative aspect-[9/16] w-full max-h-[460px] mx-auto rounded-3xl overflow-hidden bg-slate-950 border border-white/10 shadow-2xl">
            {outputUrl ? (
              <video 
                src={outputUrl} 
                autoPlay 
                muted 
                loop 
                playsInline 
                className="h-full w-full object-cover" 
              />
            ) : (
              <div className="grid h-full w-full place-items-center text-slate-500 text-xs">
                No video preview available.
              </div>
            )}

            {/* Floating Top indicators */}
            <div className="absolute top-4 left-4 bg-black/60 backdrop-blur-md px-3 py-1 rounded-full border border-white/10 text-[10px] font-bold text-violet-400 flex items-center gap-1">
              <Sparkles className="h-3 w-3" /> BEAT-SYNCED
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-2 gap-3">
            <Button
              onClick={() => {
                if (!outputUrl) return;
                const a = document.createElement("a");
                a.href = outputUrl;
                a.download = `trendrop-video-${Date.now()}.mp4`;
                document.body.appendChild(a);
                a.click();
                a.remove();
              }}
              className="h-12 bg-white text-black font-bold uppercase rounded-xl hover:bg-slate-200"
            >
              <Download className="h-4 w-4 mr-2" /> Download
            </Button>

            <Button
              onClick={async () => {
                if (!outputUrl) return;
                if (navigator.share) {
                  try {
                    await navigator.share({ title: "My viral trendrop short", url: outputUrl });
                  } catch {}
                } else {
                  await navigator.clipboard.writeText(outputUrl);
                }
              }}
              variant="outline"
              className="h-12 border-white/10 text-white font-bold uppercase rounded-xl hover:bg-white/5"
            >
              <Share2 className="h-4 w-4 mr-2" /> Share Link
            </Button>
          </div>

          {/* Scoring panel toggle — calls real /api/score-reel */}
          <Button
            onClick={async () => {
              if (showScoreCard) { setShowScoreCard(false); return; }
              setScoringLoading(true);
              try {
                const audio = activeTrend?.song ?? "unknown audio";
                const postingTime = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: false });
                const res = await scoreReel({
                  audio,
                  caption: `Trending reel using ${audio}`,
                  posting_time: postingTime,
                  niche: "general",
                });
                setScoreDetails({
                  overall: Math.round(res.overall_score),
                  hook: Math.round(res.hook_score),
                  retention: Math.round(res.audio_score),
                  fit: Math.round(res.caption_score),
                  explanation: res.top_fixes?.length
                    ? `Top fixes: ${res.top_fixes.slice(0, 2).join(" • ")}`
                    : `Grade ${res.grade} — Audio sync and hook strength are the key drivers.`,
                });
                setShowScoreCard(true);
                if (res.is_fallback) {
                  import("sonner").then(({ toast }) => toast.warning(res.fallback_reason || "Showing fallback score — LLM unavailable"));
                }
              } catch {
                import("sonner").then(({ toast }) => toast.error("Score API unavailable — try again shortly."));
              } finally {
                setScoringLoading(false);
              }
            }}
            disabled={scoringLoading}
            className="w-full h-12 bg-gradient-to-r from-violet-600 to-primary font-bold uppercase text-white rounded-xl shadow-lg"
          >
            <Star className="h-4 w-4 mr-2 text-amber-300 fill-amber-300" />
            {scoringLoading ? "Scoring..." : showScoreCard ? "Hide Score" : "Score This Video"}
          </Button>

          {/* Scorecard detail section */}
          {showScoreCard && scoreDetails && (
            <div className="rounded-2xl border border-border bg-surface-2 backdrop-blur-md p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-bold text-text text-base">Virality Analysis</h3>
                  <p className="text-[10px] text-text-muted mt-0.5">Calculated using our feedback loop.</p>
                </div>
                <div className="flex items-center justify-center h-12 w-12 rounded-full bg-violet-500/10 ring-1 ring-violet-500/30 text-violet-400 text-lg font-black">
                  {scoreDetails.overall}%
                </div>
              </div>

              <div className="space-y-3">
                {/* Hook Score */}
                <div className="space-y-3">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-400">Hook Retention Score</span>
                    <span className="text-white">{scoreDetails.hook}%</span>
                  </div>
                      <svg viewBox="0 0 100 6" className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800" aria-hidden="true">
                        <rect x="0" y="0" width={Math.max(0, Math.min(100, scoreDetails.hook))} height="6" rx="3" fill="#fbbf24" />
                      </svg>
                </div>

                {/* Audience Fit */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-400">Creator Fit Score</span>
                    <span className="text-white">{scoreDetails.fit}%</span>
                  </div>
                  <svg viewBox="0 0 100 6" className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800" aria-hidden="true">
                    <rect x="0" y="0" width={Math.max(0, Math.min(100, scoreDetails.fit))} height="6" rx="3" fill="#a78bfa" />
                  </svg>
                </div>

                {/* Platform Velocity */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-400">Audio Sync & Rhythm Fit</span>
                    <span className="text-white">{scoreDetails.retention}%</span>
                  </div>
                  <svg viewBox="0 0 100 6" className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800" aria-hidden="true">
                    <rect x="0" y="0" width={Math.max(0, Math.min(100, scoreDetails.retention))} height="6" rx="3" fill="#34d399" />
                  </svg>
                </div>
              </div>

              <p className="text-xs text-slate-400 italic bg-white/5 p-3 rounded-lg border border-white/5 leading-relaxed">
                " {scoreDetails.explanation} "
              </p>
            </div>
          )}

          <Button
            onClick={resetAll}
            variant="ghost"
            className="w-full text-slate-400 hover:text-white"
          >
            Create Another Video
          </Button>
        </div>
      )}

      {/* ── STAGE 4: ERROR STATE ── */}
      {stage === "error" && (
        <div className="flex flex-col items-center justify-center min-h-[70vh] px-6 text-center max-w-sm mx-auto">
          <div className="grid h-16 w-16 place-items-center rounded-2xl bg-red-500/10 text-red-500 ring-1 ring-red-500/30">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h2 className="mt-6 text-2xl font-bold text-white tracking-tight">Generation Failed</h2>
          <p className="mt-2 text-sm text-slate-400 leading-relaxed">
            {errorMsg || "An unknown compilation error occurred during beat mapping."}
          </p>

          <Button
            onClick={() => setStage("upload")}
            className="mt-8 h-12 bg-white text-black font-bold uppercase rounded-xl hover:bg-slate-200 w-full"
          >
            Go Back & Retry
          </Button>
        </div>
      )}
    </div>
    </PlanGate>
  );
}
