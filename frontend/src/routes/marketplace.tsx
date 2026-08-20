import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Building2 } from "lucide-react";

export const Route = createFileRoute("/marketplace")({
  head: () => ({
    meta: [
      { title: "Creator Marketplace — Trendrop" },
      { name: "description", content: "Apply for exclusive brand deals, find creators in your niche, and manage collaborations." },
    ],
  }),
  component: MarketplacePlaceholder,
});

function MarketplacePlaceholder() {
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      navigate({ to: "/login" });
    }
  }, [user, navigate]);

  if (!user) return null;

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4 text-center gap-6">
      <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-500 flex items-center justify-center text-white shadow-lg shadow-pink-500/20">
        <Building2 className="h-8 w-8" />
      </div>
      <div className="space-y-2">
        <h1 className="text-xl font-bold tracking-tight font-display">Marketplace</h1>
        <p className="text-sm text-muted-foreground max-w-xs">
          Coming soon — connecting brands and creators directly.
        </p>
      </div>
    </div>
  );
}
