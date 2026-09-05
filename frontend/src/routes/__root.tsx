import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  useRouterState,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import { Toaster } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

import appCss from "../styles.css?url";
import { reportLovableError } from "../lib/lovable-error-reporting";
import { BottomTabBar } from "../components/BottomTabBar";
import { InstallBanner } from "../components/InstallBanner";
import { registerPWA } from "../lib/pwa-register";
import { useUserStore } from "../store/useAppStore";
import { AuthProvider } from "../contexts/AuthContext";
import { AuthWrapper } from "../components/AuthWrapper";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-primary">404</h1>
        <h2 className="mt-4 text-xl font-semibold">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link to="/" className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold">This page didn't load</h1>
        <p className="mt-2 text-sm text-muted-foreground">Something went wrong on our end.</p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => { router.invalidate(); reset(); }}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Try again
          </button>
          <a href="/" className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent">
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1, viewport-fit=cover" },
      { title: "Trendrop — India's Trend Intelligence" },
      { name: "description", content: "Know what's trending before your competitor even opens Instagram. India-focused AI trend detection for Instagram Reels and YouTube Shorts." },
      { name: "theme-color", content: "#E63946" },
      { name: "mobile-web-app-capable", content: "yes" },
      { name: "apple-mobile-web-app-capable", content: "yes" },

      { name: "apple-mobile-web-app-status-bar-style", content: "black" },
      { name: "apple-mobile-web-app-title", content: "Trendrop" },
      { property: "og:title", content: "Trendrop — Know before they know" },
      { property: "og:description", content: "India's AI trend intelligence for short-form creators. Surface trends while they're still rising." },
      { property: "og:type", content: "website" },
    ],
    links: [
      { rel: "stylesheet", href: appCss },
      { rel: "manifest", href: "/manifest.webmanifest" },
      { rel: "apple-touch-icon", href: "/icon-192.png" },
      { rel: "icon", type: "image/png", sizes: "192x192", href: "/icon-192.png" },
      { rel: "icon", type: "image/png", sizes: "512x512", href: "/icon-512.png" },
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      { rel: "preconnect", href: "https://fonts.gstatic.com", crossOrigin: "anonymous" },
      { rel: "stylesheet", href: "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;

  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const body = document.body;
    const root = document.documentElement;
    if (theme === "dark") {
      body.setAttribute("data-theme", "dark");
      body.classList.add("dark");
      root.setAttribute("data-theme", "dark");
      root.classList.add("dark");
    } else {
      body.removeAttribute("data-theme");
      body.classList.remove("dark");
      root.removeAttribute("data-theme");
      root.classList.remove("dark");
    }
    localStorage.setItem("trendrop_theme", theme);
  }, [theme]);

  useEffect(() => {
    // Initialize user store from local storage after client hydration
    useUserStore.getState().initializeFromLocalStorage();

    const handleThemeChange = () => {
      const savedTheme = localStorage.getItem("trendrop_theme");
      if (savedTheme === "dark" || savedTheme === "light") {
        setTheme(savedTheme);
      }
    };
    handleThemeChange();
    window.addEventListener("storage", handleThemeChange);
    window.addEventListener("theme-change", handleThemeChange);
    return () => {
      window.removeEventListener("storage", handleThemeChange);
      window.removeEventListener("theme-change", handleThemeChange);
    };
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    localStorage.setItem("trendrop_theme", nextTheme);
    window.dispatchEvent(new Event("theme-change"));
  };

  useEffect(() => {
    registerPWA();
  }, []);

  const isAdminRoute = currentPath.startsWith("/admin");

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <AuthWrapper>
          <div className={`mx-auto flex min-h-screen w-full flex-col bg-background overflow-x-hidden relative ${isAdminRoute ? "" : "max-w-lg lg:max-w-2xl xl:max-w-4xl 2xl:max-w-5xl pb-24"}`}>

            <AnimatePresence mode="wait">
              <motion.div
                key={currentPath}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.25, ease: "easeInOut" }}
                className="flex flex-col w-full"
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </div>
          <BottomTabBar />
          <InstallBanner />
          <Toaster
            position="top-center"
            toastOptions={{
              style: {
                background: "var(--surface)",
                backdropFilter: "blur(20px)",
                WebkitBackdropFilter: "blur(20px)",
                border: "1px solid var(--border)",
                color: "var(--text-100)",
                fontFamily: "var(--font-sans)",
            boxShadow: "0 10px 30px rgba(0,0,0,0.3)",
          },
        }}
          />
        </AuthWrapper>
      </AuthProvider>
    </QueryClientProvider>
  );
}
