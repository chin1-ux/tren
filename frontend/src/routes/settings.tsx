import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState, useRef } from "react";
import { 
  Settings, User, Bell, SlidersHorizontal, ShieldCheck, 
  HelpCircle, Eye, Moon, Sun, ChevronRight, Check, X, Search, LogOut, Type, Palette, MapPin, Users
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { FEATURES } from "@/lib/features";
import { apiFetch } from "@/lib/api";

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
  "current_affairs",
  "fitness",
  "food",
  "travel",
  "fashion",
  "dance",
  "comedy",
  "motivation",
  "devotional",
  "tech",
  "narrative_edit",
  "romance_relationship",
  "personal finance",
  "gaming",
  "parenting",
  "real estate",
  "study",
  "scenic",
  "pottery",
  "true crime commentary",
];

const STATES = [
  { code: "", label: "Select State" },
  { code: "MH", label: "Maharashtra" },
  { code: "KA", label: "Karnataka" },
  { code: "KL", label: "Kerala" },
  { code: "TN", label: "Tamil Nadu" },
  { code: "DL", label: "Delhi" },
  { code: "UP", label: "Uttar Pradesh" },
  { code: "WB", label: "West Bengal" },
  { code: "GJ", label: "Gujarat" },
  { code: "RJ", label: "Rajasthan" },
  { code: "PB", label: "Punjab" },
  { code: "AP", label: "Andhra Pradesh" },
  { code: "TG", label: "Telangana" },
  { code: "AS", label: "Assam" },
  { code: "BR", label: "Bihar" },
  { code: "MP", label: "Madhya Pradesh" },
  { code: "HR", label: "Haryana" },
];

const TIERS = [
  { code: "nano",  label: "Nano (0–10k)" },
  { code: "micro", label: "Micro (10k–100k)" },
  { code: "macro", label: "Macro (100k–1M)" },
  { code: "mega",  label: "Mega (1M+)" },
];

function SettingsPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();

  // Dynamic style states
  const [fontSize, setFontSize] = useState<"normal" | "large" | "largest">("normal");
  const [themeColor, setThemeColor] = useState<"coral" | "violet" | "emerald">("coral");

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
  const [selectedState, setSelectedState] = useState("");
  const [selectedTier, setSelectedTier] = useState("nano");
  const [savingPrefs, setSavingPrefs] = useState(false);

  // Search-based filters state
  const [langSearch, setLangSearch] = useState("");
  const [customNiche, setCustomNiche] = useState("");
  const [showLangDropdown, setShowLangDropdown] = useState(false);

  const langRef = useRef<HTMLDivElement>(null);

  // Load from local storage
  useEffect(() => {
    const activeTheme = localStorage.getItem("trendrop_theme") as "light" | "dark" | null;
    if (activeTheme) setTheme(activeTheme);

    setEmail(localStorage.getItem("trendrop_user_email") || "");
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
    setSelectedState(localStorage.getItem("trendrop_user_state") ?? "");
    setSelectedTier(localStorage.getItem("trendrop_creator_tier") ?? "nano");

    // Load custom dynamic options
    const savedSize = localStorage.getItem("trendrop_font_size") as any;
    if (savedSize) {
      setFontSize(savedSize);
      applyFontSize(savedSize);
    }
    const savedColor = localStorage.getItem("trendrop_theme_color") as any;
    if (savedColor) {
      setThemeColor(savedColor);
      applyThemeColor(savedColor);
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

  const applyFontSize = (size: "normal" | "large" | "largest") => {
    const root = document.documentElement;
    if (size === "normal") root.style.fontSize = "16px";
    else if (size === "large") root.style.fontSize = "18px";
    else if (size === "largest") root.style.fontSize = "20px";
  };

  const applyThemeColor = (color: "coral" | "violet" | "emerald") => {
    const colors = {
      coral: "#FF4D3D",
      violet: "#7F77DD",
      emerald: "#1FB87A"
    };
    document.documentElement.style.setProperty("--primary", colors[color]);
    document.documentElement.style.setProperty("--color-primary", colors[color]);
  };

  const handleFontSizeChange = (size: "normal" | "large" | "largest") => {
    setFontSize(size);
    localStorage.setItem("trendrop_font_size", size);
    applyFontSize(size);
    toast.success(`Font size changed to ${size}!`);
  };

  const handleThemeColorChange = (color: "coral" | "violet" | "emerald") => {
    setThemeColor(color);
    localStorage.setItem("trendrop_theme_color", color);
    applyThemeColor(color);
    toast.success(`Theme primary color updated to ${color}!`);
  };

  const handleLogout = async () => {
    try {
      await logout();
      toast.success("Logged out successfully");
      navigate({ to: "/login" });
    } catch {
      toast.error("Failed to log out");
    }
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

  const saveSettings = async () => {
    localStorage.setItem("trendrop_user_email", email);
    localStorage.setItem("trendrop_instagram_handle", instagramHandle);
    localStorage.setItem("trendrop_followers", followers);

    localStorage.setItem("trendrop_notify_trend_alerts", String(notifyTrendAlerts));
    localStorage.setItem("trendrop_notify_daily_ideas", String(notifyDailyIdeas));
    localStorage.setItem("trendrop_notify_brand_deals", String(notifyBrandDeals));
    localStorage.setItem("trendrop_notify_weekly_report", String(notifyWeeklyReport));

    const finalNiche = customNiche.trim() || selectedNiche || "all";
    localStorage.setItem("trendrop_pref_language", selectedLanguage);
    localStorage.setItem("trendrop_pref_niche", finalNiche);
    localStorage.setItem("trendrop_user_state", selectedState);
    localStorage.setItem("trendrop_creator_tier", selectedTier);

    // Persist to backend so alerts + regional feed work correctly
    setSavingPrefs(true);
    try {
      await apiFetch("/api/users/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          niches: finalNiche !== "all" ? [finalNiche] : [],
          languages: selectedLanguage !== "all" ? [selectedLanguage] : ["en"],
          regions: ["IN"],
          creator_language: selectedLanguage !== "all" ? selectedLanguage : "en",
          state: selectedState || null,
          creator_tier: selectedTier,
          global_enabled: false,
          notification_triggers: {},
          platform_focus: ["instagram"],
        }),
      });
      toast.success("Preferences saved ✓");
    } catch {
      toast.success("Preferences saved on this device ✓");
    } finally {
      setSavingPrefs(false);
    }
  };

  const replayTutorial = () => {
    localStorage.removeItem("trendrop_visited");
    localStorage.removeItem("trendrop_tutorial_done");
    toast.success("Tutorial reset! Redirecting to dashboard...");
    setTimeout(() => {
      window.location.href = "/";
    }, 1000);
  };

  const filteredLanguages = ALL_LANGUAGES.filter(l => 
    (l.label ?? "").toLowerCase().includes(langSearch.toLowerCase())
  );

  const activeLangObj = ALL_LANGUAGES.find(l => l.code === selectedLanguage);

  return (
    <div className="flex flex-col gap-6 px-4 pb-28 pt-6 max-w-2xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/20 pb-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground flex items-center gap-2">
            <Settings className="h-6 w-6 text-primary" /> Settings Hub
          </h1>
          <p className="text-xs text-muted-foreground mt-1">Configure preference filters, profile & app styling options</p>
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
          <p className="text-[10px] text-muted-foreground">Suggestions below are optional:</p>
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

        {/* State */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
            <MapPin className="h-3 w-3" /> Your State (for regional festival alerts)
          </label>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="w-full rounded-xl bg-muted/40 border border-border px-3.5 py-2.5 text-xs font-medium text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          >
            {STATES.map((s) => (
              <option key={s.code} value={s.code}>{s.label}</option>
            ))}
          </select>
          <p className="text-[10px] text-muted-foreground">
            Used to surface Varamahalakshmi, Onam, Durga Puja etc. at the right time for your audience
          </p>
        </div>

        {/* Tier */}
        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
            <Users className="h-3 w-3" /> Creator Tier
          </label>
          <div className="grid grid-cols-4 gap-2">
            {TIERS.map((t) => (
              <button
                key={t.code}
                type="button"
                onClick={() => setSelectedTier(t.code)}
                className={`rounded-xl py-2 text-[10px] font-bold border transition-all ${
                  selectedTier === t.code
                    ? "bg-primary text-white border-primary"
                    : "bg-muted/40 text-foreground/70 border-border/30 hover:bg-muted"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── 2. Display Styles (Font & Colors) ── */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-sm font-bold flex items-center gap-2 text-foreground uppercase tracking-wider">
          <Palette className="h-4 w-4 text-primary" /> Display Styles
        </h2>

        {/* Font Size Preferences */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-foreground">
            <Type className="h-3.5 w-3.5 text-primary" /> Font Size Options
          </div>
          <div className="grid grid-cols-3 gap-2">
            {(["normal", "large", "largest"] as const).map((size) => (
              <button
                key={size}
                type="button"
                onClick={() => handleFontSizeChange(size)}
                className={`rounded-lg py-2 text-[11px] font-bold border transition-all ${
                  fontSize === size 
                    ? "bg-primary text-white border-primary" 
                    : "bg-muted/40 text-foreground border-border/30 hover:bg-muted"
                }`}
              >
                {size.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Brand Theme Colors */}
        <div className="space-y-2 border-t border-border/20 pt-3">
          <p className="text-xs font-semibold text-foreground">App Brand Color Vibe</p>
          <div className="grid grid-cols-3 gap-2">
            {(["coral", "violet", "emerald"] as const).map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => handleThemeColorChange(color)}
                className={`rounded-lg py-2 text-[11px] font-bold border capitalize transition-all ${
                  themeColor === color 
                    ? "bg-primary text-white border-primary" 
                    : "bg-muted/40 text-foreground border-border/30 hover:bg-muted"
                }`}
              >
                {color}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── 3. Theme & Tutorial ── */}
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

      {/* ── 4. Notification Settings ── */}
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
          {FEATURES.IDEAS_ENABLED && (
            <ToggleSwitch
              title="Daily Content Ideas"
              description="Daily personalized content scripts and hook ideas"
              active={notifyDailyIdeas}
              onChange={setNotifyDailyIdeas}
            />
          )}
          {FEATURES.DEALS_ENABLED && (
            <ToggleSwitch
              title="Brand Collaboration Alerts"
              description="Instant updates when high-paying brand campaigns launch"
              active={notifyBrandDeals}
              onChange={setNotifyBrandDeals}
            />
          )}
          <ToggleSwitch
            title="Weekly Trend Analysis"
            description="Detailed compilation report of the past week's performance"
            active={notifyWeeklyReport}
            onChange={setNotifyWeeklyReport}
          />
        </div>
      </div>

      {/* ── 5. Account Settings ── */}
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
          {FEATURES.INSTAGRAM_OAUTH_ENABLED && (
            <>
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
            </>
          )}
        </div>

        <div className="border-t border-border/20 pt-3 mt-4">
          <Button
            onClick={handleLogout}
            variant="destructive"
            className="w-full h-10 font-bold uppercase rounded-xl flex items-center justify-center gap-2 text-xs"
          >
            <LogOut className="h-4 w-4" /> Log out of profile
          </Button>
        </div>
      </div>

      {/* ── 6. Legal & Data Rights (DPDP Compliant) ── */}
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
          disabled={savingPrefs}
          className="h-12 flex-1 bg-primary text-white hover:bg-primary/90 font-bold uppercase rounded-xl shadow-lg transition-all"
        >
          {savingPrefs ? "Saving…" : "Save Settings ✓"}
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
