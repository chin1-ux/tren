import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Lock, ArrowRight, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { supabase } from "@/lib/supabase";

export const Route = createFileRoute("/update-password")({
  head: () => ({
    meta: [
      { title: "Update Password — Trendrop" },
      { name: "description", content: "Update your Trendrop password" },
    ],
  }),
  component: UpdatePasswordPage,
});

function UpdatePasswordPage() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    // Supabase will automatically pick up the access_token from the URL hash
    // and set the session when the user lands here from a reset password email.
    const setupSession = async () => {
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        // Look for hash token directly just in case it hasn't processed yet
        if (typeof window !== 'undefined' && window.location.hash.includes('access_token')) {
            // We have a hash, let Supabase process it.
        } else {
            setError("No valid reset token found. The link may have expired or is malformed.");
        }
      }
    };
    setupSession();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // With Supabase auth JS client, if we have a session, we can just call updateUser
      const { error: sbError } = await supabase.auth.updateUser({ password });
      
      if (sbError) throw sbError;
      
      setSuccess(true);
      toast.success("Password updated successfully!");
    } catch (err) {
      console.error("Update password error:", err);
      const errorMessage = err instanceof Error ? err.message : "An error occurred. Please try again.";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-8 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 min-h-screen">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-8 border border-slate-200 dark:border-slate-700">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
              Update Password
            </h1>
            <p className="text-slate-600 dark:text-slate-400">
              Enter your new secure password
            </p>
          </div>

          {/* Form */}
          {!success ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Password */}
              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  New Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="•••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10"
                    style={{ paddingLeft: '2.5rem' }}
                    minLength={8}
                    required
                  />
                </div>
              </div>

              {/* Error */}
              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full"
                disabled={loading || !!error}
              >
                {loading ? "Updating..." : "Update Password"}
                {!loading && <ArrowRight className="ml-2 h-4 w-4" />}
              </Button>
            </form>
          ) : (
            <div className="space-y-6 text-center">
              <div className="flex justify-center">
                <CheckCircle2 className="h-12 w-12 text-green-500" />
              </div>
              <p className="text-slate-700 dark:text-slate-300">
                Your password has been successfully updated.
              </p>
              <Button
                type="button"
                className="w-full"
                onClick={() => navigate({ to: "/login" })}
              >
                Go to Login
              </Button>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
