import React, { useState, useEffect } from "react";
import { X, ChevronRight, ChevronLeft, Sparkles, BarChart3, Globe, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface OnboardingStep {
  id: number;
  title: string;
  description: string;
  icon: React.ReactNode;
  tips: string[];
}

const onboardingSteps: OnboardingStep[] = [
  {
    id: 1,
    title: "Welcome to Your Dashboard",
    description: "Track your creator performance, generate content with AI, and access India-specific trend intelligence.",
    icon: <Sparkles className="h-8 w-8 text-purple-500" />,
    tips: [
      "Navigate between features using the tabs at the top",
      "Each section provides actionable insights for your content",
      "Data updates regularly as trends develop"
    ]
  },
  {
    id: 2,
    title: "Creator Analytics",
    description: "Track your performance metrics, growth trends, and get personalized recommendations.",
    icon: <BarChart3 className="h-8 w-8 text-blue-500" />,
    tips: [
      "Monitor your views, engagement rate, and growth trend",
      "Identify your peak performance hours for optimal posting",
      "View performance charts to understand content patterns",
      "Get personalized recommendations to improve"
    ]
  },
  {
    id: 3,
    title: "AI Content Generator",
    description: "Generate captions, content ideas, hooks, and scripts instantly using AI.",
    icon: <Sparkles className="h-8 w-8 text-pink-500" />,
    tips: [
      "Generate captions with different tones (casual, professional, funny)",
      "Get content ideas tailored to your niche",
      "Create attention-grabbing hooks with retention estimates",
      "Generate script outlines for different content durations"
    ]
  },
  {
    id: 4,
    title: "India-Specific Features",
    description: "Access regional trends, cultural events, and timing optimization for Indian creators.",
    icon: <Globe className="h-8 w-8 text-orange-500" />,
    tips: [
      "View trends specific to your region (North, South, East, West, Central)",
      "Plan content around major cultural events (Diwali, Holi, Eid)",
      "Get optimal posting times for your region",
      "Understand regional language patterns and cultural themes"
    ]
  }
];

interface OnboardingTourProps {
  onComplete: () => void;
  open: boolean;
}

export function OnboardingTour({ onComplete, open }: OnboardingTourProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);

  useEffect(() => {
    // Check if user has completed onboarding
    const hasCompleted = localStorage.getItem("trendrop_onboarding_completed");
    if (hasCompleted) {
      setIsCompleted(true);
    }
  }, []);

  const handleNext = () => {
    if (currentStep < onboardingSteps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = () => {
    localStorage.setItem("trendrop_onboarding_completed", "true");
    setIsCompleted(true);
    onComplete();
  };

  const handleSkip = () => {
    handleComplete();
  };

  if (isCompleted || !open) {
    return null;
  }

  const step = onboardingSteps[currentStep];
  const progress = ((currentStep + 1) / onboardingSteps.length) * 100;

  return (
    <Dialog open={open} onOpenChange={onComplete}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl font-bold">Dashboard Tour</DialogTitle>
            <Button variant="ghost" size="sm" onClick={handleSkip}>
              Skip
            </Button>
          </div>
        </DialogHeader>

        <div className="space-y-6">
          {/* Progress Bar */}
          <div className="w-full bg-muted rounded-full h-2">
            <div
              className="bg-primary h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          {/* Step Content */}
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 p-3 bg-muted rounded-lg">
              {step.icon}
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
              <p className="text-sm text-muted-foreground mb-4">{step.description}</p>

              <div className="space-y-2">
                {step.tips.map((tip, index) => (
                  <div key={index} className="flex items-start gap-2 text-sm">
                    <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 flex-shrink-0" />
                    <span>{tip}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between pt-4 border-t">
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={currentStep === 0}
            >
              <ChevronLeft className="h-4 w-4 mr-2" />
              Previous
            </Button>

            <div className="flex items-center gap-2">
              {onboardingSteps.map((_, index) => (
                <div
                  key={index}
                  className={`h-2 rounded-full transition-all ${
                    index === currentStep
                      ? "w-6 bg-primary"
                      : "w-2 bg-muted"
                  }`}
                />
              ))}
            </div>

            <Button onClick={handleNext}>
              {currentStep === onboardingSteps.length - 1 ? (
                <>
                  Get Started
                  <CheckCircle className="h-4 w-4 ml-2" />
                </>
              ) : (
                <>
                  Next
                  <ChevronRight className="h-4 w-4 ml-2" />
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// Hook to control onboarding — does NOT auto-open.
// Users can start the tour manually via the "Tour" button in the Dashboard.
export function useOnboarding() {
  const [isOpen, setIsOpen] = useState(false);

  const startOnboarding = () => {
    setIsOpen(true);
  };

  const closeOnboarding = () => {
    setIsOpen(false);
    localStorage.setItem("trendrop_onboarding_completed", "true");
  };

  return { isOpen, startOnboarding, closeOnboarding };
}