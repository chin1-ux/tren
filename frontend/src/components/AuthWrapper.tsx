import { useAuth } from "@/contexts/AuthContext";
import { Loader2 } from "lucide-react";
import { useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useRef } from "react";

// Public routes that don't require standard user authentication (admin routes have their own beforeLoad check)
const PUBLIC_ROUTES = [
  "/login", 
  "/signup", 
  "/verify-phone",
  "/terms", 
  "/privacy", 
  "/data-rights",
  "/admin/login",
  "/admin/users",
  "/admin/audit",
  "/admin/analytics",
  "/admin/plans",
  "/reset-password",
  "/update-password"
];

export function AuthWrapper({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const isRedirecting = useRef(false);

  // Listen for plan-gated 401s from api.ts http() helper.
  // Only log the user out if they genuinely have no session.
  useEffect(() => {
    const handleUnauthorized = () => {
      // A 401 from a plan-gated endpoint (e.g. early_detection) should NOT
      // log the user out — they are authenticated, just not on the right plan.
      // Only act if user is already null (truly unauthenticated).
      if (!user) {
        navigate({ to: "/login" });
      }
    };
    window.addEventListener("trendrop:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("trendrop:unauthorized", handleUnauthorized);
  }, [user, navigate]);

  // Handle authentication redirects
  // NOTE: useEffect must be called before any conditional return (Rules of Hooks)
  useEffect(() => {
    if (!loading) {
      isRedirecting.current = false;
    }
    if (!loading && !isRedirecting.current) {
      // If user is authenticated and trying to access login/signup, redirect to home
      if (user && (currentPath === "/login" || currentPath === "/signup")) {
        isRedirecting.current = true;
        navigate({ to: "/" });
      }
      // If user is not authenticated and trying to access protected route, redirect to login
      else if (!user && !PUBLIC_ROUTES.includes(currentPath)) {
        isRedirecting.current = true;
        navigate({ to: "/login" });
      }
    }
  }, [user, loading, navigate, currentPath]);

  // Show loading state (must be after all hooks)
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-slate-600 dark:text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  // For public routes, show content directly
  if (PUBLIC_ROUTES.includes(currentPath)) {
    return <>{children}</>;
  }

  // For protected routes, require authentication
  if (!user) {
    return null; // Will redirect in useEffect
  }

  // Show the app content
  return <>{children}</>;
}