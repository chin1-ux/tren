import { useEffect, useState } from "react";
import { Download, X } from "lucide-react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISS_KEY = "trendrop_install_dismissed";
const DELAY_MS = 30_000;

export function InstallBanner() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (localStorage.getItem(DISMISS_KEY)) return;
    const isStandalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      // @ts-expect-error iOS Safari
      window.navigator.standalone === true;
    if (isStandalone) return;

    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
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
      /* ignore */
    } finally {
      setDeferred(null);
      setVisible(false);
    }
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-x-0 bottom-20 z-50 mx-auto flex w-full max-w-md justify-center px-4 animate-in slide-in-from-bottom-8 duration-300">
      <div className="w-full rounded-2xl border border-border bg-card p-4 shadow-2xl">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary text-white font-bold">
            T
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-foreground">
              Install Trendrop on your home screen
            </h3>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Get instant trend alerts
            </p>
          </div>
          <button
            onClick={dismiss}
            aria-label="Dismiss"
            className="rounded-full p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-3 flex gap-2">
          <button
            onClick={dismiss}
            className="flex-1 rounded-xl border border-border px-4 py-2.5 text-sm font-medium text-foreground hover:bg-muted"
          >
            Not now
          </button>
          <button
            onClick={install}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-primary/90"
          >
            <Download className="h-4 w-4" />
            Install
          </button>
        </div>
      </div>
    </div>
  );
}
