import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Sparkles, ShieldCheck, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { motion } from "framer-motion";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign In — Trendrop" },
      { name: "description", content: "Sign in to your Trendrop creator account" },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const { loginWithGoogle } = useAuth();
  const [loading, setLoading] = useState(false);

  const handleGoogleLogin = async () => {
    try {
      setLoading(true);
      await loginWithGoogle();
    } catch (err: any) {
      toast.error(err?.message || "Google sign-in failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-12 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 min-h-screen">
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
            Welcome to Trendrop
          </h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm max-w-sm mb-6 leading-relaxed">
            India's AI trend intelligence platform. Spot viral audios & creator formats before they peak.
          </p>

          {/* Value Props */}
          <div className="w-full bg-slate-50 dark:bg-slate-900/60 rounded-2xl p-4 mb-6 border border-slate-100 dark:border-slate-800 space-y-2.5 text-left text-xs text-slate-600 dark:text-slate-300">
            <div className="flex items-center gap-2.5">
              <Zap className="h-4 w-4 text-[#FF4D3D] flex-shrink-0" />
              <span><strong>Instant 1-Tap Access</strong> — no passwords or reset links</span>
            </div>
            <div className="flex items-center gap-2.5">
              <Sparkles className="h-4 w-4 text-[#C7F23A] flex-shrink-0 fill-[#C7F23A]/20" />
              <span><strong>Live Audio Velocity Radar</strong> — rising songs in real time</span>
            </div>
            <div className="flex items-center gap-2.5">
              <ShieldCheck className="h-4 w-4 text-emerald-500 flex-shrink-0" />
              <span><strong>100% Free & Safe</strong> — verified Google account authentication</span>
            </div>
          </div>

          {/* Primary Google Login Button */}
          <Button
            type="button"
            disabled={loading}
            className="w-full bg-[#4285F4] hover:bg-[#3367D6] text-white py-6 text-base font-semibold shadow-md flex items-center justify-center gap-3 transition-all rounded-xl hover:shadow-lg active:scale-[0.99] disabled:opacity-70"
            onClick={handleGoogleLogin}
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
            {loading ? "Connecting to Google..." : "Continue with Google"}
          </Button>

          {/* Legal / Policy Note */}
          <p className="mt-5 text-[11px] text-slate-500 dark:text-slate-400 max-w-xs leading-normal">
            By signing in, you agree to Trendrop's{" "}
            <a href="/terms" className="underline hover:text-slate-700 dark:hover:text-slate-200">
              Terms of Service
            </a>{" "}
            and{" "}
            <a href="/privacy" className="underline hover:text-slate-700 dark:hover:text-slate-200">
              Privacy Policy
            </a>
            .
          </p>

          {/* Footer note */}
          <div className="w-full mt-6 pt-5 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400 flex flex-col gap-2">
            <div>
              New to Trendrop?{" "}
              <button
                type="button"
                onClick={() => navigate({ to: "/signup" })}
                className="text-[#FF4D3D] hover:underline font-semibold"
              >
                Get instant access
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}