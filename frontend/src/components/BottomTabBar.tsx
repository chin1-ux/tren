import { Link, useRouterState, useNavigate } from "@tanstack/react-router";
import { Sparkles, Lightbulb, Building2, User, Flame, Settings, Handshake, BarChart3, LogOut, LogIn, Wrench, LayoutDashboard, Layers, Compass, BookmarkCheck } from "lucide-react";
import { FEATURES } from "@/lib/features";
import { motion } from "framer-motion";
import { useAuth } from "@/contexts/AuthContext";
import { useUserStore } from "@/store/useAppStore";
import { useEffectivePlan } from "@/lib/plan";

export function BottomTabBar() {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const userPlan = useEffectivePlan();

  const PUBLIC_ROUTES = ["/login", "/signup", "/terms", "/privacy", "/data-rights"];
  const shouldHide = PUBLIC_ROUTES.includes(currentPath) || !user;

  if (shouldHide) {
    return null;
  }

  const handleLogout = async () => {
    await logout();
    navigate({ to: "/login" });

  };

  const tabs = [
    { to: "/", label: "Deck", Icon: Layers, tabId: "deck" },
    { to: "/?tab=explore", label: "Explore", Icon: Compass, tabId: "explore" },
    { to: "/?tab=picks", label: "Picks", Icon: BookmarkCheck, tabId: "picks" },
  ] as const;

  const gridColsClass = "grid-cols-3";

  return (
    <nav aria-label="Main navigation" className="fixed bottom-0 left-1/2 z-50 w-full max-w-lg lg:max-w-2xl xl:max-w-4xl -translate-x-1/2 border-t border-border bg-surface/95 backdrop-blur-lg">
      <ul className={`grid relative ${gridColsClass}`}>
        {tabs.map(({ to, label, Icon, tabId }) => {
          const currentSearch = typeof window !== "undefined" ? window.location.search : "";
          const isExplore = currentSearch.includes("tab=explore");
          const isPicks = currentSearch.includes("tab=picks");
          const isDeck = !isExplore && !isPicks;
          const isActive = currentPath === "/" && (
            (tabId === "deck" && isDeck) ||
            (tabId === "explore" && isExplore) ||
            (tabId === "picks" && isPicks)
          );
          
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
