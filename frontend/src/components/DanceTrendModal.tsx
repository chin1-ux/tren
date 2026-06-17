import { useState } from "react";
import { Copy, X, Check } from "lucide-react";
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
    "Open Instagram camera",
    "Select the song from the audio library",
    "Film yourself following the brief below",
    "Post using the suggested hashtags",
  ];

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-black/80 backdrop-blur-sm animate-in fade-in sm:items-center">
      <div className="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-t-3xl border border-border bg-card p-6 animate-in slide-in-from-bottom sm:rounded-3xl">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-secondary">💃 Dance Trend</h2>
            <p className="mt-1 text-sm text-muted-foreground">This trend requires you to film yourself</p>
          </div>
          <button onClick={onClose} className="rounded-full p-2 text-muted-foreground hover:bg-muted hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <Section label="Song to use">
          <div className="flex items-center justify-between gap-3 rounded-xl bg-muted p-3">
            <div className="min-w-0">
              <p className="truncate font-semibold">{trend.song}</p>
              <p className="truncate text-xs text-muted-foreground">{trend.artist}</p>
            </div>
            <button onClick={copy} className="shrink-0 rounded-lg bg-background p-2 text-muted-foreground hover:text-foreground">
              {copied ? <Check className="h-4 w-4 text-success" /> : <Copy className="h-4 w-4" />}
            </button>
          </div>
        </Section>

        <Section label="What to film">
          <p className="text-sm text-foreground/90">{trend.idealContentDescription}</p>
        </Section>

        <Section label="Camera tip">
          <p className="text-sm text-foreground/90">{trend.cameraStyle}</p>
        </Section>

        <Section label="Step by step">
          <ol className="space-y-2">
            {steps.map((s, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-secondary text-xs font-bold text-secondary-foreground">{i + 1}</span>
                <span className="pt-0.5">{s}</span>
              </li>
            ))}
          </ol>
        </Section>

        <Section label="Hashtags">
          <div className="flex flex-wrap gap-2">
            {trend.hashtags.map((h) => (
              <span key={h} className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-foreground/80">{h}</span>
            ))}
          </div>
        </Section>

        <Button onClick={onClose} className="mt-2 h-11 w-full" variant="outline">Close</Button>
      </div>
    </div>
  );
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-4 space-y-2">
      <h3 className="text-xs font-bold uppercase tracking-wide text-muted-foreground">{label}</h3>
      {children}
    </div>
  );
}
