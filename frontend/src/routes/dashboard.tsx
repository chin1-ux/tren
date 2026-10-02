import { createFileRoute } from "@tanstack/react-router";
import { CreatorAnalyticsDashboard } from "@/components/CreatorAnalyticsDashboard";
import { AIContentGenerator } from "@/components/AIContentGenerator";
import { PlanGate } from "@/components/PlanGate";
import { EarlyDetectionPanel } from "@/components/EarlyDetectionPanel";
import { NewsFeedPanel } from "@/components/NewsFeedPanel";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OnboardingTour, useOnboarding } from "@/components/OnboardingTour";
import { Button } from "@/components/ui/button";
import { HelpCircle, Newspaper, Flame, BarChart3, Sparkles } from "lucide-react";
import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";
import { useUserStore } from "@/store/useAppStore";

export const Route = createFileRoute("/dashboard")({
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

import { useEffectivePlan } from "@/lib/plan";

function Dashboard() {
  const { isOpen, startOnboarding, closeOnboarding } = useOnboarding();
  const userEmail = useUserStore((s) => s.email) ?? "";
  const userNiche = useUserStore((s) => s.niche) || "all";
  const userPlan = useEffectivePlan();

  const isCurrentAffairsCreator = userNiche === "current_affairs";
  const defaultTab = isCurrentAffairsCreator ? "breaking-news" : "early-detection";

  const nicheEmoji = NICHE_EMOJIS[userNiche] ?? "🌐";
  const nicheLabel = NICHE_LABELS[userNiche] ?? "Creator";

  return (
    <>
      <OnboardingTour open={isOpen} onComplete={closeOnboarding} />
      <div className="container mx-auto py-8 px-4 pb-28">
        {/* Personalized greeting row */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
              {nicheEmoji} {nicheLabel} Dashboard
            </p>
            <h1 className="text-xl font-bold font-display mt-0.5 text-foreground">
              {isCurrentAffairsCreator
                ? "Breaking stories & commentary windows"
                : "Curated short-form trend feed"}
            </h1>
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

        <Tabs defaultValue={defaultTab} className="w-full">
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
                value="breaking-news"
                className="shrink-0 flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs sm:text-sm font-semibold text-muted-foreground transition-all hover:text-foreground data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border/60"
              >
                <Newspaper className="h-3.5 w-3.5 text-blue-400" />
                Viral News
              </TabsTrigger>

              <TabsTrigger
                value="analytics"
                className="shrink-0 flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs sm:text-sm font-semibold text-muted-foreground transition-all hover:text-foreground data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border/60"
              >
                <BarChart3 className="h-3.5 w-3.5 text-purple-400" />
                Analytics & AI
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="early-detection" className="mt-6">
            <EarlyDetectionPanel />
          </TabsContent>

          <TabsContent value="breaking-news" className="mt-6">
            <NewsFeedPanel />
          </TabsContent>

          <TabsContent value="analytics" className="mt-6 space-y-6">
            <CreatorAnalyticsDashboard creatorEmail={userEmail} />
            <div className="border-t border-border/40 pt-6">
              <h3 className="text-lg font-bold font-display flex items-center gap-2 mb-4">
                <Sparkles className="h-5 w-5 text-primary" /> AI Content Generator
              </h3>
              <PlanGate feature="AI Content Generator" requiredPlan="pro" currentPlan={userPlan}>
                <AIContentGenerator />
              </PlanGate>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}