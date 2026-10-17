import { useState } from "react";
import { X, CheckCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

const NICHES = [
  { id: "fitness",  emoji: "💪", label: "Fitness" },
  { id: "food",     emoji: "🍜", label: "Food" },
  { id: "comedy",   emoji: "😂", label: "Comedy" },
  { id: "fashion",  emoji: "👗", label: "Fashion" },
  { id: "travel",   emoji: "✈️", label: "Travel" },
  { id: "beauty",   emoji: "💄", label: "Beauty" },
  { id: "tech",     emoji: "💻", label: "Tech" },
  { id: "dance",    emoji: "💃", label: "Dance" },
  { id: "business", emoji: "💼", label: "Business" },
  { id: "all",      emoji: "🌟", label: "All Niches" },
];

const LANGUAGES = [
  { code: "all",    emoji: "🌐", label: "All Languages" },
  { code: "hi",     emoji: "🇮🇳", label: "Hindi" },
  { code: "pa",     emoji: "🎺", label: "Punjabi" },
  { code: "ta",     emoji: "🌴", label: "Tamil" },
  { code: "te",     emoji: "🌟", label: "Telugu" },
  { code: "en",     emoji: "🇺🇸", label: "English / Western" },
  { code: "pt",     emoji: "🇧🇷", label: "Brazilian / Phonk" },
  { code: "ko",     emoji: "🇰🇷", label: "Korean" },
  { code: "ru",     emoji: "🇷🇺", label: "Russian" },
  { code: "es",     emoji: "🇪🇸", label: "Spanish / Latin" },
];

interface Props {
  onComplete: () => void;
}

export function OnboardingFlow({ onComplete }: Props) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [niche, setNiche] = useState<string>("all");
  const [language, setLanguage] = useState<string>("all");

  const handleFinish = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("trendrop_pref_niche", niche);
      localStorage.setItem("trendrop_pref_niches", JSON.stringify([niche]));
      localStorage.setItem("trendrop_pref_language", language);
      localStorage.setItem("trendrop_onboarded", "true");
    }
    onComplete();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
      <div className="relative w-full max-w-md rounded-2xl border border-border/60 bg-card p-6 shadow-2xl animate-in fade-in-50 zoom-in-95">
        <button
          onClick={handleFinish}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground p-1"
          aria-label="Skip onboarding"
        >
          <X className="h-5 w-5" />
        </button>

        {step === 1 && (
          <div className="space-y-4">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-primary">Step 1 of 3</p>
              <h2 className="text-xl font-extrabold text-foreground mt-0.5">Pick Your Creator Niche</h2>
              <p className="text-xs text-muted-foreground mt-1">We tailor trend detection to what your audience creates.</p>
            </div>

            <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto no-scrollbar pt-1">
              {NICHES.map((n) => {
                const isSelected = niche === n.id;
                return (
                  <button
                    key={n.id}
                    onClick={() => setNiche(n.id)}
                    className={`flex items-center gap-2 rounded-xl p-3 text-left text-xs font-semibold border transition-all ${
                      isSelected
                        ? "border-primary bg-primary/15 text-primary ring-1 ring-primary/40 font-bold"
                        : "border-border/50 bg-muted/40 text-foreground hover:bg-muted/70"
                    }`}
                  >
                    <span className="text-lg">{n.emoji}</span>
                    <span className="truncate">{n.label}</span>
                  </button>
                );
              })}
            </div>

            <Button
              onClick={() => setStep(2)}
              className="w-full h-11 bg-primary text-white font-bold rounded-xl mt-2"
            >
              Next: Choose Language →
            </Button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-primary">Step 2 of 3</p>
              <h2 className="text-xl font-extrabold text-foreground mt-0.5">Pick Audio Language</h2>
              <p className="text-xs text-muted-foreground mt-1">Filter sounds by language to match your regional target.</p>
            </div>

            <div className="grid grid-cols-2 gap-2 max-h-64 overflow-y-auto no-scrollbar pt-1">
              {LANGUAGES.map((l) => {
                const isSelected = language === l.code;
                return (
                  <button
                    key={l.code}
                    onClick={() => setLanguage(l.code)}
                    className={`flex items-center gap-2 rounded-xl p-3 text-left text-xs font-semibold border transition-all ${
                      isSelected
                        ? "border-primary bg-primary/15 text-primary ring-1 ring-primary/40 font-bold"
                        : "border-border/50 bg-muted/40 text-foreground hover:bg-muted/70"
                    }`}
                  >
                    <span className="text-lg">{l.emoji}</span>
                    <span className="truncate">{l.label}</span>
                  </button>
                );
              })}
            </div>

            <div className="flex gap-2 pt-2">
              <Button
                variant="outline"
                onClick={() => setStep(1)}
                className="flex-1 h-11 rounded-xl"
              >
                ← Back
              </Button>
              <Button
                onClick={() => setStep(3)}
                className="flex-1 h-11 bg-primary text-white font-bold rounded-xl"
              >
                Review & See 5 →
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-5 text-center py-2">
            <div className="mx-auto w-12 h-12 rounded-full bg-primary/15 border border-primary/30 flex items-center justify-center text-primary">
              <Sparkles className="h-6 w-6" />
            </div>

            <div>
              <p className="text-[11px] font-bold uppercase tracking-wider text-primary">Step 3 of 3</p>
              <h2 className="text-xl font-black text-foreground mt-1">Ready to Discover Trends</h2>
              <p className="text-xs text-muted-foreground mt-1">
                Viewing top viral audios for{" "}
                <strong className="text-foreground">{NICHES.find((n) => n.id === niche)?.label}</strong> in{" "}
                <strong className="text-foreground">{LANGUAGES.find((l) => l.code === language)?.label}</strong>.
              </p>
            </div>

            <Button
              id="onboarding-see-5-btn"
              onClick={handleFinish}
              className="w-full h-12 bg-primary text-white text-sm font-extrabold rounded-xl shadow-lg shadow-primary/25 hover:bg-primary/90 transition-all cursor-pointer"
            >
              Explore 2,000+ Viral Trends 🔥
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
