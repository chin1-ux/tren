import { r as reactExports, j as jsxRuntimeExports } from "../_libs/react.mjs";
import { B as Button } from "./button-DjOZMqFS.mjs";
import { s as subscribe } from "./router-CZKcgiHH.mjs";
import { t as toast } from "../_libs/sonner.mjs";
import { F as Flame, G as Globe, H as Heart, B as Bell, c as Smartphone } from "../_libs/lucide-react.mjs";
import "../_libs/radix-ui__react-slot.mjs";
import "../_libs/radix-ui__react-compose-refs.mjs";
import "../_libs/class-variance-authority.mjs";
import "../_libs/clsx.mjs";
import "../_libs/tailwind-merge.mjs";
import "../_libs/tanstack__query-core.mjs";
import "../_libs/tanstack__react-query.mjs";
import "../_libs/tanstack__react-router.mjs";
import "../_libs/tanstack__router-core.mjs";
import "../_libs/tanstack__history.mjs";
import "../_libs/cookie-es.mjs";
import "../_libs/seroval.mjs";
import "../_libs/seroval-plugins.mjs";
import "node:stream/web";
import "node:stream";
import "../_libs/react-dom.mjs";
import "util";
import "crypto";
import "async_hooks";
import "stream";
import "../_libs/isbot.mjs";
import "../_libs/zod.mjs";
const NICHES = [{
  id: "dance",
  emoji: "💃",
  label: "Dance"
}, {
  id: "fashion",
  emoji: "👗",
  label: "Fashion"
}, {
  id: "travel",
  emoji: "✈️",
  label: "Travel"
}, {
  id: "food",
  emoji: "🍳",
  label: "Food"
}, {
  id: "comedy",
  emoji: "😂",
  label: "Comedy"
}, {
  id: "motivation",
  emoji: "💪",
  label: "Motivation"
}, {
  id: "devotional",
  emoji: "🙏",
  label: "Devotional"
}, {
  id: "fitness",
  emoji: "🏋️",
  label: "Fitness"
}, {
  id: "study",
  emoji: "📚",
  label: "Study"
}, {
  id: "scenic",
  emoji: "🎬",
  label: "Cinematic"
}];
const LANGUAGES = [{
  code: "hi",
  emoji: "🇮🇳",
  label: "Hindi"
}, {
  code: "kn",
  emoji: "🎯",
  label: "Kannada"
}, {
  code: "ta",
  emoji: "🌴",
  label: "Tamil"
}, {
  code: "te",
  emoji: "🌟",
  label: "Telugu"
}, {
  code: "bn",
  emoji: "🐯",
  label: "Bengali"
}, {
  code: "mr",
  emoji: "🦁",
  label: "Marathi"
}, {
  code: "en",
  emoji: "🌐",
  label: "English"
}];
function ProfilePage() {
  const [email, setEmail] = reactExports.useState("");
  const [niche, setNiche] = reactExports.useState("dance");
  const [language, setLanguage] = reactExports.useState("hi");
  const [platform, setPlatform] = reactExports.useState("instagram");
  const [alertEnabled, setAlertEnabled] = reactExports.useState(true);
  const [saving, setSaving] = reactExports.useState(false);
  reactExports.useEffect(() => {
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
      await subscribe({
        email,
        niche,
        language
      });
      localStorage.setItem("trendrop_email", email);
      localStorage.setItem("trendrop_niche", niche);
      localStorage.setItem("trendrop_language", language);
      localStorage.setItem("trendrop_platform", platform);
      toast.success("Preferences saved! You'll get alerts for your niche.");
    } catch {
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
  const selectedNiche = NICHES.find((n) => n.id === niche);
  const selectedLang = LANGUAGES.find((l) => l.code === language);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-5 px-4 pb-10 pt-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-white text-2xl shadow-lg shadow-primary/20", children: selectedNiche?.emoji || "🎯" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "font-display text-2xl font-bold gradient-text", children: "Your Profile" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-muted-foreground", children: "Personalize your trend intelligence" })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-3 gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(StatCard, { icon: /* @__PURE__ */ jsxRuntimeExports.jsx(Flame, { className: "h-4 w-4 text-primary" }), label: "Reels Made", value: generatedCount.toString() }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(StatCard, { icon: /* @__PURE__ */ jsxRuntimeExports.jsx(Globe, { className: "h-4 w-4 text-secondary" }), label: "Language", value: selectedLang?.emoji || "🌐" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(StatCard, { icon: /* @__PURE__ */ jsxRuntimeExports.jsx(Heart, { className: "h-4 w-4 text-[#ff006e]" }), label: "Niche", value: selectedNiche?.emoji || "🎯" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h2", { className: "font-display text-base font-bold flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Bell, { className: "h-4 w-4 text-primary" }),
        " Alert Email"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("input", { type: "email", value: email, onChange: (e) => setEmail(e.target.value), placeholder: "your@email.com", className: "w-full rounded-xl bg-muted/60 px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between rounded-xl bg-muted/40 px-4 py-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-semibold", children: "Trend Alerts" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-muted-foreground", children: "Get notified when new trends match your vibe" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setAlertEnabled(!alertEnabled), className: `relative h-6 w-11 rounded-full transition-colors ${alertEnabled ? "bg-primary" : "bg-muted"}`, children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `absolute top-1 h-4 w-4 rounded-full bg-white shadow transition-all ${alertEnabled ? "left-6" : "left-1"}` }) })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h2", { className: "font-display text-base font-bold flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Heart, { className: "h-4 w-4 text-[#ff006e]" }),
        " Your Content Niche"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-5 gap-2", children: NICHES.map((n) => /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: () => setNiche(n.id), className: `flex flex-col items-center gap-1 rounded-xl p-2.5 text-center transition-all ${niche === n.id ? "bg-primary/20 border border-primary text-primary" : "bg-muted/50 border border-transparent text-muted-foreground hover:border-border"}`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xl", children: n.emoji }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] font-semibold leading-tight", children: n.label })
      ] }, n.id)) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h2", { className: "font-display text-base font-bold flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Globe, { className: "h-4 w-4 text-secondary" }),
        " Preferred Language"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-4 gap-2", children: LANGUAGES.map((l) => /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: () => setLanguage(l.code), className: `flex flex-col items-center gap-1 rounded-xl p-3 text-center transition-all ${language === l.code ? "bg-primary/20 border border-primary text-primary" : "bg-muted/50 border border-transparent text-muted-foreground hover:border-border"}`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xl", children: l.emoji }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] font-semibold", children: l.label })
      ] }, l.code)) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h2", { className: "font-display text-base font-bold flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Smartphone, { className: "h-4 w-4 text-secondary" }),
        " Platform First"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-2 gap-2", children: [{
        id: "instagram",
        emoji: "◎",
        label: "Instagram"
      }, {
        id: "youtube_shorts",
        emoji: "▶",
        label: "YT Shorts"
      }].map((p) => /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: () => setPlatform(p.id), className: `flex flex-col items-center gap-1.5 rounded-xl border py-4 text-center transition-all ${platform === p.id ? "border-primary bg-primary/20 text-primary shadow-sm" : "border-border bg-muted/40 hover:border-primary/40 text-foreground"}`, children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-2xl", children: p.emoji }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xs font-semibold", children: p.label })
      ] }, p.id)) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { onClick: save, disabled: saving, className: "h-12 w-full bg-primary font-bold uppercase tracking-widest shadow-lg shadow-primary/20", children: saving ? "Saving..." : "Save Preferences ✓" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-center text-xs text-muted-foreground", children: "Trendrop — India-first trend intelligence for creators 🇮🇳" })
  ] });
}
function StatCard({
  icon,
  label,
  value
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-3 text-center space-y-1", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex justify-center", children: icon }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-lg font-bold", children: value }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[10px] text-muted-foreground uppercase tracking-wide", children: label })
  ] });
}
export {
  ProfilePage as component
};
