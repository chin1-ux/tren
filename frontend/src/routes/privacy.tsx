import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, Shield } from "lucide-react";

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: "Privacy Policy — Trendrop" },
      { name: "description", content: "Privacy Policy compliant with India's DPDP Act 2023." },
    ],
  }),
  component: PrivacyPage,
});

function PrivacyPage() {
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
          <h1 className="font-display text-2xl font-bold gradient-text">Privacy Policy</h1>
          <p className="text-xs text-muted-foreground">Last updated: June 25, 2026</p>
        </div>
      </header>

      {/* Intro */}
      <div className="glass-card p-5 space-y-4">
        <div className="flex items-center gap-2 text-primary">
          <Shield className="h-5 w-5" />
          <h2 className="font-display text-sm font-bold uppercase tracking-wider">DPDP Act 2023 Compliant</h2>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Trendrop is committed to safeguarding your personal data. This privacy policy outlines how we, as a **Data Fiduciary**, collect, process, store, and protect your digital personal data in strict compliance with the **Digital Personal Data Protection (DPDP) Act, 2023** (India) and the **DPDP Rules, 2025**.
        </p>
      </div>

      {/* Sections */}
      <div className="space-y-4">
        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">1. Data We Collect</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            We collect only the minimum necessary data to provide you with trend intelligence services:
          </p>
          <ul className="list-disc pl-4 text-xs text-muted-foreground space-y-1 mt-1">
            <li><strong>Account Data:</strong> Email address and password (securely handled via Supabase Auth).</li>
            <li><strong>Creator Profile:</strong> Niche, platform language preferences, and Instagram/YouTube handle.</li>
            <li><strong>Usage Logs:</strong> Action timestamps, search queries, generated reels history, and consent records.</li>
            <li><strong>Device Info:</strong> IP address, browser type, and cookie identifier (in-memory sessions).</li>
          </ul>
        </section>

        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">2. Purpose of Processing</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Your personal data is processed solely under the legal basis of your **explicit, specific, and unconditional consent** for:
          </p>
          <ul className="list-disc pl-4 text-xs text-muted-foreground space-y-1 mt-1">
            <li>Generating personalized daily hooks and narrative video ideas.</li>
            <li>Sending priority notifications when relevant audio tracks trend in India.</li>
            <li>Enabling brand deal matching and collaboration workflows.</li>
          </ul>
        </section>

        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">3. Data Localization</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            To guarantee absolute compliance with regional sovereignty guidelines, all database records, user uploads, and generated outputs are stored in servers situated within Indian territory (<strong>AWS Mumbai Region, ap-south-1</strong>).
          </p>
        </section>

        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">4. Retention Policy</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            We apply a strict data minimisation and retention schedule:
          </p>
          <ul className="list-disc pl-4 text-xs text-muted-foreground space-y-1 mt-1">
            <li>Original media uploads and generated outputs are purged after <strong>24 hours</strong>.</li>
            <li>Generation job records are deleted after <strong>30 days</strong>.</li>
            <li>Inactive accounts (no login or job run for <strong>2 years</strong>) are automatically purged.</li>
            <li>Consent logs and records of exercise of rights are retained for <strong>7 years</strong> for regulatory compliance.</li>
          </ul>
        </section>

        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">5. Your Digital Rights</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            As a **Data Principal**, you have the absolute right to:
          </p>
          <ul className="list-disc pl-4 text-xs text-muted-foreground space-y-1 mt-1">
            <li>Access a summary of personal data processed and processing activities.</li>
            <li>Correct or update inaccurate or misleading personal data.</li>
            <li>Withdraw your consent at any time, leading to deletion of your personal data.</li>
            <li>Grievance redressal regarding any processing violation.</li>
          </ul>
          <p className="text-xs text-primary font-semibold mt-2">
            You can exercise these rights instantly in the <Link to="/data-rights" className="underline hover:text-primary/80">Manage Digital Data Rights</Link> panel.
          </p>
        </section>

        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">6. Data Protection Officer (DPO)</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            For any queries, grievances, or requests, please contact our designated Grievance Officer:
          </p>
          <div className="rounded-xl bg-muted/30 p-3 mt-2 border border-border text-xs text-muted-foreground space-y-1">
            <p><strong>Name:</strong> Data Protection Officer</p>
            <p><strong>Designation:</strong> Data Protection Officer & Grievance Redressal Lead</p>
            <p><strong>Email:</strong> privacy@trendrop.app</p>
            <p><strong>Response Time:</strong> Resolved within 7 business days as per rules.</p>
          </div>
        </section>
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
