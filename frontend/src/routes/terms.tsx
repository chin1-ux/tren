import { createFileRoute, Link } from "@tanstack/react-router";
import { ArrowLeft, AlertTriangle } from "lucide-react";

export const Route = createFileRoute("/terms")({
  head: () => ({
    meta: [
      { title: "Terms of Service — Trendrop" },
      { name: "description", content: "Terms of Service and Content Safety Guidelines." },
    ],
  }),
  component: TermsPage,
});

function TermsPage() {
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
          <h1 className="font-display text-2xl font-bold gradient-text">Terms of Service</h1>
          <p className="text-xs text-muted-foreground">Last updated: June 25, 2026</p>
        </div>
      </header>

      {/* Warning / Zero Tolerance Banner */}
      <div className="glass-card p-5 border-destructive/20 bg-destructive/5 space-y-3">
        <div className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="h-5 w-5" />
          <h2 className="font-display text-sm font-bold uppercase tracking-wider">Zero-Tolerance Policy</h2>
        </div>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Trendrop maintains a strict, zero-tolerance policy towards objectionable content. Violators will face immediate account termination and permanent device banning.
        </p>
      </div>

      {/* Sections */}
      <div className="space-y-4">
        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">1. User Account & Eligibility</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            By signing up, you agree to:
          </p>
          <ul className="list-disc pl-4 text-xs text-muted-foreground space-y-1 mt-1">
            <li>Provide accurate and current information.</li>
            <li>Maintain the confidentiality of your credentials.</li>
            <li>Be at least 18 years of age (or have explicit parental consent).</li>
          </ul>
        </section>

        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">2. Prohibited Content Guidelines</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            You are strictly prohibited from uploading, generating, or distributing any content that:
          </p>
          <ul className="list-disc pl-4 text-xs text-muted-foreground space-y-1 mt-1">
            <li>Contains explicit nudity, sexual material, or pornography.</li>
            <li>Promotes hate speech, discrimination, harassment, or violence.</li>
            <li>Depicts self-harm, gore, or graphic physical abuse.</li>
            <li>Infringes on copyrights, trademarks, or publicity rights of others.</li>
            <li>Includes spam, misleading metadata, or malware.</li>
          </ul>
        </section>

        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">3. Moderation & Enforcement</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            All user media uploads (images/videos) are run through an automated **Safe Search Moderation** check. Any asset flagged for adult content, violence, racy content, or spoofing will be rejected automatically.
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed">
            We reserve the right to review reports, disable accounts, and share information with law enforcement agencies if uploaded content violates local penal codes.
          </p>
        </section>

        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">4. Intellectual Property & AI Watermarking</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Videos generated via Trendrop's tool suite include an automated watermark and visual/metadata tagging identifying them as **AI-Generated Content**. You agree not to bypass, hide, or alter these compliance tags, ensuring transparency on platforms like Instagram and YouTube.
          </p>
        </section>

        <section className="glass-card p-5 space-y-2">
          <h3 className="font-bold text-sm text-foreground">5. Limitation of Liability</h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Trendrop provides trend intelligence and creative layouts "as is". We are not responsible for any copyright claims, algorithm updates, or account suspensions on external networks (Instagram, YouTube) arising from your use of generated media.
          </p>
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
