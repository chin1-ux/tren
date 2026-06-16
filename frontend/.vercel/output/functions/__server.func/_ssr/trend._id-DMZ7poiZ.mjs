import { r as reactExports, j as jsxRuntimeExports } from "../_libs/react.mjs";
import { e as useNavigate } from "../_libs/tanstack__react-router.mjs";
import { u as useQuery } from "../_libs/tanstack__react-query.mjs";
import { d as Route, e as fetchTrendById, h as fetchCaptionKit, i as fetchSimilarTrends, b as fetchTrendReels } from "./router-CZKcgiHH.mjs";
import { B as Button } from "./button-DjOZMqFS.mjs";
import { t as toast } from "../_libs/sonner.mjs";
import { o as ArrowLeft, F as Flame, h as Clock, e as Share2, p as Calendar, q as Volume2, Z as Zap, i as CheckCheck, j as Copy, r as ChevronRight } from "../_libs/lucide-react.mjs";
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
function TrendDetailPage() {
  const {
    id
  } = Route.useParams();
  const navigate = useNavigate();
  const [copiedCaption, setCopiedCaption] = reactExports.useState(null);
  const [copiedHashtags, setCopiedHashtags] = reactExports.useState(false);
  const [selectedVibe, setSelectedVibe] = reactExports.useState(0);
  const {
    data: trend,
    isLoading: trendLoading
  } = useQuery({
    queryKey: ["trend", id],
    queryFn: () => fetchTrendById(id)
  });
  const {
    data: captionKit,
    isLoading: captionLoading
  } = useQuery({
    queryKey: ["caption-kit", id],
    queryFn: () => fetchCaptionKit(id),
    enabled: !!trend
  });
  const {
    data: similarTrends
  } = useQuery({
    queryKey: ["similar-trends", id],
    queryFn: () => fetchSimilarTrends(id),
    enabled: !!trend
  });
  const {
    data: reels
  } = useQuery({
    queryKey: ["trend-reels", id],
    queryFn: () => fetchTrendReels(id),
    enabled: !!trend
  });
  const copyCaption = (idx) => {
    if (!captionKit?.captions[idx]) return;
    navigator.clipboard.writeText(captionKit.captions[idx].text);
    setCopiedCaption(idx);
    toast.success("Caption copied!");
    setTimeout(() => setCopiedCaption(null), 2e3);
  };
  const copyHashtags = () => {
    if (!captionKit?.hashtags) return;
    navigator.clipboard.writeText(captionKit.hashtags.map((h) => `#${h.replace(/^#/, "")}`).join(" "));
    setCopiedHashtags(true);
    toast.success("All hashtags copied!");
    setTimeout(() => setCopiedHashtags(false), 2e3);
  };
  const shareWhatsApp = () => {
    const text = encodeURIComponent(`🔥 Trending now: "${trend?.song}" by ${trend?.artist}
📲 Check on Trendrop → trendrop.ai`);
    window.open(`https://wa.me/?text=${text}`, "_blank");
  };
  const formatHour = (h) => {
    if (h === void 0) return "7 PM";
    const period = h >= 12 ? "PM" : "AM";
    const h12 = h % 12 === 0 ? 12 : h % 12;
    return `${h12} ${period}`;
  };
  if (trendLoading) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-4 px-4 pt-6 pb-24", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: () => navigate({
        to: "/"
      }), className: "flex items-center gap-1 text-sm text-muted-foreground", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(ArrowLeft, { className: "h-4 w-4" }),
        " Back"
      ] }),
      [1, 2, 3].map((i) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-24 rounded-2xl shimmer" }, i))
    ] });
  }
  if (!trend) {
    return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center gap-4 px-4 pt-16 text-center", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-5xl", children: "🔍" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "font-semibold", children: "Trend not found" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { onClick: () => navigate({
        to: "/"
      }), children: "Back to Feed" })
    ] });
  }
  const satPct = Math.round((trend.saturationScore ?? 0) * 100);
  Math.min(100, trend.viralMultiplier / 30 * 100);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-5 px-4 pb-28 pt-5", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: () => navigate({
      to: "/"
    }), className: "flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(ArrowLeft, { className: "h-4 w-4" }),
      " Back to Feed"
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "inline-flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-1 text-xs font-bold uppercase tracking-wide text-primary", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Flame, { className: "h-3 w-3" }),
            " ",
            trend.isEmerging ? "Emerging" : "Trending"
          ] }),
          trend.languageEmoji && /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "text-sm", children: [
            trend.languageEmoji,
            " ",
            trend.languageLabel
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "flex items-center gap-1 text-xs font-semibold text-muted-foreground", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Clock, { className: "h-3.5 w-3.5" }),
          " ",
          trend.hoursLeft,
          "h left"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "font-display text-3xl font-bold leading-tight gradient-text", children: trend.song }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-sm text-muted-foreground mt-1", children: [
          "by ",
          trend.artist
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-end gap-1.5 h-10", children: [
        [7, 4, 9, 6, 10, 5, 8, 3, 7, 5].map((h, i) => /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "waveform-bar", style: {
          height: `${h * 3}px`
        } }, i)),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "ml-2 text-xs text-muted-foreground self-center", children: [
          trend.viralMultiplier,
          "x viral"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-3 gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(StatPill, { label: "Saturation", value: `${satPct}%`, color: satPct < 30 ? "text-emerald-400" : satPct < 60 ? "text-amber-400" : "text-red-400" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(StatPill, { label: "Reels", value: `${trend.reelCount ?? "–"}` }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(StatPill, { label: "Category", value: `${trend.contentTypeEmoji} ${trend.contentType}` })
      ] }),
      trend.whyThisWorks && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-muted-foreground rounded-xl bg-white/[0.03] p-3 border border-border italic", children: [
        "💡 ",
        /* @__PURE__ */ jsxRuntimeExports.jsx("strong", { children: "Why it's viral:" }),
        " ",
        trend.whyThisWorks
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs(Button, { onClick: shareWhatsApp, variant: "outline", className: "flex-1 h-10 text-xs border-border", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx(Share2, { className: "h-3.5 w-3.5" }),
          " Share on WhatsApp"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { onClick: () => navigate({
          to: "/generate",
          search: {
            trendId: id
          }
        }), className: "flex-1 h-10 text-xs bg-primary", children: "Generate Reel →" })
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h2", { className: "font-display text-lg font-bold flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Calendar, { className: "h-5 w-5 text-primary" }),
        " Posting Strategy"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-muted/50 p-3 text-center", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-muted-foreground mb-1", children: "Best Time (IST)" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "font-display font-bold text-lg text-primary", children: formatHour(trend.optimalPostHourIst) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-muted/50 p-3 text-center", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-muted-foreground mb-1", children: "Post On" }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "font-display font-bold text-lg capitalize", children: trend.bestPlatformFirst === "youtube_shorts" ? "▶ YT Shorts" : "◎ Instagram" })
        ] })
      ] }),
      captionKit?.posting_strategy?.reasoning && /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-muted-foreground italic", children: captionKit.posting_strategy.reasoning }),
      captionKit?.saturation_alert && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-xl bg-primary/5 border border-primary/20 px-3 py-2.5", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-primary font-semibold", children: [
        "⏰ ",
        captionKit.saturation_alert
      ] }) })
    ] }),
    (trend.audioCueSecond !== void 0 || captionKit?.audio_cue) && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h2", { className: "font-display text-lg font-bold flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Volume2, { className: "h-5 w-5 text-secondary" }),
        " Audio Cue"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-xl bg-secondary/10 border border-secondary/20 p-4", children: /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-semibold text-secondary", children: captionKit?.audio_cue || `Start filming at the 0:${String(trend.audioCueSecond ?? 7).padStart(2, "0")} mark` }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-muted-foreground", children: "This is the power moment in the song — nail this cue to maximize retention and replays." })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("h2", { className: "font-display text-lg font-bold flex items-center gap-2", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Zap, { className: "h-5 w-5 text-primary" }),
        " Caption Kit"
      ] }),
      captionLoading ? /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-3", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-20 rounded-xl shimmer" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-20 rounded-xl shimmer" })
      ] }) : captionKit ? /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex gap-2", children: captionKit.captions.map((c, i) => /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => setSelectedVibe(i), className: `rounded-full px-3 py-1.5 text-xs font-semibold capitalize transition-all ${selectedVibe === i ? "bg-primary text-white" : "bg-muted text-muted-foreground hover:text-foreground"}`, children: c.vibe }, i)) }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative rounded-xl bg-white/[0.03] border border-border p-4", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm leading-relaxed pr-8", children: captionKit.captions[selectedVibe]?.text }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => copyCaption(selectedVibe), className: "absolute right-3 top-3 text-muted-foreground hover:text-foreground", children: copiedCaption === selectedVibe ? /* @__PURE__ */ jsxRuntimeExports.jsx(CheckCheck, { className: "h-4 w-4 text-success" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Copy, { className: "h-4 w-4" }) })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-2", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs font-bold uppercase tracking-wide text-muted-foreground", children: "Hashtags" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: copyHashtags, className: "flex items-center gap-1 text-xs text-primary hover:underline", children: [
              copiedHashtags ? /* @__PURE__ */ jsxRuntimeExports.jsx(CheckCheck, { className: "h-3 w-3" }) : /* @__PURE__ */ jsxRuntimeExports.jsx(Copy, { className: "h-3 w-3" }),
              "Copy all"
            ] })
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex flex-wrap gap-1.5", children: captionKit.hashtags.map((tag, i) => /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "rounded-full bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary", children: [
            "#",
            tag.replace(/^#/, "")
          ] }, i)) })
        ] })
      ] }) : /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-muted-foreground", children: "Caption kit generation failed. Try again later." })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "font-display text-lg font-bold", children: "🎬 What To Film" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm text-muted-foreground leading-relaxed", children: trend.idealContentDescription }),
      trend.cameraStyle && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-2 rounded-xl bg-muted/50 px-3 py-2.5 text-xs font-semibold", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-muted-foreground", children: "Camera style:" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "capitalize text-foreground", children: trend.cameraStyle?.replace(/_/g, " ") })
      ] })
    ] }),
    reels && reels.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "font-display text-lg font-bold", children: "📱 Source Reels" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: reels.slice(0, 5).map((reel) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between rounded-xl bg-muted/40 px-3 py-2.5", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs font-bold text-primary", children: [
            "@",
            reel.owner_username
          ] }),
          reel.caption && /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs text-muted-foreground line-clamp-1 italic mt-0.5", children: [
            '"',
            reel.caption,
            '"'
          ] })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("p", { className: "text-xs font-semibold text-muted-foreground shrink-0", children: [
          reel.view_count >= 1e3 ? `${(reel.view_count / 1e3).toFixed(0)}K` : reel.view_count,
          " views"
        ] })
      ] }, reel.id)) })
    ] }),
    similarTrends && similarTrends.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "glass-card p-5 space-y-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "font-display text-lg font-bold", children: "🔗 Similar Past Trends" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "space-y-2", children: similarTrends.map((t) => /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: () => navigate({
        to: "/trend/$id",
        params: {
          id: t.id
        }
      }), className: "flex w-full items-center justify-between rounded-xl bg-muted/40 px-3 py-2.5 hover:bg-muted/60 transition-colors text-left", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { children: [
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-sm font-semibold", children: t.song }),
          /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-muted-foreground", children: t.artist })
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center gap-1 text-xs text-muted-foreground", children: [
          /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
            t.viralMultiplier,
            "x"
          ] }),
          /* @__PURE__ */ jsxRuntimeExports.jsx(ChevronRight, { className: "h-3.5 w-3.5" })
        ] })
      ] }, t.id)) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { onClick: () => navigate({
      to: "/generate",
      search: {
        trendId: id
      }
    }), className: "h-14 w-full bg-primary text-base font-bold uppercase tracking-widest shadow-lg shadow-primary/20 hover:scale-[1.01] transition-transform", children: "🎬 Generate My Reel For This Trend" })
  ] });
}
function StatPill({
  label,
  value,
  color = "text-foreground"
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "rounded-xl bg-muted/50 p-3 text-center", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-[10px] text-muted-foreground uppercase tracking-wide mb-1", children: label }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: `text-sm font-bold ${color}`, children: value })
  ] });
}
export {
  TrendDetailPage as component
};
