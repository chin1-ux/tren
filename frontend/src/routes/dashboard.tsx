import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { EarlyDetectionPanel } from "@/components/EarlyDetectionPanel";
import { FestiveViralRadar } from "@/components/FestiveViralRadar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OnboardingTour, useOnboarding } from "@/components/OnboardingTour";
import { Button } from "@/components/ui/button";
import { HelpCircle, Flame } from "lucide-react";
import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";
import { useUserStore } from "@/store/useAppStore";
import { useEffectivePlan } from "@/lib/plan";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Creator Dashboard — Trendrop" },
      { name: "description", content: "Trending Audio early detection, Festive Viral Radar, and Creator Studio post-mortem flop audit." },
    ],
  }),
  component: Dashboard,
  errorComponent: RouteErrorBoundary,
});

const NICHE_LABELS: Record<string, string> = {
  current_affairs: "Current Affairs",
  fitness: "Fitness",
  food: "Food",
  travel: "Travel",
  fashion: "Fashion",
  dance: "Dance",
  comedy: "Comedy",
  motivation: "Motivation",
  all: "All Niches",
};

const NICHE_EMOJIS: Record<string, string> = {
  current_affairs: "📰",
  fitness: "💪",
  food: "🍽️",
  travel: "✈️",
  fashion: "👗",
  dance: "💃",
  comedy: "😂",
  motivation: "🔥",
  all: "🌐",
};

function Dashboard() {
  const { isOpen, startOnboarding, closeOnboarding } = useOnboarding();
  const userNiche = useUserStore((s) => s.niche) || "all";
  const userPlan = useEffectivePlan();

  const [activeTab, setActiveTab] = useState<string>("early-detection");

  // Read URL query params on mount (e.g. ?tab=festive or ?tab=studio)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      const tabParam = params.get("tab");
      if (tabParam === "festive" || tabParam === "festive-radar") {
        setActiveTab("festive-radar");
      } else if (tabParam === "studio" || tabParam === "flop") {
        setActiveTab("studio");
      } else if (tabParam === "audio" || tabParam === "early-detection") {
        setActiveTab("early-detection");
      }
    }
  }, []);

  const nicheEmoji = NICHE_EMOJIS[userNiche] ?? "🌐";
  const nicheLabel = NICHE_LABELS[userNiche] ?? "Creator";

  return (
    <>
      <OnboardingTour open={isOpen} onComplete={closeOnboarding} />
      <div className="container mx-auto py-8 px-4 pb-28 max-w-6xl">
        {/* Personalized greeting row */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
              {nicheEmoji} {nicheLabel} Dashboard
            </p>
            <h1 className="text-2xl font-bold font-display mt-0.5 text-foreground">
              Creator Intelligence Hub
            </h1>
            <p className="text-xs text-muted-foreground mt-0.5">
              Early audio radar, festive anticipation waves, and post-mortem flop diagnosis
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={startOnboarding}
            className="gap-1.5 text-muted-foreground hover:text-foreground"
          >
            <HelpCircle className="h-4 w-4" />
            Tour
          </Button>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <div className="w-full overflow-x-auto no-scrollbar py-1 -mx-4 px-4">
            <TabsList className="flex w-max min-w-full justify-start md:justify-center p-1.5 h-12 gap-2 bg-muted/70 border border-border/50 rounded-2xl">
              <TabsTrigger
                value="early-detection"
                className="shrink-0 flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs sm:text-sm font-semibold text-muted-foreground transition-all hover:text-foreground data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border/60"
              >
                <Flame className="h-3.5 w-3.5 text-primary" />
                Trending Audio
              </TabsTrigger>

              <TabsTrigger
                value="festive-radar"
                className="shrink-0 flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs sm:text-sm font-semibold text-muted-foreground transition-all hover:text-foreground data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border/60"
              >
                <span className="text-orange-400">🔥</span>
                Festive Viral Radar
                <span className="ml-1 text-[9px] px-1.5 py-0.2 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30 font-bold">
                  NEW
                </span>
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="early-detection" className="mt-6">
            <EarlyDetectionPanel />
          </TabsContent>

          <TabsContent value="festive-radar" className="mt-6">
            <FestiveViralRadar />
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}