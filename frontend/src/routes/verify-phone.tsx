import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect, useRef } from "react";
import { Phone, ArrowRight, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { API_URL } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";

type VerifyPhoneSearch = {
  phone?: string;
};

export const Route = createFileRoute("/verify-phone")({
  validateSearch: (search: Record<string, unknown>): VerifyPhoneSearch => {
    return {
      phone: typeof search.phone === "string" ? search.phone : undefined,
    };
  },
  head: () => ({
    meta: [
      { title: "Verify Phone — Trendrop" },
      { name: "description", content: "Verify your phone number" },
    ],
  }),
  component: VerifyPhonePage,
});

function VerifyPhonePage() {
  const { phone } = Route.useSearch();
  const navigate = useNavigate();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [error, setError] = useState("");
  const [cooldown, setCooldown] = useState(30);

  // Focus the input on mount
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  // Cooldown timer
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(c => c - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldown]);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone) {
      setError("No phone number provided.");
      return;
    }
    if (code.length !== 6) {
      setError("Please enter a valid 6-digit code.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/auth/verify-phone`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: phone, code }),
      });
      const data = await response.json();

      if (data.success) {
        toast.success("Phone verified successfully! Please log in.");
        navigate({ to: "/login" });
      } else {
        throw new Error(data.error || "Verification failed");
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Invalid verification code";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0 || !phone) return;
    
    setResending(true);
    try {
      const response = await fetch(`${API_URL}/api/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone_number: phone }),
      });
      const data = await response.json();
      
      if (data.success) {
        toast.success("Verification code sent!");
        setCooldown(30); // Reset cooldown
      } else {
        throw new Error(data.error || "Failed to resend code");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to resend code");
    } finally {
      setResending(false);
    }
  };

  if (!phone) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4">
        <h1 className="text-xl font-bold mb-4">Missing Phone Number</h1>
        <Button onClick={() => navigate({ to: "/signup" })}>Back to Signup</Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-8 border border-slate-200 dark:border-slate-700">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">
              Verify your phone
            </h1>
            <p className="text-slate-600 dark:text-slate-400 text-sm">
              We sent a 6-digit code to <span className="font-semibold text-slate-800 dark:text-slate-200">{phone}</span>
            </p>
          </div>

          <form onSubmit={handleVerify} className="space-y-6">
            <div className="space-y-2">
              <label htmlFor="code" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Verification Code
              </label>
              <div className="relative">
                <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400 pointer-events-none" />
                <Input
                  ref={inputRef}
                  id="code"
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder="123456"
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/[^0-9]/g, ''))}
                  className="pl-12 w-full text-center tracking-widest text-lg font-semibold"
                  required
                />
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-600 dark:text-red-400 text-sm">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-11"
              disabled={loading || code.length !== 6}
            >
              {loading ? "Verifying..." : "Verify & Continue"}
              {!loading && <ArrowRight className="ml-2 h-4 w-4" />}
            </Button>
            
            <div className="text-center mt-6">
              <button
                type="button"
                onClick={handleResend}
                disabled={cooldown > 0 || resending}
                className="text-sm font-medium text-primary dark:text-primary hover:text-primary dark:hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center w-full gap-2 transition-colors"
              >
                <RefreshCw className={`h-4 w-4 ${resending ? 'animate-spin' : ''}`} />
                {cooldown > 0 ? `Resend code in ${cooldown}s` : "Resend code"}
              </button>
            </div>
          </form>
        </div>
      </motion.div>
    </div>
  );
}
