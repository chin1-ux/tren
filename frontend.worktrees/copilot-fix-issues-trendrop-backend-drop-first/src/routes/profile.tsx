import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  User, Users, Mail, Award, Sparkles, ShieldCheck
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { subscribe, createPaymentOrder, verifyPayment, getUserPlan } from "@/lib/api";
import { toast } from "sonner";
import { ThemeToggle } from "@/components/ThemeToggle";

export const Route = createFileRoute("/profile")({
  head: () => ({
    meta: [
      { title: "Profile — Trendrop" },
      { name: "description", content: "Personalize your trend feed, creator info, and alert preferences." },
    ],
  }),
  component: ProfilePage,
});

const NICHES = [
  { id: "dance",      emoji: "💃", label: "Dance" },
  { id: "fashion",    emoji: "👗", label: "Fashion" },
  { id: "travel",     emoji: "✈️", label: "Travel" },
  { id: "food",       emoji: "🍳", label: "Food" },
  { id: "comedy",     emoji: "😂", label: "Comedy" },
  { id: "motivation", emoji: "💪", label: "Motivation" },
  { id: "devotional", emoji: "🙏", label: "Devotional" },
  { id: "fitness",    emoji: "🏋️", label: "Fitness" },
  { id: "study",      emoji: "📚", label: "Study" },
  { id: "scenic",     emoji: "🎬", label: "Cinematic" },
];

const LANGUAGES = [
  { code: "hi", emoji: "🇮🇳", label: "Hindi" },
  { code: "kn", emoji: "🎯", label: "Kannada" },
  { code: "ta", emoji: "🌴", label: "Tamil" },
  { code: "te", emoji: "🌟", label: "Telugu" },
  { code: "bn", emoji: "🐯", label: "Bengali" },
  { code: "mr", emoji: "🦁", label: "Marathi" },
  { code: "en", emoji: "🌐", label: "English" },
];

const FREQUENCIES = [
  { id: "daily", label: "Daily" },
  { id: "few_times_week", label: "3x a Week" },
  { id: "weekly", label: "Weekly" },
];

function ProfilePage() {
  const [email, setEmail] = useState("");
  const [instagramHandle, setInstagramHandle] = useState("");
  const [followers, setFollowers] = useState("");
  
  const [niche, setNiche] = useState("dance");
  const [language, setLanguage] = useState("hi");
  const [postingFrequency, setPostingFrequency] = useState("daily");

  const [notifyTrendAlerts, setNotifyTrendAlerts] = useState(true);
  const [notifyDailyIdeas, setNotifyDailyIdeas] = useState(true);
  const [notifyBrandDeals, setNotifyBrandDeals] = useState(true);
  const [notifyWeeklyReport, setNotifyWeeklyReport] = useState(true);

  const [plan, setPlan] = useState("Free Trial");

  const [saving, setSaving] = useState(false);
  const [upgrading, setUpgrading] = useState(false);

  const [langSearch, setLangSearch] = useState("");
  const [nicheSearch, setNicheSearch] = useState("");
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  const [showNicheDropdown, setShowNicheDropdown] = useState(false);

  useEffect(() => {
    const sync = () => {
      const e = localStorage.getItem("trendrop_email");
      const ig = localStorage.getItem("trendrop_instagram_handle");
      const f = localStorage.getItem("trendrop_followers");
      const n = localStorage.getItem("trendrop_niche");
      const l = localStorage.getItem("trendrop_language");
      const freq = localStorage.getItem("trendrop_posting_frequency");

      const nt = localStorage.getItem("trendrop_notify_trend_alerts");
      const nd = localStorage.getItem("trendrop_notify_daily_ideas");
      const nb = localStorage.getItem("trendrop_notify_brand_deals");
      const nw = localStorage.getItem("trendrop_notify_weekly_report");

      if (e) setEmail(e);
      if (ig) setInstagramHandle(ig);
      if (f) setFollowers(f);
      if (n) setNiche(n);
      if (l) setLanguage(l);
      if (freq) setPostingFrequency(freq);

      if (nt !== null) setNotifyTrendAlerts(nt === "true");
      if (nd !== null) setNotifyDailyIdeas(nd === "true");
      if (nb !== null) setNotifyBrandDeals(nb === "true");
      if (nw !== null) setNotifyWeeklyReport(nw === "true");
    };

    sync();
    window.addEventListener("storage", sync);
    window.addEventListener("focus", sync);

    // Sync plan from server (source of truth)
    const savedEmail = localStorage.getItem("trendrop_email");
    if (savedEmail) {
      getUserPlan(savedEmail)
        .then(({ plan: serverPlan }) => {
          const displayPlan = serverPlan === "pro" ? "Pro Creator" : "Free Trial";
          setPlan(displayPlan);
          localStorage.setItem("trendrop_plan", displayPlan);
        })
        .catch(() => {
          // Fallback to cached value if server is unreachable
          const p = localStorage.getItem("trendrop_plan");
          if (p) setPlan(p);
        });
    } else {
      const p = localStorage.getItem("trendrop_plan");
      if (p) setPlan(p);
    }

    return () => {
      window.removeEventListener("storage", sync);
      window.removeEventListener("focus", sync);
    };
  }, []);

  const save = async () => {
    if (!email.includes("@")) {
      toast.error("Please enter a valid email");
      return;
    }
    setSaving(true);
    try {
      const res = await subscribe({ email, niche, language });
      if (res && res.auth_token) {
        localStorage.setItem("trendrop_token", res.auth_token);
      }
      
      localStorage.setItem("trendrop_email", email);
      localStorage.setItem("trendrop_instagram_handle", instagramHandle);
      localStorage.setItem("trendrop_followers", followers);
      localStorage.setItem("trendrop_niche", niche);
      localStorage.setItem("trendrop_language", language);
      localStorage.setItem("trendrop_posting_frequency", postingFrequency);
      localStorage.setItem("trendrop_notify_trend_alerts", String(notifyTrendAlerts));
      localStorage.setItem("trendrop_notify_daily_ideas", String(notifyDailyIdeas));
      localStorage.setItem("trendrop_notify_brand_deals", String(notifyBrandDeals));
      localStorage.setItem("trendrop_notify_weekly_report", String(notifyWeeklyReport));
      
      toast.success("Profile saved successfully! ✓");
    } catch {
      // Still persist local fields, but be honest that the server sync failed
      localStorage.setItem("trendrop_email", email);
      localStorage.setItem("trendrop_instagram_handle", instagramHandle);
      localStorage.setItem("trendrop_followers", followers);
      localStorage.setItem("trendrop_niche", niche);
      localStorage.setItem("trendrop_language", language);
      localStorage.setItem("trendrop_posting_frequency", postingFrequency);
      localStorage.setItem("trendrop_notify_trend_alerts", String(notifyTrendAlerts));
      localStorage.setItem("trendrop_notify_daily_ideas", String(notifyDailyIdeas));
      localStorage.setItem("trendrop_notify_brand_deals", String(notifyBrandDeals));
      localStorage.setItem("trendrop_notify_weekly_report", String(notifyWeeklyReport));
      
      toast.error("Could not sync to server. Preferences saved locally — check your connection.");
    } finally {
      setSaving(false);
    }
  };

  const handleUpgrade = async () => {
    const activeEmail = email || localStorage.getItem("trendrop_email") || "";
    if (!activeEmail.includes("@")) {
      toast.error("Please save your email address first before upgrading.");
      return;
    }
    setUpgrading(true);
    try {
      // Step 1 — Create Razorpay order on the backend
      const order = await createPaymentOrder(activeEmail);

      // Step 2 — Load Razorpay checkout script dynamically
      await new Promise<void>((resolve, reject) => {
        if ((window as any).Razorpay) { resolve(); return; }
        const script = document.createElement("script");
        script.src = "https://checkout.razorpay.com/v1/checkout.js";
        script.onload = () => resolve();
        script.onerror = () => reject(new Error("Failed to load Razorpay SDK"));
        document.head.appendChild(script);
      });

      // Step 3 — Open checkout modal
      await new Promise<void>((resolve, reject) => {
        const rzp = new (window as any).Razorpay({
          key: order.key_id,
          amount: order.amount,
          currency: order.currency,
          name: "Trendrop",
          description: "Pro Creator Plan — ₹999/month",
          order_id: order.order_id,
          prefill: { email: activeEmail },
          theme: { color: "#8b5cf6" },
          handler: async (response: {
            razorpay_order_id: string;
            razorpay_payment_id: string;
            razorpay_signature: string;
          }) => {
            try {
              // Step 4 — Verify payment server-side (HMAC check)
              const result = await verifyPayment({
                razorpay_order_id:   response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature:  response.razorpay_signature,
                email: activeEmail,
              });
              if (result.success) {
                // Step 5 — Only now update local plan state
                setPlan("Pro Creator");
                localStorage.setItem("trendrop_plan", "Pro Creator");
                toast.success("Welcome to Pro Creator! 🚀 Your plan is now active.");
                resolve();
              } else {
                toast.error("Payment received but verification failed. Please contact support.");
                reject(new Error("Verification failed"));
              }
            } catch (err) {
              toast.error("Payment verification error. Contact support with your payment ID.");
              reject(err);
            }
          },
          modal: {
            ondismiss: () => {
              toast.info("Payment cancelled.");
              reject(new Error("Dismissed"));
            },
          },
        });
        rzp.open();
      });
    } catch (err: any) {
      if (err?.message !== "Dismissed") {
        toast.error(err?.message || "Upgrade failed. Please try again.");
      }
    } finally {
      setUpgrading(false);
    }
  };

  return (
    <div className="flex flex-col gap-5 px-4 pb-12 pt-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold gradient-text">Your Profile</h1>
          <p className="text-sm text-muted-foreground">Manage your creator info and account tier</p>
        </div>
        <ThemeToggle />
      </div>

      {/* Creator Info Section */}
      <div className="glass-card p-5 space-y-4">
        <h2 className="font-display text-base font-bold flex items-center gap-2 text-foreground">
          <User className="h-5 w-5 text-primary" /> Creator Info
        </h2>
        
        <div className="space-y-3">
          <div>
            <label className="text-xs font-semibold text-muted-foreground block mb-1">Instagram Handle</label>
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground text-sm font-semibold">@</span>
              <input
                id="profile-instagram-handle"
                name="instagramHandle"
                type="text"
                value={instagramHandle}
                onChange={(e) => setInstagramHandle(e.target.value.replace(/^@/, ""))}
                placeholder="your.handle"
                className="w-full rounded-xl bg-muted/60 pl-8 pr-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 border border-transparent focus:border-primary/30"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">Followers</label>
              <div className="relative">
                <Users className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  id="profile-followers"
                  name="followers"
                  type="text"
                  value={followers}
                  onChange={(e) => setFollowers(e.target.value)}
                  placeholder="e.g. 25K"
                  className="w-full rounded-xl bg-muted/60 pl-10 pr-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 border border-transparent focus:border-primary/30"
                />
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-muted-foreground block mb-1">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  id="profile-email"
                  name="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@domain.com"
                  className="w-full rounded-xl bg-muted/60 pl-10 pr-4 py-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 border border-transparent focus:border-primary/30"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Plan Card */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-card to-muted/30 p-5 shadow-xl">
        <div className="absolute right-0 top-0 h-28 w-28 rounded-full bg-primary/10 blur-2xl" />
        <div className="absolute left-0 bottom-0 h-28 w-28 rounded-full bg-secondary/10 blur-2xl" />
        
        <div className="flex items-start justify-between">
          <div>
            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary border border-primary/20">
              <Award className="h-3 w-3" /> Current Tier
            </span>
            <h3 className="mt-2 font-display text-xl font-bold text-foreground">
              {plan === "Pro Creator" ? "Pro Creator" : "Free Trial"}
            </h3>
            <p className="mt-1 text-xs text-muted-foreground max-w-[240px]">
              {plan === "Pro Creator" 
                ? "You have full access to emerging trends, brand deals, and all features."
                : "Limited access. Upgrade to unlock full emerging trends, high-paying brand deals."}
            </p>
          </div>

          <div className="text-right">
            <span className="text-lg font-bold text-foreground">
              {plan === "Pro Creator" ? "₹999/mo" : "Free"}
            </span>
          </div>
        </div>

        {plan !== "Pro Creator" && (
          <Button
            onClick={handleUpgrade}
            disabled={upgrading}
            className="mt-4 w-full h-11 bg-gradient-to-r from-primary to-secondary hover:from-primary/95 hover:to-secondary/95 text-white font-bold text-xs uppercase tracking-wider shadow-lg shadow-primary/20 rounded-xl flex items-center justify-center gap-1.5"
          >
            {upgrading ? (
              <span>Processing...</span>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>Upgrade to Pro</span>
              </>
            )}
          </Button>
        )}

        {plan === "Pro Creator" && (
          <div className="mt-4 flex items-center justify-center gap-1.5 rounded-xl bg-success/10 border border-success/20 py-2.5 text-success">
            <ShieldCheck className="h-4 w-4" />
            <span className="text-xs font-bold uppercase tracking-wider">Premium Access Active</span>
          </div>
        )}
      </div>

      {/* Save Button */}
      <Button
        onClick={save}
        disabled={saving}
        className="h-12 w-full bg-primary hover:bg-primary/95 text-white font-bold uppercase tracking-wider shadow-lg shadow-primary/25 rounded-xl"
      >
        {saving ? "Saving Profile..." : "Save Profile ✓"}
      </Button>

      <p className="text-center text-[10px] text-muted-foreground tracking-wide mt-2">
        Trendrop — India-first trend intelligence for short-form creators 🇮🇳
      </p>
    </div>
  );
}

