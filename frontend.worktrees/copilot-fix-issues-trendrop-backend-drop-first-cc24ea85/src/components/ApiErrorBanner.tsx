import { AlertTriangle } from "lucide-react";

export function ApiErrorBanner({ message = "Service temporarily unavailable" }: { message?: string }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-primary/30 bg-primary/10 px-4 py-3 text-sm text-primary">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
