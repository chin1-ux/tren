import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { Sparkles, Lightbulb, Building2, User, Flame, Settings, Handshake, BarChart3, LogOut, LogIn } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchEmergingTrends } from "@/lib/api";
import { FEATURES } from "@/lib/features";
import { motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";

export function BottomTabBar() {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const PUBLIC_ROUTES = ["/login", "/signup", "/terms", "/privacy", "/data-rights"];
  const shouldHide = PUBLIC_ROUTES.includes(currentPath) || !user;

  const { data: emergingTrends } = useQuery({
    queryKey: ["trends-emerging", "all"],
    queryFn: () => fetchEmergingTrends(),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
    enabled: !shouldHide,
  });

  const emergingCount = emergingTrends?.length ?? 0;

  if (shouldHide) {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    navigate({ to: "/login" });

  };

  const allTabs = [
    { to: "/", label: "Trends", Icon: Flame },
    { to: "/dashboard", label: "Dashboard", Icon: BarChart3 },
    // Generate tab: hidden behind feature flag. Files/routes are untouched.
    // TODO(brand): E-1 — Trends tab now uses Flame icon (same as other tabs)
    // so active state shows primary colour consistently. Swap back to TrenddropLogo
    // once brand finalises nav icon treatment.
    ...(FEATURES.GENERATE_ENABLED ? [{ to: "/generate", label: "Generate", Icon: Sparkles }] : []),
    ...(FEATURES.IDEAS_ENABLED ? [{ to: "/ideas", label: "Ideas", Icon: Lightbulb }] : []),
    ...(FEATURES.DEALS_ENABLED ? [{ to: "/deals", label: "Deals", Icon: Handshake }] : []),
    user ? { to: "/settings", label: "Settings", Icon: Settings } : { to: "/login", label: "Login", Icon: LogIn },
  ] as const;
  const tabs = allTabs;

  const gridCols = [
    FEATURES.GENERATE_ENABLED,
    FEATURES.IDEAS_ENABLED,
    FEATURES.DEALS_ENABLED
  ].filter(Boolean).length + 3; // Base 3 (Trends, Dashboard, Settings/Login)

  const gridColsClass = {
    3: "grid-cols-3",
    4: "grid-cols-4",
    5: "grid-cols-5",
    6: "grid-cols-6",
  }[gridCols] || "grid-cols-3";

  return (
    <nav className="fixed bottom-0 left-1/2 z-50 w-full max-w-md -translate-x-1/2 border-t border-border bg-surface/95 backdrop-blur-lg">
      <ul className={`grid relative ${gridColsClass}`}>
        {tabs.map(({ to, label, Icon }) => {
          const isActive = to === "/"
            ? currentPath === "/"
            : currentPath.startsWith(to);
          
          return (
            <li key={to}>
              <Link
                to={to}
                className={`relative flex w-full flex-col items-center justify-center gap-0.5 py-3 text-[10px] sm:text-[11px] font-medium transition-colors text-center ${
                  isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {/* Active indicator line at top */}
                {isActive && (
                  <motion.div
                    layoutId="activeTabIndicator"
                    className="absolute top-0 left-1/2 h-[3px] w-8 -translate-x-1/2 rounded-full bg-primary shadow-[0_0_8px_rgba(230,57,70,0.5)]"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <motion.div
                  animate={isActive ? { scale: 1.15 } : { scale: 1 }}
                  whileHover={{ scale: 1.1 }}
                  className="relative"
                >
                  {/* All tabs use their Icon for consistent active-state colour */}
                  <Icon className="h-5 w-5" />
                  {/* Emerging count badge on Trends tab */}
                  {label === "Trends" && emergingCount > 0 && (
                    <span className="absolute -right-2 -top-2 flex h-4 w-4 items-center justify-center rounded-full bg-[#ff006e] text-[8px] font-extrabold text-white animate-pulse">
                      {emergingCount}
                    </span>
                  )}
                </motion.div>
                <span className="text-[10px] sm:text-[11px] font-display mt-0.5">{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
      <div className="h-[env(safe-area-inset-bottom)]" />
    </nav>
  );
}
