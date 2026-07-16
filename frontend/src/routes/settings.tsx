import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState, useRef } from "react";
import { 
  Settings, User, Bell, SlidersHorizontal, ShieldCheck, 
  HelpCircle, Eye, Moon, Sun, ChevronRight, Check, X, Search 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — Trendrop" },
      { name: "description", content: "Consolidate all settings for notifications, languages, categories, and account." },
    ],
  }),
  component: SettingsPage,
});

const ALL_LANGUAGES = [
  { code: "en", label: "English", emoji: "🇬🇧" },
  { code: "hi", label: "Hindi", emoji: "🇮🇳" },
  { code: "kn", label: "Kannada", emoji: "🎯" },
  { code: "ta", label: "Tamil", emoji: "🌴" },
  { code: "te", label: "Telugu", emoji: "🌟" },
  { code: "bn", label: "Bengali", emoji: "🐯" },
  { code: "mr", label: "Marathi", emoji: "🦁" }
];

const NICHES = [
  "personal finance",
  "pottery",
  "true crime commentary",
  "dance",
  "fashion",
  "travel",
  "food",
  "comedy",
  "motivation",
  "devotional",
  "fitness",
  "study",
  "scenic",
  "technology",
  "gaming",
  "parenting",
  "real estate",
];

function SettingsPage() {
  // Theme state
  const [theme, setTheme] = useState<"light" | "dark">("light");

  // Account state
  const [email, setEmail] = useState("");
  const [instagramHandle, setInstagramHandle] = useState("");
  const [followers, setFollowers] = useState("");

  // Notification state
  const [notifyTrendAlerts, setNotifyTrendAlerts] = useState(true);
  const [notifyDailyIdeas, setNotifyDailyIdeas] = useState(true);
  const [notifyBrandDeals, setNotifyBrandDeals] = useState(true);
  const [notifyWeeklyReport, setNotifyWeeklyReport] = useState(true);

  // Preference state
  const [selectedLanguage, setSelectedLanguage] = useState("all");
  const [selectedNiche, setSelectedNiche] = useState("all");

  // Search-based filters state
  const [langSearch, setLangSearch] = useState("");
  const [customNiche, setCustomNiche] = useState("");
  const [showLangDropdown, setShowLangDropdown] = useState(false);

  const langRef = useRef<HTMLDivElement>(null);

  // Load from local storage
  useEffect(() => {
    const activeTheme = localStorage.getItem("trendrop_theme") as "light" | "dark" | null;
    if (activeTheme) setTheme(activeTheme);

    setEmail(localStorage.getItem("trendrop_email") || "");
    setInstagramHandle(localStorage.getItem("trendrop_instagram_handle") || "");
    setFollowers(localStorage.getItem("trendrop_followers") || "");

    const nt = localStorage.getItem("trendrop_notify_trend_alerts");
    const nd = localStorage.getItem("trendrop_notify_daily_ideas");
    const nb = localStorage.getItem("trendrop_notify_brand_deals");
    const nw = localStorage.getItem("trendrop_notify_weekly_report");

    if (nt !== null) setNotifyTrendAlerts(nt === "true");
    if (nd !== null) setNotifyDailyIdeas(nd === "true");
    if (nb !== null) setNotifyBrandDeals(nb === "true");
    if (nw !== null) setNotifyWeeklyReport(nw === "true");

    setSelectedLanguage(localStorage.getItem("trendrop_pref_language") ?? "all");
    const savedNiche = localStorage.getItem("trendrop_pref_niche") ?? "all";
    setSelectedNiche(savedNiche);
    setCustomNiche(savedNiche === "all" ? "" : savedNiche);
  }, []);

  // Detect Instagram OAuth redirect result
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const igSuccess = params.get("ig_success");
    const igError = params.get("ig_error");
    const igUsername = params.get("ig_username");

    if (igSuccess === "1") {
      const handle = igUsername ? `@${igUsername}` : "your account";
      toast.success(`✅ Instagram connected! ${handle} is now linked to Trendrop.`);
      if (igUsername) {
        setInstagramHandle(igUsername);
        localStorage.setItem("trendrop_instagram_handle", igUsername);
      }
    } else if (igError) {
      const errorMessages: Record<string, string> = {
        no_code: "No authorization code received from Instagram.",
        no_ig_account: "No Instagram Business/Creator account found. Make sure your Instagram is linked to a Facebook Page.",
        store_failed: "Failed to save your Instagram connection. Please try again.",
        server_error: "Something went wrong. Please try again.",
        not_configured: "Instagram OAuth is not configured on the server.",
      };
      toast.error(`❌ Instagram connection failed: ${errorMessages[igError] ?? igError}`);
    }

    // Clean up query params from URL without reload
    if (igSuccess || igError) {
      const cleanUrl = window.location.pathname;
      window.history.replaceState({}, "", cleanUrl);
    }
  }, []);


  // Theme change
  const toggleTheme = () => {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    localStorage.setItem("trendrop_theme", next);
    // Apply immediately to DOM
    const body = document.body;
    const root = document.documentElement;
    if (next === "dark") {
      body.setAttribute("data-theme", "dark");
      body.classList.add("dark");
      root.setAttribute("data-theme", "dark");
      root.classList.add("dark");
    } else {
      body.removeAttribute("data-theme");
      body.classList.remove("dark");
      root.removeAttribute("data-theme");
      root.classList.remove("dark");
    }
    toast.success(`Switched to ${next} mode!`);
  };

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (langRef.current && !langRef.current.contains(event.target as Node)) {
        setShowLangDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const saveSettings = () => {
    localStorage.setItem("trendrop_email", email);
    localStorage.setItem("trendrop_instagram_handle", instagramHandle);
    localStorage.setItem("trendrop_followers", followers);

    localStorage.setItem("trendrop_notify_trend_alerts", String(notifyTrendAlerts));
    localStorage.setItem("trendrop_notify_daily_ideas", String(notifyDailyIdeas));
    localStorage.setItem("trendrop_notify_brand_deals", String(notifyBrandDeals));
    localStorage.setItem("trendrop_notify_weekly_report", String(notifyWeeklyReport));

    localStorage.setItem("trendrop_pref_language", selectedLanguage);
    localStorage.setItem("trendrop_pref_niche", customNiche.trim() || selectedNiche || "all");

    toast.success("Settings saved successfully! ✓");
  };

  const replayTutorial = () => {
    localStorage.removeItem("trendrop_visited");
    localStorage.removeItem("trendrop_tutorial_done");
    toast.success("Tutorial reset! Redirecting to dashboard...");
    setTimeout(() => {
      window.location.href = "/";
    }, 1000);
  };

  // Filter languages and niches based on search
  const filteredLanguages = ALL_LANGUAGES.filter(l => 
    l.label.toLowerCase().includes(langSearch.toLowerCase())
  );

  const activeLangObj = ALL_LANGUAGES.find(l => l.code === selectedLanguage);
  const activeNicheLabel = customNiche.trim() || (selectedNiche !== "all" ? selectedNiche : "All niches");

  return (
    <div className="flex flex-col gap-6 px-4 pb-28 pt-6 max-w-md mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/20 pb-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground flex items-center gap-2">
            <Settings className="h-6 w-6 text-primary" /> Settings
          </h1>
          <p className="text-xs text-muted-foreground mt-1">Configure preference filters, notifications & alerts</p>
        </div>
      </div>

      {/* ── 1. Preferences & Filters (Searchable) ── */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-sm font-bold flex items-center gap-2 text-foreground uppercase tracking-wider">
          <SlidersHorizontal className="h-4 w-4 text-primary" /> Feed Preferences
        </h2>

        {/* Searchable Language Selection */}
      <div className="space-y-1.5" ref={langRef}>
          <label className="text-xs font-semibold text-muted-foreground block">Default Trend Language</label>
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowLangDropdown(!showLangDropdown)}
              className="w-full rounded-xl bg-muted/40 border border-border px-3.5 py-2.5 text-left text-xs font-medium text-foreground flex items-center justify-between hover:bg-muted/60 transition-colors"
            >
              <span>{activeLangObj ? `${activeLangObj.emoji} ${activeLangObj.label}` : "🌐 All Languages"}</span>
              <ChevronRight className={`h-4 w-4 text-muted-foreground transform transition-transform ${showLangDropdown ? "rotate-90" : ""}`} />
            </button>

            {showLangDropdown && (
              <div className="absolute z-30 mt-1.5 w-full rounded-xl border border-border bg-surface shadow-xl p-2.5 space-y-2">
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
                  <button
                    onClick={() => { setSelectedLanguage("all"); setShowLangDropdown(false); }}
                    className="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-muted transition-colors flex items-center justify-between"
                  >
                    <span>🌐 All Languages</span>
                    {selectedLanguage === "all" && <Check className="h-3.5 w-3.5 text-primary" />}
                  </button>
                  {filteredLanguages.map(l => (
                    <button
                      key={l.code}
                      onClick={() => { setSelectedLanguage(l.code); setShowLangDropdown(false); }}
                      className="w-full text-left px-3 py-2 text-xs rounded-lg hover:bg-muted transition-colors flex items-center justify-between"
                    >
                      <span>{l.emoji} {l.label}</span>
                      {selectedLanguage === l.code && <Check className="h-3.5 w-3.5 text-primary" />}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Searchable Niche Selection */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-muted-foreground block">Creator Niche / Category</label>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={customNiche}
              onChange={(e) => {
                const value = e.target.value;
                setCustomNiche(value);
                setSelectedNiche(value.trim() ? value : "all");
              }}
              placeholder="e.g. personal finance, pottery, true crime commentary"
              className="w-full rounded-xl bg-muted/40 border border-border px-8 py-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
          </div>
          <p className="text-[10px] text-muted-foreground">Free-form niche value. Suggestions below are optional, not a fixed list.</p>
          <div className="flex flex-wrap gap-2">
            {NICHES.map((niche) => (
              <button
                key={niche}
                type="button"
                onClick={() => {
                  setCustomNiche(niche);
                  setSelectedNiche(niche);
                }}
                className="rounded-full border border-border/50 bg-background/60 px-2.5 py-1 text-[10px] font-semibold text-foreground/80 hover:border-primary/50 hover:text-foreground"
              >
                {niche}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── 2. Theme & Tutorial ── */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-sm font-bold flex items-center gap-2 text-foreground uppercase tracking-wider">
          <Eye className="h-4 w-4 text-primary" /> Application
        </h2>

        {/* Theme Settings */}
        <div className="flex items-center justify-between py-1">
          <div>
            <p className="text-xs font-semibold text-foreground">Interface Theme</p>
            <p className="text-[10px] text-muted-foreground">Switch between light and dark styling</p>
          </div>
          <button
            onClick={toggleTheme}
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-muted/60 border border-border text-foreground hover:bg-muted transition-all active:scale-95"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>

        {/* Onboarding replay */}
        <div className="flex items-center justify-between py-1 border-t border-border/20 pt-3">
          <div>
            <p className="text-xs font-semibold text-foreground">Onboarding Tutorial</p>
            <p className="text-[10px] text-muted-foreground">Replay the feature walkthrough tutorial</p>
          </div>
          <Button
            onClick={replayTutorial}
            variant="outline"
            className="h-8 border-white/10 text-xs px-3"
          >
            <HelpCircle className="h-3.5 w-3.5 mr-1" /> Reset Tutorial
          </Button>
        </div>
      </div>

      {/* ── 3. Notification Settings ── */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-sm font-bold flex items-center gap-2 text-foreground uppercase tracking-wider">
          <Bell className="h-4 w-4 text-primary" /> Notification Alerts
        </h2>

        <div className="space-y-3.5">
          <ToggleSwitch
            title="Real-time Trend Alerts"
            description="Get notified instantly as soon as a new trend rises in India"
            active={notifyTrendAlerts}
            onChange={setNotifyTrendAlerts}
          />
          <ToggleSwitch
            title="Daily Content Ideas"
            description="Daily personalized content scripts and hook ideas"
            active={notifyDailyIdeas}
            onChange={setNotifyDailyIdeas}
          />
          <ToggleSwitch
            title="Brand Collaboration Alerts"
            description="Instant updates when high-paying brand campaigns launch"
            active={notifyBrandDeals}
            onChange={setNotifyBrandDeals}
          />
          <ToggleSwitch
            title="Weekly Trend Analysis"
            description="Detailed compilation report of the past week's performance"
            active={notifyWeeklyReport}
            onChange={setNotifyWeeklyReport}
          />
        </div>
      </div>

      {/* ── 4. Account Settings ── */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-sm font-bold flex items-center gap-2 text-foreground uppercase tracking-wider">
          <User className="h-4 w-4 text-primary" /> Account details
        </h2>

        <div className="space-y-3">
          <div>
            <label className="text-[10px] font-semibold text-muted-foreground block mb-1">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="creator@trendrop.app"
              className="w-full rounded-xl bg-muted/40 border border-border px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-muted-foreground block mb-1">Instagram Handle</label>
            <input
              type="text"
              value={instagramHandle}
              onChange={(e) => setInstagramHandle(e.target.value)}
              placeholder="handle"
              className="w-full rounded-xl bg-muted/40 border border-border px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
          </div>
          <div>
            <label className="text-[10px] font-semibold text-muted-foreground block mb-1">Follower Count</label>
            <input
              type="number"
              value={followers}
              onChange={(e) => setFollowers(e.target.value)}
              placeholder="0"
              className="w-full rounded-xl bg-muted/40 border border-border px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
            />
          </div>
        </div>
      </div>

      {/* ── 5. Legal & Data Rights (DPDP Compliant) ── */}
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

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          onClick={saveSettings}
          className="h-12 flex-1 bg-primary text-white hover:bg-primary/90 font-bold uppercase rounded-xl shadow-lg transition-all"
        >
          Save Settings ✓
        </Button>
      </div>
    </div>
  );
}

function ToggleSwitch({
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
    <div className="flex items-start justify-between gap-3 py-1">
      <div className="space-y-0.5">
        <p className="text-xs font-semibold text-foreground">{title}</p>
        <p className="text-[10px] text-muted-foreground leading-normal max-w-[280px]">{description}</p>
      </div>
      <button
        onClick={() => onChange(!active)}
        title={title}
        aria-label={title}
        className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none ${
          active ? "bg-primary" : "bg-muted-foreground/35"
        }`}
      >
        <span
          className={`pointer-events-none inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out mt-0.5 ${
            active ? "translate-x-4.5" : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}
