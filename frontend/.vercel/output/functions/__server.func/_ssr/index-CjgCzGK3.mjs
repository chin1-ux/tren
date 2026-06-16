import { r as reactExports, j as jsxRuntimeExports } from "../_libs/react.mjs";
import { e as useNavigate } from "../_libs/tanstack__react-router.mjs";
import { u as useQuery } from "../_libs/tanstack__react-query.mjs";
import { f as fetchTrends, c as fetchEmergingTrends, b as fetchTrendReels, s as subscribe } from "./router-CZKcgiHH.mjs";
import { c as cn, B as Button } from "./button-DjOZMqFS.mjs";
import { t as toast } from "../_libs/sonner.mjs";
import { B as Bell, T as TrendingUp, Z as Zap, g as Search, X, f as TriangleAlert, F as Flame, h as Clock, I as Info, i as CheckCheck, j as Copy, k as ChevronUp, l as ChevronDown, V as Video, m as Check, n as CircleCheckBig } from "../_libs/lucide-react.mjs";
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
import "../_libs/tanstack__query-core.mjs";
import "../_libs/zod.mjs";
import "../_libs/radix-ui__react-slot.mjs";
import "../_libs/radix-ui__react-compose-refs.mjs";
import "../_libs/class-variance-authority.mjs";
import "../_libs/clsx.mjs";
import "../_libs/tailwind-merge.mjs";
const trendCategories = [
  "All",
  "Dance",
  "Scenic",
  "Fashion",
  "Travel",
  "Food",
  "Viral"
];
function FilterPills({ active, onChange }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4 pb-1", children: trendCategories.map((cat) => {
    const isActive = active === cat;
    return /* @__PURE__ */ jsxRuntimeExports.jsx(
      "button",
      {
        onClick: () => onChange(cat),
        className: cn(
          "shrink-0 rounded-full border px-4 py-1.5 text-sm font-medium transition-all",
          isActive ? "border-primary bg-primary text-primary-foreground" : "border-border bg-muted text-muted-foreground hover:text-foreground"
        ),
        children: cat
      },
      cat
    );
  }) });
}
function getSaturationMeta(score) {
  if (score < 0.2) return { label: "Very Early 🟢", color: "text-emerald-400", dot: "bg-emerald-400" };
  if (score < 0.5) return { label: "Getting Popular 🟡", color: "text-amber-400", dot: "bg-amber-400" };
  if (score < 0.75) return { label: "Trending 🟠", color: "text-orange-400", dot: "bg-orange-400" };
  return { label: "Almost Peaked 🔴", color: "text-red-400", dot: "bg-red-400" };
}
function getPlatformMeta(platform) {
  if (platform === "youtube_shorts") return { label: "YouTube Shorts", icon: "▶" };
  return { label: "Instagram", icon: "◎" };
}
function TrendCard({ trend, onDanceTap }) {
  const navigate = useNavigate();
  const [showReels, setShowReels] = reactExports.useState(false);
  const [copied, setCopied] = reactExports.useState(false);
  const [showWhy, setShowWhy] = reactExports.useState(false);
  const cardRef = reactExports.useRef(null);
  const isEmerging = trend.isEmerging || trend.status === "emerging";
  const isUrgent = trend.hoursLeft <= 6;
  const satMeta = getSaturationMeta(trend.saturationScore ?? 0);
  const platformMeta = getPlatformMeta(trend.bestPlatformFirst ?? "instagram");
  const viralPct = Math.min(100, trend.viralMultiplier / 30 * 100);
  const { data: reels } = useQuery({
    queryKey: ["trend-reels", trend.id],
    queryFn: () => fetchTrendReels(trend.id),
    enabled: showReels,
    staleTime: 5 * 6e4
  });
  const onMouseMove = reactExports.useCallback((e) => {
    if (!cardRef.current) return;
    const rect = cardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const rotX = (y - cy) / cy * -6;
    const rotY = (x - cx) / cx * 6;
    cardRef.current.style.transform = `perspective(800px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateZ(4px)`;
  }, []);
  const onMouseLeave = reactExports.useCallback(() => {
    if (!cardRef.current) return;
    cardRef.current.style.transform = "perspective(800px) rotateX(0deg) rotateY(0deg) translateZ(0)";
  }, []);
  const formatViews = (v) => {
    if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
    if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`;
    return v.toString();
  };
  const copyCaption = () => {
    const text = `${trend.idealContentDescription || trend.song} 🔥 #trending #reels #${trend.contentType?.toLowerCase().replace(/\s+/g, "")}`;
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      toast.success("Caption copied to clipboard!");
      setTimeout(() => setCopied(false), 2e3);
    });
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(
    "article",
    {
      ref: cardRef,
      onMouseMove,
      onMouseLeave,
      className: `tilt-card relative space-y-4 rounded-2xl p-5 transition-all duration-200 ${isEmerging ? "neon-border-emerging animate-pulse-urgent bg-[rgba(255,0,110,0.04)]" : isUrgent ? "neon-border bg-[rgba(230,57,70,0.04)]" : "glass-card"}`,
      children: [
        isEmerging && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "absolute -top-3 left-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1.5 rounded-full bg-[#ff006e] px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-white shadow-lg", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Zap, { className: "h-3 w-3" }),
          " EMERGING FIRST"
        ] }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-primary", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Flame, { className: "h-3 w-3" }),
              " ",
              isEmerging ? "Emerging" : "Trending"
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 rounded-full bg-white/5 px-2 py-1 text-[10px] font-semibold text-muted-foreground", children: [
              platformMeta.icon,
              " ",
              platformMeta.label
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: `inline-flex items-center gap-1 text-xs font-semibold ${isUrgent ? "text-primary" : "text-muted-foreground"}`, children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "h-3.5 w-3.5" }),
            trend.hoursLeft > 0 ? `${trend.hoursLeft}h left` : "Ending soon"
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-0.5", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "font-display text-2xl font-bold leading-tight tracking-tight text-foreground", children: trend.song }),
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-muted-foreground", children: [
            "by ",
            trend.artist
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between text-xs", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "font-semibold uppercase tracking-wide text-muted-foreground", children: "Velocity" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "font-bold text-primary", children: [
              trend.viralMultiplier,
              "x normal"
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-end gap-[3px] h-8", children: Array.from({ length: 20 }).map((_, i) => {
            const filled = i < Math.round(viralPct / 100 * 20);
            return /* @__PURE__ */ jsxRuntimeExports.jsx(
              "div",
              {
                className: `flex-1 rounded-sm transition-all duration-300 ${filled ? "bg-gradient-to-t from-primary to-secondary" : "bg-muted/40"}`,
                style: { height: `${20 + Math.sin(i * 0.8) * 14}px` }
              },
              i
            );
          }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: `h-2 w-2 rounded-full ${satMeta.dot}` }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `text-xs font-semibold ${satMeta.color}`, children: satMeta.label }),
          trend.optimalPostHourIst !== void 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "ml-auto text-xs text-muted-foreground", children: [
            "Best: ",
            trend.optimalPostHourIst,
            ":00 IST"
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-wrap gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(Chip, { children: [
            trend.contentTypeEmoji,
            " ",
            trend.contentType
          ] }),
          trend.languageEmoji && trend.language && /* @__PURE__ */ jsxRuntimeExports.jsxs(Chip, { children: [
            trend.languageEmoji,
            " ",
            trend.language
          ] }),
          trend.isDance && /* @__PURE__ */ jsxRuntimeExports.jsx(Chip, { className: "bg-secondary/15 text-secondary", children: "FILM YOURSELF" }),
          trend.isNarrativeEdit && /* @__PURE__ */ jsxRuntimeExports.jsx(Chip, { className: "bg-narrative/15 text-narrative", children: "NARRATIVE EDIT" }),
          trend.reelCount !== void 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(Chip, { className: "bg-white/5 text-muted-foreground", children: [
            trend.reelCount,
            " reels"
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "rounded-xl bg-white/[0.03] px-3 py-2 text-sm italic text-muted-foreground border border-border", children: [
          "💡 ",
          trend.idealContentDescription || "Great for reels and short-form content"
        ] }),
        trend.whyThisWorks && /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: () => setShowWhy(!showWhy),
            className: "flex w-full items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Info, { className: "h-3.5 w-3.5 shrink-0" }),
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: showWhy ? trend.whyThisWorks : "Why is this trending? ↓" })
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs(
          "button",
          {
            onClick: copyCaption,
            className: "flex w-full items-center justify-between rounded-xl border border-border bg-white/[0.02] px-3 py-2 text-xs text-muted-foreground hover:border-primary/40 hover:text-foreground transition-all",
            children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: "📋 Quick copy caption + hashtags" }),
              copied ? /* @__PURE__ */ jsxRuntimeExports.jsx(CheckCheck, { className: "h-3.5 w-3.5 text-success" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Copy, { className: "h-3.5 w-3.5" })
            ]
          }
        ),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "border-t border-border pt-3", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            "button",
            {
              onClick: () => setShowReels(!showReels),
              className: "flex w-full items-center justify-between py-1 text-xs font-bold uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1.5", children: [
                  /* @__PURE__ */ jsxRuntimeExports.jsx(TrendingUp, { className: "h-3.5 w-3.5" }),
                  " Source Reels"
                ] }),
                showReels ? /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronUp, { className: "h-4 w-4" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronDown, { className: "h-4 w-4" })
              ]
            }
          ),
          showReels && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-3 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200", children: !reels ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-center py-4 text-xs text-muted-foreground", children: "Loading reels..." }) : reels.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-center py-4 text-xs text-muted-foreground", children: "No reels found yet." }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-1 gap-3 sm:grid-cols-2", children: reels.slice(0, 4).map((reel) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-2 rounded-xl bg-white/[0.03] p-3 border border-border/50", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between text-xs", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "font-bold text-primary", children: [
                "@",
                reel.owner_username
              ] }),
              /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-muted-foreground", children: [
                formatViews(reel.view_count),
                " views"
              ] })
            ] }),
            reel.caption && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-muted-foreground line-clamp-2 italic", children: [
              '"',
              reel.caption,
              '"'
            ] })
          ] }, reel.id)) }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2 pt-1", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs(
            Button,
            {
              onClick: () => navigate({ to: "/generate", search: { trendId: trend.id } }),
              className: "h-12 w-full bg-success font-bold uppercase tracking-wide text-success-foreground hover:bg-success/90 transition-all hover:scale-[1.01]",
              children: [
                /* @__PURE__ */ jsxRuntimeExports.jsx(Video, { className: "h-4 w-4" }),
                " Generate My Reel"
              ]
            }
          ),
          trend.isDance && /* @__PURE__ */ jsxRuntimeExports.jsx(
            Button,
            {
              onClick: () => onDanceTap(trend),
              className: "h-12 w-full bg-secondary font-bold uppercase tracking-wide text-secondary-foreground hover:bg-secondary/90",
              children: "💃 How To Film This"
            }
          )
        ] })
      ]
    }
  );
}
function Chip({ children, className = "" }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-semibold text-foreground ${className}`, children });
}
function SkeletonCard() {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-2xl border border-border bg-white/[0.02] p-5 space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-6 w-24 rounded-full shimmer" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-5 w-16 rounded-full shimmer" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-7 w-3/4 rounded-lg shimmer" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-4 w-1/3 rounded-lg shimmer" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-end gap-[3px] h-8", children: Array.from({ length: 20 }).map((_, i) => /* @__PURE__ */ jsxRuntimeExports.jsx(
      "div",
      {
        className: "flex-1 rounded-sm shimmer",
        style: { height: `${20 + Math.sin(i * 0.8) * 14}px` }
      },
      i
    )) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-6 w-16 rounded-full shimmer" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-6 w-20 rounded-full shimmer" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-6 w-12 rounded-full shimmer" })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-10 rounded-xl shimmer" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-12 rounded-xl shimmer" })
  ] });
}
function DanceTrendModal({ trend, onClose }) {
  const [copied, setCopied] = reactExports.useState(false);
  if (!trend) return null;
  const copy = async () => {
    await navigator.clipboard.writeText(`${trend.song} — ${trend.artist}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  const steps = [
    "Open Instagram camera",
    "Select the song from the audio library",
    "Film yourself following the brief below",
    "Post using the suggested hashtags"
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-[60] flex items-end justify-center bg-black/80 backdrop-blur-sm animate-in fade-in sm:items-center", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-h-[90vh] w-full max-w-md overflow-y-auto rounded-t-3xl border border-border bg-card p-6 animate-in slide-in-from-bottom sm:rounded-3xl", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-4 flex items-start justify-between", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-2xl font-bold text-secondary", children: "💃 Dance Trend" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-sm text-muted-foreground", children: "This trend requires you to film yourself" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onClose, className: "rounded-full p-2 text-muted-foreground hover:bg-muted hover:text-foreground", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "h-5 w-5" }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Section, { label: "Song to use", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between gap-3 rounded-xl bg-muted p-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-w-0", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "truncate font-semibold", children: trend.song }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "truncate text-xs text-muted-foreground", children: trend.artist })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: copy, className: "shrink-0 rounded-lg bg-background p-2 text-muted-foreground hover:text-foreground", children: copied ? /* @__PURE__ */ jsxRuntimeExports.jsx(Check, { className: "h-4 w-4 text-success" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Copy, { className: "h-4 w-4" }) })
    ] }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Section, { label: "What to film", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-foreground/90", children: trend.idealContentDescription }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Section, { label: "Camera tip", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-foreground/90", children: trend.cameraStyle }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Section, { label: "Step by step", children: /* @__PURE__ */ jsxRuntimeExports.jsx("ol", { className: "space-y-2", children: steps.map((s, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("li", { className: "flex gap-3 text-sm", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "grid h-6 w-6 shrink-0 place-items-center rounded-full bg-secondary text-xs font-bold text-secondary-foreground", children: i + 1 }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "pt-0.5", children: s })
    ] }, i)) }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Section, { label: "Hashtags", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-2", children: trend.hashtags.map((h) => /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "rounded-full bg-muted px-3 py-1 text-xs font-medium text-foreground/80", children: h }, h)) }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { onClick: onClose, className: "mt-2 h-11 w-full", variant: "outline", children: "Close" })
  ] }) });
}
function Section({ label, children }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-4 space-y-2", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-xs font-bold uppercase tracking-wide text-muted-foreground", children: label }),
    children
  ] });
}
function ApiErrorBanner({ message = "Service temporarily unavailable" }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 rounded-xl border border-primary/30 bg-primary/10 px-4 py-3 text-sm text-primary", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx(TriangleAlert, { className: "h-4 w-4 shrink-0" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: message })
  ] });
}
const NICHES = [
  { id: "dance", emoji: "💃", label: "Dance" },
  { id: "fashion", emoji: "👗", label: "Fashion" },
  { id: "travel", emoji: "✈️", label: "Travel" },
  { id: "food", emoji: "🍳", label: "Food" },
  { id: "comedy", emoji: "😂", label: "Comedy" },
  { id: "motivation", emoji: "💪", label: "Motivation" },
  { id: "devotional", emoji: "🙏", label: "Devotional" },
  { id: "fitness", emoji: "🏋️", label: "Fitness" },
  { id: "study", emoji: "📚", label: "Study" },
  { id: "scenic", emoji: "🎬", label: "Cinematic" }
];
const LANGUAGES$1 = [
  { code: "hi", emoji: "🇮🇳", label: "Hindi" },
  { code: "kn", emoji: "🎯", label: "Kannada" },
  { code: "ta", emoji: "🌴", label: "Tamil" },
  { code: "te", emoji: "🌟", label: "Telugu" },
  { code: "bn", emoji: "🐯", label: "Bengali" },
  { code: "mr", emoji: "🦁", label: "Marathi" },
  { code: "en", emoji: "🌐", label: "English" }
];
function OnboardingFlow({ onComplete }) {
  const [step, setStep] = reactExports.useState(1);
  const [niche, setNiche] = reactExports.useState("");
  const [language, setLanguage] = reactExports.useState("");
  const [email, setEmail] = reactExports.useState("");
  const [submitting, setSubmitting] = reactExports.useState(false);
  const [done, setDone] = reactExports.useState(false);
  reactExports.useEffect(() => {
    const saved = localStorage.getItem("trendrop_email");
    if (saved) setEmail(saved);
  }, []);
  const handleSubmit = async () => {
    if (!email.includes("@")) return;
    setSubmitting(true);
    try {
      await subscribe({ email, niche: niche || "all", language: language || "en" });
      localStorage.setItem("trendrop_email", email);
      localStorage.setItem("trendrop_niche", niche);
      localStorage.setItem("trendrop_language", language);
      setDone(true);
      setTimeout(onComplete, 1800);
    } catch {
      localStorage.setItem("trendrop_email", email);
      setDone(true);
      setTimeout(onComplete, 1800);
    } finally {
      setSubmitting(false);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "w-full max-w-lg animate-scale-in rounded-t-3xl bg-[#0e0e1a] border border-border p-6 pb-10 shadow-2xl", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between mb-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-1.5", children: [1, 2, 3].map((s) => /* @__PURE__ */ jsxRuntimeExports.jsx(
        "div",
        {
          className: `h-1.5 w-8 rounded-full transition-all ${step >= s ? "bg-primary" : "bg-muted"}`
        },
        s
      )) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onComplete, className: "text-muted-foreground hover:text-foreground", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "h-5 w-5" }) })
    ] }),
    done ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center gap-4 py-8 text-center animate-fade-in-up", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(CircleCheckBig, { className: "h-12 w-12 text-success" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "font-display text-2xl font-bold", children: "You're in! 🎉" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-muted-foreground", children: "We'll alert you the moment a trend matches your vibe." })
    ] }) : step === 1 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-5 animate-fade-in-up", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs font-bold uppercase tracking-widest text-primary mb-1", children: "Step 1 of 3" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "font-display text-2xl font-bold", children: "Pick your vibe 🎨" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-sm text-muted-foreground", children: "What kind of content do you create?" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-5 gap-2", children: NICHES.map((n) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setNiche(n.id),
          className: `flex flex-col items-center gap-1 rounded-xl p-2.5 text-center transition-all ${niche === n.id ? "bg-primary/20 border border-primary text-primary" : "bg-muted/50 border border-transparent text-muted-foreground hover:border-border"}`,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xl", children: n.emoji }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] font-semibold leading-tight", children: n.label })
          ]
        },
        n.id
      )) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        Button,
        {
          onClick: () => setStep(2),
          disabled: !niche,
          className: "w-full h-12 bg-primary font-bold uppercase tracking-wide",
          children: "Next →"
        }
      )
    ] }) : step === 2 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-5 animate-fade-in-up", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs font-bold uppercase tracking-widest text-primary mb-1", children: "Step 2 of 3" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "font-display text-2xl font-bold", children: "Your language? 🌍" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-sm text-muted-foreground", children: "We'll show you trends in your language first." })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-4 gap-2", children: LANGUAGES$1.map((l) => /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: () => setLanguage(l.code),
          className: `flex flex-col items-center gap-1 rounded-xl p-3 text-center transition-all ${language === l.code ? "bg-primary/20 border border-primary text-primary" : "bg-muted/50 border border-transparent text-muted-foreground hover:border-border"}`,
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-xl", children: l.emoji }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] font-semibold", children: l.label })
          ]
        },
        l.code
      )) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { onClick: () => setStep(1), variant: "ghost", className: "flex-1 h-12", children: "← Back" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          Button,
          {
            onClick: () => setStep(3),
            disabled: !language,
            className: "flex-1 h-12 bg-primary font-bold uppercase tracking-wide",
            children: "Next →"
          }
        )
      ] })
    ] }) : /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-5 animate-fade-in-up", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs font-bold uppercase tracking-widest text-primary mb-1", children: "Step 3 of 3" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "font-display text-2xl font-bold", children: "Get early alerts ⚡" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-sm text-muted-foreground", children: "We'll email you the moment a trend hits your niche — before anyone else." })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-primary/5 border border-primary/20 p-4", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-muted-foreground mb-1 font-semibold", children: "Your preferences" }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-primary font-bold", children: [
            NICHES.find((n) => n.id === niche)?.emoji,
            " ",
            NICHES.find((n) => n.id === niche)?.label
          ] }),
          " ",
          "•",
          " ",
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-primary font-bold", children: [
            LANGUAGES$1.find((l) => l.code === language)?.emoji,
            " ",
            LANGUAGES$1.find((l) => l.code === language)?.label
          ] })
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "input",
        {
          type: "email",
          value: email,
          onChange: (e) => setEmail(e.target.value),
          placeholder: "your@email.com",
          className: "w-full rounded-xl bg-muted/60 px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { onClick: () => setStep(2), variant: "ghost", className: "flex-1 h-12", children: "← Back" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(
          Button,
          {
            onClick: handleSubmit,
            disabled: submitting || !email.includes("@"),
            className: "flex-1 h-12 bg-primary font-bold uppercase tracking-wide",
            children: submitting ? "Setting up..." : "Start Dropping 🔥"
          }
        )
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: onComplete, className: "w-full text-center text-xs text-muted-foreground hover:text-foreground", children: "Skip for now" })
    ] })
  ] }) });
}
const LANGUAGES = [{
  code: "all",
  label: "🌐 All"
}, {
  code: "hi",
  label: "🇮🇳 Hindi"
}, {
  code: "kn",
  label: "🎯 Kannada"
}, {
  code: "ta",
  label: "🌴 Tamil"
}, {
  code: "te",
  label: "🌟 Telugu"
}, {
  code: "bn",
  label: "🐯 Bengali"
}, {
  code: "mr",
  label: "🦁 Marathi"
}, {
  code: "en",
  label: "🌐 English"
}];
function TrendsFeed() {
  const navigate = useNavigate();
  const [filter, setFilter] = reactExports.useState("All");
  const [language, setLanguage] = reactExports.useState("all");
  const [feedTab, setFeedTab] = reactExports.useState("rising");
  const [sortMode] = reactExports.useState("velocity");
  const [danceTrend, setDanceTrend] = reactExports.useState(null);
  const [searchQuery, setSearchQuery] = reactExports.useState("");
  const [showOnboarding, setShowOnboarding] = reactExports.useState(false);
  const [, setNow] = reactExports.useState(Date.now());
  const prevCountRef = reactExports.useRef(0);
  reactExports.useEffect(() => {
    const visited = localStorage.getItem("trendrop_visited");
    if (!visited) {
      setShowOnboarding(true);
      localStorage.setItem("trendrop_visited", "1");
    }
  }, []);
  reactExports.useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 6e4);
    return () => clearInterval(id);
  }, []);
  const {
    data: risingData,
    isLoading: risingLoading,
    isError: risingError,
    refetch: refetchRising
  } = useQuery({
    queryKey: ["trends", language, sortMode],
    queryFn: () => fetchTrends(language, sortMode),
    staleTime: 3 * 6e4,
    refetchInterval: 5 * 6e4
  });
  const {
    data: emergingData,
    isLoading: emergingLoading,
    isError: emergingError,
    refetch: refetchEmerging
  } = useQuery({
    queryKey: ["trends-emerging", language],
    queryFn: () => fetchEmergingTrends(language),
    staleTime: 3 * 6e4,
    refetchInterval: 5 * 6e4
  });
  const emergingCount = emergingData?.length ?? 0;
  reactExports.useEffect(() => {
    if (emergingCount > prevCountRef.current && prevCountRef.current > 0) {
      const diff = emergingCount - prevCountRef.current;
      toast(`🚨 ${diff} new emerging trend${diff > 1 ? "s" : ""} just detected!`, {
        description: "Switch to the Emerging tab to see them first.",
        action: {
          label: "View",
          onClick: () => setFeedTab("emerging")
        }
      });
    }
    prevCountRef.current = emergingCount;
  }, [emergingCount]);
  const activeData = feedTab === "rising" ? risingData : emergingData;
  const isLoading = feedTab === "rising" ? risingLoading : emergingLoading;
  const isError = feedTab === "rising" ? risingError : emergingError;
  const refetch = feedTab === "rising" ? refetchRising : refetchEmerging;
  const trends = reactExports.useMemo(() => {
    const list = activeData ?? [];
    const byCategory = filter === "All" ? list : list.filter((t) => t.category === filter);
    if (!searchQuery.trim()) return byCategory;
    const q = searchQuery.toLowerCase();
    return byCategory.filter((t) => t.song?.toLowerCase().includes(q) || t.artist?.toLowerCase().includes(q) || t.contentType?.toLowerCase().includes(q));
  }, [activeData, filter, searchQuery]);
  const withCountdown = (t) => ({
    ...t,
    hoursLeft: Math.max(0, Math.ceil((t.expiresAt - Date.now()) / 36e5))
  });
  const totalActive = (risingData?.length ?? 0) + (emergingData?.length ?? 0);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-0 pb-24", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative overflow-hidden bg-gradient-to-b from-[rgba(230,57,70,0.08)] to-transparent px-4 pb-5 pt-6", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "pointer-events-none absolute -top-10 left-1/2 h-40 w-40 -translate-x-1/2 rounded-full bg-primary/20 blur-3xl" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative flex items-start justify-between", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-3 animate-drop-fall", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-secondary shadow-lg shadow-primary/30 text-white text-xl font-bold", children: "◈" }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "font-display text-3xl font-extrabold tracking-tight gradient-text", children: "TRENDROP" })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-xs text-muted-foreground", children: "Know before they know 🇮🇳" })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex items-center gap-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: () => navigate({
          to: "/profile"
        }), className: "relative rounded-full bg-muted p-2.5 text-foreground transition-colors hover:bg-muted/70", "aria-label": "Notifications", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Bell, { className: "h-5 w-5" }),
          emergingCount > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-[#ff006e] text-[8px] font-bold text-white", children: emergingCount })
        ] }) })
      ] }),
      totalActive > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-4 overflow-hidden rounded-full border border-primary/20 bg-primary/5 px-4 py-2", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-center text-xs font-semibold text-primary", children: [
        "🔥 ",
        totalActive,
        " active trends detected right now •",
        " ",
        emergingCount > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-[#ff006e]", children: [
          emergingCount,
          " emerging early ⚡"
        ] })
      ] }) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "sticky top-0 z-20 bg-background/90 backdrop-blur-xl px-4 pt-3 pb-2 border-b border-border", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-1 rounded-xl bg-muted p-1 mb-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(TabButton, { active: feedTab === "rising", onClick: () => setFeedTab("rising"), icon: /* @__PURE__ */ jsxRuntimeExports.jsx(TrendingUp, { className: "h-3.5 w-3.5" }), label: "Rising", count: risingData?.length }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(TabButton, { active: feedTab === "emerging", onClick: () => setFeedTab("emerging"), icon: /* @__PURE__ */ jsxRuntimeExports.jsx(Zap, { className: "h-3.5 w-3.5" }), label: "Emerging", count: emergingCount, urgent: true })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative mb-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Search, { className: "absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("input", { value: searchQuery, onChange: (e) => setSearchQuery(e.target.value), placeholder: "Search song or artist...", className: "w-full rounded-xl bg-muted/60 py-2.5 pl-9 pr-9 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" }),
        searchQuery && /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setSearchQuery(""), className: "absolute right-3 top-1/2 -translate-y-1/2", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "h-4 w-4 text-muted-foreground" }) })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-2 overflow-x-auto no-scrollbar pb-1 mb-2", children: LANGUAGES.map((l) => /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setLanguage(l.code), className: `shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold transition-all ${language === l.code ? "bg-primary text-white shadow-sm shadow-primary/30" : "bg-muted text-muted-foreground hover:text-foreground"}`, children: l.label }, l.code)) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(FilterPills, { active: filter, onChange: setFilter })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4 px-4 pt-4", children: [
      feedTab === "emerging" && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-xl border border-[#ff006e]/30 bg-[rgba(255,0,110,0.05)] p-3", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-[#ff006e] font-semibold", children: [
        "⚡ ",
        /* @__PURE__ */ jsxRuntimeExports.jsx("strong", { children: "Early Access Feed" }),
        " — These trends were detected in the last 6 hours. You are seeing them before they go mainstream. Act fast!"
      ] }) }),
      isError && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(ApiErrorBanner, {}),
        /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => refetch(), className: "text-xs font-semibold text-primary underline", children: "Try again" })
      ] }),
      isLoading ? /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(SkeletonCard, {}),
        /* @__PURE__ */ jsxRuntimeExports.jsx(SkeletonCard, {}),
        /* @__PURE__ */ jsxRuntimeExports.jsx(SkeletonCard, {})
      ] }) : !isError && trends.length === 0 ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-12 text-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-4xl mb-3", children: "🎵" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-base font-semibold", children: "No trends right now" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-sm text-muted-foreground", children: feedTab === "emerging" ? "No emerging trends detected yet. Check back in an hour!" : "Our scrapers are working. New trends will appear soon." })
      ] }) : trends.map((t) => /* @__PURE__ */ jsxRuntimeExports.jsx(TrendCard, { trend: withCountdown(t), onDanceTap: setDanceTrend }, t.id))
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(DanceTrendModal, { trend: danceTrend, onClose: () => setDanceTrend(null) }),
    showOnboarding && /* @__PURE__ */ jsxRuntimeExports.jsx(OnboardingFlow, { onComplete: () => setShowOnboarding(false) })
  ] });
}
function TabButton({
  active,
  onClick,
  icon,
  label,
  count,
  urgent
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick, className: `flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-bold uppercase tracking-wide transition-all ${active ? urgent ? "bg-[#ff006e] text-white shadow-sm shadow-[rgba(255,0,110,0.3)]" : "bg-primary text-white shadow-sm shadow-primary/30" : "text-muted-foreground hover:text-foreground"}`, children: [
    icon,
    label,
    count !== void 0 && count > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: `rounded-full px-1.5 py-0.5 text-[9px] font-extrabold ${active ? "bg-white/20" : urgent ? "bg-[#ff006e]/20 text-[#ff006e]" : "bg-primary/15 text-primary"}`, children: count })
  ] });
}
export {
  TrendsFeed as component
};
