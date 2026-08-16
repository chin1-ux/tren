import { createFileRoute } from "@tanstack/react-router";
import { Check, Flame, Star, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/pricing")({
  component: PricingPage,
});

function PricingPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 py-16">
      <div className="text-center max-w-2xl mb-12">
        <h1 className="font-display text-4xl font-extrabold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 to-purple-600">
          Simple, Transparent Pricing
        </h1>
        <p className="text-muted-foreground text-lg">
          Choose the plan that fits your growth strategy. Unlock early access to trends and powerful ideation tools.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl w-full">
        {/* Free Tier */}
        <div className="rounded-3xl border border-border bg-surface p-8 flex flex-col hover:border-indigo-500/30 transition-colors">
          <div className="mb-6">
            <h3 className="text-xl font-bold text-foreground mb-2 flex items-center gap-2">
              <Star className="h-5 w-5 text-indigo-400" /> Free
            </h3>
            <div className="text-3xl font-black text-foreground">₹0<span className="text-sm font-normal text-muted-foreground"> / month</span></div>
          </div>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" /> Basic Trend Feed (48hr delayed access)
            </li>
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" /> Standard Trend Scoring
            </li>
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" /> 5 AI Hook Generations / day
            </li>
          </ul>
          <Button variant="outline" className="w-full rounded-xl border-border hover:bg-surface-2" onClick={() => window.location.href = '/login'}>
            Current Plan
          </Button>
        </div>

        {/* Creator Tier */}
        <div className="rounded-3xl border-2 border-indigo-500 bg-surface-2 p-8 flex flex-col relative shadow-2xl shadow-indigo-500/10 scale-105">
          <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-indigo-500 text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider">
            Most Popular
          </div>
          <div className="mb-6">
            <h3 className="text-xl font-bold text-foreground mb-2 flex items-center gap-2">
              <Flame className="h-5 w-5 text-indigo-500" /> Creator
            </h3>
            <div className="text-3xl font-black text-foreground">₹999<span className="text-sm font-normal text-muted-foreground"> / month</span></div>
          </div>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-start gap-3 text-sm text-foreground font-medium">
              <Check className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" /> 24hr Early Access to Trending Sounds
            </li>
            <li className="flex items-start gap-3 text-sm text-foreground font-medium">
              <Check className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" /> Full Ideation Hub & Calendar Access
            </li>
            <li className="flex items-start gap-3 text-sm text-foreground font-medium">
              <Check className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" /> Creator Diagnostics Dashboard
            </li>
            <li className="flex items-start gap-3 text-sm text-foreground font-medium">
              <Check className="h-4 w-4 text-indigo-500 shrink-0 mt-0.5" /> Up to 100 Sessions limit / day
            </li>
          </ul>
          <Button className="w-full rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-bold h-11" onClick={() => window.location.href = '/login'}>
            Upgrade to Creator
          </Button>
        </div>

        {/* Agency Tier */}
        <div className="rounded-3xl border border-border bg-surface p-8 flex flex-col hover:border-purple-500/30 transition-colors">
          <div className="mb-6">
            <h3 className="text-xl font-bold text-foreground mb-2 flex items-center gap-2">
              <Zap className="h-5 w-5 text-purple-400" /> Agency
            </h3>
            <div className="text-3xl font-black text-foreground">₹4999<span className="text-sm font-normal text-muted-foreground"> / month</span></div>
          </div>
          <ul className="space-y-4 mb-8 flex-1">
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-purple-500 shrink-0 mt-0.5" /> Real-time Trend Discovery Feed
            </li>
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-purple-500 shrink-0 mt-0.5" /> Access to Brand Deals & Marketplace
            </li>
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-purple-500 shrink-0 mt-0.5" /> Unlimited Sessions & Generations
            </li>
            <li className="flex items-start gap-3 text-sm text-muted-foreground">
              <Check className="h-4 w-4 text-purple-500 shrink-0 mt-0.5" /> Competitor Performance Tracking
            </li>
          </ul>
          <Button variant="outline" className="w-full rounded-xl border-border hover:bg-surface-2 hover:text-purple-400" onClick={() => window.location.href = '/login'}>
            Upgrade to Agency
          </Button>
        </div>
      </div>
    </div>
  );
}
