import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Shield, ArrowLeft, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";

export const Route = createFileRoute("/admin/login")({
  head: () => ({
    meta: [
      { title: "Admin Login — Trendrop" },
    ],
  }),
  component: AdminLoginPage,
});

function AdminLoginPage() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4 bg-background text-foreground">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary/10 mb-4">
            <Shield className="h-8 w-8 text-primary" />
          </div>
          <h1 className="text-2xl font-bold font-display mb-2">Admin Access</h1>
          <p className="text-sm text-muted-foreground">
            Admin panel now uses Supabase Auth
          </p>
        </div>

        {/* Info Card */}
        <div className="bg-card border border-border rounded-3xl p-8 shadow-xl">
          <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/20 rounded-xl mb-6">
            <AlertCircle className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-blue-500">
              The admin panel now uses your existing Supabase authentication. 
              Simply log in with your regular account if you have admin privileges.
            </p>
          </div>

          <div className="text-center">
            <p className="text-sm text-muted-foreground mb-4">
              Contact the system administrator to request admin access.
            </p>
          </div>
        </div>

        {/* Back Button */}
        <div className="mt-6 text-center">
          <button
            onClick={() => navigate({ to: "/" })}
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Return to Dashboard
          </button>
        </div>
      </motion.div>
    </div>
  );
}