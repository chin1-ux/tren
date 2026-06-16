import { r as reactExports, j as jsxRuntimeExports } from "../_libs/react.mjs";
import { e as useNavigate } from "../_libs/tanstack__react-router.mjs";
import { u as useQuery } from "../_libs/tanstack__react-query.mjs";
import { R as Route$2, f as fetchTrends, g as generateReel, r as reelStatus, a as resolveOutputUrl } from "./router-CZKcgiHH.mjs";
import { B as Button } from "./button-DjOZMqFS.mjs";
import "../_libs/sonner.mjs";
import { F as Flame, d as Upload, X, D as Download, e as Share2, f as TriangleAlert } from "../_libs/lucide-react.mjs";
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
function GeneratePage() {
  const {
    trendId
  } = Route$2.useSearch();
  const navigate = useNavigate();
  const {
    data: trends
  } = useQuery({
    queryKey: ["trends"],
    queryFn: () => fetchTrends(),
    staleTime: 6e4
  });
  const trend = trends && Array.isArray(trends) ? trends.find((t) => t.id === trendId) ?? trends[0] : void 0;
  const [stage, setStage] = reactExports.useState("upload");
  const [photos, setPhotos] = reactExports.useState([]);
  const [progress, setProgress] = reactExports.useState(0);
  const [statusText, setStatusText] = reactExports.useState("Starting...");
  const [outputUrl, setOutputUrl] = reactExports.useState(null);
  const [errorMsg, setErrorMsg] = reactExports.useState(null);
  const inputRef = reactExports.useRef(null);
  const onFiles = (files) => {
    if (!files) return;
    const arr = Array.from(files).slice(0, 15 - photos.length);
    const next = arr.map((f) => ({
      id: crypto.randomUUID(),
      url: URL.createObjectURL(f),
      file: f
    }));
    setPhotos((p) => [...p, ...next].slice(0, 15));
  };
  const remove = (id) => {
    setPhotos((p) => {
      const target = p.find((x) => x.id === id);
      if (target) URL.revokeObjectURL(target.url);
      return p.filter((x) => x.id !== id);
    });
  };
  reactExports.useEffect(() => () => photos.forEach((p) => URL.revokeObjectURL(p.url)), []);
  const reset = () => {
    setPhotos((p) => {
      p.forEach((x) => URL.revokeObjectURL(x.url));
      return [];
    });
    setProgress(0);
    setStatusText("Starting...");
    setOutputUrl(null);
    setErrorMsg(null);
    setStage("upload");
  };
  const startGeneration = async () => {
    if (!trend) return;
    setStage("progress");
    setProgress(0);
    setStatusText("Uploading your photos...");
    try {
      const email = typeof localStorage !== "undefined" && localStorage.getItem("trendrop_email") || "anonymous@trendrop.app";
      const {
        job_id
      } = await generateReel({
        files: photos.map((p) => p.file),
        trendId: trend.id,
        userEmail: email
      });
      let stop = false;
      const poll = async () => {
        if (stop) return;
        try {
          const s = await reelStatus(job_id);
          setProgress(Math.max(0, Math.min(100, s.progress ?? 0)));
          setStatusText(statusFor(s.progress ?? 0));
          if (s.status === "complete" && (s.progress ?? 0) >= 100) {
            stop = true;
            if (s.output_url) setOutputUrl(resolveOutputUrl(s.output_url));
            setStage("result");
            return;
          }
          if (s.status === "failed") {
            stop = true;
            setErrorMsg("Something went wrong. Please try again.");
            setStage("error");
            return;
          }
          setTimeout(poll, 3e3);
        } catch {
          stop = true;
          setErrorMsg("Something went wrong. Please try again.");
          setStage("error");
        }
      };
      poll();
    } catch {
      setErrorMsg("Something went wrong. Please try again.");
      setStage("error");
    }
  };
  const download = () => {
    if (!outputUrl) return;
    const a = document.createElement("a");
    a.href = outputUrl;
    a.download = `trendrop-reel-${Date.now()}.mp4`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  };
  const share = async () => {
    if (!outputUrl) return;
    if (navigator.share) {
      try {
        await navigator.share({
          title: "My Trendrop reel",
          url: outputUrl
        });
      } catch {
      }
    } else {
      await navigator.clipboard.writeText(outputUrl);
    }
  };
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col gap-5 px-4 pb-8 pt-6", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsxs("header", { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("h1", { className: "text-2xl font-extrabold tracking-tight", children: "Generate" }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-sm text-muted-foreground", children: "Turn your photos into a viral reel" })
    ] }),
    trend && /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-start gap-3 rounded-2xl border border-border bg-card p-4", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/15 text-primary", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Flame, { className: "h-5 w-5" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "min-w-0", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs font-semibold uppercase tracking-wide text-muted-foreground", children: "Generating for" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "truncate font-bold", children: trend.song }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "truncate text-xs text-muted-foreground", children: trend.artist })
      ] })
    ] }),
    stage === "upload" && /* @__PURE__ */ jsxRuntimeExports.jsx(UploadStage, { photos, setPhotos, onFiles, onRemove: remove, inputRef, onCreate: startGeneration, disabledReason: !trend ? "Loading trend..." : void 0 }),
    stage === "progress" && /* @__PURE__ */ jsxRuntimeExports.jsx(ProgressStage, { progress, statusText }),
    stage === "result" && /* @__PURE__ */ jsxRuntimeExports.jsx(ResultStage, { videoUrl: outputUrl, onDownload: download, onShare: share, onAgain: () => {
      reset();
      navigate({
        to: "/"
      });
    } }),
    stage === "error" && /* @__PURE__ */ jsxRuntimeExports.jsx(ErrorStage, { message: errorMsg ?? "", onRetry: () => setStage("upload") })
  ] });
}
function statusFor(p) {
  if (p < 20) return "Analyzing your photos...";
  if (p < 50) return "Detecting beats in the music...";
  if (p < 80) return "Assembling your reel...";
  return "Adding finishing touches...";
}
function UploadStage({
  photos,
  setPhotos,
  onFiles,
  onRemove,
  inputRef,
  onCreate,
  disabledReason
}) {
  const canCreate = photos.length >= 3 && !disabledReason;
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("input", { ref: inputRef, type: "file", accept: "image/png,image/jpeg", multiple: true, hidden: true, onChange: (e) => onFiles(e.target.files) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("button", { onClick: () => inputRef.current?.click(), className: "flex w-full flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-border bg-card px-6 py-10 transition-colors hover:border-primary hover:bg-muted", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid h-14 w-14 place-items-center rounded-full bg-muted text-primary", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Upload, { className: "h-6 w-6" }) }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "text-center", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "font-bold", children: "Upload Your Photos" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "mt-1 text-xs text-muted-foreground", children: "Tap to select or drag and drop" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-xs text-muted-foreground", children: "Supports JPG, PNG • 3–15 photos" })
      ] })
    ] }),
    photos.length > 0 && /* @__PURE__ */ jsxRuntimeExports.jsxs(jsxRuntimeExports.Fragment, { children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex items-center justify-between", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { className: "rounded-full bg-primary/15 px-3 py-1 text-xs font-bold text-primary", children: [
          photos.length,
          " photo",
          photos.length === 1 ? "" : "s",
          " selected"
        ] }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { className: "text-[10px] text-muted-foreground", children: "↕ Drag photos to reorder" })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid grid-cols-3 gap-2", children: photos.map((p, index) => /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { draggable: true, onDragStart: (e) => {
        e.dataTransfer.setData("text/plain", index.toString());
      }, onDragOver: (e) => {
        e.preventDefault();
      }, onDrop: (e) => {
        e.preventDefault();
        const fromIndex = parseInt(e.dataTransfer.getData("text/plain"), 10);
        if (isNaN(fromIndex) || fromIndex === index) return;
        const reordered = [...photos];
        const [moved] = reordered.splice(fromIndex, 1);
        reordered.splice(index, 0, moved);
        setPhotos(reordered);
      }, className: "relative aspect-square overflow-hidden rounded-xl bg-muted cursor-move active:scale-95 transition-transform border border-transparent hover:border-primary/40", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("img", { src: p.url, alt: "", className: "h-full w-full object-cover pointer-events-none" }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("button", { onClick: () => onRemove(p.id), className: "absolute right-1 top-1 grid h-6 w-6 place-items-center rounded-full bg-background/80 text-foreground hover:bg-primary hover:text-primary-foreground z-10", children: /* @__PURE__ */ jsxRuntimeExports.jsx(X, { className: "h-3.5 w-3.5" }) }),
        /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "absolute bottom-1 left-1 bg-black/60 px-1.5 py-0.5 rounded text-[8px] font-bold text-white pointer-events-none", children: index + 1 })
      ] }, p.id)) })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "rounded-xl border border-border bg-muted/40 px-4 py-3 text-xs text-muted-foreground", children: "💡 Tip: More photos = better reel" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { disabled: !canCreate, onClick: onCreate, className: "h-13 w-full bg-primary py-4 text-base font-bold uppercase tracking-wide text-primary-foreground hover:bg-primary/90", children: disabledReason ?? "Create My Reel" })
  ] });
}
function ProgressStage({
  progress,
  statusText
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center gap-6 rounded-2xl border border-border bg-card px-6 py-12 text-center", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "animate-trendrop-spin grid h-20 w-20 place-items-center rounded-full border-4 border-muted border-t-primary", children: /* @__PURE__ */ jsxRuntimeExports.jsx(Flame, { className: "h-8 w-8 text-primary" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-xl font-bold", children: "Creating your reel..." }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "w-full", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "mb-2 flex justify-between text-xs font-semibold text-muted-foreground", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx("span", { children: statusText }),
        /* @__PURE__ */ jsxRuntimeExports.jsxs("span", { children: [
          Math.round(progress),
          "%"
        ] })
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-2 w-full overflow-hidden rounded-full bg-muted", children: /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "h-full bg-gradient-to-r from-primary to-secondary transition-all", style: {
        width: `${progress}%`
      } }) })
    ] })
  ] });
}
function ResultStage({
  videoUrl,
  onDownload,
  onShare,
  onAgain
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "space-y-4", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "text-center", children: /* @__PURE__ */ jsxRuntimeExports.jsx("h2", { className: "text-2xl font-bold", children: "Your reel is ready! 🎉" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "overflow-hidden rounded-2xl border border-border bg-black", children: videoUrl ? /* @__PURE__ */ jsxRuntimeExports.jsx("video", { src: videoUrl, autoPlay: true, muted: true, loop: true, playsInline: true, className: "aspect-[9/16] w-full object-cover" }) : /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid aspect-[9/16] w-full place-items-center text-muted-foreground", children: "No preview available" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "grid grid-cols-2 gap-3", children: [
      /* @__PURE__ */ jsxRuntimeExports.jsxs(Button, { onClick: onDownload, className: "h-12 bg-primary font-bold uppercase tracking-wide text-primary-foreground hover:bg-primary/90", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Download, { className: "h-4 w-4" }),
        " Download"
      ] }),
      /* @__PURE__ */ jsxRuntimeExports.jsxs(Button, { onClick: onShare, variant: "outline", className: "h-12 border-border font-bold uppercase tracking-wide hover:bg-muted", children: [
        /* @__PURE__ */ jsxRuntimeExports.jsx(Share2, { className: "h-4 w-4" }),
        " Share"
      ] })
    ] }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "text-center text-xs text-muted-foreground", children: "Made with Trendrop" }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { onClick: onAgain, variant: "ghost", className: "w-full text-muted-foreground hover:text-foreground", children: "Create another" })
  ] });
}
function ErrorStage({
  message,
  onRetry
}) {
  return /* @__PURE__ */ jsxRuntimeExports.jsxs("div", { className: "flex flex-col items-center gap-4 rounded-2xl border border-primary/30 bg-primary/10 p-8 text-center", children: [
    /* @__PURE__ */ jsxRuntimeExports.jsx("div", { className: "grid h-12 w-12 place-items-center rounded-full bg-primary/20 text-primary", children: /* @__PURE__ */ jsxRuntimeExports.jsx(TriangleAlert, { className: "h-6 w-6" }) }),
    /* @__PURE__ */ jsxRuntimeExports.jsx("p", { className: "font-semibold text-primary", children: message }),
    /* @__PURE__ */ jsxRuntimeExports.jsx(Button, { onClick: onRetry, className: "bg-primary text-primary-foreground hover:bg-primary/90", children: "Try Again" })
  ] });
}
export {
  GeneratePage as component
};
