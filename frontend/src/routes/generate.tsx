import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Upload, X, Download, Share2, Flame, AlertTriangle } from "lucide-react";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { fetchTrends, generateReel, reelStatus, resolveOutputUrl, type UiTrend } from "@/lib/api";
import { Button } from "@/components/ui/button";

const searchSchema = z.object({ trendId: z.string().optional() });

export const Route = createFileRoute("/generate")({
  validateSearch: searchSchema,
  head: () => ({
    meta: [
      { title: "Generate your reel — Trendrop" },
      { name: "description", content: "Upload your photos and create a viral reel in seconds." },
    ],
  }),
  component: GeneratePage,
});

type Stage = "upload" | "progress" | "result" | "error";

function GeneratePage() {
  const { trendId } = Route.useSearch();
  const navigate = useNavigate();

  const { data: trends } = useQuery<UiTrend[]>({
    queryKey: ["trends"],
    queryFn: () => fetchTrends(),
    staleTime: 60_000,
  });
  const trend = trends && Array.isArray(trends) ? (trends.find((t) => t.id === trendId) ?? trends[0]) : undefined;

  const [stage, setStage] = useState<Stage>("upload");
  const [photos, setPhotos] = useState<{ id: string; url: string; file: File }[]>([]);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("Starting...");
  const [outputUrl, setOutputUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const onFiles = (files: FileList | null) => {
    if (!files) return;
    const arr = Array.from(files).slice(0, 15 - photos.length);
    const next = arr.map((f) => ({ id: crypto.randomUUID(), url: URL.createObjectURL(f), file: f }));
    setPhotos((p) => [...p, ...next].slice(0, 15));
  };

  const remove = (id: string) => {
    setPhotos((p) => {
      const target = p.find((x) => x.id === id);
      if (target) URL.revokeObjectURL(target.url);
      return p.filter((x) => x.id !== id);
    });
  };

  useEffect(() => () => photos.forEach((p) => URL.revokeObjectURL(p.url)), []); // eslint-disable-line

  const reset = () => {
    setPhotos((p) => { p.forEach((x) => URL.revokeObjectURL(x.url)); return []; });
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
      const email = (typeof localStorage !== "undefined" && localStorage.getItem("trendrop_email")) || "anonymous@trendrop.app";
      const { job_id } = await generateReel({
        files: photos.map((p) => p.file),
        trendId: trend.id,
        userEmail: email,
      });

      // Poll every 3 seconds
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
          setTimeout(poll, 3000);
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
      try { await navigator.share({ title: "My Trendrop reel", url: outputUrl }); } catch {}
    } else {
      await navigator.clipboard.writeText(outputUrl);
    }
  };

  return (
    <div className="flex flex-col gap-5 px-4 pb-8 pt-6">
      <header>
        <h1 className="text-2xl font-extrabold tracking-tight">Generate</h1>
        <p className="mt-1 text-sm text-muted-foreground">Turn your photos into a viral reel</p>
      </header>

      {trend && (
        <div className="flex items-start gap-3 rounded-2xl border border-border bg-card p-4">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary/15 text-primary">
            <Flame className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Generating for</p>
            <p className="truncate font-bold">{trend.song}</p>
            <p className="truncate text-xs text-muted-foreground">{trend.artist}</p>
          </div>
        </div>
      )}

      {stage === "upload" && (
        <UploadStage
          photos={photos}
          setPhotos={setPhotos}
          onFiles={onFiles}
          onRemove={remove}
          inputRef={inputRef}
          onCreate={startGeneration}
          disabledReason={!trend ? "Loading trend..." : undefined}
        />
      )}

      {stage === "progress" && <ProgressStage progress={progress} statusText={statusText} />}

      {stage === "result" && (
        <ResultStage
          videoUrl={outputUrl}
          onDownload={download}
          onShare={share}
          onAgain={() => { reset(); navigate({ to: "/" }); }}
        />
      )}

      {stage === "error" && <ErrorStage message={errorMsg ?? ""} onRetry={() => setStage("upload")} />}
    </div>
  );
}

function statusFor(p: number) {
  if (p < 20) return "Analyzing your photos...";
  if (p < 50) return "Detecting beats in the music...";
  if (p < 80) return "Assembling your reel...";
  return "Adding finishing touches...";
}

function UploadStage({
  photos, setPhotos, onFiles, onRemove, inputRef, onCreate, disabledReason,
}: {
  photos: { id: string; url: string; file: File }[];
  setPhotos: React.Dispatch<React.SetStateAction<{ id: string; url: string; file: File }[]>>;
  onFiles: (f: FileList | null) => void;
  onRemove: (id: string) => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onCreate: () => void;
  disabledReason?: string;
}) {
  const canCreate = photos.length >= 3 && !disabledReason;
  return (
    <div className="space-y-4">
      <input ref={inputRef} type="file" accept="image/png,image/jpeg" multiple hidden onChange={(e) => onFiles(e.target.files)} />
      <button
        onClick={() => inputRef.current?.click()}
        className="flex w-full flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-border bg-card px-6 py-10 transition-colors hover:border-primary hover:bg-muted"
      >
        <div className="grid h-14 w-14 place-items-center rounded-full bg-muted text-primary">
          <Upload className="h-6 w-6" />
        </div>
        <div className="text-center">
          <p className="font-bold">Upload Your Photos</p>
          <p className="mt-1 text-xs text-muted-foreground">Tap to select or drag and drop</p>
          <p className="text-xs text-muted-foreground">Supports JPG, PNG • 3–15 photos</p>
        </div>
      </button>

      {photos.length > 0 && (
        <>
          <div className="flex items-center justify-between">
            <span className="rounded-full bg-primary/15 px-3 py-1 text-xs font-bold text-primary">
              {photos.length} photo{photos.length === 1 ? "" : "s"} selected
            </span>
            <span className="text-[10px] text-muted-foreground">↕ Drag photos to reorder</span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {photos.map((p, index) => (
              <div
                key={p.id}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData("text/plain", index.toString());
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  const fromIndex = parseInt(e.dataTransfer.getData("text/plain"), 10);
                  if (isNaN(fromIndex) || fromIndex === index) return;
                  const reordered = [...photos];
                  const [moved] = reordered.splice(fromIndex, 1);
                  reordered.splice(index, 0, moved);
                  setPhotos(reordered);
                }}
                className="relative aspect-square overflow-hidden rounded-xl bg-muted cursor-move active:scale-95 transition-transform border border-transparent hover:border-primary/40"
              >
                <img src={p.url} alt="" className="h-full w-full object-cover pointer-events-none" />
                <button
                  onClick={() => onRemove(p.id)}
                  className="absolute right-1 top-1 grid h-6 w-6 place-items-center rounded-full bg-background/80 text-foreground hover:bg-primary hover:text-primary-foreground z-10"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
                <div className="absolute bottom-1 left-1 bg-black/60 px-1.5 py-0.5 rounded text-[8px] font-bold text-white pointer-events-none">
                  {index + 1}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      <div className="rounded-xl border border-border bg-muted/40 px-4 py-3 text-xs text-muted-foreground">
        💡 Tip: More photos = better reel
      </div>

      <Button
        disabled={!canCreate}
        onClick={onCreate}
        className="h-13 w-full bg-primary py-4 text-base font-bold uppercase tracking-wide text-primary-foreground hover:bg-primary/90"
      >
        {disabledReason ?? "Create My Reel"}
      </Button>
    </div>
  );
}

function ProgressStage({ progress, statusText }: { progress: number; statusText: string }) {
  return (
    <div className="flex flex-col items-center gap-6 rounded-2xl border border-border bg-card px-6 py-12 text-center">
      <div className="animate-trendrop-spin grid h-20 w-20 place-items-center rounded-full border-4 border-muted border-t-primary">
        <Flame className="h-8 w-8 text-primary" />
      </div>
      <h2 className="text-xl font-bold">Creating your reel...</h2>
      <div className="w-full">
        <div className="mb-2 flex justify-between text-xs font-semibold text-muted-foreground">
          <span>{statusText}</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div className="h-full bg-gradient-to-r from-primary to-secondary transition-all" style={{ width: `${progress}%` }} />
        </div>
      </div>
    </div>
  );
}

function ResultStage({
  videoUrl, onDownload, onShare, onAgain,
}: { videoUrl: string | null; onDownload: () => void; onShare: () => void; onAgain: () => void }) {
  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-2xl font-bold">Your reel is ready! 🎉</h2>
      </div>
      <div className="overflow-hidden rounded-2xl border border-border bg-black">
        {videoUrl ? (
          <video src={videoUrl} autoPlay muted loop playsInline className="aspect-[9/16] w-full object-cover" />
        ) : (
          <div className="grid aspect-[9/16] w-full place-items-center text-muted-foreground">No preview available</div>
        )}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Button onClick={onDownload} className="h-12 bg-primary font-bold uppercase tracking-wide text-primary-foreground hover:bg-primary/90">
          <Download className="h-4 w-4" /> Download
        </Button>
        <Button onClick={onShare} variant="outline" className="h-12 border-border font-bold uppercase tracking-wide hover:bg-muted">
          <Share2 className="h-4 w-4" /> Share
        </Button>
      </div>
      <p className="text-center text-xs text-muted-foreground">Made with Trendrop</p>
      <Button onClick={onAgain} variant="ghost" className="w-full text-muted-foreground hover:text-foreground">
        Create another
      </Button>
    </div>
  );
}

function ErrorStage({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-2xl border border-primary/30 bg-primary/10 p-8 text-center">
      <div className="grid h-12 w-12 place-items-center rounded-full bg-primary/20 text-primary">
        <AlertTriangle className="h-6 w-6" />
      </div>
      <p className="font-semibold text-primary">{message}</p>
      <Button onClick={onRetry} className="bg-primary text-primary-foreground hover:bg-primary/90">Try Again</Button>
    </div>
  );
}
