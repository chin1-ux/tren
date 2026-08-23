import { createFileRoute } from "@tanstack/react-router";
import { Check, Star, Zap, Coins } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUserStore } from "@/store/useAppStore";

export const Route = createFileRoute("/pricing")({
component: PricingPage,
});

function PricingPage() {
const userPlan = useUserStore((s) => s.plan) || "free";
const isPro = userPlan === "pro" || userPlan === "agency";
  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 py-16">
      <div className="text-center max-w-2xl mb-12">
        <h1 className="font-display text-4xl font-extrabold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 to-purple-600">
          Simple, Transparent Pricing
        </h1>
        <p className="text-muted-foreground text-lg">
          Browse trends for free. Pay for AI-powered content generation.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl w-full">
        {/* Free Tier */}
        <div className="rounded-3xl border border-border bg-surface p-8 flex flex-col hover:border-indigo-500/30 transition-colors">
          <div className="mb-6">
            <h3 className="text-xl font-bold text-foreground mb-2 flex items-center gap-2">
              <Star className="h-5 w-5 text-indigo-400" /> Free
            </h3>
            <div className="text-3xl font-black text-foreground">
              ₹0<span className="text-sm font-normal text-muted-foreground"> / month</span>
            </div>
          </div>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" /> Full trend browsing (24hr delayed data)
            </li>
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" /> 100 AI credits per month
            </li>
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" /> Algorithm insights & scoring
            </li>
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" /> Basic analytics dashboard
            </li>
          </ul>
          <Button
            variant="outline"
            className="w-full rounded-xl border-border hover:bg-surface-2"
            onClick={() => (window.location.href = "/login")}
          >
            Get Started Free
          </Button>
        </div>

        {/* Pro Tier */}
        <div className="rounded-3xl border-2 border-indigo-500 bg-surface-2 p-8 flex flex-col relative shadow-2xl shadow-indigo-500/10 scale-105">
          <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-indigo-500 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
            Best Value
          </div>
          <div className="mb-6">
            <h3 className="text-xl font-bold text-foreground mb-2 flex items-center gap-2">
              <Zap className="h-5 w-5 text-indigo-500" /> Pro
            </h3>
            <div className="text-3xl font-black text-foreground">
              ₹499<span className="text-sm font-normal text-muted-foreground"> / month</span>
            </div>
          </div>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-start gap-3 text-sm text-foreground font-medium">
              <Check className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" /> Real-time trend data (no delay)
            </li>
            <li className="flex items-start gap-3 text-sm text-foreground font-medium">
              <Check className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" /> 1,000 AI credits per month
            </li>
            <li className="flex items-start gap-3 text-sm text-foreground font-medium">
              <Check className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" /> AI caption, hook & idea generation
            </li>
            <li className="flex items-start gap-3 text-sm text-foreground font-medium">
              <Check className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" /> Video virality analysis
            </li>
            <li className="flex items-start gap-3 text-sm text-foreground font-medium">
              <Check className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" /> Export & download tools
            </li>
            <li className="flex items-start gap-3 text-sm text-foreground font-medium">
              <Check className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" /> India-specific trend intelligence
            </li>
          </ul>
          {isPro ? (
            <Button
              disabled
              className="w-full rounded-xl bg-muted text-muted-foreground font-bold h-11 cursor-not-allowed"
            >
              <Check className="w-4 h-4 mr-2" />
              Current Plan
            </Button>
          ) : (
            <Button
              className="w-full rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-bold h-11"
              onClick={() => (window.location.href = "/login")}
            >
              <Coins className="w-4 h-4 mr-2" />
              Upgrade to Pro
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
