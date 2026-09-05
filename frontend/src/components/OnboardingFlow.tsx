import { useState, useEffect } from "react";
import { X, CheckCircle, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { subscribe } from "@/lib/api";
import { toast } from "sonner";

const NICHES = [
  { id: "dance",      emoji: "💃", label: "Dance" },
  { id: "fashion",    emoji: "👗", label: "Fashion" },
  { id: "travel",     emoji: "✈️", label: "Travel" },
  { id: "food",       emoji: "🍳", label: "Food" },
  { id: "comedy",     emoji: "😂", label: "Comedy" },
  { id: "motivation", emoji: "💪", label: "Motivation" },
  { id: "devotional", emoji: "🙏", label: "Devotional" },
  { id: "fitness",    emoji: "🏋️", label: "Fitness" },
  { id: "tech",       emoji: "💻", label: "Tech" },
  { id: "narrative_edit", emoji: "🎞️", label: "Creative Edit" },
  { id: "romance_relationship", emoji: "💕", label: "Romance & Relationships" },
  { id: "study",      emoji: "📚", label: "Study" },
  { id: "scenic",     emoji: "🎬", label: "Cinematic" },
];

const LANGUAGES = [
  { code: "hi", emoji: "🇮🇳", label: "Hindi" },
  { code: "kn", emoji: "🎯", label: "Kannada" },
  { code: "ta", emoji: "🌴", label: "Tamil" },
  { code: "te", emoji: "🌟", label: "Telugu" },
  { code: "bn", emoji: "🐯", label: "Bengali" },
  { code: "mr", emoji: "🦁", label: "Marathi" },
  { code: "en", emoji: "🌐", label: "English" },
];

type Step = 1 | 2 | 3 | 4;

interface Props {
  onComplete: () => void;
}

export function OnboardingFlow({ onComplete }: Props) {
  const [step, setStep] = useState<Step>(1);
  const [niche, setNiche] = useState("");
  const [language, setLanguage] = useState("");
  const [followerTier, setFollowerTier] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const [agreeToS, setAgreeToS] = useState(false);
  const [agreeEmails, setAgreeEmails] = useState(true);
  const [nicheSearch, setNicheSearch] = useState("");
  const [langSearch, setLangSearch] = useState("");

  // Pre-fill email from localStorage
  useEffect(() => {
    const saved = localStorage.getItem("trendrop_user_email");
    if (saved) setEmail(saved);
  }, []);

  const persistLocalSetup = () => {
    localStorage.setItem("trendrop_user_email", email);
    localStorage.setItem("trendrop_niche", niche);
    localStorage.setItem("trendrop_language", language);
    localStorage.setItem("trendrop_pref_size", followerTier);
    localStorage.setItem("trendrop_notify_trend_alerts", String(agreeEmails));
    localStorage.setItem("trendrop_notify_daily_ideas", String(agreeEmails));
    localStorage.setItem("trendrop_notify_brand_deals", String(agreeEmails));
  };

  const handleSubmit = async () => {
    if (!email.includes("@") || !agreeToS) return;
    setSubmitting(true);
    persistLocalSetup();
    try {
      const res = await subscribe({ email, niche: niche || "all", language: language || "en" });
      if (res && res.auth_token) {
        localStorage.setItem("trendrop_token", res.auth_token);
      }

      // Log consents in supabase consent_records
      try {
        const { supabase } = await import("../lib/supabase");
        let ip = "127.0.0.1";
        try {
          const ipRes = await fetch("https://api.ipify.org?format=json");
          const ipData = await ipRes.json();
          ip = ipData.ip;
        } catch {}

        await supabase.from("consent_records").insert([
          {
            user_email: email,
            consent_type: "terms_and_privacy",
            granted: true,
            ip_address: ip,
            user_agent: navigator.userAgent
          },
          {
            user_email: email,
            consent_type: "trend_alerts",
            granted: agreeEmails,
            ip_address: ip,
            user_agent: navigator.userAgent
          }
        ]);
      } catch (err) {
        console.error("Failed to log onboarding consents:", err);
      }

      setDone(true);
      setTimeout(onComplete, 1800);
    } catch (err) {
      toast.error("Could not finish account setup. Your local preferences were saved, but the server sync failed.");
      console.error("Onboarding subscribe failed:", err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-lg animate-scale-in rounded-t-3xl bg-[#0e0e1a] border border-border p-6 pb-10 shadow-2xl">
        {/* Close */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex gap-1.5">
            {([1, 2, 3] as const).map((s) => (
              <div
                key={s}
                className={`h-1.5 w-8 rounded-full transition-all ${
                  step >= s ? "bg-primary" : "bg-muted"
                }`}
              />
            ))}
          </div>
          <button onClick={onComplete} aria-label="Close onboarding" title="Close onboarding" className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        {done ? (
          <div className="flex flex-col items-center gap-4 py-8 text-center animate-fade-in-up">
            <CheckCircle className="h-12 w-12 text-success" />
            <h2 className="font-display text-2xl font-bold">You're in! 🎉</h2>
            <p className="text-sm text-muted-foreground">
              We'll alert you the moment a trend matches your vibe.
            </p>
          </div>
        ) : step === 1 ? (
          <div className="space-y-5 animate-fade-in-up">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-primary mb-1">Step 1 of 3</p>
              <h2 className="font-display text-2xl font-bold">Pick your vibe 🎨</h2>
              <p className="mt-1 text-sm text-muted-foreground">What kind of content do you create?</p>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search niches..."
                value={nicheSearch}
                onChange={(e) => setNicheSearch(e.target.value)}
                className="w-full rounded-xl bg-muted/60 py-2.5 pl-9 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              />
            </div>
            <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto no-scrollbar">
              {NICHES.filter(n => (n.label ?? "").toLowerCase().includes(nicheSearch.toLowerCase())).map((n) => (
                <button
                  key={n.id}
                  onClick={() => setNiche(n.id)}
                  className={`flex items-center gap-2.5 rounded-xl p-2.5 transition-all text-left border ${
                    niche === n.id
                      ? "bg-primary/20 border-primary text-primary font-bold"
                      : "bg-muted/50 border-transparent text-muted-foreground hover:border-border"
                  }`}
                >
                  <span className="text-lg">{n.emoji}</span>
                  <span className="text-xs font-semibold leading-tight truncate">{n.label}</span>
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Button onClick={onComplete} variant="ghost" className="flex-1 h-12">Skip</Button>
              <Button
                onClick={() => setStep(2)}
                disabled={!niche}
                className="flex-1 h-12 bg-primary font-bold uppercase tracking-wide"
              >
                Next →
              </Button>
            </div>
          </div>
        ) : step === 2 ? (
          <div className="space-y-5 animate-fade-in-up">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-primary mb-1">Step 2 of 3</p>
              <h2 className="font-display text-2xl font-bold">Your language? 🌍</h2>
              <p className="mt-1 text-sm text-muted-foreground">We'll show you trends in your language first.</p>
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search languages..."
                value={langSearch}
                onChange={(e) => setLangSearch(e.target.value)}
                className="w-full rounded-xl bg-muted/60 py-2.5 pl-9 pr-4 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              />
            </div>
            <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto no-scrollbar">
              {LANGUAGES.filter(l => (l.label ?? "").toLowerCase().includes(langSearch.toLowerCase())).map((l) => (
                <button
                  key={l.code}
                  onClick={() => setLanguage(l.code)}
                  className={`flex items-center gap-2.5 rounded-xl p-2.5 transition-all text-left border ${
                    language === l.code
                      ? "bg-primary/20 border-primary text-primary font-bold"
                      : "bg-muted/50 border-transparent text-muted-foreground hover:border-border"
                  }`}
                >
                  <span className="text-lg">{l.emoji}</span>
                  <span className="text-xs font-semibold leading-tight truncate">{l.label}</span>
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Button onClick={() => setStep(1)} variant="ghost" className="h-12 w-12 px-0">←</Button>
              <Button onClick={onComplete} variant="ghost" className="flex-1 h-12">Skip</Button>
              <Button
                onClick={() => setStep(3)}
                disabled={!language}
                className="flex-1 h-12 bg-primary font-bold uppercase tracking-wide"
              >
                Next →
              </Button>
            </div>
          </div>
        ) : step === 3 ? (
          <div className="space-y-5 animate-fade-in-up">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-primary mb-1">Step 3 of 4</p>
              <h2 className="font-display text-2xl font-bold">Audience size? 📈</h2>
              <p className="mt-1 text-sm text-muted-foreground">Help us calibrate early warning limits for your size.</p>
            </div>
            <div className="flex flex-col gap-3">
              {[
                { id: "micro", label: "🌱 Micro Creator (Under 10K)" },
                { id: "mid", label: "🚀 Rising Creator (10K - 100K)" },
                { id: "mega", label: "👑 Established Creator (100K+)" },
              ].map((tier) => (
                <button
                  key={tier.id}
                  onClick={() => setFollowerTier(tier.id)}
                  className={`w-full rounded-xl p-4 transition-all text-left border ${
                    followerTier === tier.id
                      ? "bg-primary/20 border-primary text-primary font-bold"
                      : "bg-muted/50 border-transparent text-muted-foreground hover:border-border"
                  }`}
                >
                  <span className="text-sm font-semibold leading-tight">{tier.label}</span>
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Button onClick={() => setStep(2)} variant="ghost" className="h-12 w-12 px-0">←</Button>
              <Button onClick={onComplete} variant="ghost" className="flex-1 h-12">Skip</Button>
              <Button
                onClick={() => setStep(4)}
                disabled={!followerTier}
                className="flex-1 h-12 bg-primary font-bold uppercase tracking-wide"
              >
                Next →
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-5 animate-fade-in-up">
            <div>
              <p className="text-xs font-bold uppercase tracking-widest text-primary mb-1">Step 4 of 4</p>
              <h2 className="font-display text-2xl font-bold">Get early alerts ⚡</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                We'll email you the moment a trend hits your niche — before anyone else.
              </p>
            </div>
            <div className="rounded-xl bg-primary/5 border border-primary/20 p-4">
              <p className="text-xs text-muted-foreground mb-1 font-semibold">Your preferences</p>
              <p className="text-sm">
                <span className="text-primary font-bold">{NICHES.find(n => n.id === niche)?.emoji} {NICHES.find(n => n.id === niche)?.label}</span>
                {" "}•{" "}
                <span className="text-primary font-bold">{LANGUAGES.find(l => l.code === language)?.emoji} {LANGUAGES.find(l => l.code === language)?.label}</span>
                {" "}•{" "}
                <span className="text-primary font-bold">
                  {followerTier === "micro" ? "🌱 Micro" : followerTier === "mid" ? "🚀 Rising" : "👑 Established"}
                </span>
              </p>
            </div>
            <input
              id="onboarding-email"
              name="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="w-full rounded-xl bg-muted/60 px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
            
            {/* DPDP Compliance Consent Checkboxes */}
            <div className="space-y-3 pt-2">
              <label className="flex items-start gap-2.5 cursor-pointer select-none">
                <input
                  id="onboarding-agree-tos"
                  name="agreeToS"
                  type="checkbox"
                  checked={agreeToS}
                  onChange={(e) => setAgreeToS(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-muted-foreground/30 bg-muted/60 text-primary focus:ring-primary/50 cursor-pointer"
                />
                <span className="text-xs text-muted-foreground leading-tight">
                  I agree to the <a href="/terms" target="_blank" rel="noopener noreferrer" className="underline text-foreground hover:text-primary">Terms of Service</a> and <a href="/privacy" target="_blank" rel="noopener noreferrer" className="underline text-foreground hover:text-primary">Privacy Policy</a> (Required)
                </span>
              </label>

              <label className="flex items-start gap-2.5 cursor-pointer select-none">
                <input
                  id="onboarding-agree-emails"
                  name="agreeEmails"
                  type="checkbox"
                  checked={agreeEmails}
                  onChange={(e) => setAgreeEmails(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-muted-foreground/30 bg-muted/60 text-primary focus:ring-primary/50 cursor-pointer"
                />
                <span className="text-xs text-muted-foreground leading-tight">
                  I consent to receive real-time email alerts and daily trend ideas from Trendrop.
                </span>
              </label>
            </div>

            <div className="flex gap-2">
              <Button onClick={() => setStep(3)} variant="ghost" className="flex-1 h-12">← Back</Button>
              <Button
                onClick={handleSubmit}
                disabled={submitting || !email.includes("@") || !agreeToS}
                className="flex-1 h-12 bg-primary font-bold uppercase tracking-wide"
              >
                {submitting ? "Setting up..." : "Start Dropping 🔥"}
              </Button>
            </div>
            <button onClick={onComplete} className="w-full text-center text-xs text-muted-foreground hover:text-foreground">
              Skip for now
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
