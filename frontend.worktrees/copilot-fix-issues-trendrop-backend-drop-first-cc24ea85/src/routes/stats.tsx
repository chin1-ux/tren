import { createFileRoute } from "@tanstack/react-router";
import { BarChart3, TrendingUp, Users, Video, Award, Star } from "lucide-react";
import { useEffect, useState } from "react";

export const Route = createFileRoute("/stats")({
  head: () => ({
    meta: [
      { title: "Dashboard — Trendrop" },
      { name: "description", content: "Track your creator performance and stats." },
    ],
  }),
  component: DashboardPage,
});

function DashboardPage() {
  const [reelsCount, setReelsCount] = useState(0);
  const [niche, setNiche] = useState("Dance");
  const [platform, setPlatform] = useState("Instagram");
  const [lastGeneratedAt, setLastGeneratedAt] = useState<string | null>(null);

  useEffect(() => {
    const sync = () => {
      const count = parseInt(localStorage.getItem("trendrop_generated_count") || "0", 10);
      setReelsCount(Number.isFinite(count) ? count : 0);

      const savedNiche = localStorage.getItem("trendrop_niche");
      if (savedNiche) {
        setNiche(savedNiche.charAt(0).toUpperCase() + savedNiche.slice(1));
      }

      const savedPlatform = localStorage.getItem("trendrop_platform");
      if (savedPlatform) {
        setPlatform(savedPlatform === "youtube_shorts" ? "YT Shorts" : "Instagram");
      }

      setLastGeneratedAt(localStorage.getItem("trendrop_last_generated_at"));
    };

    sync();
    window.addEventListener("storage", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("focus", sync);
    };
  }, []);

  // Mock creator metrics based on number of generated reels
  const viewsEst = reelsCount * 12500;
  const engagementEst = reelsCount > 0 ? `${Math.min(12, 4.2 + reelsCount * 0.35).toFixed(1)}%` : "0.0%";
  const followersEst = reelsCount * 145;
  const momentumLabel = reelsCount === 0 ? "No activity yet" : reelsCount < 3 ? "Getting started" : reelsCount < 8 ? "Building momentum" : "High-output mode";

  return (
    <div className="flex flex-col gap-6 px-4 pb-24 pt-6">
      <header className="flex items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary text-white text-xl font-bold shadow-lg shadow-primary/20">
          ◈
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold gradient-text">Dashboard</h1>
          <p className="text-xs text-muted-foreground">Real-time creator performance metrics</p>
        </div>
      </header>

      {/* Overview Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="glass-card p-4 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Est. Views</span>
            <TrendingUp className="h-3.5 w-3.5 text-primary" />
          </div>
          <p className="text-2xl font-extrabold">{viewsEst.toLocaleString()}</p>
          <p className="text-[10px] text-primary font-semibold">+{reelsCount > 0 ? "24.5%" : "0%"} this week</p>
        </div>

        <div className="glass-card p-4 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Est. Followers</span>
            <Users className="h-3.5 w-3.5 text-secondary" />
          </div>
          <p className="text-2xl font-extrabold">+{followersEst.toLocaleString()}</p>
          <p className="text-[10px] text-secondary font-semibold">from Trendrop reels</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="glass-card p-4 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Reels Made</span>
            <Video className="h-3.5 w-3.5 text-[#ff006e]" />
          </div>
          <p className="text-2xl font-extrabold">{reelsCount}</p>
          <p className="text-[10px] text-muted-foreground font-medium">using active trends</p>
        </div>

        <div className="glass-card p-4 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Engagement</span>
            <Award className="h-3.5 w-3.5 text-amber-500" />
          </div>
          <p className="text-2xl font-extrabold">{engagementEst}</p>
          <p className="text-[10px] text-amber-500 font-semibold">Avg. Industry: 4.2%</p>
        </div>
      </div>

      {/* Creator Profile Summary */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-sm font-bold flex items-center gap-2">
          <Star className="h-4 w-4 text-primary" /> Creator Identity
        </h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="rounded-xl bg-muted/40 p-3">
            <span className="text-[10px] text-muted-foreground block uppercase font-bold">Primary Niche</span>
            <span className="font-bold text-foreground mt-0.5 block">{niche}</span>
          </div>
          <div className="rounded-xl bg-muted/40 p-3">
            <span className="text-[10px] text-muted-foreground block uppercase font-bold">Target Platform</span>
            <span className="font-bold text-foreground mt-0.5 block">{platform}</span>
          </div>
        </div>
        <div className="rounded-xl bg-muted/40 p-3">
          <span className="text-[10px] text-muted-foreground block uppercase font-bold">Momentum</span>
          <span className="font-bold text-foreground mt-0.5 block">{momentumLabel}</span>
        </div>
      </div>

      {/* Goal Target */}
      <div className="glass-card p-5 text-center space-y-3">
        <div className="mx-auto grid h-12 w-12 place-items-center rounded-full bg-primary/10 text-primary">
          <BarChart3 className="h-6 w-6" />
        </div>
        <h3 className="font-bold">Growth Strategy</h3>
        <p className="text-xs text-muted-foreground max-w-xs mx-auto">
          {reelsCount > 0
            ? `Awesome! You have published ${reelsCount} reels. Keep posting at the recommended times in your profile to accelerate your viral velocity.`
            : "Generate your first reel using our 3D editor to begin tracking viral analytics and performance insights here."}
        </p>
        {lastGeneratedAt && (
          <p className="text-[10px] text-muted-foreground">
            Last reel generated: {new Date(lastGeneratedAt).toLocaleString()}
          </p>
        )}
      </div>
    </div>
  );
}
