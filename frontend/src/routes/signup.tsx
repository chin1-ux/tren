import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Sparkles, ShieldCheck, Zap, TrendingUp, Music } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { motion } from "framer-motion";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Sign Up — Trendrop" },
      { name: "description", content: "Create your free Trendrop creator account" },
    ],
  }),
  component: SignupPage,
});

function SignupPage() {
  const navigate = useNavigate();
  const { loginWithGoogle } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleGoogleSignup = async () => {
    try {
      setLoading(true);
      await loginWithGoogle();
    } catch (err: any) {
      toast.error(err?.message || "Google sign-up failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        <div className="bg-white dark:bg-slate-800 rounded-3xl shadow-xl p-8 sm:p-10 border border-slate-200/80 dark:border-slate-700/80 flex flex-col items-center text-center">
          {/* Trendrop Concept 3 Logo */}
          <div className="relative mb-5 group">
            <img
              src="/icon-192.png"
              alt="Trendrop"
              className="w-20 h-20 rounded-[24%] shadow-lg object-contain transition-transform duration-300 group-hover:scale-105"
            />
          </div>

          {/* Heading */}
          <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight mb-2">
            Join Trendrop
          </h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm max-w-sm mb-6 leading-relaxed">
            Catch rising Instagram & audio trends early. Join thousands of creators engineering their viral reach.
          </p>

          {/* Feature Highlights */}
          <div className="w-full bg-slate-50 dark:bg-slate-900/60 rounded-2xl p-4 mb-6 border border-slate-100 dark:border-slate-800 space-y-3 text-left text-xs text-slate-600 dark:text-slate-300">
            <div className="flex items-center gap-2.5">
              <TrendingUp className="h-4 w-4 text-[#FF4D3D] flex-shrink-0" />
              <span><strong>Early Curve Audio Radar</strong> — discover tracks before they peak</span>
            </div>
            <div className="flex items-center gap-2.5">
              <Music className="h-4 w-4 text-[#C7F23A] flex-shrink-0" />
              <span><strong>Indian & Global Feed</strong> — filtered by language & niche</span>
            </div>
            <div className="flex items-center gap-2.5">
              <Zap className="h-4 w-4 text-amber-500 flex-shrink-0" />
              <span><strong>Instant Free Access</strong> — 100 free AI credits included</span>
            </div>
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-4 w-4 text-emerald-500 flex-shrink-0" />
              <span><strong>Verified Authentication</strong> — secure 1-tap Google sign-in</span>
            </div>
          </div>

          {/* Primary Google Signup Button */}
          <Button
            type="button"
            disabled={loading}
            className="w-full bg-[#4285F4] hover:bg-[#3367D6] text-white py-6 text-base font-semibold shadow-md flex items-center justify-center gap-3 transition-all rounded-xl hover:shadow-lg active:scale-[0.99] disabled:opacity-70"
            onClick={handleGoogleSignup}
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <svg className="h-5 w-5 bg-white rounded-full p-0.5" viewBox="0 0 24 24">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  fill="#EA4335"
                />
              </svg>
            )}
            {loading ? "Creating your account..." : "Sign up with Google (Instant Access)"}
          </Button>

          {/* Legal / Policy Note */}
          <p className="mt-5 text-[11px] text-slate-500 dark:text-slate-400 max-w-xs leading-normal">
            By signing up, you agree to Trendrop's{" "}
            <a href="/terms" className="underline hover:text-slate-700 dark:hover:text-slate-200">
              Terms of Service
            </a>{" "}
            and{" "}
            <a href="/privacy" className="underline hover:text-slate-700 dark:hover:text-slate-200">
              Privacy Policy
            </a>
            .
          </p>

          {/* Footer note: Already have an account */}
          <div className="w-full mt-6 pt-5 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
            Already have an account?{" "}
            <button
              type="button"
              onClick={() => navigate({ to: "/login" })}
              className="text-[#FF4D3D] hover:underline font-semibold"
            >
              Sign in
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}