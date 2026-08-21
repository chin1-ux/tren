import { useState, useEffect } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, X, Check, Film, Sparkles, Target, ExternalLink, Play, Calendar } from "lucide-react";
import type { UiTrend } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toggleTrendTarget, fetchTargetedTrends } from "@/lib/api";
import { toast } from "sonner";

interface Props {
  trend: UiTrend | null;
  onClose: () => void;
}

export function DanceTrendModal({ trend, onClose }: Props) {
  const [copied, setCopied] = useState(false);
  const [targetCount, setTargetCount] = useState(0);
  const [loadingTarget, setLoadingTarget] = useState(false);
  const queryClient = useQueryClient();

  const { data: targetedTrends = [] } = useQuery({
    queryKey: ["trends-targeted"],
    queryFn: fetchTargetedTrends,
    staleTime: 10_000,
  });

  const isTargeted = trend ? targetedTrends.some((t: any) => String(t.id) === String(trend.id)) : false;

  useEffect(() => {
    if (!trend) return;
    setTargetCount(trend.saturationCount ?? 0);
  }, [trend]);

  if (!trend) return null;

  const copy = async () => {
    await navigator.clipboard.writeText(`${trend.song} — ${trend.artist}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const handleToggleTarget = async () => {
    if (loadingTarget) return;
    setLoadingTarget(true);
    const newAction = isTargeted ? "untarget" : "target";
    try {
      const res = await toggleTrendTarget(trend.id, newAction);
      if (res.success) {
        setTargetCount(res.saturation_count);
        queryClient.invalidateQueries({ queryKey: ["trends-targeted"] });
        if (newAction === "target") {
          toast.success("Trend targeted! Added to your workspace 🎯");
        } else {
          toast.success("Trend removed from targeted list");
        }
      }
    } catch (err: any) {
      toast.error(err.message || "Failed to update target status");
    } finally {
      setLoadingTarget(false);
    }
  };

  // Build the storyboard items. Fallback if visualStoryboard is empty or null.
  const storyboard = (trend.visualStoryboard && trend.visualStoryboard.length > 0) 
    ? trend.visualStoryboard 
    : [
        { time: "0:00 - 0:03", instruction: `Visual Hook: Introduce "${trend.song}" with an engaging headline and match the energy of ${trend.artist || 'the artist'}.` },
        { time: "0:03 - 0:08", instruction: `Action Sequence: Record transitions matching the beat, highlighting details fitting the ${trend.category || 'Reel'} content.` },
        { time: "0:08 - 0:12", instruction: `End Scene: Bring it to a close with a call to action overlay matching the vibe of this audio.` }
      ];

  const hasTemplate = !!trend.templateLink;
  const isCapCut = trend.templateLink?.includes("capcut.com");

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      {/* Click outside backdrop to close */}
      <div className="absolute inset-0" onClick={onClose} />

      <div className="relative max-h-[85vh] w-full max-w-md overflow-y-auto rounded-t-3xl border-t border-x border-white/10 bg-zinc-950 px-6 pb-8 pt-4 shadow-2xl animate-in slide-in-from-bottom duration-300">
        
        {/* Pull/Drag indicator handle */}
        <div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-white/15" />

        <div className="mb-5 flex items-start justify-between">
          <div>
            <h2 className="text-xl font-extrabold tracking-tight text-amber flex items-center gap-2">
              <Film className="h-5 w-5 text-amber animate-pulse" /> Production Playbook
            </h2>
            <p className="mt-1 text-xs text-zinc-400">Step-by-step shooting instructions & assets</p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-full bg-white/5 p-2 text-zinc-400 hover:bg-white/10 hover:text-white transition-all"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          
          {/* Action Row: Targeting & Saturation */}
          <div className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-3">
            <div className="text-left">
              <p className="text-xs font-semibold text-zinc-400">Platform Saturation</p>
              <p className="text-sm font-extrabold text-foreground mt-0.5">
                {targetCount} {targetCount === 1 ? "Creator" : "Creators"} Targeting
              </p>
            </div>
            <Button
              onClick={handleToggleTarget}
              disabled={loadingTarget}
              className={`h-9 px-4 rounded-lg font-bold text-xs flex items-center gap-1.5 transition-all ${
                isTargeted 
                  ? "bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20" 
                  : "bg-primary text-white hover:bg-primary/90"
              }`}
            >
              <Target className={`h-4 w-4 ${isTargeted ? "animate-ping" : ""}`} />
              {isTargeted ? "Targeted 🎯" : "Target Trend"}
            </Button>
          </div>

          <Section label="Audio Details">
            <div className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-white/[0.02] p-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-white">{trend.song}</p>
                <p className="truncate text-xs text-zinc-400">by {trend.artist}</p>
              </div>
              <button
                onClick={copy}
                className="shrink-0 rounded-lg bg-white/5 p-2 text-zinc-400 hover:bg-white/10 hover:text-white transition-all flex items-center gap-1 text-xs font-semibold"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy Info</span>
                  </>
                )}
              </button>
            </div>
          </Section>

          {/* Template Deep-Link */}
          {hasTemplate && (
            <Section label="Editing Template Available">
              <a
                href={trend.templateLink!}
                target="_blank"
                rel="noopener noreferrer"
                className="flex w-full items-center justify-between rounded-xl border border-violet-500/30 bg-violet-500/10 px-4 py-3 text-xs font-bold text-violet-300 hover:bg-violet-500/20 hover:border-violet-500/50 transition-all"
              >
                <span className="flex items-center gap-2">
                  <Play className="h-4 w-4 fill-current text-violet-400" />
                  Use Template on {isCapCut ? "CapCut" : "Instagram"}
                </span>
                <ExternalLink className="h-3.5 w-3.5 opacity-60" />
              </a>
            </Section>
          )}

          <Section label="Concept Vibe">
            <div className="flex items-center gap-2">
              <span className="inline-flex rounded-full bg-white/5 border border-white/10 px-2.5 py-0.5 text-[10px] font-bold text-zinc-300 uppercase tracking-wide">
                🎨 Vibe: {trend.vibeTag ?? "general"}
              </span>
              <span className="inline-flex rounded-full bg-white/5 border border-white/10 px-2.5 py-0.5 text-[10px] font-bold text-zinc-300 uppercase tracking-wide">
                🎥 Style: {trend.cameraStyle || "general"}
              </span>
            </div>
          </Section>

          <Section label="Visual Storyboard Timeline">
            <div className="space-y-3 pl-1 border-l border-white/10 ml-2">
              {storyboard.map((step, i) => (
                <div key={i} className="relative flex gap-3.5 text-xs">
                  {/* Dot indicator */}
                  <div className="absolute -left-[19px] top-1.5 h-2 w-2 rounded-full bg-amber shadow-[0_0_8px_rgba(245,158,11,0.5)]" />
                  
                  <div className="flex-1">
                    <p className="font-extrabold text-amber text-[10px] uppercase tracking-wider">{step.time}</p>
                    <p className="mt-0.5 text-zinc-300 leading-relaxed font-medium">{step.instruction}</p>
                  </div>
                </div>
              ))}
            </div>
          </Section>

          <Section label="Ideal Caption Idea">
            <div className="rounded-xl border border-white/5 bg-white/[0.02] p-3 text-xs leading-relaxed text-zinc-300">
              {trend.idealContentDescription && !trend.idealContentDescription.includes("Short creator clips")
                ? trend.idealContentDescription
                : `Create a transition sequence synced to the beats of "${trend.song}" by ${trend.artist}. Highlight details matching the ${trend.nicheTag || 'creator'} theme.`}
            </div>
          </Section>
        </div>

        <div className="mt-6 flex gap-2">
          {hasTemplate ? (
            <a
              href={trend.templateLink!}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1"
            >
              <Button className="h-11 w-full bg-amber font-bold text-white hover:bg-amber/90">
                Open Template
              </Button>
            </a>
          ) : (
            <Button 
              onClick={async () => {
                if (!isTargeted) {
                  await handleToggleTarget();
                }
                onClose();
              }} 
              className="flex-1 h-11 bg-amber font-bold text-white hover:bg-amber/90"
            >
              Got it, Let's Film!
            </Button>
          )}
          <Button onClick={onClose} className="h-11 w-24 border-white/10 hover:bg-white/5 text-zinc-400" variant="outline">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5 text-left">
      <h3 className="text-[10px] font-bold uppercase tracking-wider text-zinc-400/80">{label}</h3>
      {children}
    </div>
  );
}
