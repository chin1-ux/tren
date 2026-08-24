import { createFileRoute, useNavigate, redirect } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { getAdminAuditLog } from "@/lib/api";
import { Shield, ArrowLeft, Search, Calendar, User, Activity, Download, Filter } from "lucide-react";
import { motion } from "framer-motion";

export const Route = createFileRoute("/admin/audit")({
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
      { title: "Audit Log — Trendrop Admin" },
    ],
  }),
  component: AdminAuditPage,
});

function AdminAuditPage() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Debounce search to avoid excessive API calls
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
    }, 500);
    return () => clearTimeout(timer);
  }, [search]);

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const response = await getAdminAuditLog(debouncedSearch, actionFilter, 100, dateFrom || undefined, dateTo || undefined);
      setLogs(response.audit_log || []);
    } catch (err: any) {
      console.error(err);
      toast.error("Failed to load audit logs");
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [debouncedSearch, actionFilter, dateFrom, dateTo]);

  const exportLogs = () => {
    // Convert logs to CSV
    const headers = ["ID", "Admin Email", "Action", "Target User", "IP Address", "Timestamp", "Details"];
    const csvContent = [
      headers.join(","),
      ...logs.map(log => [
        log.id,
        log.admin_email,
        log.action,
        log.target_user_email || "N/A",
        log.ip_address,
        log.timestamp,
        JSON.stringify(log.details).replace(/"/g, '""')
      ].join(","))
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success("Audit logs exported");
  };

  const filteredLogs = logs; // Backend handles filtering now

  const getActionColor = (action: string) => {
    switch (action) {
      case "plan_change": return "bg-blue-500/10 text-blue-500";
      case "account_lock": return "bg-red-500/10 text-red-500";
      case "account_unlock": return "bg-green-500/10 text-green-500";
      case "login_attempt": return "bg-purple-500/10 text-purple-500";
      default: return "bg-gray-500/10 text-gray-500";
    }
  };

  return (
    <div className="flex flex-col gap-6 px-4 pt-6 pb-12 min-h-screen bg-background text-foreground">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate({ to: "/admin/users" })}
            className="p-1 rounded-full hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-xl font-bold font-display bg-gradient-to-r from-primary to-rose-400 bg-clip-text text-transparent flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Audit Log
            </h1>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              View all admin actions and security events
            </p>
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={exportLogs}
          className="rounded-full gap-2"
        >
          <Download className="h-4 w-4" />
          Export
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by email, action..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="pl-10 pr-8 py-2 bg-card border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 appearance-none cursor-pointer"
          >
            <option value="all">All Actions</option>
            <option value="plan_change">Plan Changes</option>
            <option value="account_lock">Account Locks</option>
            <option value="account_unlock">Account Unlocks</option>
            <option value="login_attempt">Login Attempts</option>
          </select>
        </div>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="px-4 py-2 bg-card border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
        <input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="px-4 py-2 bg-card border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>

      {/* Audit Log List */}
      {loading ? (
        <div className="grid grid-cols-1 gap-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-24 bg-card/50 border border-border/50 animate-pulse rounded-2xl" />
          ))}
        </div>
      ) : logs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Activity className="h-12 w-12 text-muted-foreground mb-3" />
          <p className="text-sm text-muted-foreground">No audit logs found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {logs.map((log, index) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className="bg-card border border-border p-4 rounded-2xl hover:border-primary/20 transition-all"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full ${getActionColor(log.action)}`}>
                      {log.action.replace("_", " ").toUpperCase()}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {new Date(log.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex items-center gap-2">
                      <User className="h-3 w-3 text-muted-foreground" />
                      <span className="font-medium">{log.admin_email}</span>
                      {log.target_user_email && (
                        <>
                          <span className="text-muted-foreground">→</span>
                          <span className="text-muted-foreground">{log.target_user_email}</span>
                        </>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                      <span>IP: {log.ip_address}</span>
                    </div>
                    {log.details && Object.keys(log.details).length > 0 && (
                      <div className="text-[10px] text-muted-foreground mt-2">
                        {Object.entries(log.details).map(([key, value]) => (
                          <span key={key} className="mr-3">
                            <strong>{key}:</strong> {String(value)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}