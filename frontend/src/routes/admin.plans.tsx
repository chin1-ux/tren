import { createFileRoute, useNavigate, redirect } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { getAdminPlanFeatures, createAdminPlanFeature } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Shield, ShieldAlert, Crown, ArrowLeft, Plus, Save, X, DollarSign, CheckCircle } from "lucide-react";
import { motion } from "framer-motion";

export const Route = createFileRoute("/admin/plans")({
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
      { title: "Admin Plans — Trendrop" },
    ],
  }),
  component: AdminPlansPage,
});

function AdminPlansPage() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingPlan, setEditingPlan] = useState<any>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [authorized, setAuthorized] = useState(true);

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const data = await getAdminPlanFeatures();
      setPlans(data.plan_features || []);
      setAuthorized(true);
    } catch (err: any) {
      console.error(err);
      if (err?.status === 403) {
        setAuthorized(false);
        toast.error("Access Forbidden: Admin privileges required.");
      } else {
        toast.error("Failed to load plans.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlans();
  }, []);

  const handleEdit = (plan: any) => {
    setEditingPlan({ ...plan });
    setShowEditModal(true);
  };

  const handleSave = async () => {
    if (!editingPlan) return;

    try {
      await createAdminPlanFeature({
        plan_name: editingPlan.plan_name,
        display_name: editingPlan.display_name,
        price_monthly: editingPlan.price_monthly,
        price_yearly: editingPlan.price_yearly,
        api_limit_per_day: editingPlan.api_limit_per_day,
        trend_views_per_day: editingPlan.trend_views_per_day,
        features: editingPlan.features,
      });
      toast.success("Plan saved successfully");
      setShowEditModal(false);
      setEditingPlan(null);
      fetchPlans();
    } catch (err) {
      console.error(err);
      toast.error("Failed to save plan");
    }
  };

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
            This plan management panel is strictly restricted to internal administrators.
          </p>
          <Button onClick={() => navigate({ to: "/" })} className="w-full rounded-full mt-2">
            Return to Dashboard
          </Button>
        </motion.div>
      </div>
    );
  }

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
            <Crown className="h-5 w-5 text-primary" />
            Plan Management
          </h1>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            Manage subscription plans and features
          </p>
        </div>
      </div>

      {/* Plans List */}
      {loading ? (
        <div className="grid grid-cols-1 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-card/50 border border-border/50 animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plans.map((plan, index) => (
            <motion.div
              key={plan.plan_name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-card border border-border p-5 rounded-2xl hover:border-primary/20 transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold font-display">{plan.display_name}</h3>
                  <p className="text-xs text-muted-foreground">{plan.plan_name}</p>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleEdit(plan)}
                  className="rounded-full text-xs"
                >
                  Edit
                </Button>
              </div>

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Monthly:</span>
                  <span className="text-sm font-semibold flex items-center gap-1">
                    <DollarSign className="h-3 w-3" />
                    {plan.price_monthly}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Yearly:</span>
                  <span className="text-sm font-semibold flex items-center gap-1">
                    <DollarSign className="h-3 w-3" />
                    {plan.price_yearly}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">API/day:</span>
                  <span className="text-sm font-semibold">
                    {plan.api_limit_per_day === -1 ? "Unlimited" : plan.api_limit_per_day}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">Trends/day:</span>
                  <span className="text-sm font-semibold">
                    {plan.trend_views_per_day === -1 ? "Unlimited" : plan.trend_views_per_day}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-border">
                <p className="text-xs text-muted-foreground mb-2">Features:</p>
                <div className="flex flex-wrap gap-1">
                  {Array.isArray(plan.features) && plan.features.map((feature: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 text-[10px] bg-primary/10 text-primary rounded-full flex items-center gap-1"
                    >
                      <CheckCircle className="h-2 w-2" />
                      {feature}
                    </span>
                  ))}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && editingPlan && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-card border border-border rounded-3xl p-6 max-w-md w-full max-h-[80vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold font-display">Edit Plan</h2>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowEditModal(false)}
                className="rounded-full"
              >
                ✕
              </Button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Plan Name</label>
                <input
                  type="text"
                  value={editingPlan.plan_name}
                  onChange={(e) => setEditingPlan({ ...editingPlan, plan_name: e.target.value })}
                  className="w-full px-3 py-2 bg-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  disabled
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Display Name</label>
                <input
                  type="text"
                  value={editingPlan.display_name}
                  onChange={(e) => setEditingPlan({ ...editingPlan, display_name: e.target.value })}
                  className="w-full px-3 py-2 bg-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Monthly Price</label>
                  <input
                    type="number"
                    value={editingPlan.price_monthly}
                    onChange={(e) => setEditingPlan({ ...editingPlan, price_monthly: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Yearly Price</label>
                  <input
                    type="number"
                    value={editingPlan.price_yearly}
                    onChange={(e) => setEditingPlan({ ...editingPlan, price_yearly: parseFloat(e.target.value) })}
                    className="w-full px-3 py-2 bg-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">API Limit/day</label>
                  <input
                    type="number"
                    value={editingPlan.api_limit_per_day}
                    onChange={(e) => setEditingPlan({ ...editingPlan, api_limit_per_day: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Trend Views/day</label>
                  <input
                    type="number"
                    value={editingPlan.trend_views_per_day}
                    onChange={(e) => setEditingPlan({ ...editingPlan, trend_views_per_day: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-muted-foreground mb-1 block">Features (comma-separated)</label>
                <textarea
                  value={Array.isArray(editingPlan.features) ? editingPlan.features.join(', ') : editingPlan.features}
                  onChange={(e) => setEditingPlan({ ...editingPlan, features: e.target.value.split(',').map(f => f.trim()) })}
                  className="w-full px-3 py-2 bg-muted border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 h-24 resize-none"
                />
              </div>

              <Button onClick={handleSave} className="w-full rounded-full">
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </Button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}