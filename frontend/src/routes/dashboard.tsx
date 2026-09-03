import { createFileRoute } from "@tanstack/react-router";
import { CreatorAnalyticsDashboard } from "@/components/CreatorAnalyticsDashboard";
import { AIContentGenerator } from "@/components/AIContentGenerator";
import { PlanGate } from "@/components/PlanGate";
import { IndiaFeaturesDashboard } from "@/components/IndiaFeaturesDashboard";
import { EarlyDetectionPanel } from "@/components/EarlyDetectionPanel";
import { VideoAnalysisPanel } from "@/components/VideoAnalysisPanel";
import { NewsFeedPanel } from "@/components/NewsFeedPanel";
import { RegionalFestivalPanel } from "@/components/RegionalFestivalPanel";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OnboardingTour, useOnboarding } from "@/components/OnboardingTour";
import { Button } from "@/components/ui/button";
import { HelpCircle, Newspaper, Calendar } from "lucide-react";
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

function Dashboard() {
  const { isOpen, startOnboarding, closeOnboarding } = useOnboarding();
  const userEmail = useUserStore((s) => s.email) ?? "";
  const userNiche = useUserStore((s) => s.niche) || "all";
  const userPlan = useUserStore((s) => s.plan) || "free";

  // Current affairs creators get a special "Breaking News" tab as their default
  const isCurrentAffairsCreator = userNiche === "current_affairs";
  const defaultTab = isCurrentAffairsCreator ? "breaking-news" : "early-detection";

  const nicheEmoji = NICHE_EMOJIS[userNiche] ?? "🌐";
  const nicheLabel = NICHE_LABELS[userNiche] ?? "Creator";

  return (
    <>
      <OnboardingTour open={isOpen} onComplete={closeOnboarding} />
      <div className="container mx-auto py-8 px-4">
        {/* Personalized greeting row */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
              {nicheEmoji} {nicheLabel} Dashboard
            </p>
            <h1 className="text-xl font-bold font-display mt-0.5">
              {isCurrentAffairsCreator
                ? "Breaking stories & commentary windows"
                : "Your personalised trend feed"}
            </h1>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={startOnboarding}
            className="gap-1.5 text-muted-foreground"
          >
            <HelpCircle className="h-4 w-4" />
            Tour
          </Button>
        </div>

        <Tabs defaultValue={defaultTab} className="w-full">
          <div className="w-full overflow-x-auto no-scrollbar py-1 -mx-4 px-4">
            <TabsList className="flex w-max min-w-full justify-start md:justify-center p-1 h-11 gap-1.5 bg-muted/60 rounded-xl">
              {/* Show Breaking News tab first for current affairs creators */}
              {isCurrentAffairsCreator && (
                <TabsTrigger value="breaking-news" className="shrink-0 flex items-center gap-1.5">
                  <Newspaper className="h-3.5 w-3.5" />
                  Breaking News
                </TabsTrigger>
              )}
              <TabsTrigger value="early-detection" className="shrink-0">
                Early Detection
              </TabsTrigger>
              <TabsTrigger value="video-analysis" className="shrink-0">
                Video Analysis
              </TabsTrigger>
              {/* Regional Events tab for all users */}
              <TabsTrigger value="festivals" className="shrink-0 flex items-center gap-1.5">
                <Calendar className="h-3.5 w-3.5" />
                Festivals
              </TabsTrigger>
              <TabsTrigger value="analytics" className="shrink-0">
                Analytics
              </TabsTrigger>
              <TabsTrigger value="ai" className="shrink-0">
                AI Generator
              </TabsTrigger>
              {!isCurrentAffairsCreator && (
                <TabsTrigger value="india" className="shrink-0">
                  India Features
                </TabsTrigger>
              )}
            </TabsList>
          </div>

          {/* Breaking News — current affairs primary tab */}
          {isCurrentAffairsCreator && (
            <TabsContent value="breaking-news" className="mt-6">
              <NewsFeedPanel />
            </TabsContent>
          )}

          <TabsContent value="early-detection" className="mt-6">
            <EarlyDetectionPanel />
          </TabsContent>

          <TabsContent value="video-analysis" className="mt-6">
            <VideoAnalysisPanel />
          </TabsContent>

          {/* Regional Festival tab — available to all users */}
          <TabsContent value="festivals" className="mt-6">
            <RegionalFestivalPanel />
          </TabsContent>

          <TabsContent value="analytics" className="mt-6">
            <CreatorAnalyticsDashboard creatorEmail={userEmail} />
          </TabsContent>

          <TabsContent value="ai" className="mt-6">
            <PlanGate feature="AI Content Generator" requiredPlan="pro" currentPlan={userPlan}>
              <AIContentGenerator />
            </PlanGate>
          </TabsContent>

          {!isCurrentAffairsCreator && (
            <TabsContent value="india" className="mt-6">
              <IndiaFeaturesDashboard />
            </TabsContent>
          )}
        </Tabs>
      </div>
    </>
  );
}