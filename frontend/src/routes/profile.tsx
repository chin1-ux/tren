import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Check, User, Bell, Flame, Globe, Heart, Smartphone,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { subscribe } from "@/lib/api";
import { toast } from "sonner";

export const Route = createFileRoute("/profile")({
  head: () => ({
    meta: [
      { title: "Profile — Trendrop" },
      { name: "description", content: "Personalize your trend feed and alert preferences." },
    ],
  }),
  component: ProfilePage,
});

const NICHES = [
  { id: "dance",      emoji: "💃", label: "Dance" },
  { id: "fashion",    emoji: "👗", label: "Fashion" },
  { id: "travel",     emoji: "✈️", label: "Travel" },
  { id: "food",       emoji: "🍳", label: "Food" },
  { id: "comedy",     emoji: "😂", label: "Comedy" },
  { id: "motivation", emoji: "💪", label: "Motivation" },
  { id: "devotional", emoji: "🙏", label: "Devotional" },
  { id: "fitness",    emoji: "🏋️", label: "Fitness" },
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

function ProfilePage() {
  const [email, setEmail] = useState("");
  const [niche, setNiche] = useState("dance");
  const [language, setLanguage] = useState("hi");
  const [platform, setPlatform] = useState("instagram");
  const [alertEnabled, setAlertEnabled] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const e = localStorage.getItem("trendrop_email");
    const n = localStorage.getItem("trendrop_niche");
    const l = localStorage.getItem("trendrop_language");
    const p = localStorage.getItem("trendrop_platform");
    if (e) setEmail(e);
    if (n) setNiche(n);
    if (l) setLanguage(l);
    if (p) setPlatform(p);
  }, []);

  const save = async () => {
    if (!email.includes("@")) {
      toast.error("Please enter a valid email");
      return;
    }
    setSaving(true);
    try {
      const res = await subscribe({ email, niche, language });
      if (res && res.auth_token) {
        localStorage.setItem("trendrop_token", res.auth_token);
      }
      localStorage.setItem("trendrop_email", email);
      localStorage.setItem("trendrop_niche", niche);
      localStorage.setItem("trendrop_language", language);
      localStorage.setItem("trendrop_platform", platform);
      toast.success("Preferences saved! You'll get alerts for your niche.");
    } catch {
      // Still save locally
      localStorage.setItem("trendrop_email", email);
      localStorage.setItem("trendrop_niche", niche);
      localStorage.setItem("trendrop_language", language);
      localStorage.setItem("trendrop_platform", platform);
      toast.success("Saved locally!");
    } finally {
      setSaving(false);
    }
  };

  const generatedCount = parseInt(localStorage.getItem("trendrop_generated_count") || "0");
  const selectedNiche = NICHES.find(n => n.id === niche);
  const selectedLang = LANGUAGES.find(l => l.code === language);

  return (
    <div className="flex flex-col gap-5 px-4 pb-10 pt-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-white text-2xl shadow-lg shadow-primary/20">
          {selectedNiche?.emoji || "🎯"}
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold gradient-text">Your Profile</h1>
          <p className="text-sm text-muted-foreground">Personalize your trend intelligence</p>
        </div>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-2">
        <StatCard icon={<Flame className="h-4 w-4 text-primary" />} label="Reels Made" value={generatedCount.toString()} />
        <StatCard icon={<Globe className="h-4 w-4 text-secondary" />} label="Language" value={selectedLang?.emoji || "🌐"} />
        <StatCard icon={<Heart className="h-4 w-4 text-[#ff006e]" />} label="Niche" value={selectedNiche?.emoji || "🎯"} />
      </div>

      {/* Email */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-base font-bold flex items-center gap-2">
          <Bell className="h-4 w-4 text-primary" /> Alert Email
        </h2>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="your@email.com"
          className="w-full rounded-xl bg-muted/60 px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
        />
        <div className="flex items-center justify-between rounded-xl bg-muted/40 px-4 py-3">
          <div>
            <p className="text-sm font-semibold">Trend Alerts</p>
            <p className="text-xs text-muted-foreground">Get notified when new trends match your vibe</p>
          </div>
          <button
            onClick={() => setAlertEnabled(!alertEnabled)}
            className={`relative h-6 w-11 rounded-full transition-colors ${alertEnabled ? "bg-primary" : "bg-muted"}`}
          >
            <div className={`absolute top-1 h-4 w-4 rounded-full bg-white shadow transition-all ${alertEnabled ? "left-6" : "left-1"}`} />
          </button>
        </div>
      </div>

      {/* Niche picker */}
      <div className="glass-card p-5 space-y-3">
        <h2 className="font-display text-base font-bold flex items-center gap-2">
          <Heart className="h-4 w-4 text-[#ff006e]" /> Your Content Niche
        </h2>
        <div className="grid grid-cols-5 gap-2">
          {NICHES.map((n) => (
            <button
              key={n.id}
              onClick={() => setNiche(n.id)}
              className={`flex flex-col items-center gap-1 rounded-xl p-2.5 text-center transition-all ${
                niche === n.id
                  ? "bg-primary/20 border border-primary text-primary"
                  : "bg-muted/50 border border-transparent text-muted-foreground hover:border-border"
              }`}
            >
              <span className="text-xl">{n.emoji}</span>
              <span className="text-[10px] font-semibold leading-tight">{n.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Language picker */}
      <div className="glass-card p-5 space-y-3">
        <h2 className="font-display text-base font-bold flex items-center gap-2">
          <Globe className="h-4 w-4 text-secondary" /> Preferred Language
        </h2>
        <div className="grid grid-cols-4 gap-2">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              onClick={() => setLanguage(l.code)}
              className={`flex flex-col items-center gap-1 rounded-xl p-3 text-center transition-all ${
                language === l.code
                  ? "bg-primary/20 border border-primary text-primary"
                  : "bg-muted/50 border border-transparent text-muted-foreground hover:border-border"
              }`}
            >
              <span className="text-xl">{l.emoji}</span>
              <span className="text-[10px] font-semibold">{l.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Platform preference */}
      <div className="glass-card p-5 space-y-3">
        <h2 className="font-display text-base font-bold flex items-center gap-2">
          <Smartphone className="h-4 w-4 text-secondary" /> Platform First
        </h2>
        <div className="grid grid-cols-2 gap-2">
          {[
            { id: "instagram", emoji: "◎", label: "Instagram" },
            { id: "youtube_shorts", emoji: "▶", label: "YT Shorts" },
          ].map((p) => (
            <button
              key={p.id}
              onClick={() => setPlatform(p.id)}
              className={`flex flex-col items-center gap-1.5 rounded-xl border py-4 text-center transition-all ${
                platform === p.id
                  ? "border-primary bg-primary/20 text-primary shadow-sm"
                  : "border-border bg-muted/40 hover:border-primary/40 text-foreground"
              }`}
            >
              <span className="text-2xl">{p.emoji}</span>
              <span className="text-xs font-semibold">{p.label}</span>
            </button>
          ))}
        </div>
      </div>

      <Button
        onClick={save}
        disabled={saving}
        className="h-12 w-full bg-primary font-bold uppercase tracking-widest shadow-lg shadow-primary/20"
      >
        {saving ? "Saving..." : "Save Preferences ✓"}
      </Button>

      <p className="text-center text-xs text-muted-foreground">
        Trendrop — India-first trend intelligence for creators 🇮🇳
      </p>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="glass-card p-3 text-center space-y-1">
      <div className="flex justify-center">{icon}</div>
      <p className="text-lg font-bold">{value}</p>
      <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</p>
    </div>
  );
}
