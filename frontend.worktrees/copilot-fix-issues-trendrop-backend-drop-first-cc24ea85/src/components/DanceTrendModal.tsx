import { useState } from "react";
import { Copy, X, Check, Film, Sparkles, AlertCircle } from "lucide-react";
import type { UiTrend } from "@/lib/api";
import { Button } from "@/components/ui/button";

interface Props {
  trend: UiTrend | null;
  onClose: () => void;
}

export function DanceTrendModal({ trend, onClose }: Props) {
  const [copied, setCopied] = useState(false);
  if (!trend) return null;

  const copy = async () => {
    await navigator.clipboard.writeText(`${trend.song} — ${trend.artist}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const steps = [
    "Open Instagram or YouTube Shorts camera",
    "Select the trending song from the audio library",
    "Record yourself following the brief described below",
    "Add a high-quality filter & follow camera hints",
    "Post using the suggested tags and captions"
  ];

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-black/75 backdrop-blur-md animate-in fade-in duration-200">
      {/* Click outside backdrop to close */}
      <div className="absolute inset-0" onClick={onClose} />

      <div className="relative max-h-[85vh] w-full max-w-md overflow-y-auto rounded-t-3xl border-t border-x border-border bg-surface px-6 pb-8 pt-4 shadow-2xl animate-in slide-in-from-bottom duration-300">
        
        {/* Pull/Drag indicator handle */}
        <div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-white/10" />

        <div className="mb-5 flex items-start justify-between">
          <div>
            <h2 className="text-xl font-extrabold tracking-tight text-amber flex items-center gap-2">
              <Film className="h-5 w-5 animate-pulse" /> Dance Film Guide
            </h2>
            <p className="mt-1 text-xs text-muted-foreground">Follow this production playbook to go viral</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full bg-white/5 p-2 text-muted-foreground hover:bg-white/10 hover:text-foreground transition-all"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          <Section label="Song to use">
            <div className="flex items-center justify-between gap-3 rounded-xl border border-border bg-white/[0.02] p-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-foreground">{trend.song}</p>
                <p className="truncate text-xs text-muted-foreground">by {trend.artist}</p>
              </div>
              <button
                onClick={copy}
                className="shrink-0 rounded-lg bg-white/5 p-2 text-muted-foreground hover:bg-white/10 hover:text-foreground transition-all flex items-center gap-1 text-xs"
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-success" />
                    <span className="text-success font-semibold">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy</span>
                  </>
                )}
              </button>
            </div>
          </Section>

          <Section label="What to film">
            <div className="rounded-xl border border-border bg-white/[0.02] p-3 text-xs leading-relaxed text-foreground/90">
              {trend.idealContentDescription || "Record transition or sync your dance movement to the beat drop."}
            </div>
          </Section>

          <Section label="Camera tip & setup">
            <div className="rounded-xl border border-border bg-white/[0.02] p-3 text-xs leading-relaxed text-foreground/90 flex gap-2.5 items-start">
              <Sparkles className="h-4 w-4 text-amber shrink-0 mt-0.5" />
              <span>{trend.cameraStyle || "Use portrait mode, tripod setup, eye-level angle with high saturation filter."}</span>
            </div>
          </Section>

          <Section label="Step-by-step tutorial">
            <ol className="space-y-3">
              {steps.map((s, i) => (
                <li key={i} className="flex gap-3 text-xs">
                  <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full bg-amber/25 text-[10px] font-bold text-amber border border-amber/20">
                    {i + 1}
                  </span>
                  <span className="pt-0.5 text-muted-foreground font-medium leading-relaxed">{s}</span>
                </li>
              ))}
            </ol>
          </Section>

          <Section label="Production hashtags">
            <div className="flex flex-wrap gap-1.5">
              {trend.hashtags && trend.hashtags.length > 0 ? (
                trend.hashtags.map((h) => (
                  <span
                    key={h}
                    className="rounded-full bg-white/5 border border-border px-2.5 py-0.5 text-[10px] font-semibold text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {h}
                  </span>
                ))
              ) : (
                <>
                  <span className="rounded-full bg-white/5 border border-border px-2.5 py-0.5 text-[10px] font-semibold text-muted-foreground">#viral</span>
                  <span className="rounded-full bg-white/5 border border-border px-2.5 py-0.5 text-[10px] font-semibold text-muted-foreground">#trendingreels</span>
                </>
              )}
            </div>
          </Section>
        </div>

        <div className="mt-6 flex gap-2">
          <Button onClick={onClose} className="h-11 w-full bg-amber font-bold text-white hover:bg-amber/90">
            Got it, Let's Film!
          </Button>
          <Button onClick={onClose} className="h-11 w-full border-border hover:bg-white/5" variant="outline">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <h3 className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground/80">{label}</h3>
      {children}
    </div>
  );
}
