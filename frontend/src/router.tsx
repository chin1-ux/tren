import { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { routeTree } from "./routeTree.gen";

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
        staleTime: 30_000,
      },
    },
  });

  const router = createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
  });

  return router;
};
