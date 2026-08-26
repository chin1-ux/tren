import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { TrendingUp, Clock, Zap, ArrowUpRight, BarChart3 } from "lucide-react";
import { apiFetch } from "@/lib/api";

export const Route = createFileRoute("/proof")({
  head: () => ({
    meta: [
      { title: "Proof — Trendrop" },
      { name: "description", content: "Real early detection data. See how early Trendrop detected trending audio before it peaked." },
    ],
  }),
  component: ProofPage,
});

interface ProofItem {
  trend_id: number;
  title: string;
  artist: string;
  audio_name: string;
  status: string;
  detected_at: string;
  peak_at: string | null;
  hours_early: number | null;
  velocity_score: number;
  niche: string;
  language: string;
}

function ProofPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["proof"],
    queryFn: async () => {
      const res = await apiFetch("/api/proof");
      if (!res.ok) throw new Error("Failed to load proof data");
      return res.json();
    },
    staleTime: 5 * 60 * 1000,
  });

  const proofItems: ProofItem[] = data?.proof ?? [];

  const formatTime = (iso: string | null) => {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleDateString("en-IN", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "—";
    }
  };

  return (
    <div className="flex flex-col gap-6 px-4 pb-28 pt-6 max-w-2xl mx-auto w-full">
      {/* Hero */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10 text-primary text-xs font-bold uppercase tracking-wider">
          <Zap className="h-3.5 w-3.5" /> Early Detection Proof
        </div>
        <h1 className="font-display text-3xl font-extrabold tracking-tight">
          We detect trends <span className="text-primary">before they peak</span>
        </h1>
        <p className="text-sm text-muted-foreground max-w-md mx-auto">
          Real data from our trend engine. Each row shows when we detected a trend and when it actually peaked — proving early detection works.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-2xl border border-border bg-surface p-4 text-center">
          <BarChart3 className="h-5 w-5 text-primary mx-auto mb-1" />
          <div className="text-xl font-black text-foreground">{proofItems.length}</div>
          <div className="text-[10px] font-bold text-muted-foreground uppercase">Trends Tracked</div>
        </div>
        <div className="rounded-2xl border border-border bg-surface p-4 text-center">
          <Clock className="h-5 w-5 text-primary mx-auto mb-1" />
          <div className="text-xl font-black text-foreground">
            {proofItems.filter((p) => p.hours_early && p.hours_early > 0).length}
          </div>
          <div className="text-[10px] font-bold text-muted-foreground uppercase">Detected Early</div>
        </div>
        <div className="rounded-2xl border border-border bg-surface p-4 text-center">
          <TrendingUp className="h-5 w-5 text-primary mx-auto mb-1" />
          <div className="text-xl font-black text-foreground">
            {proofItems.filter((p) => p.status === "peaked" || p.status === "expired").length}
          </div>
          <div className="text-[10px] font-bold text-muted-foreground uppercase">Already Peaked</div>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 rounded-2xl bg-muted/30 animate-pulse" />
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-2xl border border-border bg-surface p-8 text-center">
          <p className="text-sm text-muted-foreground">Failed to load proof data. Please try again later.</p>
        </div>
      )}

      {/* Proof Table */}
      {!isLoading && !error && (
        <div className="space-y-2">
          {proofItems.map((item) => (
            <div
              key={item.trend_id}
              className="rounded-2xl border border-border bg-surface p-4 flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-foreground truncate">
                    {item.title || item.audio_name || "Unknown"}
                  </span>
                  <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${
                    item.status === "rising"
                      ? "bg-emerald-500/10 text-emerald-500"
                      : item.status === "peaked"
                      ? "bg-amber-500/10 text-amber-500"
                      : "bg-muted text-muted-foreground"
                  }`}>
                    {item.status}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  {item.artist} · {item.niche || "General"} · {item.language || "Hindi"}
                </div>
                <div className="flex items-center gap-3 mt-2 text-[10px] text-muted-foreground">
                  <span>Detected: <strong className="text-foreground">{formatTime(item.detected_at)}</strong></span>
                  <span>Peaked: <strong className="text-foreground">{formatTime(item.peak_at)}</strong></span>
                </div>
              </div>
              {item.hours_early !== null && item.hours_early > 0 && (
                <div className="text-right shrink-0">
                  <div className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-primary/10 text-primary">
                    <ArrowUpRight className="h-3 w-3" />
                    <span className="text-sm font-black">{item.hours_early}h</span>
                  </div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">early</div>
                </div>
              )}
            </div>
          ))}
          {proofItems.length === 0 && (
            <div className="rounded-2xl border border-border bg-surface p-12 text-center">
              <p className="text-3xl mb-2">📊</p>
              <p className="font-bold text-foreground">No proof data yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Our trend engine needs more data cycles to generate proof. Check back soon.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
