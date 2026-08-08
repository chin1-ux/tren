import { useEffect, useRef, useState } from "react";
import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = (import.meta.env.VITE_SUPABASE_URL as string) ?? "";
const SUPABASE_ANON = (import.meta.env.VITE_SUPABASE_ANON_KEY as string) ?? "";

// Singleton realtime client so we don't open multiple WS connections
let _realtimeClient: ReturnType<typeof createClient> | null = null;
function getRealtimeClient() {
  if (!_realtimeClient && SUPABASE_URL && SUPABASE_ANON) {
    _realtimeClient = createClient(SUPABASE_URL, SUPABASE_ANON);
  }
  return _realtimeClient;
}

/**
 * useSaturationCount
 *
 * Subscribes to INSERT/DELETE events on the `trend_actions` table for a
 * specific trend_id and returns a live saturation count.
 *
 * Falls back to the `initialCount` prop if Supabase Realtime is unavailable
 * (e.g. env vars not configured).
 */
export function useSaturationCount(trendId: string | number, initialCount: number = 0): number {
  const [count, setCount] = useState<number>(initialCount);
  const channelRef = useRef<ReturnType<ReturnType<typeof createClient>["channel"]> | null>(null);

  // Keep count in sync when the parent re-renders with a fresh value (e.g. after target toggle)
  useEffect(() => {
    setCount(initialCount);
  }, [initialCount]);

  useEffect(() => {
    const sb = getRealtimeClient();
    if (!sb || !trendId) return;

    const channelName = `trend_saturation:${trendId}`;

    const channel = sb
      .channel(channelName)
      .on(
        "postgres_changes",
        {
          event: "*",           // INSERT or DELETE
          schema: "public",
          table: "trend_actions",
          filter: `trend_id=eq.${trendId}`,
        },
        async () => {
          // Re-fetch the live count from Supabase instead of computing delta
          // to avoid off-by-one issues from concurrent updates.
          try {
            const { count: liveCount } = await sb
              .from("trend_actions")
              .select("*", { count: "exact", head: true })
              .eq("trend_id", trendId)
              .eq("action", "target");

            if (typeof liveCount === "number") {
              setCount(liveCount);
            }
          } catch {
            // silently ignore — count will update on next event
          }
        }
      )
      .subscribe();

    channelRef.current = channel;

    return () => {
      sb.removeChannel(channel);
      channelRef.current = null;
    };
  }, [trendId]);

  return count;
}
