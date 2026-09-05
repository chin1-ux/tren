import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { FEATURES } from "@/lib/features";
import { ArrowLeft, Handshake } from "lucide-react";

export const Route = createFileRoute("/deals/new")({
  head: () => ({
    meta: [
      { title: "Create Brand Deal — Trendrop" },
      { name: "description", content: "Create a new brand collaboration deal." },
    ],
  }),
  component: CreateDealPlaceholder,
});

function CreateDealPlaceholder() {
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!user) {
      navigate({ to: "/login" });
    } else if (!FEATURES.DEALS_ENABLED) {
      navigate({ to: "/" });
    }
  }, [user, navigate]);

  if (!user || !FEATURES.DEALS_ENABLED) return null;

  return (
    <div className="flex flex-col gap-6 px-4 pt-6 pb-12 min-h-screen text-foreground">
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate({ to: "/deals" })}
          className="p-1 rounded-full hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold tracking-tight font-display">Create Campaign Deal</h1>
          <p className="text-[10px] text-muted-foreground mt-0.5">Fill details to auto-generate contract PDF</p>
        </div>
      </div>

      <div className="flex flex-col items-center justify-center min-h-[40vh] text-center gap-6">
        <div className="h-16 w-16 rounded-2xl bg-muted/60 flex items-center justify-center text-muted-foreground">
          <Handshake className="h-8 w-8" />
        </div>
        <div className="space-y-2">
          <h2 className="text-lg font-bold font-display">Coming Soon</h2>
          <p className="text-sm text-muted-foreground max-w-xs">
            Deal creation will be available once the marketplace launches. For now, use the Brand Deals dashboard to track existing deals.
          </p>
        </div>
      </div>
    </div>
  );
}
