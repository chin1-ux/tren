import { Link, useRouterState } from "@tanstack/react-router";
import { Sparkles, Lightbulb, Building2, User, Flame, Settings, Handshake } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchEmergingTrends } from "@/lib/api";
import { motion } from "framer-motion";
import { TrenddropLogo } from "@/components/TrenddropLogo";

export function BottomTabBar() {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;

  const { data: emergingTrends } = useQuery({
    queryKey: ["trends-emerging", "all"],
    queryFn: () => fetchEmergingTrends(),
    staleTime: 5 * 60_000,
    refetchInterval: 5 * 60_000,
  });
  const emergingCount = emergingTrends?.length ?? 0;

  const tabs = [
    { to: "/", label: "Trends", Icon: Flame },
    { to: "/generate", label: "Generate", Icon: Sparkles },
    { to: "/ideas", label: "Ideas", Icon: Lightbulb },
    { to: "/deals", label: "Deals", Icon: Handshake },
    { to: "/profile", label: "Profile", Icon: User },
    { to: "/stats", label: "Stats", Icon: Settings },
  ] as const;

  return (
    <nav className="fixed bottom-0 left-1/2 z-50 w-full max-w-md -translate-x-1/2 border-t border-border bg-surface/95 backdrop-blur-lg">
      <ul className="grid grid-cols-6 relative">
        {tabs.map(({ to, label, Icon }) => {
          const isActive = to === "/"
            ? currentPath === "/"
            : currentPath.startsWith(to);
          return (
            <li key={to}>
              <Link
                to={to}
                className={`relative flex flex-col items-center justify-center gap-0.5 py-2 text-[10px] sm:text-[11px] font-medium transition-colors text-center ${
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
                  {/* Show logo icon only on the Trends tab */}
                  {label === "Trends" ? (
                    <TrenddropLogo iconOnly size={20} animate={false} />
                  ) : (
                    <Icon className="h-5 w-5" />
                  )}
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
