import { useAuth } from "@/contexts/AuthContext";
import { Loader2 } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";

// Public routes that don't require authentication
const PUBLIC_ROUTES = ["/login", "/signup", "/terms", "/privacy", "/data-rights"];

export function AuthWrapper({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const navigate = useNavigate();
  const currentPath = window.location.pathname;

  // Show loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          <p className="text-slate-600 dark:text-slate-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Handle authentication redirects
  useEffect(() => {
    if (!loading) {
      // If user is authenticated and trying to access login/signup, redirect to home
      if (user && (currentPath === "/login" || currentPath === "/signup")) {
        navigate({ to: "/" });
      }
      // If user is not authenticated and trying to access protected route, redirect to login
      else if (!user && !PUBLIC_ROUTES.includes(currentPath)) {
        navigate({ to: "/login" });
      }
    }
  }, [user, loading, navigate, currentPath]);

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