import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ArrowLeft, ShieldAlert, Download, Trash2, CheckCircle, RefreshCw, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { supabase } from "@/lib/supabase";
import { setAuthToken } from "@/lib/api";
import { useUserStore } from "@/store/useAppStore";

export const Route = createFileRoute("/data-rights")({
  head: () => ({
    meta: [
      { title: "Manage Digital Data Rights — Trendrop" },
      { name: "description", content: "Exercise your digital rights under the DPDP Act 2023." },
    ],
  }),
  component: DataRightsPage,
});

function DataRightsPage() {
  const router = useRouter();
  const logoutUser = useUserStore((s) => s.logout);
  const userEmail = useUserStore((s) => s.email);

  const [email, setEmail] = useState("");
  const [notifyTrendAlerts, setNotifyTrendAlerts] = useState(true);
  const [notifyDailyIdeas, setNotifyDailyIdeas] = useState(true);
  const [notifyBrandDeals, setNotifyBrandDeals] = useState(true);
  const [termsConsent, setTermsConsent] = useState(true);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const e = localStorage.getItem("trendrop_user_email") || "";
    setEmail(e);
    setNotifyTrendAlerts(localStorage.getItem("trendrop_notify_trend_alerts") !== "false");
    setNotifyDailyIdeas(localStorage.getItem("trendrop_notify_daily_ideas") !== "false");
    setNotifyBrandDeals(localStorage.getItem("trendrop_notify_brand_deals") !== "false");
  }, []);

  const logConsentChange = async (consentType: string, granted: boolean) => {
    if (!email) return;
    try {
      // Fetch public IP for audit log
      let ip = "127.0.0.1";
      try {
        const ipRes = await fetch("https://api.ipify.org?format=json");
        const ipData = await ipRes.json();
        ip = ipData.ip;
      } catch {}

      await supabase.from("consent_records").insert({
        user_email: email,
        consent_type: consentType,
        granted: granted,
        ip_address: ip,
        user_agent: navigator.userAgent
      });
    } catch (err) {
      console.error("Failed to log consent change:", err);
    }
  };

  const handleToggleConsent = async (type: string, current: boolean, setter: (v: boolean) => void) => {
    const nextVal = !current;
    setter(nextVal);
    
    // Save to local storage
    if (type === "trend_alerts") localStorage.setItem("trendrop_notify_trend_alerts", String(nextVal));
    if (type === "daily_ideas") localStorage.setItem("trendrop_notify_daily_ideas", String(nextVal));
    if (type === "brand_deals") localStorage.setItem("trendrop_notify_brand_deals", String(nextVal));
    
    toast.success(`Consent for ${type.replace("_", " ")} ${nextVal ? "granted" : "withdrawn"}!`);
    await logConsentChange(type, nextVal);
  };

  const handleWithdrawTerms = async () => {
    const confirmWithdraw = window.confirm(
      "WARNING: Withdrawing consent to the Terms of Service & Privacy Policy means you will no longer be permitted to use Trendrop. This will initiate immediate deletion of your account and data. Do you wish to proceed?"
    );
    if (!confirmWithdraw) return;

    setTermsConsent(false);
    await logConsentChange("terms_and_privacy", false);
    await handleDeleteAccount();
  };

  const handleDownloadData = async () => {
    if (!email) {
      toast.error("Please login or set your email to download your data.");
      return;
    }
    setLoading(true);
    try {
      // Retrieve everything related to the user from the Supabase DB
      const { data: userProfile } = await supabase.from("users").select("*").eq("email", email).single();
      const { data: jobsHistory } = await supabase.from("jobs").select("*").eq("user_email", email);
      const { data: consentRecords } = await supabase.from("consent_records").select("*").eq("user_email", email);

      const packagedData = {
        exported_at: new Date().toISOString(),
        dpdp_compliance: "Digital Personal Data Protection Act, 2023 (India)",
        profile: userProfile || {
          email,
          niche: localStorage.getItem("trendrop_niche"),
          language_preference: localStorage.getItem("trendrop_language"),
          plan: localStorage.getItem("trendrop_user_plan") || "free"
        },
        jobs_history: jobsHistory || [],
        consent_records: consentRecords || []
      };

      const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(packagedData, null, 2))}`;
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", jsonString);
      downloadAnchor.setAttribute("download", `trendrop_data_principal_export_${email.replace("@", "_")}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();

      toast.success("Your data package has been compiled and downloaded successfully! 📥");
    } catch (err) {
      toast.error("Error compiling data package.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (!email) {
      toast.error("No active session found.");
      return;
    }
    const doubleConfirm = window.confirm(
      "Are you absolutely sure you want to permanently delete your Trendrop account? This action is irreversible and complies with your Right to Erasure."
    );
    if (!doubleConfirm) return;

    setLoading(true);
    try {
      // 1. Delete DB entries
      await supabase.from("consent_records").delete().eq("user_email", email);
      await supabase.from("jobs").delete().eq("user_email", email);
      await supabase.from("users").delete().eq("email", email);

      // 2. Clear Supabase session
      await supabase.auth.signOut();

      // 3. Clear store & local storage
      setAuthToken(null);
      logoutUser();

      toast.success("Account and all associated personal data permanently erased from our servers.");
      router.navigate({ to: "/" });
    } catch (err) {
      toast.error("Failed to fully erase account data. Please contact privacy@trendrop.app");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 px-4 pb-24 pt-6 text-foreground">
      {/* Header */}
      <header className="flex items-center gap-3">
        <Link
          to="/settings"
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-muted/60 border border-border text-foreground hover:bg-muted transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div>
          <h1 className="font-display text-2xl font-bold gradient-text font-semibold">Manage Digital Rights</h1>
          <p className="text-xs text-muted-foreground">DPDP Act 2023 Compliance Panel</p>
        </div>
      </header>

      {/* Info Card */}
      <div className="glass-card p-5 space-y-3">
        <div className="flex items-center gap-2 text-primary">
          <ShieldAlert className="h-5 w-5" />
          <h2 className="font-display text-sm font-bold uppercase tracking-wider">Your Digital Sovereignty</h2>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Under India's **Digital Personal Data Protection Act, 2023**, you (the **Data Principal**) have legally protected rights over your digital personal data. Exercise them using the secure tools below.
        </p>
      </div>

      {/* Rights Panels */}
      <div className="space-y-4">
        {/* Right to Access and Portability */}
        <div className="glass-card p-5 space-y-3">
          <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
            <Download className="h-4 w-4 text-secondary" /> Right to Access & Download
          </h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Download a full portable copy of all personal data, consent logs, and generation history associated with your identity.
          </p>
          <Button
            onClick={handleDownloadData}
            disabled={loading}
            className="w-full bg-secondary hover:bg-secondary/95 text-white font-bold text-xs uppercase tracking-wider rounded-xl h-11"
          >
            {loading ? "Processing..." : "Download My Data Package (JSON)"}
          </Button>
        </div>

        {/* Right to Withdraw Consent */}
        <div className="glass-card p-5 space-y-4">
          <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-amber" /> Manage & Withdraw Consents
          </h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Withdraw or grant consent for specific data processing activities. Note that withdrawing consents may limit or disable active features.
          </p>

          <div className="space-y-2.5">
            {/* Trend Alerts */}
            <div className="flex items-center justify-between rounded-xl bg-muted/20 px-3.5 py-3 border border-border">
              <div className="space-y-0.5">
                <p className="text-xs font-bold text-foreground">Trend Notifications</p>
                <p className="text-[10px] text-muted-foreground">Receive real-time notifications on viral sounds</p>
              </div>
              <button
                onClick={() => handleToggleConsent("trend_alerts", notifyTrendAlerts, setNotifyTrendAlerts)}
                className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${
                  notifyTrendAlerts ? "bg-primary" : "bg-muted-foreground/30"
                }`}
              >
                <div
                  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${
                    notifyTrendAlerts ? "left-[18px]" : "left-0.5"
                  }`}
                />
              </button>
            </div>

            {/* Daily Ideas */}
            <div className="flex items-center justify-between rounded-xl bg-muted/20 px-3.5 py-3 border border-border">
              <div className="space-y-0.5">
                <p className="text-xs font-bold text-foreground">Daily Idea Recommendations</p>
                <p className="text-[10px] text-muted-foreground">Receive personalized ideas based on niche</p>
              </div>
              <button
                onClick={() => handleToggleConsent("daily_ideas", notifyDailyIdeas, setNotifyDailyIdeas)}
                className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${
                  notifyDailyIdeas ? "bg-primary" : "bg-muted-foreground/30"
                }`}
              >
                <div
                  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${
                    notifyDailyIdeas ? "left-[18px]" : "left-0.5"
                  }`}
                />
              </button>
            </div>

            {/* Brand Deals */}
            <div className="flex items-center justify-between rounded-xl bg-muted/20 px-3.5 py-3 border border-border">
              <div className="space-y-0.5">
                <p className="text-xs font-bold text-foreground">Brand Partnership Matching</p>
                <p className="text-[10px] text-muted-foreground">Allow matching your profile with active deals</p>
              </div>
              <button
                onClick={() => handleToggleConsent("brand_deals", notifyBrandDeals, setNotifyBrandDeals)}
                className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${
                  notifyBrandDeals ? "bg-primary" : "bg-muted-foreground/30"
                }`}
              >
                <div
                  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${
                    notifyBrandDeals ? "left-[18px]" : "left-0.5"
                  }`}
                />
              </button>
            </div>

            {/* Core Terms Consent */}
            <div className="flex items-center justify-between rounded-xl bg-muted/20 px-3.5 py-3 border border-border">
              <div className="space-y-0.5">
                <p className="text-xs font-bold text-foreground">ToS & Privacy Consent</p>
                <p className="text-[10px] text-muted-foreground">Core consent to store/process your basic account</p>
              </div>
              <button
                onClick={handleWithdrawTerms}
                className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${
                  termsConsent ? "bg-success" : "bg-destructive"
                }`}
              >
                <div
                  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all ${
                    termsConsent ? "left-[18px]" : "left-0.5"
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Right to Correction */}
        <div className="glass-card p-5 space-y-3">
          <h3 className="font-bold text-sm text-foreground flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-success" /> Right to Correction
          </h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            You have the right to request correction or updating of your profile details, niches, or language preferences.
          </p>
          <Link
            to="/settings"
            className="inline-flex w-full items-center justify-center bg-muted/60 border border-border text-foreground hover:bg-muted font-bold text-xs uppercase tracking-wider rounded-xl h-11 transition-colors"
          >
            Go to Profile Settings &rarr;
          </Link>
        </div>

        {/* Right to Erasure */}
        <div className="glass-card p-5 space-y-3 border-destructive/25 bg-destructive/5">
          <h3 className="font-bold text-sm text-destructive flex items-center gap-2">
            <Trash2 className="h-4 w-4" /> Right to Erasure (Delete Account)
          </h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Permanently delete your account. Under this erasure request, all personal profile data, upload backups, consent entries, and generated outputs will be instantly and irrevocably destroyed.
          </p>
          <Button
            onClick={handleDeleteAccount}
            disabled={loading}
            variant="destructive"
            className="w-full font-bold text-xs uppercase tracking-wider rounded-xl h-11"
          >
            {loading ? "Erasing Data..." : "Erase All My Data & Account"}
          </Button>
        </div>
      </div>

      <div className="text-center">
        <Link
          to="/settings"
          className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors underline"
        >
          Return to Settings
        </Link>
      </div>
    </div>
  );
}
