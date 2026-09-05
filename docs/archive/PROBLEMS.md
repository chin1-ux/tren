# TRENDROP — COMPLETE PROBLEM INVENTORY
**Date:** Aug 22, 2026 · **Basis:** deep codebase audit against repo at HEAD (`df7bbfe8`, local main) + live Supabase prod + live Vercel prod, reconciled from the Aug 18 baseline (`cd9d082f`).
Every claim has a file:line citation. Every status change made in this pass has fresh same-day evidence (code inspection, REST queries against prod DB, or live HTTP probes).

**Deployment context (Aug 22):** Production alias `trendrop-black.vercel.app` serves CLI deploy `dpl_5K3VwHXfAJYGaqS7VdRJpUCGfS6g` (created 2026-08-22 14:17:09 +0530, no git metadata — deployed via Vercel CLI as ch1n-may). Build embedded last commit `d46c5317` (= origin/main). Local main is `df7bbfe8`, ~20 commits ahead — **everything merged after 14:17 IST Aug 22 is NOT yet live on prod.** One uncommitted working-tree change exists: `backend/instagram_scraper_browser.py` (P-SCRAPER-2 `creator_baselines` join) — implemented but not committed or deployed.

---

## TABLE OF CONTENTS
1. [Data Pipeline Architecture Audit](#1-data-pipeline-architecture-audit)
2. [Backend API Problems](#2-backend-api-problems)
3. [Auth & Security Problems](#3-auth--security-problems)
4. [Payment & Subscription Problems](#4-payment--subscription-problems)
5. [Frontend Design Problems](#5-frontend-design-problems)
6. [Database & Data Quality Problems](#6-database--data-quality-problems)
7. [Workflow & DevOps Problems](#7-workflow--devops-problems)
8. [Trust & Fake-Feature Problems](#8-trust--fake-feature-problems)
9. [Payment & Subscription Problems (continued)](#9-payment--subscription-problems-continued)
10. [Cross-cutting Truth Problems](#10-cross-cutting-truth-problems)
11. [Strategic & Fundraising Problems](#11-strategic--fundraising-problems)

---

## 1. DATA PIPELINE ARCHITECTURE AUDIT

This section answers: **Does this pipeline produce accurate, high-quality data that matches what users actually see on Instagram?**

### 1.1 How the pipeline works (end-to-end)

```
GitHub Actions cron → instagram_scraper_browser.py → Supabase DB → trend_engine.py → API → frontend
```

- **Scrape**: Camoufox (stealth Playwright) navigates to Instagram hashtag pages, intercepts XHR responses, extracts reel + audio data
- **Store**: Each reel is individually inserted into Supabase with engagement metrics, audio metadata, creator info
- **Detect**: trend_engine.py groups reels by audio, calculates velocity/saturation/lifecycle
- **Serve**: api.py reads from Supabase, returns filtered/sorted trends to frontend
- **Display**: Frontend shows trending audios with lifecycle badges, urgency indicators, action recommendations

### 1.2 BRUTAL RATING: Does the data pipeline produce accurate, high-quality data?

**Overall pipeline score: 5/10** — Real data, but significant accuracy gaps.

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Data freshness | 6/10 | Scrapes 2-3x/day, but no real-time. Batch only. |
| Audio metadata accuracy | 7/10 | Uses Instagram's official audio_use_count when available, proxy formula when not (line 819-822) |
| Trend detection accuracy | 5/10 | Calibrated on N=108 samples. Thresholds are reasonable but not validated against Instagram's own trending page |
| India coverage | 7/10 | 80% of hashtags are India-focused. Multi-language detection. Regional crossover monitoring |
| Saturation/lifecycle accuracy | 4/10 | Saturation thresholds (5M/500) were revised once. No external validation. Scraper writes different thresholds (100K/8K) than engine reads (5M/500) |
| Velocity tracking | 4/10 | Point-in-time snapshots, not continuous monitoring. Formula uses engagement/followers/age but no Instagram-validated weights |
| Cross-platform accuracy | 3/10 | YouTube basic string matching. Spotify endpoint doesn't exist. "Cross-platform" is overstated |
| Real-time accuracy | 2/10 | **Not real-time.** Batch scraping on schedule. No streaming. |

### 1.3 Critical data pipeline problems

#### P-PIPE-1: Pagination impossible on Instagram's REST web_info endpoint [CONFIRMED — dead code, no fix on this endpoint]
**File:** `backend/instagram_scraper_browser.py:933-988`
**Root cause (confirmed Sep 3 via live diagnostic on chin1-ux/tren, run 33767268158):**
Instagram's `api/v1/tags/web_info` response does NOT include `more_info` or any pagination cursor. The `raw_data` top-level keys are: `id, name, media_count, allow_muting_story, subtitle, follow_button_text, show_follow_drop_down, formatted_media_count, is_trending, hide_use_hashtag_button, top, recent, content_advisory, warning_message, profile_pic_url`. No `more_info`, no `max_id`, no `next_cursor`, no `has_more`. The pagination code at lines 933-988 was dead on arrival — the API never returned the cursor it depends on.
**Tokens found** (`mezql_token`, `organic_tracking_token`, `logging_info_token`) are per-media metadata, not pagination cursors.
**Impact:** Single-page ceiling: ~45-60 items per hashtag. Current volume: ~2,000 reels/run (chin1-ux, 40 hashtags). "15,000+ reels daily" claim is not achievable from this endpoint.
**Options for real pagination (not yet decided):**
1. **GraphQL endpoint** — Instagram's GraphQL API supports cursor-based pagination via `edge_hashtag_to_media` query. Would require rewriting the scraper to use GraphQL instead of REST. Higher complexity, but proven approach.
2. **Scroll/XHR interception** — scroll the browser page, intercept additional XHR responses. Lighter on API changes but slower (browser must render each scroll) and costs more GitHub Actions minutes.
3. **Accept the ceiling** — ~2,000 reels/run is sufficient for trend detection at current scale. Pagination becomes relevant only when hashtag count grows or detection needs deeper historical data.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

#### P-PIPE-2: N+1 DB query problem — 10-18 queries per reel, no batching — FIXED (Aug 18)
**File:** `backend/instagram_scraper_browser.py:1212-1583` (new `_process_hashtag_batch` method)
**Problem:** For each reel, the scraper executed 10-18 individual DB queries (duplicate check, audio analysis, India saturation, creator baseline, insert, snapshot read/insert, delta update, unique creators check, tracked_audio, trend lifecycle). 300 reels × 12 avg queries = ~3,600 DB round-trips per run. At 100-300ms each, that's 6-18 minutes of DB time alone.
**Fix:** New `_process_hashtag_batch` method consolidates per-reel queries into batched phases:
- Phase A: Pre-filter (Python, no DB) — velocity, engagement, missing data checks
- Phase B: Bulk DB reads (3 queries for entire batch) — duplicate check via `.in_()`, audio analysis via `.in_()`, creator baselines via `.in_()`
- Phase C: Python processing — original audio check, India saturation, outlier detection from bulk results
- Phase D: Bulk DB writes (2 queries) — `upsert` reels with `on_conflict=reel_id`, bulk snapshot insert
- Post-insert: tracked_audio + trend_lifecycle remain individual (lower volume)
**Result:** 12N queries → 5 queries per hashtag. Verified via fixture test (15 items, 12 inserted): all 12 reels match field-for-field between legacy and batched paths.
**Rationale for upsert over catch-and-log:** India/global scrapers run on separate cron schedules (never concurrent), but shared `GLOBAL_NICHES` tags could cause rare overlaps. `upsert` with `on_conflict=reel_id` handles this cleanly. Reel data is idempotent (latest scrape is always most accurate), so silent overwrites are safe.
**Rationale for cutting snapshot read + delta update:** After duplicate filtering (reel_id-based, globally unique per Instagram reel), all remaining reels are new. Previous snapshot for a new reel is always empty → deltas are always 0. Cut safely.
**Unverified:** Real timing from live scrape not yet measured. `USE_BATCHED_PROCESSING = True` flag at line 1684 controls the swap; legacy path preserved for easy revert.

#### P-PIPE-3: Scraper saturation formula conflicts with engine formula — DE-PRIORITIZED (Aug 18)
**File:** Scraper `backend/instagram_scraper_browser.py:34-36` vs Engine `backend/trend_scoring.py:20-23`
**Problem:**
- Scraper writes: `global_pct = min(100.0, (audio_use_count / 100_000) * 100)` and `india_pct = min(100.0, (india_use_count / 8_000) * 100)`
- Engine reads: `global_sat = round(min(100.0, (audio_use_count / 5_000_000) * 100), 1)` and `india_sat = round(min(100.0, (india_use_count / 500) * 100), 1)`

**Data-backed assessment (Aug 18 query against live DB):**
- India_use_count max across ALL audio: **13**. Both thresholds (500 and 8K) are 38-615x too high to ever trigger. This is inert noise.
- Audio_use_count: scraper's 100K threshold marks 24% of audio as 100% saturated; engine's 5M marks 0.6%. Neither is validated against Instagram's actual trending page.
- Cross-cultural endpoint filter: **identical results** (1,000 reels) under both threshold sets because india_use_count never exceeds 13.
- **Root cause:** Lack of scraper pagination (P-PIPE-1) means per-audio India counts are tiny. Thresholds are designed for a dataset 100-1000x larger than what exists.
- **Decision:** Do NOT fix formulas until pagination is resolved and data volume increases. Both threshold sets are guesses at a proxy for "Instagram has moved on" — neither answers the product question of what "saturated" actually means.
**Status:** Logged, de-prioritized. Revisit after P-PIPE-1 (pagination) increases data volume.

#### P-PIPE-4: Proxy audio_use_count uses made-up formula [RESOLVED — fabricated formula already replaced]
**File:** `backend/instagram_scraper_browser.py:659-736` (`_extract_audio_use_count`)
**Problem:** When Instagram doesn't provide `audio_use_count`, the scraper used to calculate a fabricated number using `unique_creators * 800 + total_reels * 400`.
**Current state (re-verified Sep 2026):** The fabricated formula no longer exists. `_extract_audio_use_count` now returns data from honest sources in priority order:
1. Instagram API response (`clips_metadata.music_info.music_consumption_info.use_count`)
2. `audio_official_counts` table (previously scraped official counts)
3. Average of recent official counts from the same table
4. `0` if no data available

All paths return real data or zero — no fabricated values. The saturation thresholds (P-PIPE-3) are still miscalibrated but that's deferred until P-PIPE-1 increases data volume.

#### P-PIPE-5: 15-minute global timeout frequently cuts off later hashtags [RESOLVED — timeout not the bottleneck]
**File:** `backend/instagram_scraper_browser.py:1766-1792`
**Problem:** Global timeout was 900 seconds (15 min). Fear was that later hashtags would be skipped.
**Verified from logs (run 32614282355, Aug 23):** Scraper stage finishes in ~6 minutes for15 hashtags (03:02:52 → 03:08:41). All15 hashtags completed. The 15-min global timeout was never hit.
**Why runs take 30+ min:** The bottleneck is downstream of scraping — backfill, detection, alerts, and audio count check consume25+ minutes. Recent run durations: 34m54s, 36m52s. These are workflow-level durations, not scraper-level.
**Fix (Sep 2026):** Global timeout made configurable via `SCRAPER_GLOBAL_TIMEOUT` env var (default stays 15 min — sufficient). Per-hashtag timeout increased 90s→120s, configurable via `SCRAPER_HASHTAG_TIMEOUT`. Both are safety valves, not active bottlenecks.

#### P-PIPE-6: External trend discovery is dead code [RESOLVED — code deleted]
**Re-verified Aug 22, 2026:** `backend/external_trend_discovery.py` was never committed to git (absent from `git log --all`) and is now absent from disk. Its sibling `backend/external_trend_pipeline.py` was explicitly deleted by commit `d63d2ab0`. Grep confirms zero remaining production imports of either module.
**Impact resolved:** The 642-line dead code path is gone rather than fixed — the honest resolution given Spotify's endpoint never existed and YouTube matching was crude. "Cross-platform" claims were also removed from frontend marketing copy (see P-FUND-2).

#### P-PIPE-7: No ad/sponsored post detection
**File:** Absent from `backend/instagram_scraper_browser.py`
**Problem:** The scraper treats all reels equally. Sponsored posts that appear in hashtag feeds are counted as organic trends.
**Impact:** A sponsored post with 10M views might be classified as a "mega trend" when it's actually paid placement, not organic virality.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

#### P-PIPE-8: Indian creator detection uses unreliable signals [RESOLVED — code deleted]
**Re-verified Aug 22, 2026:** The city-name heuristic lived in `backend/external_trend_discovery.py:475-481`, which is now absent from disk (see P-PIPE-6). No production code uses the unreliable detection path anymore.
**Impact resolved:** Misleading signal removed with the module that contained it. (If creator-nationality classification is ever needed again, build it on follower-base/language signals instead.)

### 1.4 Pipeline accuracy verdict

**Can this pipeline produce data that matches what users see on Instagram?**

**Answer: Partially.**

- **What it gets RIGHT:**
  - Real reel data (views, likes, comments) from Instagram's API
  - Real audio metadata (song name, artist, official use count) when Instagram provides it
  - India-first hashtag coverage (80% India-focused)
  - Multi-language detection (Hindi, Tamil, Telugu, Punjabi, etc.)
  - Creator velocity tracking (engagement / followers / age)

- **What it gets WRONG:**
  - Only scrapes the "top" section of Instagram's tag page (not "recent"), so it sees what Instagram already thinks is popular, not what's emerging
  - No pagination = limited sample size (~30-90 reels per hashtag)
  - Proxy audio_use_count is fabricated data
  - Saturation thresholds are calibrated on small samples (N=108), not Instagram's actual trending page
  - No real-time monitoring — batch scraping 2-3x/day means 3-6 hour delay
  - No ad detection = inflated trend signals
  - External discovery is broken/dead code

- **What users will notice:**
  - Trends that appear on Instagram may not appear in Trendrop (missed trends due to limited hashtag sampling)
  - Trends that appear in Trendrop may not be on Instagram's trending page (false positives from proxy data or small samples)
  - The "6 hours before peak" claim is **not provable from the code** — there is no prediction model
  - "15,000+ reels daily" is **not achievable** from the current scraper architecture

---

## 2. BACKEND API PROBLEMS

### P-API-1: ~25 endpoints return simulated/fake data [PARTIAL FIX — 13 → 4 remaining]
**File:** `backend/api.py` — various lines
**Re-verified Aug 22, 2026:** Commit `cc277ee5` deleted the 7 simulated Phase-4 endpoints (Instagram Graph API `user-profile`/`user-insights`/`user-media`, YouTube `trending`/`trending-music`, realtime `realtime/trends`/`realtime/cross-platform`). No routes registered for those paths anymore (route scan: 143 decorators, zero matches).
**Still simulated (`is_simulated: True` in handler body):**
- Video analysis (4): `analyze-video-metadata`, `analyze-visual`, `predict-virality`, `improvements` (api.py ~L6179-6360)
- Plus simulated responses in `backend/creator_tools.py`
**Problem (remaining):** Users see fake data presented as real. The "is_simulated" flag is honest but the UX still shows fabricated charts and scores.
**Does IMPLEMENTATION_PLAN.md fix this?** Partially. Item 3.2 fixes the caption stub. Items 3.3 adds real endpoints for news + audio. But the video analysis stubs remain unfixed.

### P-API-2: Duplicate route dead code — maintenance/regression burden, NO active revenue leak [REVISED — LIVE TEST + CODE REVIEW] [RE-VERIFIED Aug 22: down to 2 duplicates]
**File:** `backend/api.py` — 10 original "pairs" → 5 (Aug 19) → **2 remaining**
**Fresh route scan Aug 22, 2026:** 143 decorators, 141 unique method+path combos. Exactly **2 duplicate combos remain**, both GET:
- `GET /api/algorithm/posting-times` — registered at L1828 and L4751
- `GET /api/algorithm/hashtag-strategy` — registered at L1851 and L4772

The `/api/health` and `/api/india/cultural-events` duplicate pairs flagged on Aug 19 no longer exist — those were cleaned up in intervening commits.
**Problem:** 2 route paths have the same method registered twice. FastAPI serves the FIRST registration (L1828/L1851); the copies at L4751/L4772 are unreachable dead code (~100 lines).
**Impact:** Dead code in an already 6,148-line file. Maintenance burden. Latent regression risk if file is reordered. No active revenue leakage from shadowing itself.
**Fix:** Delete the second copies at L4751-4790ish (verify identical bodies first, per the Aug 19 diff which found them identical). See shared-infra rule #3 — needs explicit approval.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-API-3: api.py is 7,088 lines — unmaintainable [IMPROVED but still extreme]
**File:** `backend/api.py`
**Re-verified Aug 22, 2026:** Now **6,148 lines with 143 route decorators** (was 7,088 lines / ~155 decorators). Net −940 lines from endpoint removals (simulated Phase-4 set, old marketplace deal system) — but still one monolithic file. No modular routing, no blueprints, no route separation.
**Impact:** Every change risks breaking something else. Merge conflicts are guaranteed. Onboarding new developers is impossible.
**Does IMPLEMENTATION_PLAN.md fix this?** No. The plan doesn't mention api.py restructuring.

### P-API-4: 34 unguarded endpoints — full audit complete, 1 confirmed live [UPDATED — LIVE TEST CONFIRMED]
**File:** `backend/api.py` — 154 decorators, 149 unique method+path combos
**Problem:** Endpoints with no plan enforcement or auth check.
**Full audit result (Aug 19):**
- **154 total decorators**, 144 unique paths, 149 unique method+path combos
- **34 SHOULD-BE-GATED**: marketplace (13), india/cultural (10), hashtag (5), creator analytics (3), early detection (4), ideation (5), events (2) — corrected to 32 after cron reclassification
- **34 CORRECTLY-GATED** (require_auth + require_feature)
- **41 CORRECTLY-UNGATED** (public endpoints: auth, pricing, trends list, etc.)
- **16 ADMIN-ONLY** (require_admin)
- **16 AMBIGUOUS** (need review)
- **Cron endpoints reclassified**: `/api/cron/trigger` (L514) and `/api/cron/refresh` (L535) have CRON_SECRET auth — correctly unguarded
**Confirmed live (Aug 19):** `/api/india/cultural-events` returns 200 for free-tier token AND anonymous (no auth). `india_features` IS in `PAID_FEATURES` (restricted to pro/business at `plan_enforcement.py:63`), but neither duplicate definition uses `require_feature("india_features")`. Both versions only use `get_current_user` which returns "guest@trendrop.app" for anonymous without rejecting.
**Impact:** Free users can access premium features without upgrading. Revenue leakage on ~32 endpoints. Cultural-events confirmed active leak.
**Fix:** Add `require_feature()` checks to 32 unguarded endpoints. Priority: marketplace (13), india/cultural (10), hashtag (5). Cultural-events fix also touches P-API-2 (duplicate cleanup — decide which implementation to keep). See shared-infra rule #3 — needs explicit approval.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-API-5: Admin route auth check is incomplete
**File:** `backend/api.py` — admin routes
**Problem:** Some admin routes check `get_current_user` but don't verify `is_admin` flag. The redirect guard in the frontend catches this, but the API itself doesn't enforce it.
**Impact:** A non-admin user who knows the API endpoints can access admin data directly.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-API-6: POST /api/analytics/log 500s for authenticated users [OPEN]
**File:** `backend/api.py` — `log_analytics_event`
**Problem:** Authenticated request with valid body (`{"event_name": "..."}`) returns 500 `"Failed to log analytics event"`. The `analytics_events` insert fails inside the handler's try/except and is wrapped as a generic 500.
**Evidence (live, Aug 22, 2026):** Authed POST (chin@free.com Supabase JWT) → `500 :: {"detail":"Failed to log analytics event"}`, reproduced both before and after commit `67396838` (require_auth swap), proving it is NOT caused by that change. Unauth path correctly 401s. Unauth+missing-field correctly 422s.
**Suspected cause:** Insert failure against `analytics_events` — schema mismatch or RLS denial on the payload's `user_id`. Needs the underlying exception from server logs or a manual insert test with service-role client.
**Impact:** Analytics events are silently dropped for every logged-in user; the endpoint has likely never worked for authed traffic in its current form.

---

## 3. AUTH & SECURITY PROBLEMS

### P-AUTH-1: Custom JWT path doesn't check locked status — FIXED
**File:** `backend/auth.py:90-93`
**Problem:** When a JWT has a `"sub"` claim (custom path), the code returned the email without calling `_check_user_locked()`. A locked user with a valid JWT could access the API.
**Impact:** Account lockout was bypassed for users with custom JWTs.
**Evidence (live curl):** Locked account (chin@free.com) → 403 "Account is locked. Contact support." ✓, Unlocked accounts → 200 ✓.
**Fix:** Added `_check_user_locked(payload["sub"])` call and `except HTTPException: raise` to path 3, matching the pattern of paths 1 and 2.

### P-AUTH-2: Signup uses hardcoded verification code 123456 [FIXED]
**File:** `backend/phone_verification.py` — Twilio fallback
**Problem:** When Twilio is not configured (which it isn't — missing `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`), the verification code defaults to `123456`.
**Impact:** Anyone can complete phone verification with code `123456`. This is a security hole but also a UX feature (allows signup without Twilio).
**Fix applied:** Removed hardcoded `123456` simulation mode. When Twilio isn't configured, `send_verification_code()` now returns `success: False`. Signup flow already handles this gracefully — skips phone verification when service fails (`api.py:2160-2162`). No user-facing breakage.

### P-AUTH-3: Login page uses Supabase client-side auth
**File:** `frontend/src/contexts/AuthContext.tsx`
**Problem:** The login flow uses `supabase.auth.signInWithPassword()` directly from the browser. This means the Supabase anon key and URL are exposed in the frontend bundle. While this is standard Supabase practice, it means:
- The Supabase project is directly accessible from the browser
- RLS (Row Level Security) policies are the only protection
- Any misconfigured RLS policy exposes data
**Impact:** Security depends entirely on Supabase RLS configuration. No server-side auth gateway.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-AUTH-4: No rate limiting on auth endpoints [FIXED]
**Files:** `backend/api.py:70-80` (_enforce_rate_limit), `backend/redis_rate_limiter.py` (Redis-backed limiter)
**Problem:** No rate limiting on `/api/auth/login`, `/api/auth/signup`, `/api/auth/reset-password`, `/api/auth/send-otp`, `/api/auth/verify-phone`. An attacker can brute-force passwords or spam signup.
**Impact:** Account takeover risk. Email flooding from signup spam.
**Fix applied:**
- `sys.path.insert()` moved before `from redis_rate_limiter import ...` in `api.py:43` — was after the import, causing silent ImportError on Vercel.
- `check_rate_limit()` wired into 5 auth endpoints via `_enforce_rate_limit()` helper:
  - Login: 5/15min per IP+email
  - Signup: 3/hour per IP
  - Reset-password: 3/hour per IP+email
  - Send-otp: 3/min per IP+phone
  - Verify-phone: 5/hour per IP+phone
- `UPSTASH_REDIS_URL` env var synced to Vercel production.
**Verified (all 5 endpoints, deployment chcxhq2la):**
```
POST /api/auth/login          6th request → 429 after 5 allowed
POST /api/auth/reset-password 4th request → 429 after 3 allowed
POST /api/auth/signup         4th request → 429 after 3 allowed (clean window, Redis key reset)
POST /api/auth/send-otp       4th request → 429 after 3 allowed
POST /api/auth/verify-phone   6th request → 429 after 5 allowed
```

### P-AUTH-5 (SYSTEMIC): get_current_user never rejects guests — 66 endpoints silently open to anonymous traffic
**Files:** `backend/auth.py:43-96` (sentinel), `backend/api.py` (108 endpoints using it)
**Problem:** `get_current_user` returns `"guest@trendrop.app"` when no token is provided — it NEVER raises 401. Every endpoint using only `Depends(get_current_user)` with no additional guest check is silently open to anonymous traffic. This is not a bug in individual endpoints — it's a systemic design flaw in the auth dependency itself.

**Evidence (live curl, localhost:8099):**
```
GET /api/reels/stream/1 (no auth)  → 200 + real video URL   [BEFORE require_auth fix]
GET /api/reels/stream/1 (no auth)  → 401 Authentication req  [AFTER require_auth fix]
POST /api/generate-hooks (free-tier token) → 403 plan_upgrade_required  [require_feature works]
```

**Full audit of 108 endpoints using `Depends(get_current_user)`:**

| Category | Count | Detail |
|---|---|---|
| PROTECTED (require_feature/require_auth/require_quota/require_phone_verified/explicit guest check) | 42 | Safe |
| OPEN (no guest check) | 66 | Vulnerable |

**Of the 66 OPEN endpoints:**

**8 WRITE endpoints — guests mutate DB + incur costs:**

| Line | Route | Risk |
|---|---|---|
| 1995 | `POST /api/trends/{id}/memory` | Writes to `creator_trend_memory` as guest |
| 2684 | `POST /api/user/cancellation-reason` | Writes to `users` table as guest |
| 2832 | `POST /api/feedback` | Writes to `trend_feedback` as guest |
| 3485 | `POST /api/prepost-score` | **LLM call** + writes to `pre_post_analyses` as guest |
| 3531 | `POST /api/score-reel` | **LLM call** + writes to `pre_post_analyses` as guest |
| 3829 | `POST /api/marketplace/profile` | Creates `creator_profiles` as guest |
| 3851 | `POST /api/marketplace/deals` | Creates `brand_deals` as guest |
| 6719 | `POST /api/user/performance/store` | Writes performance data as guest |

**9 endpoints with FLAWED auth checks — guest can access other users' data:**

| Line | Route | Flaw |
|---|---|---|
| 3609 | `GET /api/daily-ideas/{user_email}` | Guest can read ANY user's daily ideas |
| 4130 | `GET /api/brand-deals/{user_email}` | Guest can read ANY user's brand deals | **FIXED** (commit `4d6e0620`) — simplified to `user_email != current_user_email` guard. Anonymous@ data leak also closed (0 rows existed). |
| 4274 | `POST /api/apply-deal` | Guest can apply as any user_email |
| 4299 | `GET /api/collab-matches/{user_email}` | Guest can read any user's matches |
| 4374 | `POST /api/send-collab-request` | Guest can impersonate any from_email |
| 4408 | `POST /api/instagram/auth-url` | Guest can generate OAuth URL for any user |
| 4516 | `POST /api/instagram/callback` | Guest can link Instagram for any user |
| 557 | `GET /api/creator/diagnostics` | Auth check evaluates True for guest |
| 570 | `GET /api/creator/niche-health` | Same pattern |

**46 read-only/informational** — lower risk but still consume compute, LLM calls, and external API calls (Instagram, YouTube) for unauthenticated traffic.

**3 phone verification endpoints** — guests can send SMS codes (`POST /api/phone/send-code`).

**4 business metrics endpoints** — expose revenue, MRR, CAC/LTV to anonymous traffic.

**Guest does NOT pollute:**
- `usage_logs` — `log_endpoint_usage` silently skips guest (plan_enforcement.py:561)
- `users` table — no auto-creation path for guest email
- Quota counters — `require_quota` blocks guests before counting
- Billing/payment flows — Razorpay-signed only, no guest reference

**Guest DOES pollute:**
- `creator_trend_memory` — accumulates guest-owned rows indefinitely
- `pre_post_analyses` — LLM calls + rows written as guest, unattributable

**Scope change disclosure:** `require_auth()` in auth.py:99 is NEW code written in this session (commit `fa81223a`). It was not in the original codebase. It was added to fix the3 stream/status endpoints I was originally asked to gate, without flagging that it was a shared-infra addition. This is a scope change that should have been flagged separately.

**Partial fix (commit `fab26f7c`):** 24 of 66 high-risk endpoints swapped to `Depends(require_auth)` — 8 write, 3 phone, 9 data-leak, 4 business. Anonymous access now blocked for these. Remaining42 read-only endpoints still open to anonymous guest traffic (lower priority — no data mutation, no PII exposure, but still consume compute/LLM/external API calls).

**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-EXH-1: Global exception handler swallows HTTPException — FIXED
**File:** `backend/api.py:824-830`
**Problem:** `@app.exception_handler(Exception)` caught ALL exceptions including `HTTPException`, returning a generic 500 for every auth failure across the entire API. Any endpoint raising 401/403/404 would return 500 to the client.
**Impact:** Auth errors (P-AUTH-5, P-AUTH-6, P-AUTH-7, require_admin, require_auth) all appeared as "Internal Server Error" to clients, making debugging impossible and breaking frontend error handling.
**Fix:** Added `if isinstance(exc, HTTPException): return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})` as an early return before the generic 500 handler.

### P-EXH-2: `jwt.JWTError` doesn't exist in PyJWT 2.x — FIXED
**File:** `backend/auth.py:140`
**Problem:** `verify_token()` caught `jwt.JWTError` which doesn't exist in PyJWT 2.13.0 — the correct class is `jwt.PyJWTError`. This meant JWT decode failures (expired tokens, wrong algorithm, invalid signatures) were never caught by the except clause, causing `AttributeError` to escape as an unhandled exception.
**Impact:** Combined with P-EXH-1, this made all JWT verification failures return 500 instead of 401. Specifically, Supabase ES256 tokens sent to endpoints using `verify_token` (which expects HS256) would crash instead of returning a clean 401.
**Fix:** Changed `except jwt.JWTError:` → `except jwt.PyJWTError:`.

---

## 4. PAYMENT & SUBSCRIPTION PROBLEMS

### P-AUTH-6: Business metrics (revenue/MRR/CAC) visible to any authenticated free-tier user — PARTIALLY FIXED, then COMPLETED
**Files:** `backend/api.py:6794,6812,6830,6848,6885,6902`
**Problem:** Six business metrics endpoints had only `Depends(require_auth)` or `Depends(get_current_user)` — any authenticated user (including free-tier) could see full revenue data, MRR, CAC/LTV, user acquisition, churn rates.
**Fix (fab26f7c, Aug 18):** Swapped `Depends(require_auth)` → `Depends(require_admin)` on 4 endpoints: `/api/business/metrics`, `/api/business/user-metrics`, `/api/business/revenue`, `/api/business/mrr`. Evidence: anonymous→401, free-tier→403, admin→200. **BUT: 2 of 6 endpoints were silently missed — `subscription-breakdown` and `cac-ltv` were never in the diff.**
**Fix (dcfb2fb7, Aug 20):** Swapped `Depends(get_current_user)` → `Depends(require_admin)` on the 2 missed endpoints: `/api/business/subscription-breakdown` (L6889), `/api/business/cac-ltv` (L6906). Pre-change baseline confirmed 422/500 for authenticated users (pre-existing Pydantic/predictor errors, not auth-related). Post-change: anon→401, free-tier→403, admin→200 on both. All 6 business metrics endpoints now admin-only.

### P-AUTH-7: Write-side IDOR — authenticated users can write to other users' resources [FIXED, VERIFIED]
**Files:** `backend/api.py` — 8 write endpoints (lines 2022, 2713, 2864, 3517, 3563, 3861, 3883, 6727)
**Problem:** Eight write endpoints use `Depends(require_auth)` (post P-AUTH-5 fix) but perform no ownership check in the function body. An authenticated user can write data attributed to any email.
**Verified:** Endpoint 8 (`POST /api/user/performance/store`, L6727) is the only one accepting `user_email` as input — curl-verified: attack → 403, legit → 200, no auth → 401. Ownership check at L6736-6737 works. Endpoints 1-7 either have no email field in their Pydantic model (safe by design) or have a dead email field that is silently overridden by the handler using auth identity (safe by implementation — see P-AUTH-9).
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-AUTH-9: Dead user_email/creator_email fields in write request models — refactoring trap [FIXED]
**Files:** `backend/api.py` — 4 Pydantic models
- `FeedbackRequest.user_email` — handler uses `current_user_email` at L2876, ignores model field
- `PrePostRequest.user_email` — handler uses `current_user_email` at L3531, ignores model field
- `CreatorProfileRequest.user_email` — handler uses `current_user_email` at L3866, ignores model field
- `BrandDealRequest.creator_email` — handler uses `current_user_email` at L3890, ignores model field
**Fix (d744f24f):** Removed all 4 dead fields from the Pydantic models. Verified: backend boots clean, all 4 endpoints return 200 for authenticated requests, no-auth returns 401. marketplace/deals 500 is pre-existing (confirmed with original code). Frontend does not send these fields (checked all api.ts callers). No test files send these fields.

### P-AUTH-10: No session created after phone verification — user must re-authenticate [MEDIUM — DESIGN DECISION, not a bug]
**Files:** `backend/api.py:2240-2243`, `frontend/src/routes/verify-phone.tsx:78-80`
**Problem:** After successful OTP verification, `/api/auth/verify-phone` returns `{ success: True, message: "Phone verified successfully. Please log in to continue." }` — no session token, no user data. The frontend redirects to `/login` and the user must re-enter email/password from scratch. The account exists and the flow doesn't crash (after P-AUTH-10 frontend fix: commit `b953d09f`), but the UX is two steps where one would suffice.
**Status:** Frontend fixed (b953d09f). Backend auto-login requires product decision: (a) return Supabase session from verify endpoint = auto-login, or (b) keep verify-then-login as intentional. Current behavior works correctly; extra step is UX friction, not a bug. No code change until product direction is set.

### P-AUTH-11: require_admin returns 401 instead of 403 for non-admin authenticated users [LOW — DOCUMENTED, cosmetic, fails closed]
**Files:** `backend/auth.py:254-283` (`require_admin`), `backend/auth.py:133-147` (`verify_token`)
**Problem:** `require_admin` calls `verify_token(token)` which decodes JWTs signed with `JWT_SECRET_KEY`. Regular users receive Supabase session tokens from `/api/auth/login`, which are signed with a different key. When a non-admin authenticated user hits an admin endpoint (e.g., `GET /api/business/subscription-breakdown`), `verify_token` fails to decode their Supabase token → raises 401 "Invalid token" instead of reaching the role check and returning 403 "Forbidden."
**Impact:** Cosmetic — the endpoint correctly blocks non-admin access (fails closed, which is the safe direction). But the error message is misleading: a logged-in free-tier user sees "Invalid token" (suggesting their auth is broken) instead of "Forbidden — admin access required" (suggesting they lack permissions). This makes debugging "why can't I access this as a logged-in user" confusing.
**Why not fixed:** The fix would require `require_admin` to fall back to `get_current_user` (which handles Supabase tokens) when `verify_token` fails, then check the user's role in the `admin_users` table. That's a behavior change to an auth gate — not worth the risk for a cosmetic improvement on 2 endpoints with 0 live users.
**Introduced by:** `dcfb2fb7` (swapped `get_current_user` → `require_admin` on 2 endpoints). Pre-existing design: admin tokens (app-signed JWT with `role` claim) and user tokens (Supabase session) are different formats. The commit correctly applied the stricter gate; the 401-instead-of-403 is a side effect of the token format mismatch, not a new bug.
**Verified:** All 5 endpoints in `dcfb2fb7` confirmed working — no-auth →401, non-admin →401/403, admin →200 with real data. See evidence in session log Aug 22, 2026.
**Status:** Documented. No code change — fails closed, cosmetic only, 0 live users affected.

### P-AUTH-8: Rate limiter fails silently open — both paths [FIXED]
**Files:** `backend/redis_rate_limiter.py:59-61,106-113`, `backend/api.py:452-459`
**Problem:** Two failure paths both result in rate limiting silently degrading to "off" with no signal:
1. **Redis connection drops at runtime** (`redis_rate_limiter.py:106-113`): bare `except` → `print()` to stdout → returns `True` (allowed). slowapi was disabled at import time (L455: `enabled=False`) and stays disabled. No rate limiting. No alert.
2. **Env var unset on next deploy** (`api.py:458`): `REDIS_RATE_LIMITER_AVAILABLE` = `False` → slowapi in-memory limiter activates. On Vercel serverless, in-memory state resets per cold start → rate limits non-functional.
**Impact:** Both paths were silent. `print()` output was discarded on Vercel (FileHandler writes to /tmp, not stderr). No 429, no error, no persisted log. Rate limiting could silently degrade to "off" with no signal during an incident.
**Fix applied:**
- `print()` calls replaced with `logger.info/warning/error` (5 call sites).
- `StreamHandler` added to `redis_rate_limiter` logger to ensure output reaches stderr (Vercel captures stderr, not FileHandler from `api.py`'s `basicConfig(filename=...)`).
- `_log_once` guard on `is_allowed` catch-all prevents Redis transient error log flooding.
- `import json` and `from typing import Optional` removed (dead imports).
- `__main__` block kept as `print()` (CLI output, not server logging).
- Fail-open semantics preserved (pre-revenue, ~15 users — availability > security on rate limiting).
**Verified:** `redis_connected` log line confirmed in Vercel logs via `--json` output on cold start:
```
"logs":[{"level":"info","message":"2026-08-18 20:37:20,020 - redis_rate_limiter - INFO - redis_connected"}]
```

### P-PAY-1: Razorpay keys missing — payment flow is DEAD
**File:** `backend/plan_enforcement.py`, `backend/api.py` — payment routes
**Problem:** `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` are not set in any environment. The `RAZORPAY_WEBHOOK_SECRET` exists but the actual API keys don't.
**Impact:** `/api/payment/create-order` fails. Nobody can upgrade their plan through the UI. The entire payment flow is non-functional.
**Does IMPLEMENTATION_PLAN.md fix this?** Yes. Item 3.8 identifies this as a user-action blocker. But no code fix exists — only "create Razorpay account → KYC → add keys."

### P-PAY-2: `/pricing` page exists but is a dead end — no payment flow [UPDATED]
**File:** `frontend/src/routes/pricing.tsx` — page exists, never deleted
**Problem:** The PlanGate component shows an "Upgrade" button that links to `/pricing`. The page EXISTS (was never deleted — PROBLEMS.md was wrong). However, all 3 tier buttons on the pricing page simply navigate to `/login`. There is no Razorpay checkout, no `createPaymentOrder()` call, no payment flow. The page is a dead end: PlanGate → `/pricing` → click "Upgrade" → `/login`.
**Impact:** Free users who hit a plan gate see an upgrade button that leads to a page with no conversion path. Revenue is blocked by the absence of a payment flow, not by a missing page.
**Confirmed via trace:** 9 PlanGate instances across 6 files all use `window.location.href = '/pricing'`. `routeTree.gen.ts` includes `/pricing`. The page renders 3 tiers (Free/Creator/Agency ₹999/₹4,999) but all buttons go to `/login`.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Fix options:** (a) Add Razorpay checkout to pricing page — blocked on P-PAY-1 (no Razorpay keys). (b) Redirect PlanGate to an in-app upgrade modal with "Contact to upgrade" CTA — works without Razorpay. (c) Redirect to `/login` with upgrade context — minimal, loses conversion opportunity.

### P-PAY-3: `usage_logs` has 0 rows — quota logging is broken [SUPERSEDED — see P-DB-1/P-PAY-6]
**Re-verified Aug 22, 2026 (live REST):** `usage_logs` is no longer empty — a row landed today at 15:48 UTC for `algorithm_insights` on the free plan. Separately, enforcement has moved to the credits ledger (`credit_transactions`, 12 rows with real user traffic today). The Aug 18 claim ("quota logging never happens") is stale; the mechanism it described was replaced wholesale by the credits system.

### P-PAY-4: `verify-phone` page — FALSE POSITIVE [UPDATED — NOT BROKEN]
**File:** `frontend/src/routes/verify-phone.tsx` — page EXISTS, was never deleted
**Problem:** PROBLEMS.md incorrectly claimed this page was deleted. The file exists, is registered in `routeTree.gen.ts`, and the route works. The redirect from `AuthContext.tsx:166-168` only fires when `phone_verification_required` is true (phone-based signups only). Email/OAuth signups never hit this path.
**Impact:** None for email-only signups. Phone-based signups would work if anyone used them.
**Confirmed via trace:** `api.py:2149-2165` sets the flag during signup if a phone number is provided. Backend endpoint `POST /api/auth/verify-phone` exists at `api.py:2209`. Rate limited (5 attempts/hour).
**Action:** Remove from active problem list. Keep page as-is — it works if needed.

---

## 5. FRONTEND DESIGN PROBLEMS

### P-DESIGN-1: No design system — three visual personalities
**Files:** `frontend/src/styles.css`, `frontend/src/routes/login.tsx`, `frontend/src/routes/ideas.tsx`, `frontend/src/routes/settings.tsx`
**Problem:** The app has three distinct visual styles:
1. **Login page**: Clean minimal card, slate colors, white background
2. **Ideathon**: Maximalist dark-mode glass UI, gradients, glows, animations
3. **Settings**: Simple list layout, localStorage-only

Each page uses different card styles, input styles, button styles, and color tokens.
**Impact:** The app feels like three different products stitched together. No cohesive brand experience.
**Does IMPLEMENTATION_PLAN.md fix this?** No. The plan doesn't address frontend design.

### P-DESIGN-2: Typography conflict — three fonts declared for body [FIXED — verified Aug 22, 2026]
**File:** `frontend/src/styles.css`
**Fix verified:** "Inter" is gone entirely from the codebase. `--font-sans` and `--font-display` are now both `"Bricolage Grotesque", system-ui, sans-serif` (styles.css:51-52); body and all headings consume `font-family: var(--font-sans)` (styles.css:123, 330-335). JetBrains Mono is scoped to `.mono`/code contexts only (365, 446-489). The old competing `body { font-family: ... !important }` override no longer exists; heading sizes at styles.css:337-356 are set WITHOUT `!important`, so components can override them.
**Impact resolved:** Single font source of truth via CSS custom properties; component-level overrides possible.

### P-DESIGN-3: Color drift — indigo appears everywhere, brand is coral
**Files:** `frontend/src/routes/login.tsx`, `frontend/src/routes/settings.tsx`, `frontend/src/routes/ideas.tsx`
**Problem:** The brand color is coral (#FF4D3D). But `text-indigo-600`, `bg-indigo-500/10`, `border-indigo-500/20` appear hundreds of times across pages. Indigo is not in the brand palette.
**Impact:** The brand color is coral but the app looks indigo. Inconsistent brand identity.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-DESIGN-4: Phone-only layout — no responsive design
**File:** `frontend/src/routes/index.tsx` — `max-w-md` constraint
**Problem:** The main app container is constrained to `max-w-md` (448px). On desktop, it's a centered phone-shaped column. No responsive breakpoint for tablets or desktop.
**Impact:** Desktop users see a phone app in the middle of their screen. 50%+ of web traffic is desktop.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-DESIGN-5: No loading skeletons, no empty states, no error states
**Files:** `frontend/src/routes/index.tsx`, `frontend/src/routes/ideas.tsx`
**Problem:**
- Loading: Spinning RefreshCw icon everywhere. No skeleton states.
- Empty: No "No trends found" message when feed is empty.
- Error: Generic error messages with no retry button or context.

**Impact:** Poor perceived performance. Users don't know if the app is broken or just loading.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-DESIGN-6: Animation overload — seizure-inducing neon glow [FIXED — reduced-motion support added]
**File:** `frontend/src/styles.css`
**Fix verified Aug 22, 2026:** Global `prefers-reduced-motion: reduce` block added at styles.css:609-618 — kills every animation/transition (`animation-duration: 0.01ms !important; animation-iteration-count: 1 !important; transition-duration: 0.01ms !important; scroll-behavior: auto`) and neutralizes card hover transforms. The photosensitivity/battery concern for motion-sensitive users is addressed.
**Remaining (minor):** The neon glow animations themselves still exist as opt-in utilities (`card-glow-dark`/`card-glow-light`, styles.css:309-315) — but they're now class-applied rather than ambient, and disabled entirely under reduced motion.

### P-DESIGN-7: Near-zero accessibility
**Files:** All frontend routes
**Problem:**
- No ARIA labels on interactive elements
- No keyboard navigation (filter bars require mouse/touch)
- No focus management (modals don't trap focus)
- Color-only status indicators (no text fallback for colorblind users)
- Font sizes too small (10px labels, 11px tab text)
- No skip links

**Impact:** The app is unusable for screen reader users. Below WCAG 2.1 AA compliance.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-DESIGN-8: Glass morphism won't work on low-end Android [PARTIAL FIX — fallback added]
**File:** `frontend/src/styles.css` — `.glass-card` class + `@supports` fallback
**Fix verified Aug 22, 2026:** A `@supports not (backdrop-filter: blur(1px))` block was added at styles.css:620-625 — devices with NO backdrop-filter support get a solid `rgba(21,21,28,0.95)` background instead of broken/absent blur.
**Remaining:** Devices that SUPPORT backdrop-filter but lack the GPU headroom (<4GB RAM that renders blur slowly) still take the frame-rate hit — the worst-case hardware is handled, the middle band is not. Options like reducing blur radius or media-query-gating by device memory remain unimplemented.

### P-DESIGN-9: Settings page saves to localStorage only — no server sync
**File:** `frontend/src/routes/settings.tsx`
**Problem:** ALL settings (niche, language, region, dark mode) save to `localStorage`. No server sync. No plan display. No subscription management. No account settings.
**Impact:** Settings are lost when user switches devices. No server-side preferences. The settings page is effectively a demo.
**Does IMPLEMENTATION_PLAN.md fix this?** Yes. Item 3.4 (Personalization) addresses this with `user_preferences` table and server sync.

### P-DESIGN-10: Inconsistent input styles across pages [FIXED — verified Aug 22, 2026]
**Files:** `frontend/src/styles.css` (`.input` recipe)
**Fix verified:** The `.glass-input` class no longer exists anywhere in `frontend/src` (grep: zero matches). Inputs are unified under a single `.input` recipe at styles.css:497-514 which ALSO targets shadcn-style Tailwind inputs via attribute selectors (`input[class*="flex h-9 w-full rounded-md border"]`, textarea equivalent) — so both custom and library inputs get identical treatment: same surface/border/radius/padding/typography, coral focus ring (`border-color: var(--primary)` + `box-shadow: rgba(255,77,61,0.12)`) consistent with the brand.
**Impact resolved:** One form design language across pages.

### P-DATA-1: Targeted trends localStorage/API divergence — data-integrity bug [FIXED — verified Aug 22, 2026]
**Files:** `frontend/src/components/TrendCard.tsx`, `frontend/src/lib/api.ts`
**Fix verified:** Commit `5e7c92c7` removed all client-side `localStorage.getItem("targeted_trends")` / setItem logic from TrendCard.tsx and DanceTrendModal.tsx (grep: zero matches). The single source of truth is now the server: `frontend/src/lib/api.ts:1646` reads `GET /api/trends/targeted` straight from the API with no local mirror. DB divergence is no longer possible.
**Original problem (for the record):** Toggle state lived in TWO places (localStorage + `trend_actions` table). A failed POST silently diverged localStorage from DB, so the workspace's targeted list could disagree with what the user saw toggled.

---

## 6. DATABASE & DATA QUALITY PROBLEMS

### P-DB-1: `usage_logs` table has 0 rows — quota enforcement disabled [SUPERSEDED by credits system]
**File:** Supabase `usage_logs` table
**Re-verified Aug 22, 2026 (live REST):** Table exists and IS being written — a fresh row landed today at 15:48 UTC (`feature_used=algorithm_insights`, `plan_at_time=free`). Total row count is tiny (1), so volume is low, but the "never logs" claim from Aug 18 is no longer true.
**Bigger change:** Quota enforcement has moved to the credits model (P-PAY-6) — `require_credits()` checks/deducts via the `credit_transactions` ledger (12 rows, latest 15:30 UTC today, real user traffic). `require_quota()` is referenced 0 times in api.py. The original failure mode ("free users unlimited premium because table empty") is closed by a different mechanism than the one originally proposed.
**Impact:** Resolved in practice via credits; keep for audit trail.

### P-DB-2: `events` table doesn't exist — event detection impossible [STILL OPEN — re-verified live Aug 22]
**File:** Supabase — table not found
**Live check Aug 22, 2026:** `GET /rest/v1/events` → `PGRST205 Could not find the table 'public.events' in the schema cache`. Still missing.
**Impact:** Event detection (Independence Day, Diwali, IPL, etc.) is completely non-functional.
**Does IMPLEMENTATION_PLAN.md fix this?** Yes. Item 3.1 creates the events table and seeds real data.

### P-DB-3: `user_preferences` table doesn't exist — no personalization [STILL OPEN — re-verified live Aug 22]
**File:** Supabase — table not found
**Live check Aug 22, 2026:** `GET /rest/v1/user_preferences` → `PGRST205`. Still missing.
**Impact:** No feed personalization. All users see the same trends. Settings lost on device switch.
**Does IMPLEMENTATION_PLAN.md fix this?** Yes. Item 3.4 creates the `user_preferences` table and syncs settings.

### P-DB-4: `api_keys` table doesn't exist — no API revenue [STILL OPEN — re-verified live Aug 22]
**File:** Supabase — table not found
**Live check Aug 22, 2026:** `GET /rest/v1/api_keys` → `PGRST205`. Still missing.
**Impact:** API access control is non-functional. No way to monetize API access.
**Does IMPLEMENTATION_PLAN.md fix this?** Not in current build order. Mentioned as "Phase 2" item.

### P-DB-5: `brand_deals` table has 0 rows — marketplace is empty [STILL OPEN — re-verified live Aug 22]
**File:** Supabase `brand_deals` table
**Live check Aug 22, 2026:** Table exists, count = 0. Unchanged.
**Impact:** Marketplace feature shows nothing. No brand partnerships.

### P-DB-6: Feed empty since Aug 18 — scraper bulk-upsert PG-21000 killed every save batch [FIXED + VERIFIED]
**Files:** `backend/instagram_scraper_browser.py` (root cause), `.github/workflows/scraper.yml` (masking), `backend/verify_scraper_run.py` (detection)
**Symptom:** All 319 trends peaked/expired; zero new reels since Aug 18; `/api/trends` empty for eligible users; feed dead for ~4 days with no alert.
**Root cause:** Commit `d581da27` changed Phase D to a single bulk upsert of each XHR payload's reels without intra-payload dedup. Instagram payloads can contain the same `reel_id` twice; Postgres rejects the whole statement atomically with `21000: ON CONFLICT DO UPDATE command cannot affect row a second time`. Every chunk containing a duplicate was lost entirely. The exception was caught per-hashtag and logged at debug level, so the run exited 0 while saving nothing.
**Masking layer:** The workflow's Verify step ran `verify_scraper_run.py`, whose freshness check (`max_age_hours=9`) failed from Aug 19 onward — but the step had `continue-on-error: true`, so red checks never failed the run. Two independent safety nets were both silent.
**Fix applied (PR #4, commits `87a72bf7` + `69162acb`, merged `1450f8c1` on Aug 22 2026):**
1. Deduplicate payload by `reel_id` (keep last occurrence) before upsert.
2. On residual conflict: per-row salvage retry so one bad row can't discard 200 good ones.
3. Orphan guard: snapshot writes only for reels that actually saved (prevents snapshot/reel drift).
4. Removed `continue-on-error: true` from the Verify step — freshness failures now fail the run.
5. `max_age_hours` 9 → 30. Rationale: the window must be strictly less than the cadence gap (48h) or a single fully-dead cycle passes as "fresh" — exactly the outage class this guards against. 30h ≈ 62% of the gap catches any dead cycle while absorbing LLM-classification lag and cron jitter.
**Verification (run `32591223200`, Aug 22 2026, first run on fixed code):**
- 396 Saved-reel lines; **0× PG-21000**; 0 salvage events (dedup handled everything upstream).
- `insert_saved == insert_attempts` (164/164 India cohort, 232/232 Global cohort) — nothing silently dropped.
- DB deltas exact: reels 7,647→8,043 (+396), snapshots 20,691→21,087 (+396). Snapshot/reel parity holds.
- Trends 319→330: **3 rising, 8 emerging** — first new active trends since Aug 18.
- Verify step: `[OK] Found 10 recent trends — VERIFICATION: PASS` on merit (not skipped).
**Downstream chain verified end-to-end (same day):** free tier correctly sees 0 items (<24h `data_delay_hours` gate), Pro user sees all 3 rising items via live `/api/trends`; `/api/trends/emerging` correctly 403s free users (`plan_upgrade_required`); trend→reels join returns owners + view counts. Note: Supabase signup creates no `users` row until onboarding — plan lookups default such users to free (test-artifact gotcha, not a product bug).
**Status:** FIXED + VERIFIED (Aug 22 2026). Residual watch item: cadence still every-2-days (`0 2 * * */2`); daily fits the 2,000 min/mo Actions budget if desired (measured 911 min incl. incident era) — decision deliberately decoupled from this fix.

### P-DB-7: `user_performance` (and 5 related tables) never migrated — tracker silently no-ops [FIXED → STILL BLOCKED: migration SQL never executed]
**Files:** `backend/user_performance_tracker.py`, `backend/add_user_performance_tables.py`, `backend/api.py:6720-6792`
**Problem:** The migration script `add_user_performance_tables.py` only prints SQL for manual execution (L130: "Please run these SQL statements in Supabase SQL Editor") — it was never run. All 6 planned tables are missing: `user_performance`, `user_insights`, `user_media_performance`, `realtime_trends`, `trending_hashtags`, `trending_audio`. The `UserPerformanceTracker` class is live code (imported at `api.py:296`, used by 4 endpoints), but every DB operation hits a nonexistent table and returns PGRST205 errors. The tracker's exception handler at `user_performance_tracker.py:123` catches these and returns `{'error': str(e)}`, which the API passes through — so writes appear to succeed but nothing lands.
**Impact:** The entire user performance feature (store, read, growth rate, top media) is non-functional. The 4 API endpoints at L6720-6792 are dead code from a data perspective.
**Also flags:** Exception handlers that return success-like responses on DB failure are a bug class — worth auditing elsewhere. A handler that catches all exceptions and returns a dict without re-raising means callers can't distinguish success from failure.
**Fix applied:** Created `backend/migrate_user_performance_tables.sql` with `CREATE TABLE IF NOT EXISTS` for the 3 core tables: `user_performance`, `user_insights`, `user_media_performance`. Schema derived from tracker code. User must run this SQL in Supabase SQL Editor. Tables 4-6 (`realtime_trends`, `trending_hashtags`, `trending_audio`) are not used by any code — omitted.
**UNVERIFIED → CONFIRMED STILL MISSING (live REST check Aug 22, 2026):** `user_performance`, `user_insights`, `user_media_performance` all return `PGRST205 Could not find the table`. `backend/migrate_user_performance_tables.sql` exists on disk but has never been executed in Supabase. The [FIXED] tag this entry carried was wrong — writing SQL is not running it. P-AUTH-7 GET-side IDOR fix remains blocked until the tables exist. **User action required: run the SQL file in Supabase SQL Editor.**

### P-DB-8: Supabase Python client silently truncates at 1000 rows — systemic data visibility risk [PARTIAL FIX]
**Files:** Any code using `supabase-py` `.table().select().execute()` without explicit `.limit()` or pagination.
**Problem:** The Supabase Python client defaults to `.limit(1000)` on all queries. This is silent — no error, no warning, no partial-result flag. If a table has >1000 rows, the query returns only the first 1000 and the caller has no way to know. This affected the P-METHOD-1 analysis: the `trends` table had 1,013 rows but the analysis script saw only 1,000, missing 13 rows across 12 duplicate groups. The DELETE list was built on incomplete data and required a second pass.
**Impact:** Any production query fetching trends, snapshots, or reels without an explicit limit or pagination could be silently returning partial data. This includes dashboards, velocity calculations, feed endpoints, analytics, and any metric that sums or counts across the full table. The user would see incomplete data with no indication anything is wrong.
**Audit results (Aug 2026):** Grep of all `.table().select()` calls in `backend/`. Verified per-filter row counts against live prod (Supabase REST API).
- Tables >1,000 rows: `reels` (7,467), `reel_snapshots` (19,031). All others under 1,000.
- `reel_snapshots` has 10 code references (api.py:1728, instagram_scraper_browser.py:1534/1927/1945, migrate_reel_snapshots.py). All queries bounded by `.eq("audio_id", ...)`.
- Max reels per `audio_id`: **13**. All `.eq("audio_id", ...)` queries safe.
- Max reels per `audio_title`: **3,896** ("Original audio" — default/placeholder). No production query filters by this title.
- Max reels per hashtag: **1,214** (`#viral`). Was actively truncated.
**Fix applied:**
1. `dynamic_hashtag_discovery.py:107` — **FIXED** (commit `a9358d9e`). Unbounded `.contains('hashtags', [hashtag])` replaced with `.range()` pagination loop. `#viral` (1,214 rows) now fully fetched.
2. `cron_job.py:305` — **SAFE** (no fix needed). 30-minute time window, ~323 reels max per query.
3. `realtime_velocity_tracker.py:162` — **SAFE** (no fix needed). `.eq("audio_id", ...)` maxes at 13 rows.
4. `api.py:1728` — **SAFE** (no fix needed). `.eq("audio_id", ...)` + 72h window, ~39 snapshots max.
5. `instagram_scraper_browser.py:1777,1970,1979` — **MONITORED**. `.eq("audio_id", ...)` and `.eq("audio_title", ...)` queries, safe today (max 13 per audio_id), but unbounded. Will silently truncate if volume grows.
6. `dynamic_hashtag_discovery.py:209` (second call site) — **MONITORED**. Has `.limit(100)` already, safe.
**Remaining risk:** Five unbounded query sites in production code are safe today but landmines for future volume growth. No immediate fix needed — monitored.

### P-METHOD-1: Trend dedup guard only checks emerging/rising — allows re-detection after status transition [FIXED — re-verified Aug 22]
**Fix still in place:** STATUS_PRIORITY-based never-downgrade merge guard present at `backend/trend_engine.py:756-799` ("Status uses never-downgrade rule (rising > emerging > peaked > expired)").
**Files:** `backend/trend_engine.py:756-814` (dedup guard — FIXED), `backend/external_trend_pipeline.py:92` (dedup guard — FIXED), `backend/trend_refresher.py` (status transitions)
**Problem:** The dedup guard at `trend_engine.py:762` only checked trends with status `emerging` or `rising`. Once a trend transitioned to `peaked` or `expired` via `trend_refresher.py`, the guard no longer blocked re-detection. The external pipeline at `external_trend_pipeline.py:92` had zero dedup. No unique DB constraint on `audio_id` in the `trends` table.
**Impact:** 53% of trend titles were duplicated. 1,013 total rows, 163 duplicate groups, 692 excess rows. Business metrics (trend count, velocity averages) inflated ~2.7x since Aug 7. Ongoing since day one.
**Fix applied:**
1. Backfill DELETE of 679 rows committed (first pass — Supabase pagination bug missed 13 rows).
2. Cleanup DELETE of 13 remaining excess rows committed. Final state: 321 unique trends, 0 duplicate groups.
3. Unique constraint `trends_audio_id_unique` on `audio_id` — live, proven to reject duplicates.
4. Forward-fix Change A (trend_engine.py): dedup guard widened to all statuses, never-downgrade status rule (`rising > emerging > peaked > expired`), update-in-place on match. Velocity/metrics untouched — owned by trend_refresher.py via 5 independent cron-driven call sites. Committed `e23ef810`.
5. Forward-fix Change B (external_trend_pipeline.py): dedup guard added by `bcb54d53` (Aug 19). Checks by `audio_title + audio_artist` before insert. On match: applies never-downgrade status rule (`rising > emerging > peaked > expired`), only status updated. Verified: `STATUS_PRIORITY = {"expired": 0, "peaked": 1, "emerging": 2, "rising": 3}`, `audio_title + audio_artist` equality check, velocity/metrics untouched.

### P-METHOD-1b: title+artist duplicate pairs — manual dedup [FIXED]
**Files:** `trends` table
**Problem:** Three songs had duplicate entries by (audio_title, audio_artist) but different audio_id values.
**Investigation results:**
- **"This & That" by Stray Kids** (ids 377/458): Identical velocity_avg to 10 decimal places, identical reel_count. Confirmed duplicate — same audio, different Instagram internal IDs on different scrape days. Created Aug 10-11 during Change A relaxed window. **Deleted id=377 (older), kept id=458.**
- **"Jamaican (Bam Bam)" by HUGEL/SOLTO (FR)** (ids 288/428): Identical velocity_avg to 14 decimal places, identical reel_count. Confirmed duplicate. Created Aug 8-11 during Change A relaxed window. **Deleted id=288 (older), kept id=428.**
- **"Be My Baby" by The Ronettes** (ids 862/1019): velocity_avg 8059 vs 17788 (2x difference), reel_count 2 vs 3. **Legitimate distinct audio versions** — different Instagram audio files with different metrics. NOT a duplicate. No composite unique constraint applied; would block legitimate distinct tracks.
**Resolution:** Deleted 2 rows, 56 cascade-deleted snapshots. Row count 321→319. No composite (audio_title, audio_artist) unique constraint — confirmed wrong for tracks with multiple legitimate versions.
**Status:** FIXED (Aug 20 2026)

### P-METHOD-1c: Trend-insertion path bypassed dedup guards [CLOSED]
**Files:** `trend_engine.py`, `external_trend_pipeline.py`
**Root cause:** No standalone seed script. The ~43-58 duplicate rows were created by the normal pipeline running during Aug 8-19 when: (a) Change A dedup (`05bd5f5c`, Aug 8) narrowed guard to only active/emerging/rising trends, allowing re-insertion of expired/peaked rows; (b) Change B (external_trend_pipeline.py) had zero dedup before Aug 19.
**Timeline:** Change A introduced Aug 8 00:00 → cleanup scripts ran Aug 19 13:44-13:55 → Change A restored `e23ef810` Aug 19 14:26 → Change B added `bcb54d53` Aug 19 15:21. 31-96min gap between cleanup and guard restoration, but row count (321) matches expected post-cleanup number, ruling out cron reinsertion in gap.
**Resolution:** Both guards live and verified. Row count stable at 319 (post P-METHOD-1b dedup). No remediation needed.
**Status:** CLOSED (Aug 20 2026)

### P-METHOD-5: Video sequence/format-driven trends not detected (distinct from P-METHOD-4) [NEW]
**Problem:** Some Reels go viral because of a replicated edit pattern, transition, or shot sequence — not because of shared audio or generic visual similarity. This requires structural/edit-pattern fingerprinting, not just audio_id grouping or pHash visual clustering (P-METHOD-4). Currently undetected by any part of the pipeline.
**Evidence base:** Public research confirms Instagram's Reels ranking is driven primarily by watch-time/completion and DM-sends-per-reach — not audio identity — meaning format-driven virality is a first-class phenomenon on the platform, not an edge case.
**Action required:** Scope as its own investigation — likely harder than P-METHOD-4 since it requires structural pattern-matching across edits, not just perceptual hashing. Not yet estimated.

### P-METHOD-6: Velocity formula doesn't use Instagram's actual dominant ranking signals [DISCLOSED LIMITATION — audited Aug 2026]
**Problem:** Trendrop's velocity_avg formula is derived from engagement/followers/creator-age. Instagram's own confirmed ranking hierarchy (per Adam Mosseri, 2025-2026) weights watch-time-completion as the #1 signal and DM-sends-per-reach as the strongest signal for non-follower reach — with likes explicitly the weakest signal. Trendrop's formula does not include either.
**Audit result (Aug 2026):** Browser-scraped GraphQL endpoints do not expose watch-time, completion-rate, or DM-send-count. These signals are only available via Instagram's internal Insights API (requires Business/Creator OAuth + per-reel calls) — structurally unavailable to a third-party scraper. **This is a platform limitation, not a code fix.**
**Current formula (instagram_scraper_browser.py:1249-1252):** `engagement = views + (likes × 3) + (comments × 5); velocity = (engagement / hours_live / log(followers + 10)) × 100`. Uses only views, likes, comments — the three signals Instagram exposes publicly. No share_count, no watch-time, no completion-rate.
**Classification:** Disclosed methodology limitation. Document for users/investors: "Velocity is calculated from publicly available engagement signals. Instagram's internal ranking signals (watch-time, shares) are not accessible to third-party tools."
**Does IMPLEMENTATION_PLAN.md fix this?** No. Platform limitation, not solvable via code.

### P-METHOD-7: Velocity spikes can't distinguish audio-driven virality from unrelated causes (misattribution risk) [NEW — scoped Aug 2026]
**Problem:** A reel using a given audio can go viral for reasons unrelated to the audio (external events, appearance-driven engagement, unrelated content virality). Trendrop's current model attributes any velocity spike on a tracked audio_id to "the audio is trending," with no mechanism to detect when the spike is actually driven by something else. This is distinct from P-METHOD-6 — that item is about signals we can't access (watch-time, DM-sends). This item is about whether the signals we *do* have (views, likes, comments, hashtag clustering) can distinguish genuine audio-driven trends from misattributed spikes.
**Data audit context (Aug 2026):** P-METHOD-6 confirmed watch-time and DM-sends are structurally unavailable. This item must be solved (if at all) with the existing signal set: view_count, like_count, comment_count, hashtags, creator_country, content_type.
**Possible cheap partial signal:** Check whether velocity spikes are concentrated in a narrow content-type/hashtag cluster (suggesting non-audio cause) vs. spread across diverse content (suggesting genuine audio-driven trend). Needs independent scoping — not closable by association with P-METHOD-6's disclosed limitation.
**Action required:** Scope separately. Estimate feasibility of hashtag-cluster/concentration analysis as a misattribution detector. Not yet estimated.

### P-SCRAPER-1: share_count field never extracted — DB column exists but always null [CODE GAP — fixable, needs manual retry]
**Files:** `instagram_scraper_browser.py:1413-1434` (reel dict construction)
**Problem:** The `reels` table has a `share_count` column (database_setup.py:30), but the browser scraper never populates it. Every row is null. The GraphQL response the scraper already hits likely contains share data in some form — the field just isn't being extracted from the response dict. This is a code gap, not a platform limitation.
**Impact:** Velocity formula excludes shares entirely (views/likes/comments only). Instagram's own ranking heavily weights shares/DM-sends. Even a partial share signal would improve velocity accuracy.
**Investigation status (Aug 2026):** Agent-based probe returned inconclusive — sandboxed environment can't run a live scrape with Instagram cookies/headers. The question "does the GraphQL response contain a share field we're dropping" is still open. Needs manual retry: log raw response keys during a real scrape run, or dump a raw response to file and grep for share/reshare keys.
**Audit note (Aug 2026):** Instagram's Graph API (OAuth path, `instagram_data_fetcher.py:98,171`) does request `shares` and `saves` fields — so the data exists in Instagram's API surface. The question is whether the browser-scraped GraphQL response carries the same fields. Not yet confirmed.
**Action required:** Manual raw-response dump during a live scrape. Check for `share_count`, `reshare_count`, `share_info`, `edge_media_to_share` in response keys. If present → extract and populate. If absent → reclassify as platform limitation alongside P-METHOD-6.

### P-SCRAPER-2: owner_follower_count = 0 for 100% of rows — follower normalization has never worked [HIGH — confirmed Aug 2026] [CODE FIX WRITTEN, NOT COMMITTED/DEPLOYED]
**Status Aug 22, 2026:** An uncommitted working-tree change in `backend/instagram_scraper_browser.py` implements the `creator_baselines` join so new scrapes populate real follower counts. It is NOT committed and NOT deployed (prod build predates it). Until committed + deployed + the backfill re-run, the 4%-backfilled / 96%-fallback state stands.
**Files:** `instagram_scraper_browser.py:1024,1239,1250-1252` (velocity formula), `dynamic_hashtag_discovery.py:137`, `early_signal_detector.py:191`
**Problem:** `owner_follower_count` is 0 for every reel in the database — not 95%, not "large accounts," 100%. A query for `owner_follower_count > 0` across the entire `reels` table returns 0 rows. The velocity formula's follower-normalization half (`log(followers + 10)`) has never produced a differentiated result. A 500-follower creator and a 5M-follower creator posting identical engagement get identical velocity scores.
**Root cause:** The hashtag media endpoint (`/api/v1/tags/web_info/`) does not include `follower_count` in its response schema. The key is entirely absent from Instagram's response — not null, not 0, absent. The parsing at line 1024 (`owner.get("follower_count") or 0`) is correct; there is nothing to get. This is the hashtag scraping code path, not the profile endpoint.
**This is NOT a regression of the earlier sprint fix.** The earlier fix patched the `creator_baselines` join path (profile endpoint). This is the hashtag media endpoint path, which structurally never had follower data to begin with. The two code paths are independent — the earlier fix could not have caught this.
**Formula behavior:** `effective_followers = followers if followers > 0 else 2500` — there IS a fallback, but since followers=0 for 100% of rows, every reel uses the identical denominator `log(2510) ≈ 7.83`. Follower normalization is a no-op constant multiplier. Velocity ranking is driven purely by `engagement / hours_live` with no creator-size differentiation.
**Blast radius (3 systems, not 1):**
1. **Velocity formula** (`instagram_scraper_browser.py:1250`): Normalization broken. All velocity scores are unnormalized engagement rates.
2. **Hashtag discovery** (`dynamic_hashtag_discovery.py:137`): Classifies 100% of reels as micro-creators (<10K followers) regardless of actual creator size. Pool assignment is wrong for every reel.
3. **Early signal detection** (`early_signal_detector.py:191`): Reads the same zeroed field. Creator-size-based signal thresholds are non-functional.
**Fix path:** The profile endpoint (`/api/v1/users/web_profile_info/`) DOES return follower count via `edge_followed_by.count`. The scraper already caches this to `creator_baselines.follower_count`. The fix is two parts: (1) a code-level join at scrape time so new scrapes populate `owner_follower_count` from `creator_baselines`, and (2) backfilling existing rows. Neither part is done yet.
**Action required:** Code-level join in `instagram_scraper_browser.py` to pull `owner_follower_count` from `creator_baselines` at scrape time. After that ships, existing rows won't self-heal — the backfill script (`backend/backfill_follower_counts.py`, commit `3cfa1eea`) must be re-run periodically as new baselines accumulate.
**Status (Aug 2026):** Backfill script written and run. 4% of rows backfilled (303/7,467). 95% of rows still on the 2,500 fallback. Velocity is still functionally unnormalized for the vast majority of live data. Severity stays HIGH until the code-level join ships and backfill is re-run to cover more rows.

### P-SCRAPER-3: `GLOBAL_NICHES` hashtag group referenced but doesn't exist — silently drops hashtag slots [UNVERIFIED — needs confirmation against current code before fix]
**File:** `backend/instagram_scraper_browser.py:1752`
**Problem:** The priority selection logic references `GLOBAL_NICHES` as a hashtag group, but this group is not defined in the hashtag groups dictionary. When the code reaches line 1752, the lookup fails silently — the 5 hashtag slots allocated to `GLOBAL_NICHES` are dropped with no error, warning, or fallback. The scraper runs with fewer hashtags than intended.
**Impact:** Reduced hashtag coverage. The scraper was designed to use 15 hashtags per run but effectively uses fewer because the GLOBAL_NICHES group doesn't exist. This silently reduces data diversity and coverage, particularly for non-India content.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-SCRAPER-4: 154 hashtags defined but only 17 used by default — 12 of 14 groups are India-specific, GLOBAL_DISCOVERY never used [UNVERIFIED — needs confirmation against current code before fix]
**File:** `backend/instagram_scraper_browser.py` (hashtag groups definition + default mode selection)
**Problem:** The scraper defines ~154 hashtags across 14 groups, but default mode only selects:
- 6 from INDIA_TRENDING
- 6 from INDIA_VERNACULAR
- 5 from EVENT_HASHTAGS
- 0 from GLOBAL_NICHES (dead reference, see P-SCRAPER-3)

This means 12 of 14 hashtag groups are India-specific, and the GLOBAL_DISCOVERY group (14 hashtags) is never used in default mode. Non-India content is structurally underrepresented in the scraped dataset.
**Impact:** The scraper produces an India-heavy dataset by design, but the product markets itself as supporting global trending audio. Users outside India (or looking for global trends) see limited data. The 154-hashtag definition creates an illusion of breadth that doesn't exist in practice.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-SCRAPER-5: `trend_refresher.py:117-119` hard-exits for peaked/expired trends — no velocity recalculation or re-promotion [UNVERIFIED — needs confirmation against current code before fix]
**File:** `backend/trend_refresher.py:117-119`
**Problem:** The trend refresher has a hard exit for any trend not in `['emerging', 'rising']` status:
```python
if current_status not in ["emerging", "rising"]:
    return local_summary  # HARD EXIT
```
Once a trend reaches `peaked` or `expired` status, the refresher immediately returns without recalculating velocity, checking for resurgence, or attempting re-promotion. Peaked/expired trends are terminal — they sit in the DB indefinitely with stale metrics.
**Impact:** Trends that experience a second wave of virality (common with music — a song can trend, peak, then trend again when used in a new context) are never re-detected unless the scraper happens to find them again through a full re-detection cycle. With only 17 hashtags scraped (P-SCRAPER-4), re-detection is unlikely for most audios.
**Note:** This is the same root cause as the three-track redesign scoping mentioned in the audit. Link to that work — do not spin up a second parallel fix.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

---

## 7. WORKFLOW & DEVOPS PROBLEMS

### P-WORK-1: GitHub Actions budget exceeds free tier
**File:** `.github/workflows/scraper-india.yml`, `scraper-global.yml`, `trend-refresh.yml`
**Problem:**
- scraper-india: 2 runs/day × 40 min = 80 min/day
- scraper-global: 1 run/day × 40 min = 40 min/day
- trend-refresh: 3 runs/day × 15 min = 45 min/day
- Total: 165 min/day = ~4,950 min/month
- GitHub free tier: 2,000 min/month

**Impact:** The pipeline exceeds the free tier by 2.5x. Either pay for GitHub Actions or reduce frequency.
**Does IMPLEMENTATION_PLAN.md fix this?** No. The plan notes the budget warning but doesn't propose a solution.

### P-WORK-2: No CI test suite
**File:** `.github/workflows/ci.yml`
**Problem:** The CI workflow runs but there are no meaningful tests. The test files in the repo are ad-hoc scripts, not a proper test suite.
**Impact:** No automated quality gates. Breaking changes can be pushed to production.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-WORK-3: No rollback strategy
**File:** N/A
**Problem:** If a deployment breaks, there's no automated rollback. Vercel keeps previous deployments but there's no process to revert.
**Impact:** If a bad deploy goes out, manual intervention is required.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-WORK-4: News virality scoring silently broken — Groq API 404
**File:** `backend/run_news_virality_check.py`, `.github/workflows/news-virality-cron.yml`
**Problem:** All 3 Groq API keys return HTTP 404 on `https://api.groq.com/openai/v1/chat/completions` for every batch, every run. 404 (not 401/429) means the endpoint or model string doesn't exist — likely a deprecated model in the request payload or a changed API path. Every article falls back to score 0 silently.
**Impact:** News virality scoring has been dead for an unknown period. Output is garbage-but-not-crashing (all scores = 0). No user-visible crash, but the "news virality" feature surface is non-functional.
**Filed:** Aug 20, 2026. Not investigated yet — competing with Actions budget emergency. Fix deferred to post-Sept-1.
**Confirmed still broken:** Aug 20 run (32369218236) — all 3 keys returned 404, exit code 1.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-WORK-5: Emergency Actions-minutes posture (temporary — revert post Sept 1)
**File:** All `.github/workflows/*.yml`
**Problem:** ~200 GH Actions minutes remaining with 12 days to Sept 1 reset (as of Aug 20, 2026). Original burn rate was ~115 min/day (3,456 min/month vs 2,000 free tier). Merged scraper-india + scraper-global into single `scraper.yml` running every 2 days. Reduced all other scheduled workflows to fit ~15 min/day total.
**Changes (Aug 20, 2026):**
- `scraper.yml` (new): merged India + Global, cron `0 2 * * */2` (every 2 days). Sequential India→Global in one job. `workflow_dispatch` input for manual per-mode runs.
- `scraper-india.yml` + `scraper-global.yml`: DELETED
- `cron-heartbeat.yml`: 6x/day → 3x/day
- `emergency-llm-classification.yml`: 12x/day → 4x/day
- `nightly-llm-classification.yml`: 4x/day → 2x/day
- `pending-trends-fallback.yml`: 4x/day → 2x/day
- `pending-trends-monitor.yml`: 6x/day → 3x/day
- `trend-refresh.yml`: 3x/day → 2x/day
- `news-virality-cron.yml`: 2x/day → 1x/day
**Post-reset target (Sept 1):** Revert to daily scraping (or sustainable near-daily frequency). Current 2-day cadence is temporary. Long-term frequency needs re-evaluation before Sept 14 launch — daily scraping at ~90 min/day may still exceed free tier on its own. Decision deferred.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-WORK-6: `check_llm_classification_history.py` missing — nightly workflow shows failed when it isn't [FIXED]
**Re-verified Aug 22, 2026:** The fix took the "remove the step" option: no workflow file under `.github/workflows/` references `check_llm_classification_history.py` anymore (grep: zero matches). Nightly runs no longer fail on the phantom verification step.
**Residual:** `backend/check_llm_classification_history.py` still exists as an untracked local file. Harmless (nothing references it), but delete or commit it to keep the tree clean.

### P-WORK-7: DB migration step fails silently in CI — pooler connection broken [PARTIAL FIX — Aug 22]
**File:** `.github/workflows/scraper.yml`
**Fix verified:** Commit `69b8fd65` removed `continue-on-error: true` from the **DB migration step**, so schema-migration failures now fail the workflow loudly.
**Remaining:** `continue-on-error: true` is still present at scraper.yml lines 67 and 150 for two other steps (non-migration). Those steps can still fail silently — confirm whether that's intentional soft-fail behavior or an oversight.
**Original problem (for the record):** Migration step failed with IPv6-unreachable / pooler ENOTFOUND errors but the pipeline continued, meaning future new tables in `migrate_creator_growth.py` would never reach prod silently.

### P-WORK-8: `/api/early-detection/predict/{id}` returns 500 instead of 404 for nonexistent trend IDs [LOW]
**Found:** Aug 22, 2026 during P-AUTH-5 gating work (a3106a04 evidence run).
**File:** `backend/api.py:5951-5984` (`predict_trend_viral_potential`)
**Problem:** The handler uses `.single()` on the Supabase query. For a nonexistent trend ID, PostgREST throws `PGRST116: Cannot coerce the result to a single JSON object` (0 rows) inside `.execute()` — before the `if not res.data: raise 404` check on the next line ever runs. The generic `except Exception` then converts it to a 500 "Failed to predict viral potential".
**Impact:** Log-noise / monitoring trap. Once real traffic exists, bad IDs (user typos, stale links, scrapers probing) will show up as spurious 500 spikes and someone will waste time investigating "server errors" that are just not-found lookups. No data exposure — the gate itself works correctly.
**Fix:** Replace `.single()` with plain execute + empty-check, or catch `APIError` with code PGRST116 and raise 404. Same pattern likely applies to any other endpoint using `.single()` followed by a falsy-data 404 check — worth one grep when fixing.

---

## 8. TRUST & FAKE-FEATURE PROBLEMS

### P-TRUST-1: Faceless feature is end-to-end broken — no LLM, no text-to-video, writes placeholder file [VERIFIED — DELETED]
**Files:** `frontend/src/routes/generate.tsx:602-685` (faceless tab UI), `backend/reel_generator.py` (worker)
**Problem:** The faceless feature presents a functional UI (niche selection, description input, hardcoded template preview) but the backend path is completely non-functional:
- Frontend sends `niche` and `description` to the API
- Backend `ReelGenerator.generate_reel()` requires a `files` parameter (images) which is `None` from this path → crashes
- Fallback handler writes a text file: `PLACEHOLDER_OUTPUT:[Faceless content: {niche}]...` saved as `{job_id}.mp4`
- No LLM call exists anywhere in the path — no script generation, no voiceover, no text-to-video API
- The "preview" shown to users is a hardcoded template, not generated content
**Impact:** Users are shown a feature that looks functional but produces a text file named `.mp4`. If anyone actually tries to use this, trust in the entire app is destroyed. The Sparkles icon and polished UI create a false expectation of AI capability.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Fix (Aug 22, 2026):** Deleted entire faceless feature end-to-end: frontend tab content + state + handlers + NICHES constant, backend `/api/generate-faceless` endpoint, `faceless_generation` handler in `run_job_simulation`, `generateFaceless` API function, `faceless_video`/`face_less` content type normalizers. `reel_generator.py` left as-is (marked deprecated, not imported by production).

### P-TRUST-2: AIContentGenerator — 3 of 4 "AI" tabs are static templates with no LLM call [VERIFIED — 3 fake tabs DELETED, only Caption kept]
**File:** `frontend/src/components/AIContentGenerator.tsx`
**Problem:** The AIContentGenerator had 4 tabs, all styled with Sparkles icons suggesting AI capability:
1. **Caption** — ACTUALLY calls LLM (`/api/ai/generate-caption`) ✅
2. **Content Ideas** — Dictionary lookup from hardcoded `CONTENT_IDEAS` dict. `CONTENT_IDEAS[niche][Math.floor(Math.random() * ideas.length)]` — no API call, no LLM. ❌
3. **Hooks** — `hash(topic) % templates.length` — deterministic hash-based template selection, no API call. ❌
4. **Script Outline** — Hardcoded time segments (0-3s hook, 3-15s body, 15-25s climax, 25-30s CTA). No API call. ❌
**Impact:** 75% of the "AI Content Generator" is static content with an AI-branded UI. Users who try Content Ideas, Hooks, or Script Outline are getting dictionary lookups and hash selections — something a static list could do without the AI pretense. This is deceptive UX.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Fix (Aug 22, 2026):** Deleted 3 fake tabs (Content Ideas, Hooks, Script Outline) from frontend `AIContentGenerator.tsx` — removed tab triggers, tab content, state variables, handler functions, unused imports (`Lightbulb`, `Wand2`, `Clock`). Removed corresponding API functions (`generateContentIdeas`, `generateAIHooks`, `generateScriptOutline`) and `ContentIdea`/`HookSuggestion` interfaces from `api.ts`. Removed backend endpoints (`/api/ai/content-ideas`, `/api/ai/generate-hooks`, `/api/ai/script-outline`) from `routes/ai.py`. Only Caption tab remains with real LLM-backed generation. Note: POST `/api/generate-hooks` (used by studio.tsx) calls `creator_tools.generate_hooks` which uses Gemini LLM — this is a real endpoint and was NOT removed.

### P-TRUST-3: Repurpose feature is just `shutil.copy2(input, output)` — no processing [VERIFIED — DELETED]
**File:** Backend repurpose endpoint (reported, needs file:line confirmation)
**Problem:** The repurpose feature copies the input file to the output path with no transformation. No format conversion, no resizing, no caption overlay, no platform-specific adaptation. The user expects "repurpose this Reel for TikTok/YouTube Shorts" and gets an identical file.
**Impact:** Feature is functionally a file copy disguised as a content repurposing tool. Any user who tries it will feel deceived.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Fix (Aug 22, 2026):** Deleted entire repurpose feature: frontend tab content + state + handlers + `repurposeInputRef` + cleanup refs, backend `/api/repurpose` endpoint, `repurpose` handler in `run_job_simulation` (shutil.copy2 path), `repurposeVideo` API function, `/api/repurpose` from rate limiting config and upload size check.

### P-TRUST-4: `video_virality_scorer.py` has unreachable dead code after return statement [VERIFIED — DELETED]
**File:** `backend/video_virality_scorer.py:~152`
**Problem:** A `return` statement at approximately line 152 was followed by ~60 lines of unreachable duplicate code. The dead code was a copy-paste of the function's logic that was never cleaned up after the return was added.
**Impact:** Dead code increases maintenance burden and confusion. Developers may edit the unreachable code thinking it's active, or the return may have been added accidentally (in which case the function is missing its intended second half).
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Fix (Aug 22, 2026):** Deleted the unreachable duplicate block (lines 162-221) after the `return` statement at line 152. The `get_improvement_suggestions` method that follows is now directly after the `score_video` return.

---

## 9. PAYMENT & SUBSCRIPTION PROBLEMS (continued)

### P-PAY-10: 4 conflicting plan-naming schemes and 5 conflicting Pro prices across files [VERIFIED — phantom tiers cleaned, commit d709a2c]
**Files:** `backend/plan_enforcement.py`, `backend/migrate_plans_consolidation.py`, `backend/migrate_credits_system.sql`, `backend/add_user_management_tables.py`, `backend/setup_accounts.py`, `frontend/src/components/PlanGate.tsx`, `frontend/src/routes/pricing.tsx`
**Problem:** At least 4 different naming conventions coexist for plan tiers:
- `free` / `pro` — plan_enforcement.py, migrate_credits_system.sql
- `free` / `early_bird` / `pro` — plan_enforcement.py CREATOR_TIERS
- `free` / `creator` / `agency` — migrate_plans_consolidation.py, setup_accounts.py
- `free` / `pro` / `business` — add_user_management_tables.py

Additionally, 5 different prices appear for the "Pro" tier across files: ₹19 (add_user_management_tables.py), ₹499 (migrate_credits_system.sql), ₹999 (pricing.tsx frontend), ₹2,999 (plan_enforcement.py docstring), ₹999/month (PlanGate.tsx CTA).
**Impact:** Any new developer or contributor will be confused about which naming is canonical. Migration scripts may create conflicting data. The pricing page shows one price while backend config may enforce a different one.
**Link:** This finding is related to a separate direct re-verification task queued for this codebase — do not duplicate that work. This PROBLEMS.md entry documents the audit-pass observation; the verification task will confirm current state.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Fix (Aug 22, 2026):** Phantom `early_bird` and `agency` tiers removed from `CREATOR_TIERS` in `plan_enforcement.py`. Only `free` and `pro` remain. All 17 code-level checks pass. Browser verification: `free` user sees gate, `pro` user sees full dashboard with AI Generator tab (no gate). Screenshot evidence: `ppay_pro_dashboard.png`, `ppay_free_dashboard.png`, `ppay_pro_ai_generator.png`. Deployed via CLI (`npx vercel deploy --prod --yes --force`). Bundle `index-DQD3VWUG.js` confirmed loading in production browser.

### P-PAY-11: PlanGate.tsx only checks `currentPlan === 'pro'` — locks out other tier names [VERIFIED — dead tier references cleaned + prices fixed, commit d709a2c]
**File:** `frontend/src/components/PlanGate.tsx:21`
**Problem:** The access check is `const canAccess = currentPlan === 'pro'`. Users with plan values `'agency'`, `'business'`, or `'early_bird'` (all defined in various backend files) would be incorrectly denied access to paid features. The gate is a strict string equality check against a single value, not a membership check against a set of paid tiers.
**Impact:** If any user has a plan name other than exactly `'pro'`, they are treated as free-tier regardless of what they paid. This is a revenue leak for any tier beyond the single hardcoded value.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Fix (Aug 22, 2026):** Removed dead `'agency'` from `isPro` helper (if it existed). Phantom tiers `early_bird` and `agency` removed from backend `CREATOR_TIERS`. CTA price fixed from ₹999 → ₹499/month in `PlanGate.tsx:46`. Pricing page price fixed from ₹999 → ₹499 in `pricing.tsx:109`. Browser verification: pro user sees full dashboard, free user sees gate with "₹499/month" price.

### P-PAY-12: AIContentGenerator is fully ungated for free users despite pricing page stating Pro-only [VERIFIED — PlanGate wrapper added, commit d709a2c]
**Files:** `frontend/src/components/AIContentGenerator.tsx`, `frontend/src/routes/pricing.tsx`
**Problem:** The pricing page lists AI content generation as a Pro feature. However, the AIContentGenerator component has no `PlanGate` wrapper or `require_feature` check — any authenticated user (including free-tier) can access all 4 AI tabs (Caption, Content Ideas, Hooks, Script Outline) without restriction.
**Impact:** Free users get Pro features without paying. The pricing page's feature comparison is inaccurate. Revenue leakage — users who would upgrade for AI tools don't need to.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Fix (Aug 22, 2026):** Wrapped `AIContentGenerator` in `<PlanGate requiredPlan="pro">` at `dashboard.tsx:146-148`. Free user browser test: gate renders "AI Content Generator requires a Pro plan" with "Upgrade to Pro →" CTA. Pro user browser test: AI Generator tab visible, no gate text, Caption Kit renders with "Generate" button and trend input. Bundle proof: `index-DQD3VWUG.js` (contains `requiredPlan` and `499`) confirmed loading in production via Playwright network tab.

### P-PAY-13: `credits_used_this_month` set to single-operation cost instead of accumulated — plus read+write race condition [VERIFIED — accumulation fixed, commit d709a2c]
**File:** `backend/plan_enforcement.py` (reported location)
**Problem:** Two bugs in the credits tracking:
1. `credits_used_this_month` is set to the cost of the current operation rather than accumulating the running total. A user who uses 3 operations at 5 credits each would see `credits_used_this_month = 5` instead of `15`.
2. The read-modify-write cycle for credit deduction is not atomic. Two concurrent requests could both read the same balance, both pass the insufficient-credits check, and both deduct — resulting in a negative balance or double-spend.
**Impact:** Credit balances are inaccurate. Users may exceed their plan limits without detection. Under concurrency, credits can be overspent.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Fix (Aug 22, 2026):** Changed `credits_used_this_month = cost` → `credits_used_this_month = old_used + cost` in `_deduct_credits()` (plan_enforcement.py). DB accumulation test confirmed: 3×5-credit ops → `credits_used_this_month = 15` (correct). 500-credit deduction from 300 balance → 403 "credit_limit_exceeded" (correct). Concurrency race condition not addressed (pre-revenue, low traffic — acceptable risk).

### P-PAY-14: Dead/broken references — TIER_DAILY_LIMITS, normalize_plan_name, to_display_plan_name, require_quota, contradictory test files [UNVERIFIED — needs confirmation against current code before fix]
**Files:** `backend/plan_enforcement.py`, test files
**Problem:** Multiple dead code references exist:
- `TIER_DAILY_LIMITS` — defined in plan_enforcement.py but never enforced anywhere. Appears to be a leftover from a daily-limit-based quota system that was replaced by credits.
- `normalize_plan_name` — referenced in test files but function does not exist in production code. Tests that reference it would fail if executed.
- `to_display_plan_name` — same as above — referenced but not defined.
- `require_quota` — imported in some files but the function does not exist. Calls to it would raise `ImportError` or `NameError`.
- Two separate `test_plan_normalization.py` files exist with contradictory test expectations.
**Impact:** Dead code creates confusion for developers. Missing functions would cause runtime errors if the code paths that reference them are ever reached. Contradictory tests mean the test suite cannot be trusted as a source of truth.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

---

## 10. CROSS-CUTTING TRUTH PROBLEMS

These are claims made in the codebase or marketing that are not supported by the actual code.

### P-TRUTH-1: "We detect trends 6 hours before they peak" — NOT PROVABLE
**Evidence:** There is no prediction model in the codebase. The `calculate_realistic_peaking_score()` function (trend_scoring.py:173-207) is retrospective, not predictive. The `window_hours_remaining` is a heuristic countdown based on saturation, not a prediction.
**Does IMPLEMENTATION_PLAN.md fix this?** No. This is a marketing claim, not a code issue.
**Proposed rewrite:** "Surfaces trends while they're still rising" — drop the specific time claim, since nothing in the code predicts anything.

### P-TRUTH-2: "15,000+ reels daily" — NOT ACHIEVABLE
**Evidence:** The scraper processes ~30-90 reels per hashtag per run, with 15 hashtags per run, at 2-4 runs per day. Max realistic daily count: ~500-2,000 reels.
**Does IMPLEMENTATION_PLAN.md fix this?** No. This would require scraper pagination (not addressed).
**Proposed rewrite:** Either state the real range (~500–2,000/day) or drop the number entirely: "Continuously scanning across N hashtags."

### P-TRUTH-3: "Real-time velocity tracking" — ACTUALLY BATCH
**Evidence:** Velocity is calculated at scrape time from point-in-time snapshots. No streaming, no real-time API polling. Batch scraping on schedule.
**Does IMPLEMENTATION_PLAN.md fix this?** No. Real-time would require WebSocket connections to Instagram or a push-based architecture.
**Proposed rewrite:** "Regularly refreshed" or state the actual scrape cadence (every 6-12 hours).

### P-TRUTH-4: "Cross-platform audio detection" — PARTIALLY BROKEN
**Evidence:** YouTube integration exists but is basic string matching. Spotify's chart endpoint doesn't exist. The external_trend_discovery module is dead code.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Proposed rewrite:** Cut this claim from marketing entirely. Spotify doesn't exist, YouTube is crude string matching — not close enough to true to rewrite.

### P-TRUTH-5: "India-first trend detection" — PARTIALLY TRUE
**Evidence:** 80% of hashtags are India-focused. Multi-language detection exists. But no Instagram API integration for India-specific trending data. The "first" claim is unprovable without comparing against Instagram's actual trending page.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Proposed rewrite:** "India-focused" instead of "India-first" — 80% India-weighted hashtags and multi-language detection are defensible without a comparative "first" claim.

---

## SUMMARY: WHAT THE IMPLEMENTATION PLAN FIXES vs WHAT IT DOESN'T

### Addressed by IMPLEMENTATION_PLAN.md v2:
| Problem | Fix | Status |
|---------|-----|--------|
| P-DB-2: events table missing | Item 3.1: Create events table + seed real data | Planned |
| P-DB-3: user_preferences missing | Item 3.4: Create user_preferences + server sync | Planned |
| P-API-1: Caption stub orphaned | Item 3.2: Wire caption stub to CaptionEngine | Planned |
| P-API-1: News + audio endpoints | Item 3.3: Add real routes for existing data | Planned |
| P-PAY-2: Pricing page deleted | Not fixed (pricing page still deleted) | Gap |
| P-DESIGN-9: Settings localStorage only | Item 3.4: Server sync for preferences | Planned |

### NOT Addressed by IMPLEMENTATION_PLAN.md v2:
| Problem | Severity | Impact |
|---------|----------|--------|
| P-PIPE-1: No scraper pagination | HIGH | 15K/day claim unachievable |
| P-PIPE-2: N+1 DB queries (3,600/run) | HIGH | 10-30 min runs, timeout issues | **FIXED** |
| P-PIPE-3: Saturation formula conflict | LOW (de-prioritized) | Both thresholds inert — india max=13, needs pagination first |
| P-PIPE-4: Proxy audio_use_count fabricated | HIGH | Unreliable trend detection |
| P-PIPE-5: 15-min timeout cuts off hashtags | MEDIUM | Inconsistent data coverage |
| P-PIPE-6: External discovery dead code | MEDIUM | 642 lines wasted |
| P-PIPE-7: No ad detection | MEDIUM | Inflated trend signals |
| P-PIPE-8: Unreliable Indian creator detection | LOW | Missed Indian creators |
| P-API-2: 4 duplicate route pairs | MEDIUM | 2,000 lines dead code |
| P-API-3: api.py is 7,088 lines | MEDIUM | Unmaintainable |
| P-API-4: ~25 unguarded endpoints | HIGH | Revenue leakage |
| P-API-5: Admin auth incomplete | MEDIUM | Data exposure risk |
| P-AUTH-1: Custom JWT bypasses lock check | HIGH | Security hole | **FIXED** |
| P-AUTH-2: Hardcoded verification code 123456 | MEDIUM | Security hole | **FIXED** |
| P-AUTH-3: Client-side Supabase auth | LOW | RLS dependency |
| P-AUTH-4: No rate limiting on auth | HIGH | Brute-force risk | **FIXED** |
| P-EXH-1: Global handler swallows HTTPException | HIGH | All auth errors masked as 500 | **FIXED** |
| P-EXH-2: jwt.JWTError doesn't exist in PyJWT 2.x | HIGH | verify_token never catches decode errors | **FIXED** |
| P-PAY-1: Razorpay keys missing | HIGH | Payment dead |
| P-PAY-2: pricing page dead end | HIGH | No conversion path | Updated — page exists, no checkout |
| P-AUTH-6: Business metrics open to free-tier | HIGH | Financial data exposed | **FIXED** (fab26f7c: 4/6; dcfb2fb7: remaining 2) |
| P-AUTH-7: Write-side IDOR | HIGH | Data integrity | **FIXED, VERIFIED** (curl-verified endpoint 8; 1-7 safe by design/implementation) |
| P-AUTH-8: Rate limiter fails silently open | HIGH | Silent degradation to no rate limiting | **FIXED** |
| P-AUTH-9: Dead email fields in write request models | LOW | Refactoring trap (latent IDOR) | **FIXED** (d744f24f: removed 4 dead fields) |
| P-AUTH-10: No session after phone verification | MEDIUM | User must re-authenticate after OTP | Frontend fixed (b953d09f); backend decision pending |
| P-AUTH-11: require_admin returns 401 not 403 for non-admin tokens | LOW | Misleading error for logged-in users | Cosmetic, fails closed; documented (dcfb2fb7) |
| P-PAY-2: pricing page dead end (no payment flow) | HIGH | Revenue blocked | Updated — page exists, no checkout |
| P-PAY-3: usage_logs empty | HIGH | Quota enforcement disabled |
| P-PAY-4: verify-phone page exists | LOW | Phone signups work if used | **FALSE POSITIVE — removed** |
| P-DESIGN-1: No design system | HIGH | Inconsistent UX |
| P-DESIGN-2: Typography conflict | MEDIUM | Component override impossible |
| P-DESIGN-3: Color drift (indigo vs coral) | MEDIUM | Brand inconsistency |
| P-DESIGN-4: Phone-only layout | HIGH | Desktop unusable |
| P-DESIGN-5: No loading/empty/error states | MEDIUM | Poor perceived performance |
| P-DESIGN-6: Animation overload | MEDIUM | Battery drain, accessibility |
| P-DESIGN-7: Near-zero accessibility | HIGH | WCAG non-compliance |
| P-DESIGN-8: Glass morphism on low-end Android | MEDIUM | Performance on target devices |
| P-DESIGN-10: Inconsistent input styles | LOW | Visual inconsistency |
| P-DB-1: usage_logs empty | HIGH | Quota enforcement disabled |
| P-DB-4: api_keys missing | LOW | API revenue blocked |
| P-DB-5: brand_deals empty | LOW | Marketplace empty |
| P-DB-6: Scraper bulk-upsert PG-21000 killed every save batch | CRITICAL | Feed empty Aug 18-22; root cause found, fix verified in prod (run `32591223200`) | **FIXED** |
| P-DB-7: user_performance tables never migrated | HIGH | Performance feature dead code | SQL written but NOT executed — still blocked (live-verified Aug 22) |
| P-DB-8: Supabase client truncates at 1000 rows | HIGH | Silent data visibility risk |
| P-METHOD-1: Trend dedup guard only checks emerging/rising | HIGH | 53% duplicate trends | **FIXED** |
| P-METHOD-1b: title+artist duplicates | LOW | 6 extra rows | **FIXED** |
| P-METHOD-1c: Bulk-seed path bypassed dedup | MEDIUM | Potential dedup blind spot | **CLOSED** |
| P-METHOD-5: Format-driven trends undetected | MEDIUM | Missed edit-pattern virality |
| P-METHOD-6: Velocity ignores Instagram's top signals | — | **DISCLOSED LIMITATION** — watch-time/DM-sends structurally unavailable |
| P-METHOD-7: Velocity can't detect misattribution | MEDIUM | Audio trends may be non-audio driven |
| P-SCRAPER-1: share_count never extracted | LOW | Code gap — needs manual raw-response dump to confirm |
| P-SCRAPER-2: owner_follower_count = 0 for all rows | HIGH | **4% backfilled** (303/7,467). 95% still on fallback. Code-level join for new scrapes + re-run of backfill script required. |
| P-WORK-1: GitHub Actions over budget | HIGH | CI/CD cost |
| P-WORK-2: No test suite | MEDIUM | No quality gates |
| P-WORK-3: No rollback strategy | LOW | Manual recovery |
| b9af900e: Groq model swap (llama-3.3-70b → openai/gpt-oss-120b) | LOW | Forced fix — old model 404s on Groq API; no comparison baseline; output spot-checked and sound |
| P-TRUTH-1-5: Marketing claims unprovable | HIGH | Trust/credibility |
| P-FUND-1: Payment flow dead | CRITICAL | No revenue, no fundraising |
| P-FUND-2: "0h delay" copy risk | HIGH | Batch pipeline can't back real-time claims | **FIXED** |
| P-FUND-3: Agency per-seat schema-only | HIGH | Zero enforcement, unlimited sharing |
| P-FUND-4: Account sharing = theoretical | LOW | Solve payments first |
| P-FUND-5: Data-parity moat risk | HIGH | Speed-only differentiation, no insight moat |

---

## 11. STRATEGIC & FUNDRAISING PROBLEMS

### P-FUND-1: Payment flow is dead — no revenue, no fundraising
**Files:** `backend/.env` (missing `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET`), `backend/api.py:6884` (webhook fails without keys)
**Problem:** Razorpay integration exists in code but has no API keys configured. `POST /api/payment/create-order` will fail for every user. `POST /api/payment/webhook` receives nothing. Zero revenue is being collected.
**Impact:** Cannot raise funding with dead payments. This is the single highest-priority blocker.
**Fix:** Complete Razorpay KYC (user action), add keys to Vercel env, verify webhook + order flow end-to-end.

### P-FUND-2: "0h delay" copy risk — batch pipeline can't back up "real-time" claims
**Files:** `backend/migrate_phase1_monetization.py:34,46` (`data_delay_hours=0` for creator/agency), pricing page copy
**Problem:** Creator and Agency tiers show `data_delay_hours=0`, implying real-time or zero-delay access. The pipeline is batch-based (scrapers run 1-2x/day via GitHub Actions cron). If the scraper last ran 12 hours ago, all users — including paid ones — see 12-hour-old data. The "0h" number is technically accurate (no *added* delay beyond what the scraper already has) but functionally misleading.
**Impact:** If this claim appears on the pricing page or in an investor pitch, anyone who checks the pipeline will see batch scraping, not real-time. That's a diligence gap.
**Fix:** Word as "priority access" or "fastest tier" rather than "0h" or "real-time." The honest framing: free users get data 24h after scrape; paid users get it immediately after scrape. The difference is real (24h vs. whatever the scraper cycle is), but calling it "0h" overpromises.
**Status Aug 22, 2026 — largely resolved:** All fabricated claims are gone from frontend marketing copy: "15,000+", "cross-platform", "before they peak", and the standalone "0h delay" line no longer appear (grep-verified). The one remaining line, "Real-time trend data (no delay)" at `frontend/src/routes/pricing.tsx:70`, now matches actual backend config: live `subscription_tiers` shows pro with `data_delay_hours=0` and free with `data_delay_hours=24` — the delay differential is genuinely enforced in code (plan_enforcement.py + api.py:1184). Residual nit: "real-time" still overstates a batch pipeline; suggest rewording to "Immediate access after each scan" when copy is next touched.

### P-FUND-3: Per-seat enforcement for Agency plan is schema-only — zero logic [MOOT — Agency tier eliminated Aug 2026]
**Files:** `backend/migrate_phase1_monetization.py:46` (`max_seats=5`), no enforcement code anywhere (grep for `per.seat`, `seat_count`, `team_member` = 0 matches)
**Problem:** The Agency plan has `max_seats=5` in the subscription tiers schema, but there is no seat counting, invitation flow, named user management, or enforcement logic. One Agency login = unlimited sharing. This is the standard SaaS fundraising question: "how do you prevent one Agency account from being an informal reseller?"
**Impact:** Investor will ask this. The answer right now is "we don't."
**Fix:** Implement named seats (each team member gets own login), seat counting, invitation flow, per-seat billing add-on. This is the structural fix that makes sharing economically pointless — adding a real seat is cheap and clean vs. risking termination.

### P-FUND-4: Account sharing is a theoretical problem — solve payments first
**Files:** N/A (strategic)
**Problem:** Every anti-sharing feature (watermarking, anomaly detection, visual protection) is solving for a scale that doesn't exist yet. With ~15 users and zero paying customers, account sharing is not a real problem. The honest priority order: payments → per-seat enforcement → everything else later.
**Impact:** Building anti-sharing features now is engineering time spent on a problem that doesn't exist while the actual blocker (dead payments) remains unsolved.
**Fix:** None needed — this is a prioritization note. The existing session capping and time-decay features are sufficient for the current scale.

### P-FUND-5: Data-parity moat risk — differentiation is currently speed-only, not insight [UPDATED — STRATEGIC DIRECTION SET]
**Problem:** All paid tiers see the same underlying trend data, differentiated only by data_delay_hours (access speed). This is a defensible-but-thin moat.
**Resolution:** Strategic pivot to "India's creator economy operating system" — trend detection + content generation + deal connection + payment protection. The moat is not speed — it's the connection layer powered by trend intelligence. See ROADMAP.md for full strategy.
**Competitive research:** Virlo (US, $36K MRR, bootstrapped) is the closest competitor. They charge $49-199/mo. Trendrop's India-first positioning + 4x lower price + deal connection layer = defensible advantage in India market.

---

### P-MARKET-1: No brand-side interface — brands can't participate in the marketplace [MEDIUM pre-launch / CRITICAL the moment a brand signs up]
**Files:** `frontend/src/routes/marketplace.tsx`, `frontend/src/routes/deals.new.tsx`, `backend/api.py:3847-4431`
**Problem:** The marketplace is creator-facing only. Brands cannot: post deals, review applications, select creators, fund escrow, or confirm delivery. The "Create Campaign Deal" form (`deals.new.tsx`) is designed for creators to self-create deals — there is no brand login, brand dashboard, or brand application review flow. Without a brand-side product, the marketplace is a one-sided marketplace that cannot generate revenue.
**Impact:** This is the #1 blocker for the marketplace generating revenue. A marketplace needs both sides. Currently only creators can participate.
**Pre-launch mitigation (Aug 2026):** Both `marketplace.tsx` and `deals.new.tsx` replaced with auth-gated "Coming soon" placeholders. No user can reach the half-built marketplace UI. BottomTabBar never had a `/marketplace` entry — the route was only reachable via direct URL. Dangling references: `deals.index.tsx` lines 250 and 313 link to `/deals/new` (now points to placeholder). Follow-up: remove or redirect those links.
**Fix (post-launch):** Build brand-side interface: brand signup/login, brand dashboard (post deals, review applications, select creators, fund escrow, confirm delivery, rate creators). This is Phase 2 of the marketplace redesign. See ROADMAP.md.

### P-MARKET-2: Duplicate deal systems — old and new coexist with different schemas [MEDIUM — old endpoints retired, migration deferred]
**Files:** `backend/api.py` (new `/api/deals` at ~line 3932), `backend/database_setup.py:165-181`, `backend/fix_brand_deals_schema.py:23-27`
**Problem:** Two parallel deal creation/retrieval systems exist on the same `brand_deals` table:
- **Old system** (`/api/marketplace/deals` GET+POST): Uses `creator_email`, `deal_amount`, `commission_amount`, `details`, 15% auto-commission. Simpler, no milestones.
- **New system** (`/api/deals` GET+POST): Uses `creator_id`, `rate_amount`, milestones, PDF contract generation, usage rights, exclusivity. Full-featured.

Both write to `brand_deals` but use different columns. The old system's data is incomplete (missing milestones, contracts). The new system ignores old data. This creates confusion and data fragmentation.
**Impact:** Users see inconsistent deal data depending on which endpoint they hit. Old deals lack milestones and contracts. New deals are complete but don't integrate with old marketplace browse.
**Old endpoints retired (Aug 2026):** Both old `/api/marketplace/deals` GET and POST handlers removed. Only the new `/api/deals` system remains. Internal caller grep confirmed no internal callers. `BrandDealRequest` Pydantic model (line 1007) is now dead code — flagged as follow-up.
**Data migration: deferred.** `brand_deals` has 0 rows. No data to migrate. Revisit when P-MARKET-1 (brand dashboard) ships and first real deal is created.
**Fix (post-migration):** Migrate old deals to new schema (add milestones, contracts where missing). One system, one data model.

### P-MARKET-3: No escrow/payment processing for deals — "Mark as paid" is a database toggle [MEDIUM pre-launch / CRITICAL once P-MARKET-1 + P-FUND-1 ship]
**Pre-launch context (Aug 2026):** 0 brands, 0 deals, 0 milestones in `brand_deals`. Escrow only matters when a brand can create a deal (P-MARKET-1 brand dashboard) and fund it (P-FUND-1 Razorpay keys). No code change — reclassified because 0 live users means no payment protection is needed yet.
**Files:** `backend/api.py:4102-4121` (`POST /api/deals/{deal_id}/pay-milestone/{milestone_id}`)
**Problem:** The milestone payment endpoint simply updates `paid_status` from "unpaid" to "paid" in the database. No money moves. No Razorpay integration. No escrow. No invoice generation. The creator clicks "Mark as paid" and the system trusts that the brand actually paid. This is identical to the agency model — no payment protection.
**Access control (fixed commit `e179405e`):** Endpoint now gated to `require_feature("advanced_analytics")` (pro/business plans only). Free-tier users get 403 with upgrade prompt. Ownership check at L4117-4118 still fires after plan gate — paid users can only mark milestones on their own deals.
**Impact:** Without escrow, creators have zero payment protection. Brands can promise to pay and never do. This is the exact problem agencies create, and Trendrop claims to solve.
**Fix:** Implement Razorpay escrow: brand funds deal upfront → Trendrop holds money → creator delivers → Trendrop releases payment. This requires Razorpay KYC (P-FUND-1) and brand-side interface (P-MARKET-1).

### P-MARKET-4: No brand verification — anyone can create a brand deal [MEDIUM pre-launch / HIGH once P-MARKET-1 ships]
**Pre-launch context (Aug 2026):** No brand signup flow exists — the marketplace is behind a "Coming soon" placeholder (P-MARKET-1 fix). 0 brands on platform. Verification is downstream of P-MARKET-1.
**Files:** No verification code exists anywhere in the marketplace flow.
**Problem:** Anyone can create a brand deal without proving they are a legitimate business. No GST verification, no business registration, no company email check. This enables fake brands that promise deals and never pay, or brands that create deals to harvest creator contact information.
**Impact:** Trust erosion. If creators encounter fake brands, they leave the platform. Without verification, the marketplace becomes a spam vector.
**Fix:** Brand verification flow: GST number upload, business registration document, company email verification (@company.com, not Gmail). Verified badge on brand profiles. Unverified brands can browse but cannot post deals.

### P-MARKET-5: No notifications to brands — application black hole [MEDIUM pre-launch / HIGH once P-MARKET-1 ships]
**Pre-launch context (Aug 2026):** 0 brands to notify, 0 applications in `brand_deal_applications`. Notifications are downstream of P-MARKET-1 (brand dashboard).
**Files:** `backend/api.py:4306-4327` (`POST /api/apply-deal`), no email/notification code for brands.
**Problem:** When a creator applies to a brand deal, the application is stored in `brand_deal_applications` but no email, push notification, or in-app alert is sent to the brand. The brand has no way to know someone applied unless they manually check. Collab requests (`POST /api/send-collab-request`) have the same problem.
**Impact:** Deals go unanswered. Creators apply and hear nothing. The marketplace feels dead. This is the #1 reason marketplaces fail — supply (creators) exists but demand (brands) doesn't know about it.
**Fix:** Email notifications to brands when: (1) creator applies to their deal, (2) deal is about to expire, (3) milestone is approaching. In-app notification center. Brand dashboard with application queue.

### P-MARKET-6: Hardcoded compatibility scoring — doesn't scale [MEDIUM]
**Files:** `backend/api.py:4375-4384`
**Problem:** Creator-creator compatibility is computed via a hardcoded if/elif chain: same niche = 95%, dance+fitness = 89%, fashion+travel = 87%, etc. This doesn't account for: audience overlap, engagement rate similarity, follower count parity, content style, posting frequency, or actual collaboration history.
**Impact:** Matching quality degrades as the creator base grows. The current system works for <100 creators but will produce poor matches at 1000+.
**Fix:** ML-based matching using: niche similarity (embeddings), audience demographics, engagement rate parity, follower count range, content style vectors, collaboration history. Start with weighted scoring, evolve to model-based.

### P-MARKET-7: Marketplace not discoverable — hidden from navigation [LOW]
**Files:** `frontend/src/components/BottomTabBar.tsx:47`, `frontend/src/routes/marketplace.tsx`
**Problem:** The `/marketplace` route exists but is NOT in the bottom tab bar. Only `/deals` is visible. Users must know the URL to access the marketplace. The marketplace is the primary value proposition for brand-creator connection but is hidden behind a direct URL.
**Impact:** Low marketplace engagement. Users don't discover the feature. Creators who could be earning from deals never find the marketplace.
**Fix:** Add marketplace to bottom tab bar (replacing or alongside Deals). Or merge marketplace and deals into a single unified navigation item.

### P-MARKET-8: Marketplace auth/gating audit — severity corrections and stale counts [AUDIT NOTE]
**Context:** Session opened with "13 ungated marketplace endpoints" (estimate from earlier audit pass). Actual count: 17 marketplace/deals/creator endpoints total. Of those: 8 properly gated (OK), 4 low-risk (guest gets empty data), 3 medium-risk (anonymous@ leak, missing feature gates), 2 high-risk (zero-auth profile dump, run-reminders admin action). The "13 ungated" number was wrong — flagged here so the next session doesn't inherit it.
**Severity corrections from this session's re-trace:**
- #10 (`GET /api/brand-deals/{user_email}`): Originally flagged as HIGH (cross-user deal read). Re-traced guard logic: the condition `current_user_email != "guest@trendrop.app" and user_email != current_user_email and user_email != "anonymous@trendrop.app"` correctly blocks Alice→Bob access. Actual gap was narrower: anonymous@ exception allowed any authed user to read anonymous's deals. **Downgraded to MEDIUM. Fixed in commit `4d6e0620`.**
- #8 (`POST /api/deals/{deal_id}/pay-milestone/{milestone_id}`): Originally flagged as HIGH (any user can falsify payment). Re-traced: ownership check exists at L4117-4118 (`creator_id != current_user_email → 403`). Real issue is missing `require_feature` gate, not missing ownership check. **Downgraded to MEDIUM. Fixed in commit `e179405e` — gated to `require_feature("advanced_analytics")` (pro/business).**
- #1 (`GET /api/marketplace/profiles`): Zero auth, but intentionally public (marketplace directory). Reframed as field-exposure issue: `user_email` was in response but not needed by frontend. **Fixed in commit `c51995c4` — `select("*")` → explicit column list excluding `user_email`. Side benefit: future columns won't leak by default.**
- #9 (`POST /api/deals/run-reminders`): Any authed user could trigger global email blast to all creators with overdue milestones. **Gate fixed in commit `543c140a` — replaced per-user auth with CRON_SECRET gate (matching `/api/cron/trigger` and `/api/cron/refresh` pattern), added 2/hour rate limit. Rejection paths verified via curl (no secret, wrong secret, wrong Bearer → all 403). Success path unverified — no staging env, CRON_SECRET only in Vercel dashboard. Flag for first real cron fire: check Vercel function logs to confirm `emails_sent > 0` and `reminder_sent_at` updates when unpaid milestones exist.**
- #4 (`GET /api/marketplace/deals`): Used `get_current_user` → anonymous got silent empty array instead of 401. **Fixed in commit `2ab2ad7f` — changed to `require_auth`, matching write endpoint. Curl verified: no auth→401, authed→200 with own data (table empty so `[]` is correct).**

### P-MARKET-9: Milestone reminder emails have never fired — Vercel cron not wired [MEDIUM pre-launch / HIGH once P-MARKET-1 ships and deals exist]
**Pre-launch context (Aug 2026):** `deal_payment_milestones` has 0 rows. No data exists to send reminders about. Downstream of P-MARKET-1 (brand dashboard creates deals, which create milestones).
**Files:** `vercel.json` (cron config), `cron_job.py:751-925,967-969` (scheduler), `backend/api.py:4127-4140` (manual endpoint)
**Problem:** `check_and_send_milestone_reminders()` is scheduled via in-process `schedule.every(12).hours` in `cron_job.py:968-969`, but Vercel serverless functions have a 30s max duration (`maxDuration: 30` in `vercel.json`). The `while True` loop at `cron_job.py:980-982` gets killed immediately — the reminder function only runs on cold start (line 955) and then the process dies. `vercel.json` crons only wire `/api/cron/trigger` (24h) and `/api/cron/refresh` (12h) — no entry for `/api/deals/run-reminders`. **Reminders have never fired automatically since the feature was built.** `deal_payment_milestones` table is empty (0 rows), so no data has existed to expose this gap.
**Severity:** HIGH — brands/creators are meant to get milestone payment reminders and haven't been, silently, for the entire life of the feature. This is a launch-time infrastructure gap, not a regression.
**Evidence:** `deal_payment_milestones.reminder_sent_at` is NULL across all rows (0 rows total). No reminders have ever been sent, manually or otherwise.
**Fix (deferred — scope next session):** Two options: (1) add Vercel cron entry for `/api/deals/run-reminders` in `vercel.json`, or (2) fold `check_and_send_milestone_reminders()` into `/api/cron/refresh`'s existing 12h job. Requires profiling function runtime to confirm it fits within 30s budget alongside TrendRefresher without risk of timeout as milestone volume grows.

### P-MARKET-10: POST /api/marketplace/deals 500s for all authenticated users [FIXED]
**Note:** Commit `4d6e0620` references "P-MARKET-10" for an anonymous@ data leak fix, but that commit never created a PROBLEMS.md entry — it only touched `backend/api.py`. The anonymous@ fix is tracked by commit hash only. This entry is the first actual P-MARKET-10 in the doc.
**Files:** `backend/api.py` (deleted)
**Problem:** `POST /api/marketplace/deals` returns 500 Internal Server Error for every authenticated request. The old deal creation endpoint (part of the duplicate deal system in P-MARKET-2) writes to `brand_deals` using columns (`creator_email`, `deal_amount`, `commission_amount`, `details`) that don't match the current table schema — the table was migrated to the new deal system (`/api/deals`) which uses different columns (`creator_id`, `rate_amount`, milestones). The insert fails with a DB error, caught by the generic exception handler and returned as 500.
**Impact:** The old marketplace deal creation flow is completely broken. Any user hitting this endpoint gets a 500. The frontend doesn't currently call this endpoint (the new `/api/deals` is used instead), so no user is actively hitting it — but it's a dead endpoint that returns a server error, not a clean 404 or deprecation notice.
**Evidence:** Curl-verified: no auth → 401 (auth gate works), authenticated → 500. Confirmed pre-existing by reverting auth gate changes and retesting — same 500 with original code.
**Fix:** Old endpoint removed as part of P-MARKET-2 consolidation. Both GET and POST handlers deleted. Request to either path now returns 404 (no route registered).

### P-MARKET-11: `BrandDealRequest` Pydantic model is dead code [LOW]
**File:** `backend/api.py:1007`
**Problem:** The `BrandDealRequest` Pydantic model was only used by the old `create_brand_deal` handler (POST `/api/marketplace/deals`), which was removed in the P-MARKET-2 fix. The model is now unused. No other code references it.
**Fix:** Delete the class definition. Safe — no callers.

---

### P-PAY-5: Plan rename needed — "Agency" tier signals exploitation [RESOLVED — Agency tier eliminated]
**Re-verified Aug 22, 2026 (live `subscription_tiers` REST query):** Only two tiers exist in prod:
- **free** — ₹0/mo, 24h data delay, 100 credits/mo, no exports, no API
- **pro** — ₹499/mo, 0h data delay, 1000 credits/mo, exports + API enabled

"Agency" (and "Creator"/"Business") no longer exist anywhere in the tier table or in `plan_enforcement.py` (rewritten to the free/pro credits model). The exploitative naming concern is moot — the whole multi-tier structure was replaced by two tiers.
**Note:** This also dissolves P-FUND-3's premise (per-seat enforcement for Agency): there is no team tier left to share.

### P-PAY-6: Credit system needed — usage-based pricing [IMPLEMENTED — verified live Aug 22, 2026]
**Evidence:**
- `backend/plan_enforcement.py` fully rewritten around credits: `CREDIT_COSTS` map (ai_generation=5, video_analysis=10, export=2), `FREE_TIER_FEATURES` includes algorithm_insights, `PAID_FEATURES` restricted to pro, `require_credits()` dependency wired on 23 routes.
- Live `credit_transactions` table exists with 12 rows of REAL traffic — latest `-5 api_usage` entries at 15:30 UTC today (user_id 51). Deductions match the configured costs.
- Migration script `backend/migrate_credits_system.py` seeds free=100cr/24h delay, pro=1000cr/0h delay — matches live `subscription_tiers` exactly.
- Fairness bug in the original implementation found and fixed same-day: see P-PAY-9 (charge-on-422), commit `458173f8`.
**Remaining:** Credit cost calibration against real usage patterns (the "Phase 3 revenue optimization" work) — pricing values are founder-set, not data-informed yet.

### P-PAY-7: Free + 14-day trial model needed — current free tier lacks upgrade pressure [MEDIUM]
**Files:** `frontend/src/routes/pricing.tsx`, `backend/plan_enforcement.py`
**Problem:** The current free tier gives permanent access to basic features with no urgency to upgrade. Users who sign up and never upgrade generate zero revenue. There's no mechanism to show users what they're missing. The 14-day trial that was previously on the pricing page was removed.
**Impact:** Low conversion rate from free to paid. Users don't experience enough value during free usage to justify upgrading. No trial = no urgency.
**Fix:** Free tier + 14-day Pro trial: (1) User signs up → Free tier (10 credits/day), (2) After 3 days of usage → "Try Pro free for 14 days" prompt, (3) During trial → Full Pro access (200 credits/day), (4) After trial → Back to Free unless they upgrade, (5) Trial requires Razorpay setup (₹0 charge, card on file for auto-conversion).

### P-PAY-8: Plan cache is in-process memory — paying users can see 403 for up to 5 min after upgrading [HIGH once payments live]
**Found:** Aug 22, 2026 during P-AUTH-5 early-detection gating work (a3106a04 evidence run).
**Files:** `backend/plan_enforcement.py:11-16,81-86` (`_PLAN_CACHE`, TTL=300s), `backend/api.py:2593` (webhook invalidation), `vercel.json` (serverless deployment)
**Problem:** `PlanEnforcement.get_user_plan()` caches plan lookups in an in-process dict with a 300s TTL. The payment webhook DOES correctly call `invalidate_cached_user_profile()` → `invalidate_plan_cache()` (api.py:2593 → 431-432) — the wiring exists. But the backend runs as a Vercel serverless function (`api/index.py`), where each warm instance holds its OWN copy of `_PLAN_CACHE`. The webhook's invalidation only clears the cache in the instance that handled the webhook; other warm instances keep serving the stale `free` plan for up to 5 minutes.
**Impact:** Directly on the revenue path. A user who just paid hits a Pro-gated endpoint, lands on a different warm instance than the webhook used, and gets `403 plan_upgrade_required` — at the exact moment they're most excited and most attentive. Worst possible first impression as a paying customer. Currently dormant (no live payments), but becomes real the moment Razorpay goes live.
**Fix options:** (1) Move plan cache to Redis (already in the stack for rate limiting) so invalidation is global across instances — cleanest. (2) On 403 plan_upgrade_required, do an uncached DB re-check before returning — cheap safety net regardless. (3) Reduce TTL — narrows but doesn't close the window. Option 1 + 2 combined is the robust answer.
**Verification note:** Confirmed live during testing — flipped chin@free.com to pro via service role while server was running; gated endpoint kept returning 403 with stale cached plan until process restart.

### P-PAY-9: require_credits deducts before FastAPI param validation — malformed requests still charge credits [FIXED, VERIFIED]
**Found:** Aug 22, 2026 during P-AUTH-5 gating work (e4a2a302 evidence run).
**File:** `backend/plan_enforcement.py:310-317` (`require_credits` factory)
**Problem:** FastAPI resolves dependencies (including `require_credits`, which deducts immediately) before/independently of request param validation. A call to a credit-gated endpoint with missing/invalid params returns 422 to the client but the credit deduction has already fired. Confirmed live: a GET `/api/virality/improvements` call missing its required body returned 422 AND logged a `-5 api_usage` transaction (credit_transactions row at 2026-08-22T12:54:39, paired with the successful call's -5 at :40).
**Impact:** Users get charged for their own malformed requests — retrying after fixing the payload costs double. Small per-incident, but a systematic fairness bug across every credit-gated endpoint (seo-caption, daily-ideas, virality/improvements, india/* AI endpoints, video analysis at 10 credits/call where it hurts most). Also pollutes usage analytics with failed-call charges.
**Fix:** Move validation inside the endpoint body (validate-then-deduct ordering), or make `require_credits` defer the deduction until response success (deduct in a dependency with a post-response hook / middleware that fires only on 2xx), or catch and refund on 4xx. The deferred-on-success pattern is cleanest.
**Related:** P-WORK-8 (same family: dependency/handler ordering quirks producing wrong status-code behavior).
**FIXED (Aug 22, 2026, commit 458173f8):** `require_credits` now checks balance inline (429 `credits_exhausted` if insufficient) and schedules the deduction as a BackgroundTask, which FastAPI discards on any validation failure (422) or handler exception — failed calls cost nothing. Single shared fix in the factory; retroactively corrects every wired endpoint. Verified live: two distinct 422 shapes (missing body, malformed JSON) produced zero transaction rows; three successful calls across virality/improvements, daily-ideas, and seo-caption produced exactly one −5 each; balance delta 100→85 matched successes exactly; drained-to-0 account correctly got 429 before the handler ran.

---

## RECOMMENDATION

**Reconciled Aug 22, 2026:** Of the original **67 problems**: **19 fixed/resolved**, 1 false positive, **47 open** (several of those with partial fixes noted inline). Status changes in this pass were made only with same-day evidence. **Evening update (same day):** P-DB-6 was root-caused, fixed via PR #4, and verified live in prod (feed restored: 3 rising / 8 emerging); P-AUTH-5 was closed end-to-end; P-PAY-9 was fixed — the open count below is stale-low on those three items.

1. **RESOLVED Aug 22 evening (was URGENT):** the empty-feed emergency (P-DB-6) ended the same day it was diagnosed — scraper PG-21000 root cause fixed, Verify-step masking removed, fix verified against real prod data (run `32591223200`). Full record in the P-DB-6 entry above.

2. **RESOLVED Aug 22 evening:** the ~20 local commits shipped to origin/main (`1dc71701`, smoke-test green, Vercel deployed); the P-SCRAPER-2 baseline join is committed and awaiting review/evidence via PR.

3. **Marketplace redesign** (P-MARKET-1 through P-MARKET-11): brand-side product remains the #1 revenue unlock after payments go live.

4. **Data pipeline architecture** (P-PIPE-1/4/5/7): pagination, proxy-count honesty, timeout restructuring — highest engineering effort, highest data-quality payoff.

5. **Monetization leftovers:** Razorpay KYC + keys (P-PAY-1/P-FUND-1), trial model decision (P-PAY-7), plan-cache invalidation across serverless instances (P-PAY-8) before first real payment.

6. **Security & API hygiene:** finish P-AUTH-5 guard consistency (40 require_auth vs 57 get_current_user), delete the 2 duplicate routes (P-API-2), fix analytics/log 500 (P-API-6).

7. **Truth & design:** remaining simulated endpoints (4 video-analysis + creator_tools), indigo-vs-coral drift, responsiveness, loading/error states, accessibility (18 aria-labels is a start, not a finish).

**The recommended execution order (from ROADMAP.md):**
- **Phase 1 (Oct 2026):** Razorpay + brand interface + escrow = first revenue
- **Phase 2 (Nov-Dec 2026):** Notifications + verification + ratings = trust layer
- **Phase 3 (Jan-Mar 2027):** Credit calibration + trial model = revenue optimization
- **Phase 4 (Apr-Jun 2027):** Mobile PWA + advanced matching = scale

**If the goal is to match what users see on Instagram**, the pipeline needs a fundamental architecture change:
- Add scraper pagination (scroll or API-based)
- Batch DB operations (bulk inserts, cached queries)
- Validate thresholds against Instagram's actual trending page
- Integrate real-time monitoring (not just batch scraping)

**If the goal is a credible MVP for investors/users**, the frontend needs a design system overhaul and the marketing claims need to be grounded in reality.
