import { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";
import { initGlobalErrorCapture } from "./lib/lovable-error-reporting";

initGlobalErrorCapture();

export const getRouter = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error: any) => {
          // Never retry 401/403 — they're auth/plan errors, not transient
          const status = error?.status || error?.message?.match?.(/^(\d{3})/)?.[1];
          if (status === "401" || status === "403" || status === 401 || status === 403) return false;
          return failureCount < 2;
        },
        staleTime: 60_000, // 1 min stale time for instant page back/forward
        gcTime: 10 * 60_000, // 10 min garbage collection cache
        refetchOnWindowFocus: false, // Prevent jarring background refetches
      },
    },
  });

  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreload: 'intent',
    defaultPreloadDelay: 50,
    defaultPreloadStaleTime: 5 * 60_000, // 5 min cache for preloaded routes
  });

  return router;
};
