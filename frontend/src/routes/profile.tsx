import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Check, User, Bell, Flame, Globe, Heart, Smartphone,
  Instagram, Users, Mail, Calendar, Award, Sparkles, ShieldCheck,
  Search, ChevronRight, SlidersHorizontal
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { subscribe } from "@/lib/api";
import { toast } from "sonner";
import { ThemeToggle } from "@/components/ThemeToggle";

export const Route = createFileRoute("/profile")({
  head: () => ({
    meta: [
      { title: "Profile — Trendrop" },
      { name: "description", content: "Personalize your trend feed, creator info, and alert preferences." },
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

const FREQUENCIES = [
  { id: "daily", label: "Daily" },
  { id: "few_times_week", label: "3x a Week" },
  { id: "weekly", label: "Weekly" },
];

function ProfilePage() {
  const [email, setEmail] = useState("");
  const [instagramHandle, setInstagramHandle] = useState("");
  const [followers, setFollowers] = useState("");
  
  const [niche, setNiche] = useState("dance");
  const [language, setLanguage] = useState("hi");
  const [postingFrequency, setPostingFrequency] = useState("daily");

  const [notifyTrendAlerts, setNotifyTrendAlerts] = useState(true);
  const [notifyDailyIdeas, setNotifyDailyIdeas] = useState(true);
  const [notifyBrandDeals, setNotifyBrandDeals] = useState(true);
  const [notifyWeeklyReport, setNotifyWeeklyReport] = useState(true);

  const [plan, setPlan] = useState("Free Trial");

  const [saving, setSaving] = useState(false);
  const [upgrading, setUpgrading] = useState(false);

  const [langSearch, setLangSearch] = useState("");
  const [nicheSearch, setNicheSearch] = useState("");
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  const [showNicheDropdown, setShowNicheDropdown] = useState(false);

  useEffect(() => {
    const sync = () => {
      const e = localStorage.getItem("trendrop_email");
      const ig = localStorage.getItem("trendrop_instagram_handle");
      const f = localStorage.getItem("trendrop_followers");
      const n = localStorage.getItem("trendrop_niche");
      const l = localStorage.getItem("trendrop_language");
      const freq = localStorage.getItem("trendrop_posting_frequency");
      const p = localStorage.getItem("trendrop_plan");

      const nt = localStorage.getItem("trendrop_notify_trend_alerts");
      const nd = localStorage.getItem("trendrop_notify_daily_ideas");
      const nb = localStorage.getItem("trendrop_notify_brand_deals");
      const nw = localStorage.getItem("trendrop_notify_weekly_report");

      if (e) setEmail(e);
      if (ig) setInstagramHandle(ig);
      if (f) setFollowers(f);
      if (n) setNiche(n);
      if (l) setLanguage(l);
      if (freq) setPostingFrequency(freq);
      if (p) setPlan(p);

      if (nt !== null) setNotifyTrendAlerts(nt === "true");
      if (nd !== null) setNotifyDailyIdeas(nd === "true");
      if (nb !== null) setNotifyBrandDeals(nb === "true");
      if (nw !== null) setNotifyWeeklyReport(nw === "true");
    };

    sync();
    window.addEventListener("storage", sync);
    window.addEventListener("focus", sync);
    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("focus", sync);
    };
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
      localStorage.setItem("trendrop_instagram_handle", instagramHandle);
      localStorage.setItem("trendrop_followers", followers);
      localStorage.setItem("trendrop_niche", niche);
      localStorage.setItem("trendrop_language", language);
      localStorage.setItem("trendrop_posting_frequency", postingFrequency);
      localStorage.setItem("trendrop_notify_trend_alerts", String(notifyTrendAlerts));
      localStorage.setItem("trendrop_notify_daily_ideas", String(notifyDailyIdeas));
      localStorage.setItem("trendrop_notify_brand_deals", String(notifyBrandDeals));
      localStorage.setItem("trendrop_notify_weekly_report", String(notifyWeeklyReport));
      localStorage.setItem("trendrop_plan", plan);
      
      toast.success("Profile saved successfully! ✓");
    } catch {
      localStorage.setItem("trendrop_email", email);
      localStorage.setItem("trendrop_instagram_handle", instagramHandle);
      localStorage.setItem("trendrop_followers", followers);
      localStorage.setItem("trendrop_niche", niche);
      localStorage.setItem("trendrop_language", language);
      localStorage.setItem("trendrop_posting_frequency", postingFrequency);
      localStorage.setItem("trendrop_notify_trend_alerts", String(notifyTrendAlerts));
      localStorage.setItem("trendrop_notify_daily_ideas", String(notifyDailyIdeas));
      localStorage.setItem("trendrop_notify_brand_deals", String(notifyBrandDeals));
      localStorage.setItem("trendrop_notify_weekly_report", String(notifyWeeklyReport));
      localStorage.setItem("trendrop_plan", plan);
      
      toast.success("Saved locally!");
    } finally {
      setSaving(false);
    }
  };

  const handleUpgrade = async () => {
    const activeEmail = email || "creator@trendrop.app";
    setUpgrading(true);
    try {
      const res = await subscribe({ email: activeEmail, niche, language });
      if (res && res.auth_token) {
        localStorage.setItem("trendrop_token", res.auth_token);
      }
      setPlan("Pro Creator");
      localStorage.setItem("trendrop_plan", "Pro Creator");
      toast.success("Successfully upgraded to Pro Creator! 🚀");
    } catch {
      setPlan("Pro Creator");
      localStorage.setItem("trendrop_plan", "Pro Creator");
      toast.success("Upgraded to Pro Creator locally!");
    } finally {
      setUpgrading(false);
    }
  };

  const selectedNiche = NICHES.find(n => n.id === niche);

  return (
    <div className="flex flex-col gap-5 px-4 pb-12 pt-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="font-display text-2xl font-bold gradient-text">Your Profile</h1>
            <p className="text-sm text-muted-foreground">Configure your trend preferences and alerts</p>
          </div>
        </div>
        <ThemeToggle />
      </div>

      {/* Creator Info Section */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-base font-bold flex items-center gap-2 text-foreground">
          <User className="h-5 w-5 text-primary" /> Creator Info
        </h2>
        
        <div className="space-y-3">
          <div>
            <label className="text-xs font-semibold text-muted-foreground block mb-1">Instagram Handle</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground text-sm font-semibold">@</span>
              <input
                id="profile-instagram-handle"
                name="instagramHandle"
                type="text"
                value={instagramHandle}
                onChange={(e) => setInstagramHandle(e.target.value.replace(/^@/, ""))}
                placeholder="your.handle"
                className="w-full rounded-xl bg-muted/60 pl-8 pr-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 border border-transparent focus:border-primary/30"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">Followers</label>
              <div className="relative">
                <Users className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  id="profile-followers"
                  name="followers"
                  type="text"
                  value={followers}
                  onChange={(e) => setFollowers(e.target.value)}
                  placeholder="e.g. 25K"
                  className="w-full rounded-xl bg-muted/60 pl-10 pr-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 border border-transparent focus:border-primary/30"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  id="profile-email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@domain.com"
                  className="w-full rounded-xl bg-muted/60 pl-10 pr-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 border border-transparent focus:border-primary/30"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content Preferences Section */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-base font-bold flex items-center gap-2 text-foreground">
          <Sparkles className="h-5 w-5 text-secondary" /> Content Preferences
        </h2>

        {/* Niche selector */}
        <div className="space-y-1.5 relative">
          <label className="text-xs font-semibold text-muted-foreground block">Select Your Niche</label>
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowNicheDropdown(!showNicheDropdown)}
              className="w-full rounded-xl bg-muted/60 border border-transparent px-3.5 py-2.5 text-left text-xs font-medium text-foreground flex items-center justify-between hover:bg-muted/80 transition-colors"
            >
              <span>{selectedNiche ? `${selectedNiche.emoji} ${selectedNiche.label}` : "Select Niche"}</span>
              <ChevronRight className={`h-4 w-4 text-muted-foreground transform transition-transform ${showNicheDropdown ? "rotate-90" : ""}`} />
            </button>

            {showNicheDropdown && (
              <div className="absolute left-0 right-0 z-30 mt-1.5 rounded-xl border border-border bg-surface shadow-xl p-2.5 space-y-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="text"
                    value={nicheSearch}
                    onChange={(e) => setNicheSearch(e.target.value)}
                    placeholder="Search niches..."
                    className="w-full rounded-lg bg-muted/60 py-1.5 pl-8 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none"
                  />
                </div>
                <div className="max-h-40 overflow-y-auto space-y-1">
                  {NICHES.filter(n => n.label.toLowerCase().includes(nicheSearch.toLowerCase())).map(n => (
                    <button
                      key={n.id}
                      onClick={() => { setNiche(n.id); setShowNicheDropdown(false); }}
                      className="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-muted transition-colors flex items-center justify-between"
                    >
                      <span>{n.emoji} {n.label}</span>
                      {niche === n.id && <Check className="h-3.5 w-3.5 text-primary" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Language selector */}
        <div className="space-y-1.5 relative">
          <label className="text-xs font-semibold text-muted-foreground block">Select Language</label>
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowLangDropdown(!showLangDropdown)}
              className="w-full rounded-xl bg-muted/60 border border-transparent px-3.5 py-2.5 text-left text-xs font-medium text-foreground flex items-center justify-between hover:bg-muted/80 transition-colors"
            >
              <span>{language ? `${LANGUAGES.find(l => l.code === language)?.emoji || ""} ${LANGUAGES.find(l => l.code === language)?.label || ""}` : "Select Language"}</span>
              <ChevronRight className={`h-4 w-4 text-muted-foreground transform transition-transform ${showLangDropdown ? "rotate-90" : ""}`} />
            </button>

            {showLangDropdown && (
              <div className="absolute left-0 right-0 z-30 mt-1.5 rounded-xl border border-border bg-surface shadow-xl p-2.5 space-y-2">
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                  <input
                    type="text"
                    value={langSearch}
                    onChange={(e) => setLangSearch(e.target.value)}
                    placeholder="Search languages..."
                    className="w-full rounded-lg bg-muted/60 py-1.5 pl-8 pr-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none"
                  />
                </div>
                <div className="max-h-40 overflow-y-auto space-y-1">
                  {LANGUAGES.filter(l => l.label.toLowerCase().includes(langSearch.toLowerCase())).map(l => (
                    <button
                      key={l.code}
                      onClick={() => { setLanguage(l.code); setShowLangDropdown(false); }}
                      className="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-muted transition-colors flex items-center justify-between"
                    >
                      <span>{l.emoji} {l.label}</span>
                      {language === l.code && <Check className="h-3.5 w-3.5 text-primary" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Posting Frequency */}
        <div className="space-y-2">
          <span className="text-xs font-semibold text-muted-foreground block">Posting Frequency</span>
          <div className="grid grid-cols-3 gap-2">
            {FREQUENCIES.map((freq) => (
              <button
                key={freq.id}
                onClick={() => setPostingFrequency(freq.id)}
                className={`flex items-center justify-center gap-1.5 rounded-xl py-2.5 px-3 text-center transition-all border ${
                  postingFrequency === freq.id
                    ? "bg-secondary/20 border-secondary text-secondary font-bold"
                    : "bg-muted/30 border-transparent text-muted-foreground hover:border-border hover:bg-muted/50"
                }`}
              >
                <Calendar className="h-3.5 w-3.5" />
                <span className="text-[11px] font-semibold">{freq.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications Section */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-base font-bold flex items-center gap-2 text-foreground">
          <Bell className="h-5 w-5 text-amber" /> Notification Alerts
        </h2>

        <div className="space-y-3">
          <NotificationToggle
            title="Trend Alerts"
            description="Real-time alerts when new audio formats match your profile"
            active={notifyTrendAlerts}
            onChange={setNotifyTrendAlerts}
          />
          <NotificationToggle
            title="Daily Ideas"
            description="Fresh customized hooks and audio suggestions every morning"
            active={notifyDailyIdeas}
            onChange={setNotifyDailyIdeas}
          />
          <NotificationToggle
            title="Brand Deals"
            description="Get notified about high-matching campaigns & opportunities"
            active={notifyBrandDeals}
            onChange={setNotifyBrandDeals}
          />
          <NotificationToggle
            title="Weekly Report"
            description="Digest of viral formats, niches growing fastest in India"
            active={notifyWeeklyReport}
            onChange={setNotifyWeeklyReport}
          />
        </div>
      </div>

      {/* Plan Card */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-card to-muted/30 p-5 shadow-xl">
        <div className="absolute right-0 top-0 h-28 w-28 rounded-full bg-primary/10 blur-2xl" />
        <div className="absolute left-0 bottom-0 h-28 w-28 rounded-full bg-secondary/10 blur-2xl" />
        
        <div className="flex items-start justify-between">
          <div>
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary border border-primary/20">
              <Award className="h-3 w-3" /> Current Tier
            </span>
            <h3 className="mt-2 font-display text-xl font-bold text-foreground">
              {plan === "Pro Creator" ? "Pro Creator" : "Free Trial"}
            </h3>
            <p className="mt-1 text-xs text-muted-foreground max-w-[240px]">
              {plan === "Pro Creator" 
                ? "You have full access to emerging trends, brand deals, and all features."
                : "Limited access. Upgrade to unlock full emerging trends, high-paying brand deals."}
            </p>
          </div>

          <div className="text-right">
            <span className="text-lg font-bold text-foreground">
              {plan === "Pro Creator" ? "₹999/mo" : "Free"}
            </span>
          </div>
        </div>

        {plan !== "Pro Creator" && (
          <Button
            onClick={handleUpgrade}
            disabled={upgrading}
            className="mt-4 w-full h-11 bg-gradient-to-r from-primary to-secondary hover:from-primary/95 hover:to-secondary/95 text-white font-bold text-xs uppercase tracking-wider shadow-lg shadow-primary/20 rounded-xl flex items-center justify-center gap-1.5"
          >
            {upgrading ? (
              <span>Processing...</span>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>Upgrade to Pro</span>
              </>
            )}
          </Button>
        )}

        {plan === "Pro Creator" && (
          <div className="mt-4 flex items-center justify-center gap-1.5 rounded-xl bg-success/10 border border-success/20 py-2.5 text-success">
            <ShieldCheck className="h-4 w-4" />
            <span className="text-xs font-bold uppercase tracking-wider">Premium Access Active</span>
          </div>
        )}
      </div>

      {/* Legal & Privacy Section */}
      <div className="glass-card p-5 space-y-3">
        <h2 className="font-display text-sm font-bold flex items-center gap-2 text-foreground uppercase tracking-wider">
          <ShieldCheck className="h-4 w-4 text-primary" /> Legal & Privacy
        </h2>
        <p className="text-[10px] text-muted-foreground leading-normal">
          Manage digital consent in compliance with India's DPDP Act 2023.
        </p>
        <div className="grid grid-cols-3 gap-2">
          <Link to="/privacy" className="rounded-lg bg-muted/40 hover:bg-muted text-[10px] py-2 text-center text-foreground font-semibold border border-border/20">
            Privacy
          </Link>
          <Link to="/terms" className="rounded-lg bg-muted/40 hover:bg-muted text-[10px] py-2 text-center text-foreground font-semibold border border-border/20">
            Terms
          </Link>
          <Link to="/data-rights" className="rounded-lg bg-muted/40 hover:bg-muted text-[10px] py-2 text-center text-primary font-semibold border border-primary/20">
            DPDP Rights
          </Link>
        </div>
      </div>

      {/* Save Button */}
      <Button
        onClick={save}
        disabled={saving}
        className="h-12 w-full bg-primary hover:bg-primary/95 text-white font-bold uppercase tracking-wider shadow-lg shadow-primary/25 rounded-xl"
      >
        {saving ? "Saving Preferences..." : "Save Profile ✓"}
      </Button>

      <p className="text-center text-[10px] text-muted-foreground tracking-wide mt-2">
        Trendrop — India-first trend intelligence for short-form creators 🇮🇳
      </p>
    </div>
  );
}

function NotificationToggle({
  title,
  description,
  active,
  onChange,
}: {
  title: string;
  description: string;
  active: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between rounded-xl bg-muted/30 px-3.5 py-3 border border-transparent hover:border-border transition-colors">
      <div className="space-y-0.5 pr-4">
        <p className="text-xs font-bold text-foreground">{title}</p>
        <p className="text-[10px] text-muted-foreground leading-normal">{description}</p>
      </div>
      <button
        onClick={() => onChange(!active)}
        className={`relative h-5 w-9 shrink-0 rounded-full transition-colors focus:outline-none ${
          active ? "bg-primary" : "bg-muted-foreground/30"
        }`}
      >
        <div
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${
            active ? "left-[18px]" : "left-0.5"
          }`}
        />
      </button>
    </div>
  );
}

