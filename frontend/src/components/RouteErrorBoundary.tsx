import { useRouter } from "@tanstack/react-router";
import { useEffect } from "react";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { AlertCircle } from "lucide-react";

export function RouteErrorBoundary({ error, reset }: { error: Error; reset: () => void }) {
  const router = useRouter();
  
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_route_error_component" });
  }, [error]);

  return (
    <div className="flex h-[60vh] flex-col items-center justify-center p-6 text-center animate-in fade-in zoom-in duration-300">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10 mb-4">
        <AlertCircle className="h-8 w-8 text-red-500" />
      </div>
      <h2 className="text-xl font-bold mb-2">Something went wrong</h2>
      <p className="text-sm text-muted-foreground max-w-[280px] mb-6">
        We ran into an issue loading this section. Our team has been notified.
      </p>
      <div className="flex gap-3">
        <button
          onClick={() => { router.invalidate(); reset(); }}
          className="rounded-full bg-primary px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-primary/90 transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
