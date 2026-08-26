import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { 
  Sparkles, TrendingUp, AlertTriangle, CheckCircle, RefreshCw, BarChart2, ShieldAlert
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchCreatorDiagnostics, fetchCreatorNicheHealth } from "@/lib/api";
import { toast } from "sonner";
import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";

export const Route = createFileRoute("/stats")({
  head: () => ({
    meta: [
      { title: "Diagnostics Dashboard — Trendrop" },
      { name: "description", content: "Audit post performance, identify content flops, and assess niche health." },
    ],
  }),
  errorComponent: RouteErrorBoundary,
  component: StatsPage,
});

function StatsPage() {
  const [email, setEmail] = useState("");
  const [activeTab, setActiveTab] = useState<"diagnostics" | "niche">("diagnostics");

  useEffect(() => {
    // Read the key AuthContext actually writes (trendrop_user_email); never
    // fall back to a fictional address — queries stay disabled until known.
    setEmail(localStorage.getItem("trendrop_user_email") || "");
  }, []);

  const { data: diagnostics, isLoading: loadingDiag, refetch: refetchDiag } = useQuery({
    queryKey: ["creator-diagnostics", email],
    queryFn: () => fetchCreatorDiagnostics(email),
    enabled: !!email,
    staleTime: 5 * 60_000,
  });

  const { data: nicheHealth, isLoading: loadingNiche, refetch: refetchNiche } = useQuery({
    queryKey: ["creator-niche-health", email],
    queryFn: () => fetchCreatorNicheHealth(email),
    enabled: !!email,
    staleTime: 5 * 60_000,
  });

  const handleRefresh = () => {
    if (activeTab === "diagnostics") {
      refetchDiag();
      toast.success("Refreshing performance diagnostics...");
    } else {
      refetchNiche();
      toast.success("Refreshing niche consistency audit...");
    }
  };

  const currentNicheScore = nicheHealth?.data?.niche_health_score ?? 0.0;
  const nicheStatusLabel = currentNicheScore >= 0.85 
    ? "Highly Focused Niche" 
    : currentNicheScore >= 0.60 
      ? "Slight Algorithmic Dilution" 
      : "Multi-Niche Drift Warning";

  return (
    <div className="flex flex-col gap-5 px-4 pb-12 pt-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold gradient-text">Creator Diagnostics</h1>
          <p className="text-sm text-muted-foreground">Identify underperformance & niche alignment</p>
        </div>
        <Button size="icon" variant="outline" onClick={handleRefresh} className="rounded-xl h-10 w-10">
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex rounded-xl bg-muted/60 p-1 border border-border/50">
        <button
          onClick={() => setActiveTab("diagnostics")}
          className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider rounded-lg transition-all ${
            activeTab === "diagnostics" 
              ? "bg-background text-foreground shadow-sm" 
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Flop Audit
        </button>
        <button
          onClick={() => setActiveTab("niche")}
          className={`flex-1 py-2 text-xs font-bold uppercase tracking-wider rounded-lg transition-all ${
            activeTab === "niche" 
              ? "bg-background text-foreground shadow-sm" 
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Niche Health
        </button>
      </div>

      {/* Tab Contents */}
      {activeTab === "diagnostics" && (
        <div className="space-y-4">
          {loadingDiag ? (
            <div className="flex items-center justify-center py-10">
              <RefreshCw className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : diagnostics?.status === "no_data" ? (
            <div className="glass-card p-6 text-center space-y-3">
              <AlertTriangle className="h-10 w-10 text-warning mx-auto" />
              <h3 className="font-bold text-foreground text-sm">No Sync Data Available</h3>
              <p className="text-xs text-muted-foreground max-w-xs mx-auto">
                Instagram sync is coming soon — diagnostics will appear here once syncing launches.
              </p>
            </div>
          ) : (
            <>
              {/* Stats Card */}
              <div className="grid grid-cols-2 gap-3">
                <div className="glass-card p-4 text-center">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Rolling Avg Reach</span>
                  <div className="text-lg font-bold text-foreground mt-1">
                    {diagnostics?.data?.baseline_avg_plays?.toLocaleString() ?? 0}
                  </div>
                </div>
                <div className="glass-card p-4 text-center">
                  <span className="text-[10px] uppercase font-bold text-muted-foreground">Flop Ratio</span>
                  <div className="text-lg font-bold text-error mt-1">
                    {diagnostics?.data?.flops_detected ?? 0} / {diagnostics?.data?.total_posts_analyzed ?? 0}
                  </div>
                </div>
              </div>

              {/* Identified Flops */}
              <div className="glass-card p-5 space-y-4">
                <h3 className="font-display text-sm font-bold flex items-center gap-2 text-foreground">
                  <ShieldAlert className="h-4 w-4 text-error" /> Underperforming Posts
                </h3>
                {diagnostics?.data?.flops?.map((f) => (
                  <div key={f.media_id} className="border-b border-border/40 pb-3 last:border-b-0 last:pb-0 space-y-1">
                    <p className="text-xs text-foreground font-medium line-clamp-2 italic">
                      "{f.caption || "No caption"}"
                    </p>
                    <div className="flex justify-between items-center text-[10px] text-muted-foreground">
                      <span>Plays: <strong className="text-foreground">{f.plays_count}</strong></span>
                      <a href={f.permalink} target="_blank" rel="noreferrer" className="text-primary font-bold hover:underline">
                        View Post →
                      </a>
                    </div>
                  </div>
                ))}
              </div>

              {/* Suggested Remedy Tracks */}
              <div className="glass-card p-5 space-y-4">
                <h3 className="font-display text-sm font-bold flex items-center gap-2 text-foreground">
                  <TrendingUp className="h-4 w-4 text-primary" /> Algorithmic Recovery Tracks
                </h3>
                <p className="text-xs text-muted-foreground">
                  Post high-retention content using these trending audios to reset test-audience distribution metrics.
                </p>
                <div className="space-y-3">
                  {diagnostics?.data?.suggested_remedy_tracks?.map((t) => (
                    <div key={t.audio_title} className="p-3 bg-muted/40 rounded-xl space-y-1">
                      <div className="flex justify-between items-center">
                        <strong className="text-xs text-foreground">{t.audio_title}</strong>
                        <span className="text-[10px] text-primary font-bold">{t.audio_artist}</span>
                      </div>
                      <p className="text-[10px] text-muted-foreground">{t.why_this_works}</p>
                      {t.transfer_instructions && (
                        <p className="text-[10px] text-[#ff006e] border-t border-border/20 pt-1 mt-1 font-medium">
                          💡 {t.transfer_instructions}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {activeTab === "niche" && (
        <div className="space-y-4">
          {loadingNiche ? (
            <div className="flex items-center justify-center py-10">
              <RefreshCw className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : nicheHealth?.status === "no_data" ? (
            <div className="glass-card p-6 text-center space-y-3">
              <AlertTriangle className="h-10 w-10 text-warning mx-auto" />
              <h3 className="font-bold text-foreground text-sm">No Sync Data Available</h3>
              <p className="text-xs text-muted-foreground max-w-xs mx-auto">
                Instagram sync is coming soon — niche analysis unlocks once your posts can be synced.
              </p>
            </div>
          ) : (
            <>
              {/* Niche Health Score */}
              <div className="glass-card p-5 text-center space-y-2 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-2 h-full bg-gradient-to-b from-primary to-secondary" />
                <span className="text-xs uppercase font-bold text-muted-foreground">Niche Health Index</span>
                <div className="text-4xl font-extrabold text-foreground tracking-tight">
                  {Math.round(currentNicheScore * 100)}%
                </div>
                <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-[11px] font-bold text-primary">
                  {nicheHealth?.data?.alignment_drift_detected ? (
                    <>
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span>{nicheStatusLabel}</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-3.5 w-3.5" />
                      <span>{nicheStatusLabel}</span>
                    </>
                  )}
                </div>
              </div>

              {/* Niches Profile */}
              <div className="glass-card p-5 space-y-3">
                <h3 className="font-display text-sm font-bold text-foreground">Algorithmic Niche Classification</h3>
                <div className="space-y-2">
                  <div>
                    <span className="text-[10px] text-muted-foreground font-bold uppercase block mb-1">Primary Niche</span>
                    <span className="inline-flex items-center rounded-lg bg-surface border border-border px-3 py-1.5 text-xs font-bold text-foreground">
                      🎨 {nicheHealth?.data?.primary_niche}
                    </span>
                  </div>
                  {nicheHealth?.data?.secondary_niches && nicheHealth.data.secondary_niches.length > 0 && (
                    <div>
                      <span className="text-[10px] text-muted-foreground font-bold uppercase block mb-1">Diluting Secondary Niches</span>
                      <div className="flex flex-wrap gap-1.5">
                        {nicheHealth.data.secondary_niches.map((sn) => (
                          <span key={sn} className="inline-flex items-center rounded-lg bg-[#ff006e]/10 border border-[#ff006e]/20 px-2 py-1 text-[10px] font-bold text-[#ff006e]">
                            ⚠️ {sn}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Recommendations */}
              <div className="glass-card p-5 space-y-3">
                <h3 className="font-display text-sm font-bold text-foreground">Optimization Action Plan</h3>
                <ul className="space-y-2.5">
                  {nicheHealth?.data?.recommendations?.map((rec, i) => (
                    <li key={i} className="flex gap-2 text-xs text-foreground">
                      <span className="text-primary font-bold">0{i + 1}.</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
