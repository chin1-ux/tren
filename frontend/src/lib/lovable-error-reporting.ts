type LovableErrorOptions = {
  mechanism?: "manual" | "onerror" | "unhandledrejection" | "react_error_boundary";
  handled?: boolean;
  severity?: "error" | "warning" | "info";
};

type LovableEvents = {
  captureException?: (
    error: unknown,
    context?: Record<string, unknown>,
    options?: LovableErrorOptions,
  ) => void;
};

declare global {
  interface Window {
    __lovableEvents?: LovableEvents;
  }
}

let lastReportTime = 0;
const MIN_REPORT_INTERVAL_MS = 2000;

function sendTelemetry(data: { message?: string; stack?: string; route?: string; source?: string }) {
  const now = Date.now();
  if (now - lastReportTime < MIN_REPORT_INTERVAL_MS) return;
  lastReportTime = now;

  fetch("/api/client-errors", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...data,
      timestamp: new Date().toISOString(),
    }),
  }).catch(() => {
    // Silent catch to prevent error logging feedback loop
  });
}

export function reportLovableError(error: unknown, context: Record<string, unknown> = {}) {
  if (typeof window === "undefined") return;
  const errObj = error as any;
  sendTelemetry({
    message: errObj?.message || String(error),
    stack: errObj?.stack,
    route: window.location.pathname,
    source: "react_error_boundary",
  });
  window.__lovableEvents?.captureException?.(
    error,
    {
      source: "react_error_boundary",
      route: window.location.pathname,
      ...context,
    },
    {
      mechanism: "react_error_boundary",
      handled: false,
      severity: "error",
    },
  );
}

export function initGlobalErrorCapture() {
  if (typeof window === "undefined" || (window as any).__globalErrorCaptureInitialized) return;
  (window as any).__globalErrorCaptureInitialized = true;

  window.addEventListener("error", (event) => {
    const stack = event.error?.stack || String(event.error || event.message);
    console.error("[GlobalWindowErrorCaptured]", {
      message: event.message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      errorStack: stack,
      route: window.location.pathname,
      timestamp: new Date().toISOString(),
    });
    sendTelemetry({
      message: event.message,
      stack: stack,
      route: window.location.pathname,
      source: "window_onerror",
    });
  });

  window.addEventListener("unhandledrejection", (event) => {
    const stack = event.reason?.stack || String(event.reason);
    console.error("[UnhandledPromiseRejectionCaptured]", {
      reason: stack,
      route: window.location.pathname,
      timestamp: new Date().toISOString(),
    });
    sendTelemetry({
      message: event.reason?.message || String(event.reason),
      stack: stack,
      route: window.location.pathname,
      source: "unhandledrejection",
    });
  });
}


