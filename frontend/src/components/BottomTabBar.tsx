import { Link, useRouterState } from "@tanstack/react-router";
import { Flame, Sparkles, BarChart3, User, Zap } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchEmergingTrends } from "@/lib/api";

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
    { to: "/", label: "Trends", Icon: Flame, badge: 0 },
    { to: "/generate", label: "Generate", Icon: Sparkles, badge: 0 },
    { to: "/stats", label: "Dashboard", Icon: BarChart3, badge: 0 },
    { to: "/profile", label: "Profile", Icon: User, badge: 0 },
  ] as const;

  return (
    <nav className="fixed bottom-0 left-1/2 z-50 w-full max-w-md -translate-x-1/2 border-t border-border bg-background/95 backdrop-blur-md">
      <ul className="grid grid-cols-4">
        {tabs.map(({ to, label, Icon }) => {
          const isActive = to === "/"
            ? currentPath === "/"
            : currentPath.startsWith(to);
          return (
            <li key={to}>
              <Link
                to={to}
                className={`relative flex flex-col items-center gap-1 py-3 text-xs font-medium transition-colors ${
                  isActive ? "text-primary" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {/* Active indicator line at top */}
                {isActive && (
                  <div className="absolute top-0 left-1/2 h-0.5 w-6 -translate-x-1/2 rounded-full bg-primary" />
                )}
                <div className="relative">
                  <Icon className="h-5 w-5" />
                  {/* Emerging count badge on Trends tab */}
                  {label === "Trends" && emergingCount > 0 && (
                    <span className="absolute -right-2 -top-2 flex h-4 w-4 items-center justify-center rounded-full bg-[#ff006e] text-[8px] font-extrabold text-white">
                      {emergingCount}
                    </span>
                  )}
                </div>
                <span className="text-[10px]">{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
      <div className="h-[env(safe-area-inset-bottom)]" />
    </nav>
  );
}
