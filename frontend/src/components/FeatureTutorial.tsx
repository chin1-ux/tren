import { useState } from "react";
import { X, ChevronRight, ChevronLeft, Sparkles, TrendingUp, Compass, Lightbulb, PlayCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FeatureTutorialProps {
  onClose: () => void;
}

const STEPS = [
  {
    title: "Welcome to Trendrop! 🚀",
    description: "India's first AI-powered short-form trend intelligence platform. Let's take a quick 1-minute tour of your creator dashboard.",
    icon: <Sparkles className="h-10 w-10 text-primary" />,
  },
  {
    title: "Real-Time Trends Feed 📈",
    description: "The 'Rising' tab shows trending audios gaining speed in India, while the 'Emerging' tab spots trends early in their lifecycle. Save the audio and start creating before it saturates!",
    icon: <TrendingUp className="h-10 w-10 text-emerald-400" />,
  },
  {
    title: "AI Video Generation 🎬",
    description: "Upload your photos/videos in the 'Generate' tab, select a trending audio, and let our AI engine compile high-velocity vertical reels for you instantly.",
    icon: <PlayCircle className="h-10 w-10 text-primary" />,
  },
  {
    title: "Ideation & Script Scoring 💡",
    description: "Head to the 'Ideas' tab for custom-tailored daily hooks and posting schedules, or use our Pre-Post Reel Scorer to forecast your script performance.",
    icon: <Lightbulb className="h-10 w-10 text-amber-400" />,
  },
  {
    title: "Creator Marketplace 🤝",
    description: "Explore exclusive brand campaigns with verified creator payouts, or find nearby co-creators in your niche with high compatibility scores to double your reach.",
    icon: <Compass className="h-10 w-10 text-primary" />,
  },
];

export function FeatureTutorial({ onClose }: FeatureTutorialProps) {
  const [currentStep, setCurrentStep] = useState(0);

  const handleNext = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = () => {
    localStorage.setItem("trendrop_tutorial_done", "1");
    onClose();
  };

  const stepInfo = STEPS[currentStep];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-in fade-in duration-300">
      <div className="w-full max-w-md overflow-hidden rounded-3xl border border-border bg-[#0e0e1a] p-6 shadow-2xl space-y-6 relative">
        {/* Skip button top right */}
        <button
          onClick={handleComplete}
          className="absolute right-4 top-4 rounded-full p-1.5 text-muted-foreground hover:bg-white/5 hover:text-foreground transition-colors"
          aria-label="Skip Tutorial"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Step Icon */}
        <div className="flex justify-center pt-4">
          <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-white/5 border border-white/10 shadow-inner">
            {stepInfo.icon}
          </div>
        </div>

        {/* Content */}
        <div className="text-center space-y-2.5 px-2">
          <h2 className="font-display text-xl font-bold tracking-tight text-white">
            {stepInfo.title}
          </h2>
          <p className="text-xs text-[#888888] leading-relaxed">
            {stepInfo.description}
          </p>
        </div>

        {/* Progress indicators */}
        <div className="flex justify-center gap-1.5 py-1">
          {STEPS.map((_, idx) => (
            <div
              key={idx}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                idx === currentStep ? "w-8 bg-primary" : "w-1.5 bg-white/10"
              }`}
            />
          ))}
        </div>

        {/* Controls */}
        <div className="flex gap-3 pt-2">
          {currentStep > 0 ? (
            <Button
              onClick={handleBack}
              variant="outline"
              className="flex-1 h-11 border-white/10 text-xs font-bold uppercase tracking-wider rounded-xl text-white hover:bg-white/5"
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Back
            </Button>
          ) : (
            <Button
              onClick={handleComplete}
              variant="ghost"
              className="flex-1 h-11 text-xs font-bold uppercase tracking-wider rounded-xl text-muted-foreground hover:text-white"
            >
              Skip
            </Button>
          )}

          <Button
            onClick={handleNext}
            className="flex-1 h-11 bg-gradient-to-r from-primary to-purple-600 hover:from-primary hover:to-purple-500 text-white font-bold text-xs uppercase tracking-wider rounded-xl shadow-lg shadow-primary/20"
          >
            {currentStep === STEPS.length - 1 ? "Get Started 🔥" : "Next"}
            {currentStep < STEPS.length - 1 && <ChevronRight className="h-4 w-4 ml-1" />}
          </Button>
        </div>
      </div>
    </div>
  );
}
