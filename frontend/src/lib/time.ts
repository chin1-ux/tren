/**
 * time.ts — shared date-parsing helpers for Trendrop frontend.
 *
 * Problem: Supabase stores several timestamp columns (e.g. first_detected_at,
 * created_at) without a timezone suffix ("2026-09-29T15:03:59.334036").
 * The ECMAScript spec treats such strings as *local time* in browsers, which
 * means IST users see times 5h30m too early (UTC clock value displayed as IST).
 *
 * Fix: parseApiDate() forces bare ISO strings to UTC before constructing the
 * Date object. All API-sourced date fields must go through this helper.
 */

/**
 * Parse an ISO-8601 string that may or may not carry a timezone offset.
 * A string without a trailing "Z" or "±HH:MM" is assumed to be UTC and gets
 * a "Z" appended before parsing so the browser treats it as UTC everywhere.
 *
 * Returns a valid Date, or null if the input is falsy or not parseable.
 */
export function parseApiDate(s: string | null | undefined): Date | null {
  if (!s) return null;
  // Already carries explicit timezone info — leave unchanged.
  const hasOffset = s.endsWith("Z") || /[+\-]\d{2}:\d{2}$/.test(s);
  const normalized = hasOffset ? s : s + "Z";
  const d = new Date(normalized);
  return isNaN(d.getTime()) ? null : d;
}

/**
 * Format an API timestamp string as a human-readable IST date+time string,
 * e.g. "29 Sept 2026, 8:33 pm".
 *
 * Returns null if the input is falsy or not parseable.
 */
export function formatApiDateIst(
  s: string | null | undefined,
  opts?: Intl.DateTimeFormatOptions,
): string | null {
  const d = parseApiDate(s);
  if (!d) return null;
  return d.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
    timeZone: "Asia/Kolkata",
    ...opts,
  });
}

/**
 * Human-friendly relative time, e.g. "just now", "15m ago", "2h ago", "4d ago".
 */
export function formatRelativeTime(s: string | Date | null | undefined): string {
  const d = s instanceof Date ? s : parseApiDate(s);
  if (!d) return "recently";
  const diffSec = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
  if (diffSec < 60) return "just now";
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  const diffMonths = Math.floor(diffDays / 30);
  return `${diffMonths}mo ago`;
}

/**
 * Short month + day format, e.g. "Sep 24".
 */
export function formatShortDate(s: string | Date | null | undefined): string {
  const d = s instanceof Date ? s : parseApiDate(s);
  if (!d) return "";
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "Asia/Kolkata",
  });
}
