import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Mail, Lock, User, ArrowRight, AlertCircle, Phone } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { motion } from "framer-motion";

const NICHES = [
  { id: "dance", label: "Dance" },
  { id: "fashion", label: "Fashion" },
  { id: "travel", label: "Travel" },
  { id: "food", label: "Food" },
  { id: "comedy", label: "Comedy" },
  { id: "motivation", label: "Motivation" },
  { id: "fitness", label: "Fitness" },
  { id: "current_affairs", label: "Current Affairs" },
  { id: "devotional", label: "Devotional" },
  { id: "tech", label: "Tech" },
  { id: "narrative_edit", label: "Creative Edit" },
  { id: "romance_relationship", label: "Romance & Relationships" },
  { id: "all", label: "All" },
];

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "kn", label: "Kannada" },
  { code: "ta", label: "Tamil" },
  { code: "te", label: "Telugu" },
  { code: "bn", label: "Bengali" },
  { code: "mr", label: "Marathi" },
];

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Sign Up — Trendrop" },
      { name: "description", content: "Create your Trendrop account" },
    ],
  }),
  component: SignupPage,
});

function SignupPage() {
  const navigate = useNavigate();
  const { signup } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [niche, setNiche] = useState("all");
  const [language, setLanguage] = useState("en");
  const [stateName, setStateName] = useState("");
  const [tier, setTier] = useState("nano");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validate passwords match
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      toast.error("Passwords do not match");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      toast.error("Password must be at least 6 characters");
      return;
    }

    if (!phoneNumber || phoneNumber.length < 10) {
      setError("Please enter a valid phone number");
      toast.error("Please enter a valid phone number");
      return;
    }

    setLoading(true);

    try {
      await signup(email, password, phoneNumber, niche, language, stateName, tier);
      toast.success("Account created successfully!");
      // AuthContext handles navigation automatically
    } catch (err) {
      console.error("Signup error:", err);
      const errorMessage = err instanceof Error ? err.message : "An error occurred. Please try again.";
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
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
              Create Account
            </h1>
            <p className="text-slate-600 dark:text-slate-400">
              Join Trendrop to discover trending content
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div className="space-y-2">
              <label htmlFor="email" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Email
              </label>
              <div className="relative flex items-center">
                <Mail className="absolute left-3.5 h-5 w-5 text-slate-400 pointer-events-none" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-12 w-full"
                  required
                />
              </div>
            </div>

            {/* Phone Number */}
            <div className="space-y-2">
              <label htmlFor="phoneNumber" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Phone Number
              </label>
              <div className="relative flex items-center">
                <Phone className="absolute left-3.5 h-5 w-5 text-slate-400 pointer-events-none" />
                <Input
                  id="phoneNumber"
                  type="tel"
                  placeholder="+91 98765 43210"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="pl-12 w-full"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div className="space-y-2">
              <label htmlFor="password" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Password
              </label>
              <div className="relative flex items-center">
                <Lock className="absolute left-3.5 h-5 w-5 text-slate-400 pointer-events-none" />
                <Input
                  id="password"
                  type="password"
                  placeholder="•••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-12 w-full"
                  required
                  minLength={6}
                />
              </div>
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <label htmlFor="confirmPassword" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Confirm Password
              </label>
              <div className="relative flex items-center">
                <Lock className="absolute left-3.5 h-5 w-5 text-slate-400 pointer-events-none" />
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="•••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="pl-12 w-full"
                  required
                  minLength={6}
                />
              </div>
            </div>

            {/* Niche */}
            <div className="space-y-2">
              <label htmlFor="niche" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Niche
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
                <select
                  id="niche"
                  value={niche}
                  onChange={(e) => setNiche(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                  required
                >
                  {NICHES.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Language */}
            <div className="space-y-2">
              <label htmlFor="language" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Language
              </label>
              <select
                id="language"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
                required
              >
                {LANGUAGES.map((l) => (
                  <option key={l.code} value={l.code}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            {/* State */}
            <div className="space-y-2">
              <label htmlFor="state" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                State (Optional)
              </label>
              <select
                id="state"
                value={stateName}
                onChange={(e) => setStateName(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="">Select State</option>
                <option value="MH">Maharashtra</option>
                <option value="KA">Karnataka</option>
                <option value="KL">Kerala</option>
                <option value="TN">Tamil Nadu</option>
                <option value="DL">Delhi</option>
                <option value="UP">Uttar Pradesh</option>
                <option value="WB">West Bengal</option>
                <option value="GJ">Gujarat</option>
                <option value="RJ">Rajasthan</option>
                <option value="PB">Punjab</option>
                <option value="AP">Andhra Pradesh</option>
                <option value="TG">Telangana</option>
                <option value="AS">Assam</option>
              </select>
            </div>

            {/* Tier */}
            <div className="space-y-2">
              <label htmlFor="tier" className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Creator Tier
              </label>
              <select
                id="tier"
                value={tier}
                onChange={(e) => setTier(e.target.value)}
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <option value="nano">Nano (0-10k)</option>
                <option value="micro">Micro (10k-100k)</option>
                <option value="macro">Macro (100k-1M)</option>
                <option value="mega">Mega (1M+)</option>
              </select>
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
              disabled={loading}
            >
              {loading ? "Creating account..." : "Create Account"}
              {!loading && <ArrowRight className="ml-2 h-4 w-4" />}
            </Button>
          </form>

          {/* Footer */}
          <div className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
            Already have an account?{" "}
            <button
              type="button"
              onClick={() => navigate({ to: "/login" })}
              className="text-primary dark:text-primary hover:underline font-medium"
            >
              Login
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}