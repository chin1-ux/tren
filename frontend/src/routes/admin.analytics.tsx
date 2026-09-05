import { createFileRoute, useNavigate, redirect } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { getAdminAnalyticsSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { BarChart2, RefreshCw, ShieldAlert, ArrowLeft, Activity } from "lucide-react";
import { motion } from "framer-motion";

export const Route = createFileRoute("/admin/analytics")({
  beforeLoad: async () => {
    if (typeof window === "undefined") {
      throw redirect({ to: "/admin/login" });
    }
    const token = localStorage.getItem("admin_token");
    if (!token) {
      throw redirect({ to: "/admin/login" });
    }
    try {
      const response = await fetch("/api/admin/validate-token", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        localStorage.removeItem("admin_token");
        localStorage.removeItem("admin_email");
        localStorage.removeItem("admin_role");
        throw redirect({ to: "/admin/login" });
      }
    } catch (err: any) {
      if (!err?.isRedirect) {
        localStorage.removeItem("admin_token");
        localStorage.removeItem("admin_email");
        localStorage.removeItem("admin_role");
        throw redirect({ to: "/admin/login" });
      }
      throw err;
    }
  },
  head: () => ({
    meta: [
      { title: "Admin Analytics Summary — Trendrop" },
    ],
  }),
  component: AdminAnalyticsPage,
});

function AdminAnalyticsPage() {
  const navigate = useNavigate();
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [authorized, setAuthorized] = useState(true);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const data = await getAdminAnalyticsSummary();
      setCounts(data.event_counts || {});
      setAuthorized(true);
    } catch (err: any) {
      console.error(err);
      if (err.message?.includes("403")) {
        setAuthorized(false);
        toast.error("Access Forbidden: Admin privileges required.");
      } else {
        toast.error("Failed to load analytics data.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  if (!authorized) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4 text-center bg-background text-foreground">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-card border border-border p-8 rounded-3xl max-w-sm flex flex-col items-center gap-4 shadow-xl"
        >
          <div className="w-12 h-12 rounded-full bg-red-500/10 flex items-center justify-center text-red-500">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h2 className="text-xl font-bold font-display">Access Restricted</h2>
          <p className="text-xs text-muted-foreground leading-relaxed">
            This analytics panel is strictly restricted to internal administrators. Your current account does not have access.
          </p>
          <Button onClick={() => navigate({ to: "/" })} className="w-full rounded-full mt-2">
            Return to Dashboard
          </Button>
        </motion.div>
      </div>
    );
  }

  const eventDescriptions: Record<string, string> = {
    deal_created: "Total contract campaign configurations completed.",
    contract_downloaded: "Total PDF collaboration agreements generated and downloaded.",
    milestone_set: "Total scheduled milestones created for tracking.",
    reminder_clicked: "Total follow-up template drafts copied/clicked."
  };

  return (
    <div className="flex flex-col gap-6 px-4 pt-6 pb-12 min-h-screen bg-background text-foreground">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button 
          onClick={() => navigate({ to: "/" })}
          className="p-1 rounded-full hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-xl font-bold font-display bg-gradient-to-r from-primary to-rose-400 bg-clip-text text-transparent flex items-center gap-2">
            <Activity className="h-5 w-5 text-primary" />
            System Analytics
          </h1>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            Internal usage summary
          </p>
        </div>
      </div>

      <div className="flex justify-between items-center bg-card border border-border p-4 rounded-2xl shadow-sm">
        <span className="text-xs font-semibold text-muted-foreground">Aggregate Usage Telemetry</span>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={fetchAnalytics} 
          disabled={loading}
          className="rounded-full gap-1 px-3"
        >
          <RefreshCw className={`h-3 w-3 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-24 bg-card/50 border border-border/50 animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {Object.keys(eventDescriptions).map((eventKey) => {
            const count = counts[eventKey] || 0;
            return (
              <motion.div
                key={eventKey}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-card border border-border p-5 rounded-2xl flex items-center justify-between shadow-sm hover:border-primary/20 transition-all"
              >
                <div className="flex flex-col gap-1 pr-4">
                  <span className="text-sm font-bold capitalize font-display">
                    {eventKey.replace("_", " ")}
                  </span>
                  <span className="text-[10px] text-muted-foreground leading-relaxed">
                    {eventDescriptions[eventKey]}
                  </span>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold font-display text-sm">
                    {count}
                  </div>
                  <span className="text-[9px] uppercase tracking-wider font-bold text-muted-foreground/60">Events</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
