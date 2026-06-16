import { b as QueryClient } from "../_libs/tanstack__query-core.mjs";
import { Q as QueryClientProvider, u as useQuery } from "../_libs/tanstack__react-query.mjs";
import { c as createRouter, a as createRootRouteWithContext, u as useRouter, L as Link, O as Outlet, H as HeadContent, S as Scripts, b as createFileRoute, l as lazyRouteComponent, d as useRouterState } from "../_libs/tanstack__react-router.mjs";
import { r as reactExports, j as jsxRuntimeExports } from "../_libs/react.mjs";
import { T as Toaster } from "../_libs/sonner.mjs";
import { F as Flame, S as Sparkles, C as ChartColumn, U as User, X, D as Download } from "../_libs/lucide-react.mjs";
import { o as objectType, s as stringType } from "../_libs/zod.mjs";
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
const appCss = "/assets/styles-D-n4XtJ6.css";
function reportLovableError(error, context = {}) {
  if (typeof window === "undefined") return;
  window.__lovableEvents?.captureException?.(
    error,
    {
      source: "react_error_boundary",
      route: window.location.pathname,
      ...context
    },
    {
      mechanism: "react_error_boundary",
      handled: false,
      severity: "error"
    }
  );
}
const API_URL = "http://localhost:8000"?.replace(/\/$/, "") ?? "";
const CATEGORY_EMOJI = {
  dance: { emoji: "💃", category: "Dance" },
  scenic: { emoji: "🎬", category: "Scenic" },
  fashion: { emoji: "👗", category: "Fashion" },
  travel: { emoji: "✈️", category: "Travel" },
  food: { emoji: "🍳", category: "Food" },
  comedy: { emoji: "😂", category: "Comedy" },
  devotional: { emoji: "🙏", category: "Devotional" },
  festival: { emoji: "🪔", category: "Festival" },
  motivation: { emoji: "💪", category: "Motivation" },
  fitness: { emoji: "🏋️", category: "Fitness" },
  study: { emoji: "📚", category: "Study" },
  narrative_edit: { emoji: "🎞️", category: "Narrative" },
  text_overlay: { emoji: "✏️", category: "Text Overlay" },
  other: { emoji: "🔥", category: "Viral" },
  viral: { emoji: "🔥", category: "Viral" }
};
const LANGUAGE_INFO = {
  hi: { emoji: "🇮🇳", label: "Hindi" },
  kn: { emoji: "🎯", label: "Kannada" },
  ta: { emoji: "🌴", label: "Tamil" },
  te: { emoji: "🌟", label: "Telugu" },
  bn: { emoji: "🐯", label: "Bengali" },
  mr: { emoji: "🦁", label: "Marathi" },
  en: { emoji: "🌐", label: "English" }
};
function adaptTrend(t) {
  const key = (t.content_type || "viral").toLowerCase();
  const meta = CATEGORY_EMOJI[key] ?? { emoji: "🔥", category: "Viral" };
  const hours = Math.max(0, Number(t.window_hours_remaining) || 0);
  const langInfo = LANGUAGE_INFO[(t.language ?? "").toLowerCase()] ?? null;
  return {
    id: String(t.id),
    song: t.song || t.audio_title || "Unknown Song",
    artist: t.artist || t.audio_artist || "Unknown Artist",
    hoursLeft: Math.round(hours),
    expiresAt: Date.now() + hours * 3600 * 1e3,
    viralMultiplier: Math.round((Number(t.velocity_avg) || 0) * 10) / 10,
    contentType: meta.category,
    contentTypeEmoji: meta.emoji,
    category: meta.category,
    language: langInfo?.label ?? t.language ?? void 0,
    languageEmoji: langInfo?.emoji ?? (t.language ? "🌍" : void 0),
    languageLabel: langInfo?.label,
    isDance: !!t.is_dance,
    isNarrativeEdit: !!t.narrative_edit,
    idealContentDescription: t.ideal_content_description ?? "",
    cameraStyle: t.camera_style ?? "",
    hashtags: t.hashtags ?? [],
    // New v2 fields
    status: t.status ?? "rising",
    saturationScore: t.saturation_score ?? 0,
    optimalPostHourIst: t.optimal_post_hour_ist,
    bestPlatformFirst: t.best_platform_first ?? "instagram",
    whyThisWorks: t.why_this_works,
    audioCueSecond: t.audio_cue_second,
    reelCount: t.reel_count,
    isEmerging: t.status === "emerging"
  };
}
async function http(path, init) {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}
async function fetchTrends(language, sort) {
  const params = new URLSearchParams();
  if (language && language !== "all") params.set("language", language);
  if (sort) params.set("sort", sort);
  const qs = params.toString() ? `?${params}` : "";
  const data = await http(`/api/trends${qs}`);
  const list = Array.isArray(data) ? data : data.trends ?? [];
  return list.map(adaptTrend);
}
async function fetchEmergingTrends(language) {
  const qs = language && language !== "all" ? `?language=${language}` : "";
  const data = await http(`/api/trends/emerging${qs}`);
  return data.map(adaptTrend);
}
async function fetchTrendById(id) {
  const data = await http(`/api/trends/${encodeURIComponent(id)}`);
  return adaptTrend(data);
}
async function fetchSimilarTrends(trendId) {
  const data = await http(`/api/trends/${encodeURIComponent(trendId)}/similar`);
  return data.map(adaptTrend);
}
async function fetchCaptionKit(trendId) {
  return http(`/api/trends/${encodeURIComponent(trendId)}/caption`);
}
async function fetchTrendReels(trendId) {
  return http(`/api/trends/${encodeURIComponent(trendId)}/reels`);
}
async function generateReel(args) {
  const fd = new FormData();
  args.files.forEach((f) => fd.append("files", f));
  fd.append("trend_id", args.trendId);
  fd.append("user_email", args.userEmail);
  return http("/api/generate-reel", { method: "POST", body: fd });
}
async function reelStatus(jobId) {
  return http(`/api/reel-status/${encodeURIComponent(jobId)}`);
}
function resolveOutputUrl(outputUrl) {
  if (/^https?:\/\//i.test(outputUrl)) return outputUrl;
  return `${API_URL}/${outputUrl.replace(/^\//, "")}`;
}
async function subscribe(body) {
  await http("/api/subscribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
}
function BottomTabBar() {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const { data: emergingTrends } = useQuery({
    queryKey: ["trends-emerging", "all"],
    queryFn: () => fetchEmergingTrends(),
    staleTime: 5 * 6e4,
    refetchInterval: 5 * 6e4
  });
  const emergingCount = emergingTrends?.length ?? 0;
  const tabs = [
    { to: "/", label: "Trends", Icon: Flame, badge: 0 },
    { to: "/generate", label: "Generate", Icon: Sparkles, badge: 0 },
    { to: "/stats", label: "Dashboard", Icon: ChartColumn, badge: 0 },
    { to: "/profile", label: "Profile", Icon: User, badge: 0 }
  ];
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("nav", { className: "fixed bottom-0 left-1/2 z-50 w-full max-w-md -translate-x-1/2 border-t border-border bg-background/95 backdrop-blur-md", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("ul", { className: "grid grid-cols-4", children: tabs.map(({ to, label, Icon }) => {
      const isActive = to === "/" ? currentPath === "/" : currentPath.startsWith(to);
      return /* @__PURE__ */ jsxRuntimeExports.jsx("li", { children: /* @__PURE__ */ jsxRuntimeExports.jsxs(
        Link,
        {
          to,
          className: `relative flex flex-col items-center gap-1 py-3 text-xs font-medium transition-colors ${isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"}`,
          children: [
            isActive && /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "absolute top-0 left-1/2 h-0.5 w-6 -translate-x-1/2 rounded-full bg-primary" }),
            /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "relative", children: [
              /* @__PURE__ */ jsxRuntimeExports.jsx(Icon, { className: "h-5 w-5" }),
              label === "Trends" && emergingCount > 0 && /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "absolute -right-2 -top-2 flex h-4 w-4 items-center justify-center rounded-full bg-[#ff006e] text-[8px] font-extrabold text-white", children: emergingCount })
            ] }),
            /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px]", children: label })
          ]
        }
      ) }, to);
    }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-[env(safe-area-inset-bottom)]" })
  ] });
}
const DISMISS_KEY = "trendrop_install_dismissed";
const DELAY_MS = 3e4;
function InstallBanner() {
  const [deferred, setDeferred] = reactExports.useState(null);
  const [visible, setVisible] = reactExports.useState(false);
  reactExports.useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem(DISMISS_KEY)) return;
    const isStandalone = window.matchMedia("(display-mode: standalone)").matches || // @ts-expect-error iOS Safari
    window.navigator.standalone === true;
    if (isStandalone) return;
    const onPrompt = (e) => {
      e.preventDefault();
      setDeferred(e);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    const timer = window.setTimeout(() => setVisible(true), DELAY_MS);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.clearTimeout(timer);
    };
  }, []);
  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, "1");
    setVisible(false);
  };
  const install = async () => {
    if (!deferred) {
      dismiss();
      return;
    }
    try {
      await deferred.prompt();
      const { outcome } = await deferred.userChoice;
      if (outcome === "accepted" || outcome === "dismissed") {
        localStorage.setItem(DISMISS_KEY, "1");
      }
    } catch {
    } finally {
      setDeferred(null);
      setVisible(false);
    }
  };
  if (!visible) return null;
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "fixed inset-x-0 bottom-20 z-50 mx-auto flex w-full max-w-md justify-center px-4 animate-in slide-in-from-bottom-8 duration-300", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "w-full rounded-2xl border border-white/10 bg-[#15151c] p-4 shadow-2xl", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#E63946] text-white font-bold", children: "T" }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex-1", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("h3", { className: "text-sm font-semibold text-white", children: "Install Trendrop on your home screen" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-0.5 text-xs text-[#888888]", children: "Get instant trend alerts" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: dismiss,
          "aria-label": "Dismiss",
          className: "rounded-full p-1 text-[#888888] hover:bg-white/5 hover:text-white",
          children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "h-4 w-4" })
        }
      )
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-3 flex gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: dismiss,
          className: "flex-1 rounded-xl border border-white/10 px-4 py-2.5 text-sm font-medium text-white hover:bg-white/5",
          children: "Not now"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(
        "button",
        {
          onClick: install,
          className: "flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-[#E63946] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#E63946]/90",
          children: [
            /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "h-4 w-4" }),
            "Install"
          ]
        }
      )
    ] })
  ] }) });
}
const SW_URL = "/sw.js";
function isRefusedContext() {
  if (typeof window === "undefined") return true;
  try {
    if (window.self !== window.top) return true;
  } catch {
    return true;
  }
  const url = new URL(window.location.href);
  if (url.searchParams.get("sw") === "off") return true;
  const h = window.location.hostname;
  if (h.startsWith("id-preview--") || h.startsWith("preview--") || h === "lovableproject.com" || h.endsWith(".lovableproject.com") || h === "lovableproject-dev.com" || h.endsWith(".lovableproject-dev.com") || h === "beta.lovable.dev" || h.endsWith(".beta.lovable.dev")) {
    return true;
  }
  return false;
}
async function unregisterExisting() {
  if (!("serviceWorker" in navigator)) return;
  try {
    const regs = await navigator.serviceWorker.getRegistrations();
    await Promise.all(
      regs.filter((r) => r.active?.scriptURL?.endsWith(SW_URL)).map((r) => r.unregister())
    );
  } catch {
  }
}
function registerPWA() {
  if (typeof window === "undefined") return;
  if (isRefusedContext()) {
    void unregisterExisting();
    return;
  }
  if (!("serviceWorker" in navigator)) return;
  window.addEventListener("load", () => {
    navigator.serviceWorker.register(SW_URL, { scope: "/" }).catch(() => {
    });
  });
}
function NotFoundComponent() {
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex min-h-screen items-center justify-center bg-background px-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-md text-center", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-7xl font-bold text-primary", children: "404" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "mt-4 text-xl font-semibold", children: "Page not found" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-2 text-sm text-muted-foreground", children: "The page you're looking for doesn't exist or has been moved." }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mt-6", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Link, { to: "/", className: "inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90", children: "Go home" }) })
  ] }) });
}
function ErrorComponent({ error, reset }) {
  console.error(error);
  const router2 = useRouter();
  reactExports.useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);
  return /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "flex min-h-screen items-center justify-center bg-background px-4", children: /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "max-w-md text-center", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-xl font-semibold", children: "This page didn't load" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-2 text-sm text-muted-foreground", children: "Something went wrong on our end." }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mt-6 flex flex-wrap justify-center gap-2", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx(
        "button",
        {
          onClick: () => {
            router2.invalidate();
            reset();
          },
          className: "inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90",
          children: "Try again"
        }
      ),
      /* @__PURE__ */ jsxRuntimeExports.jsx("a", { href: "/", className: "inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent", children: "Go home" })
    ] })
  ] }) });
}
const Route$5 = createRootRouteWithContext()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1, viewport-fit=cover" },
      { title: "Trendrop — India's Trend Intelligence" },
      { name: "description", content: "Know what's trending before your competitor even opens Instagram. India-first AI trend detection for Instagram Reels and YouTube Shorts." },
      { name: "theme-color", content: "#E63946" },
      { name: "apple-mobile-web-app-capable", content: "yes" },
      { name: "apple-mobile-web-app-status-bar-style", content: "black" },
      { name: "apple-mobile-web-app-title", content: "Trendrop" },
      { property: "og:title", content: "Trendrop — Know before they know" },
      { property: "og:description", content: "India's first AI trend intelligence for short-form creators. Detect trends before they peak." },
      { property: "og:type", content: "website" }
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "manifest", href: "/manifest.webmanifest" },
      { rel: "apple-touch-icon", href: "/icon-192.png" },
      { rel: "icon", type: "image/png", sizes: "192x192", href: "/icon-192.png" },
      { rel: "icon", type: "image/png", sizes: "512x512", href: "/icon-512.png" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600;700;800&display=swap" }
    ]
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent
});
function RootShell({ children }) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("html", { lang: "en", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("head", { children: /* @__PURE__ */ jsxRuntimeExports.jsx(HeadContent, {}) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("body", { children: [
      children,
      /* @__PURE__ */ jsxRuntimeExports.jsx(Scripts, {})
    ] })
  ] });
}
function RootComponent() {
  const { queryClient } = Route$5.useRouteContext();
  reactExports.useEffect(() => {
    registerPWA();
  }, []);
  return /* @__PURE__ */ jsxRuntimeExports.jsxs(QueryClientProvider, { client: queryClient, children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "mx-auto flex min-h-screen w-full max-w-md flex-col bg-background pb-24", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Outlet, {}) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(BottomTabBar, {}),
    /* @__PURE__ */ jsxRuntimeExports.jsx(InstallBanner, {}),
    /* @__PURE__ */ jsxRuntimeExports.jsx(
      Toaster,
      {
        position: "top-center",
        toastOptions: {
          style: {
            background: "#111120",
            border: "1px solid rgba(255,255,255,0.08)",
            color: "#f0f0ff",
            fontFamily: "Inter, sans-serif"
          }
        }
      }
    )
  ] });
}
const $$splitComponentImporter$4 = () => import("./stats-DmFUjw6R.mjs");
const Route$4 = createFileRoute("/stats")({
  head: () => ({
    meta: [{
      title: "Dashboard — Trendrop"
    }, {
      name: "description",
      content: "Track your creator performance and stats."
    }]
  }),
  component: lazyRouteComponent($$splitComponentImporter$4, "component")
});
const $$splitComponentImporter$3 = () => import("./profile-dA2xL3Re.mjs");
const Route$3 = createFileRoute("/profile")({
  head: () => ({
    meta: [{
      title: "Profile — Trendrop"
    }, {
      name: "description",
      content: "Personalize your trend feed and alert preferences."
    }]
  }),
  component: lazyRouteComponent($$splitComponentImporter$3, "component")
});
const $$splitComponentImporter$2 = () => import("./generate-BcGOa_-q.mjs");
const searchSchema = objectType({
  trendId: stringType().optional()
});
const Route$2 = createFileRoute("/generate")({
  validateSearch: searchSchema,
  head: () => ({
    meta: [{
      title: "Generate your reel — Trendrop"
    }, {
      name: "description",
      content: "Upload your photos and create a viral reel in seconds."
    }]
  }),
  component: lazyRouteComponent($$splitComponentImporter$2, "component")
});
const $$splitComponentImporter$1 = () => import("./index-CjgCzGK3.mjs");
const Route$1 = createFileRoute("/")({
  head: () => ({
    meta: [{
      title: "Trendrop — India's Trend Intelligence"
    }, {
      name: "description",
      content: "Know what's trending before your competitor even opens Instagram. India-first AI trend detection."
    }]
  }),
  component: lazyRouteComponent($$splitComponentImporter$1, "component")
});
const $$splitComponentImporter = () => import("./trend._id-DMZ7poiZ.mjs");
const Route = createFileRoute("/trend/$id")({
  head: () => ({
    meta: [{
      title: "Trend Details — Trendrop"
    }, {
      name: "description",
      content: "Deep dive into this trend: caption kit, timing, strategy."
    }]
  }),
  component: lazyRouteComponent($$splitComponentImporter, "component")
});
const StatsRoute = Route$4.update({
  id: "/stats",
  path: "/stats",
  getParentRoute: () => Route$5
});
const ProfileRoute = Route$3.update({
  id: "/profile",
  path: "/profile",
  getParentRoute: () => Route$5
});
const GenerateRoute = Route$2.update({
  id: "/generate",
  path: "/generate",
  getParentRoute: () => Route$5
});
const IndexRoute = Route$1.update({
  id: "/",
  path: "/",
  getParentRoute: () => Route$5
});
const TrendIdRoute = Route.update({
  id: "/trend/$id",
  path: "/trend/$id",
  getParentRoute: () => Route$5
});
const rootRouteChildren = {
  IndexRoute,
  GenerateRoute,
  ProfileRoute,
  StatsRoute,
  TrendIdRoute
};
const routeTree = Route$5._addFileChildren(rootRouteChildren)._addFileTypes();
const getRouter = () => {
  const queryClient = new QueryClient();
  const router2 = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0
  });
  return router2;
};
const router = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  getRouter
}, Symbol.toStringTag, { value: "Module" }));
export {
  Route$2 as R,
  resolveOutputUrl as a,
  fetchTrendReels as b,
  fetchEmergingTrends as c,
  Route as d,
  fetchTrendById as e,
  fetchTrends as f,
  generateReel as g,
  fetchCaptionKit as h,
  fetchSimilarTrends as i,
  router as j,
  reelStatus as r,
  subscribe as s
};
