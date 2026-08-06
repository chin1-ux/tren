import { createFileRoute } from "@tanstack/react-router";
import { CreatorAnalyticsDashboard } from "@/components/CreatorAnalyticsDashboard";
import { AIContentGenerator } from "@/components/AIContentGenerator";
import { IndiaFeaturesDashboard } from "@/components/IndiaFeaturesDashboard";
import { EarlyDetectionPanel } from "@/components/EarlyDetectionPanel";
import { VideoAnalysisPanel } from "@/components/VideoAnalysisPanel";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { OnboardingTour, useOnboarding } from "@/components/OnboardingTour";

export const Route = createFileRoute("/dashboard")({
  component: Dashboard,
});

function Dashboard() {
  const { isOpen, closeOnboarding } = useOnboarding();

  return (
    <>
      <OnboardingTour open={isOpen} onComplete={closeOnboarding} />
      <div className="container mx-auto py-8 px-4">
        <Tabs defaultValue="early-detection" className="w-full">
          <TabsList className="grid w-full grid-cols-5">
            <TabsTrigger value="early-detection">Early Detection</TabsTrigger>
            <TabsTrigger value="video-analysis">Video Analysis</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="ai">AI Generator</TabsTrigger>
            <TabsTrigger value="india">India Features</TabsTrigger>
          </TabsList>

          <TabsContent value="early-detection" className="mt-6">
            <EarlyDetectionPanel />
          </TabsContent>

          <TabsContent value="video-analysis" className="mt-6">
            <VideoAnalysisPanel />
          </TabsContent>

          <TabsContent value="analytics" className="mt-6">
            <CreatorAnalyticsDashboard creatorEmail="user@example.com" />
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