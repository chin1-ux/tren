import { createFileRoute, useNavigate, redirect } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { 
  getAdminUsers, 
  getAdminUserDetails, 
  updateAdminUserPlan, 
  lockAdminUserAccount, 
  unlockAdminUserAccount 
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Shield, ShieldAlert, Search, Lock, Unlock, ChevronDown, AlertCircle, ArrowLeft, Users, Filter, Crown, Activity, Clock } from "lucide-react";
import { motion } from "framer-motion";

export const Route = createFileRoute("/admin/users")({
  beforeLoad: async () => {
    // beforeLoad runs server-side in SSR — localStorage only exists in the browser
    if (typeof window === "undefined") {
      throw redirect({ to: "/admin/login" });
    }
    const token = localStorage.getItem("admin_token");
    if (!token) {
      throw redirect({ to: "/admin/login" });
    }
    
    // Validate token with backend
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
      // Only clear storage and redirect if it's not already a redirect
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
      { title: "Admin Users — Trendrop" },
    ],
  }),
  component: AdminUsersPage,
});

function AdminUsersPage() {
  const navigate = useNavigate();
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState("all");
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [showUserDetails, setShowUserDetails] = useState(false);
  const [authorized, setAuthorized] = useState(true);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await getAdminUsers(search, planFilter);
      setUsers(data.users || []);
      setAuthorized(true);
    } catch (err: any) {
      console.error(err);
      if (err?.status === 403) {
        setAuthorized(false);
        toast.error("Access Forbidden: Admin privileges required.");
      } else {
        toast.error("Failed to load users.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [search, planFilter]);

  const updatePlan = async (email: string, newPlan: string) => {
    try {
      await updateAdminUserPlan(email, newPlan, "Admin update");
      toast.success(`Plan updated to ${newPlan}`);
      fetchUsers();
    } catch (err) {
      console.error(err);
      toast.error("Failed to update plan");
    }
  };

  const lockAccount = async (email: string) => {
    try {
      await lockAdminUserAccount(email, "Admin lock");
      toast.success("Account locked");
      fetchUsers();
    } catch (err) {
      console.error(err);
      toast.error("Failed to lock account");
    }
  };

  const unlockAccount = async (email: string) => {
    try {
      await unlockAdminUserAccount(email, "Admin unlock");
      toast.success("Account unlocked");
      fetchUsers();
    } catch (err) {
      console.error(err);
      toast.error("Failed to unlock account");
    }
  };

  const viewUserDetails = async (email: string) => {
    try {
      const data = await getAdminUserDetails(email);
      setSelectedUser(data);
      setShowUserDetails(true);
    } catch (err) {
      console.error(err);
      toast.error("Failed to load user details");
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
            This user management panel is strictly restricted to internal administrators.
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
            <Users className="h-5 w-5 text-primary" />
            User Management
          </h1>
          <p className="text-[10px] text-muted-foreground mt-0.5">
            Manage users, plans, and account security
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <select
            value={planFilter}
            onChange={(e) => setPlanFilter(e.target.value)}
            className="pl-10 pr-8 py-2 bg-card border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 appearance-none cursor-pointer"
          >
            <option value="all">All Plans</option>
            <option value="free">Free</option>
            <option value="pro">Pro</option>
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>
      </div>

      {/* User List */}
      {loading ? (
        <div className="grid grid-cols-1 gap-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-20 bg-card/50 border border-border/50 animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : users.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Users className="h-12 w-12 text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground">No users found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {users.map((user, index) => (
            <motion.div
              key={user.email}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-card border border-border p-4 rounded-2xl hover:border-primary/20 transition-all"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-sm font-semibold font-display truncate">{user.email}</h3>
                    {user.status === 'locked' && (
                      <span className="px-2 py-0.5 text-[10px] font-bold bg-red-500/10 text-red-500 rounded-full">
                        LOCKED
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Crown className="h-3 w-3" />
                      {user.plan || 'free'}
                    </span>
                    <span className="flex items-center gap-1">
                      <Activity className="h-3 w-3" />
                      {user.usage_count || 0} uses
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => viewUserDetails(user.email)}
                    className="rounded-full text-xs"
                  >
                    Details
                  </Button>
                  {user.status === 'locked' ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => unlockAccount(user.email)}
                      className="rounded-full text-xs"
                    >
                      <Unlock className="h-3 w-3" />
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => lockAccount(user.email)}
                      className="rounded-full text-xs"
                    >
                      <Lock className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* User Details Modal */}
      {showUserDetails && selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-card border border-border rounded-3xl p-6 max-w-md w-full max-h-[80vh] overflow-y-auto"
          >
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold font-display">User Details</h2>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowUserDetails(false)}
                className="rounded-full"
              >
                ✕
              </Button>
            </div>

            <div className="space-y-4">
              {/* User Info */}
              <div className="bg-muted/50 rounded-xl p-4">
                <h3 className="text-xs font-semibold text-muted-foreground mb-2">Account Information</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Email:</span>
                    <span className="font-medium">{selectedUser.user?.email}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Plan:</span>
                    <span className="font-medium">{selectedUser.user?.plan}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status:</span>
                    <span className={`font-medium ${selectedUser.user?.status === 'locked' ? 'text-red-500' : 'text-green-500'}`}>
                      {selectedUser.user?.status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Created:</span>
                    <span className="font-medium">
                      {selectedUser.user?.created_at ? new Date(selectedUser.user.created_at).toLocaleDateString() : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Plan Change */}
              <div className="bg-muted/50 rounded-xl p-4">
                <h3 className="text-xs font-semibold text-muted-foreground mb-2">Change Plan</h3>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant={selectedUser.user?.plan === 'free' ? 'default' : 'outline'}
                    onClick={() => updatePlan(selectedUser.user?.email, 'free')}
                    className="flex-1 rounded-full text-xs"
                  >
                    Free
                  </Button>
                  <Button
                    size="sm"
                    variant={selectedUser.user?.plan === 'pro' ? 'default' : 'outline'}
                    onClick={() => updatePlan(selectedUser.user?.email, 'pro')}
                    className="flex-1 rounded-full text-xs"
                  >
                    Pro
                  </Button>
                </div>
              </div>

              {/* Usage Stats */}
              {selectedUser.usage_stats && (
                <div className="bg-muted/50 rounded-xl p-4">
                  <h3 className="text-xs font-semibold text-muted-foreground mb-2">Usage Statistics</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Total Usage:</span>
                      <span className="font-medium">{selectedUser.usage_stats.total_usage || 0}</span>
                    </div>
                    {selectedUser.usage_stats.feature_usage && Object.keys(selectedUser.usage_stats.feature_usage).length > 0 && (
                      <div>
                        <span className="text-muted-foreground text-xs">Feature Usage:</span>
                        <div className="mt-1 space-y-1">
                          {Object.entries(selectedUser.usage_stats.feature_usage).map(([feature, count]) => (
                            <div key={feature} className="flex justify-between text-xs">
                              <span className="text-muted-foreground">{feature}:</span>
                              <span className="font-medium">{count as number}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Devices */}
              {selectedUser.devices && selectedUser.devices.length > 0 && (
                <div className="bg-muted/50 rounded-xl p-4">
                  <h3 className="text-xs font-semibold text-muted-foreground mb-2">Registered Devices</h3>
                  <div className="space-y-2">
                    {selectedUser.devices.map((device: any, index: number) => (
                      <div key={index} className="text-xs">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Device:</span>
                          <span className="font-medium">{device.device_fingerprint?.substring(0, 16)}...</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Last Seen:</span>
                          <span className="font-medium">
                            {device.last_seen ? new Date(device.last_seen).toLocaleDateString() : 'N/A'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}