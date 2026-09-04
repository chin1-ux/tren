# Production Checklist - Trendrop Hardening & Audit

This document outlines the security, scalability, and legal compliance checks implemented to ensure Trendrop is ready for production and fully compliant with India's DPDP Act 2023 and Google/Apple Store policies.

## 1. Security & Authentication
- [x] **Supabase Auth Integration**: User sessions are authenticated on the backend via official Supabase JWT token verification (`supabase.auth.get_user(token)`).
- [x] **In-Memory JWT Storage**: The frontend stores JWT access tokens purely in memory. No tokens are written to `localStorage` or `sessionStorage`.
- [x] **Secure Session Expiry**: API sessions expire after 30 minutes of inactivity.
- [x] **Logout Invalidation**: Sign-out invokes `supabase.auth.signOut()` on both the client and server side, clearing all local cookie state and in-memory caches.
- [x] **HTTP-Only Cookies**: Secure, HttpOnly, SameSite cookies are set on the frontend for persistent sessions.
- [x] **Security Headers**: Standard headers are injected by FastAPI middleware:
  - `Content-Security-Policy`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security` (HSTS)
- [x] **Strict CORS**: Origins are explicitly restricted to production domains, blocking wildcard access.
- [x] **Rate Limiting (SlowAPI)**: Critical routes are protected:
  - `/api/subscribe`: Max 5 per hour
  - `/api/score-reel`: Max 20 per hour
  - Video Generation: Max 10 per hour

## 2. Database Optimization & Row Level Security (RLS)
- [x] **Supabase RLS Enabled**: Row-level security is active on all tables.
- [x] **Tenant-Owner Policies**: Users can only read, write, or update records matching their Supabase JWT email (`auth.jwt() ->> 'email'`).
- [x] **Database Optimization Indexes**: Composite indexes exist on high-frequency query columns:
  - `idx_reels_vel_type_lang_posted_audio`
  - `idx_trends_status_vel_type_lang_first`
  - `idx_jobs_status_email_created`
  - `idx_users_email_niche_lang`

## 3. Scalability & Background Jobs
- [x] **Background Worker Queue**: Video generation, faceless generation, and repurposing tasks are offloaded to Upstash Redis standard and priority queues (`rq`).
- [x] **Tiered Processing**: Pro plan creators utilize the `priority` queue, while free-tier creators run on the `standard` queue.
- [x] **Storage Upload Integration**: Client source files are validated, passed through content moderation, and uploaded securely to Supabase Storage `uploads` bucket under `current_user_email/job_id/filename`. Generated files are uploaded to `outputs` bucket.

## 4. Legal Compliance (India's DPDP Act 2023)
- [x] **Data Localization**: Database and storage endpoints are hosted inside Indian borders (AWS Mumbai Region `ap-south-1`).
- [x] **Legal Consensus & Onboarding**: Required consent checkboxes for Terms of Service and Privacy Policy added to onboarding. Toggling notifications logs consent events.
- [x] **Consent Logging**: Every consent decision writes a record to `consent_records` containing the user email, consent type, granted state, IP address, and User Agent.
- [x] **Data Rights Panel**: Users can access the `/data-rights` dashboard to:
  - **Download Data**: Retrieve a full JSON export of profile, job history, and consent records.
  - **Correct Profile**: Link to profile settings.
  - **Withdraw Consent**: Instantly update consent options.
  - **Right to Erasure (Delete Account)**: Irrevocably purge profile, jobs, and consent data.
- [x] **Retention Cron Job**: A daily cleanup script runs at 2:00 AM IST:
  - Purges uploads/outputs older than 24 hours.
  - Deletes database jobs older than 30 days.
  - Purges inactive users (no activity for 2 years).
  - Retains consent records for exactly 7 years.

## 5. Content Policy & App Store Compliance
- [x] **Safe Search Verification**: Automated image and video validation rejects files with magic bytes discrepancies or containing objectionable material (Safe Search content moderation).
- [x] **AI Content Tagging**: Watermarks and metadata tags are appended to generated outputs to clearly denote AI-generated media.
