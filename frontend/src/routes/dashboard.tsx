import { createFileRoute } from "@tanstack/react-router";
import { CreatorAnalyticsDashboard } from "@/components/CreatorAnalyticsDashboard";
import { AIContentGenerator } from "@/components/AIContentGenerator";
import { IndiaFeaturesDashboard } from "@/components/IndiaFeaturesDashboard";
import { EarlyDetectionPanel } from "@/components/EarlyDetectionPanel";
import { VideoAnalysisPanel } from "@/components/VideoAnalysisPanel";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OnboardingTour, useOnboarding } from "@/components/OnboardingTour";
import { Button } from "@/components/ui/button";
import { HelpCircle } from "lucide-react";

import { RouteErrorBoundary } from "@/components/RouteErrorBoundary";
import { useUserStore } from "@/store/useAppStore";

export const Route = createFileRoute("/dashboard")({
  component: Dashboard,
  errorComponent: RouteErrorBoundary,
});

function Dashboard() {
  const { isOpen, startOnboarding, closeOnboarding } = useOnboarding();
  const userEmail = useUserStore((s) => s.email) ?? "";

  return (
    <>
      <OnboardingTour open={isOpen} onComplete={closeOnboarding} />
      <div className="container mx-auto py-8 px-4">
        <div className="flex items-center justify-between mb-4">
          <div />
          <Button variant="ghost" size="sm" onClick={startOnboarding} className="gap-1.5 text-muted-foreground">
            <HelpCircle className="h-4 w-4" />
            Tour
          </Button>
        </div>
        <Tabs defaultValue="early-detection" className="w-full">
          <div className="w-full overflow-x-auto no-scrollbar py-1 -mx-4 px-4">
            <TabsList className="flex w-max min-w-full justify-start md:justify-center p-1 h-11 gap-1.5 bg-muted/60 rounded-xl">
              <TabsTrigger value="early-detection" className="shrink-0">Early Detection</TabsTrigger>
              <TabsTrigger value="video-analysis" className="shrink-0">Video Analysis</TabsTrigger>
              <TabsTrigger value="analytics" className="shrink-0">Analytics</TabsTrigger>
              <TabsTrigger value="ai" className="shrink-0">AI Generator</TabsTrigger>
              <TabsTrigger value="india" className="shrink-0">India Features</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="early-detection" className="mt-6">
            <EarlyDetectionPanel />
          </TabsContent>

          <TabsContent value="video-analysis" className="mt-6">
            <VideoAnalysisPanel />
          </TabsContent>

          <TabsContent value="analytics" className="mt-6">
            <CreatorAnalyticsDashboard creatorEmail={userEmail} />
          </TabsContent>

          <TabsContent value="ai" className="mt-6">
            <AIContentGenerator />
          </TabsContent>

          <TabsContent value="india" className="mt-6">
            <IndiaFeaturesDashboard />
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}