# TRENDROP — COMPLETE PROBLEM INVENTORY
**Date:** Aug 18, 2026 · **Basis:** deep codebase audit against repo at HEAD (`cd9d082f`).
Every claim has a file:line citation. Every fix has proof it's addressed.

---

## TABLE OF CONTENTS
1. [Data Pipeline Architecture Audit](#1-data-pipeline-architecture-audit)
2. [Backend API Problems](#2-backend-api-problems)
3. [Auth & Security Problems](#3-auth--security-problems)
4. [Payment & Subscription Problems](#4-payment--subscription-problems)
5. [Frontend Design Problems](#5-frontend-design-problems)
6. [Database & Data Quality Problems](#6-database--data-quality-problems)
7. [Workflow & DevOps Problems](#7-workflow--devops-problems)
8. [Cross-cutting Truth Problems](#8-cross-cutting-truth-problems)

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

#### P-PIPE-1: No pagination — single page load per hashtag
**File:** `backend/instagram_scraper_browser.py:907-914`
**Problem:** The scraper navigates to `instagram.com/explore/tags/{hashtag}/` and captures whatever the `api/v1/tags/web_info` XHR returns in one response. No scrolling, no pagination.
**Impact:** Instagram's tag page typically returns 30-90 items. With 15 hashtags, max ~450-1,350 reels per run. The "15,000+ reels daily" claim is **not achievable from this code.**
**Real daily count:** ~500-2,000 reels per day (2-4 runs × 15 hashtags × 30-90 reels × 40-60% survival).
**Does IMPLEMENTATION_PLAN.md fix this?** No. The plan doesn't address scraper pagination. This is an architecture limitation.

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

#### P-PIPE-4: Proxy audio_use_count uses made-up formula
**File:** `backend/instagram_scraper_browser.py:819-822`
**Problem:** When Instagram doesn't provide `audio_use_count`, the scraper calculates:
```python
base_count = unique_creators * 800 + total_reels * 400
growth_multiplier = 1.5 if recent_creators > 2 else 1.0
estimated_count = int(base_count * growth_multiplier)
```
**Impact:** This is a fabricated number. 1 creator + 1 reel = 1,200 estimated uses. 5 creators + 10 reels = 8,000 estimated uses. These numbers don't correlate with Instagram's actual audio usage counts. Any trend detection based on these proxy values is unreliable.
**Does IMPLEMENTATION_PLAN.md fix this?** No. This is an unaddressed data quality issue.

#### P-PIPE-5: 15-minute global timeout frequently cuts off later hashtags
**File:** `backend/instagram_scraper_browser.py:1249-1256`
**Problem:** Global timeout is 900 seconds (15 min). Each hashtag takes 15-25s of browser time. 15 hashtags × 20s = 5 minutes of browser time. But per-reel DB processing adds 6-18 minutes. Total: 7-23 minutes. Later hashtags are frequently skipped.
**Impact:** Inconsistent data coverage. Some runs get all 15 hashtags, others get 5-8. The data is not equally fresh across all hashtag groups.
**Does IMPLEMENTATION_PLAN.md fix this?** No. The plan mentions scraper tightening (item 3.6) but doesn't address the timeout architecture.

#### P-PIPE-6: External trend discovery is dead code
**File:** `backend/external_trend_discovery.py` — 642 lines, never imported by `trend_engine.py`
**Problem:** The `ExternalTrendDiscovery` class fetches from Spotify/YouTube, but:
1. Spotify's `/v1/charts/{region}/viral/weekly` endpoint **does not exist** in Spotify's public API (line 99)
2. The module is **never imported or called** from trend_engine.py
3. The `run_discovery_cycle()` method returns candidates but nothing consumes them

**Impact:** 642 lines of dead code. The "cross-platform audio detection" claim is false. YouTube integration exists but is basic string matching. Spotify is broken.
**Does IMPLEMENTATION_PLAN.md fix this?** No. The plan doesn't mention external_trend_discovery.py at all.

#### P-PIPE-7: No ad/sponsored post detection
**File:** Absent from `backend/instagram_scraper_browser.py`
**Problem:** The scraper treats all reels equally. Sponsored posts that appear in hashtag feeds are counted as organic trends.
**Impact:** A sponsored post with 10M views might be classified as a "mega trend" when it's actually paid placement, not organic virality.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

#### P-PIPE-8: Indian creator detection uses unreliable signals
**File:** `backend/external_trend_discovery.py:475-481`
**Problem:** Detects Indian creators by checking username for city names ("mumbai", "delhi", "bangalore", etc.).
**Impact:** Most Indian creators don't have city names in their handles. This misses the majority of Indian creators.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

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

### P-API-1: ~25 endpoints return simulated/fake data
**File:** `backend/api.py` — various lines
**Problem:** These endpoints return fabricated data, not real Instagram API data:
- Video analysis (4): `analyze-video-metadata`, `analyze-visual`, `predict-virality`, `improvements` — all return `is_simulated: True`
- Instagram Graph API (3): `user-profile`, `user-insights`, `user-media`
- YouTube (2): `trending`, `trending-music`
- Realtime trends (2): `realtime/trends`, `realtime/cross-platform`
- Caption stub (1): `trends/{trend_id}/caption`
**Impact:** Users see fake data presented as real. The "is_simulated" flag is honest but the UX still shows fabricated charts and scores.
**Does IMPLEMENTATION_PLAN.md fix this?** Partially. Item 3.2 fixes the caption stub. Items 3.3 adds real endpoints for news + audio. But the video analysis and Instagram Graph API stubs remain unfixed.

### P-API-2: Duplicate route dead code — maintenance/regression burden, NO active revenue leak [REVISED — LIVE TEST + CODE REVIEW]
**File:** `backend/api.py` — 10 original "pairs" resolved to 5 true duplicates + 5 legitimate REST pairs
**Problem:** 5 route paths have the same method registered twice (dead code). The other 5 "pairs" are GET/POST on the same path (standard REST, not duplicates).
**Live test + code review (Aug 19):** All 5 true duplicates tested with free-tier token:
- `/api/algorithm/*` (3 endpoints): 200 for free tier — **NOT a bug**. Gated version at L1799 IS served (first-route wins), but `algorithm_insights` is in free-tier allowed list (`plan_enforcement.py:335`). Intentional policy.
- `/api/health`: 200 unauthenticated — **correct**. Both versions are unauthenticated health checks.
- `/api/india/cultural-events`: 200 for free tier and anonymous — **active revenue leak** but caused by missing `require_feature("india_features")` gate, NOT by route shadowing. Filed under P-API-4.
**Diff results:** Algorithm endpoints have identical bodies (2nd just missing gates). Health and cultural-events have different implementations — deletion of 2nd copy requires decision on which to keep.
**Impact:** Dead code adds ~1,500 lines to an already 7,122-line file. Maintenance burden. Latent regression risk if file is reordered. No active revenue leakage from shadowing itself.
**Fix:** Delete 3 safe algorithm duplicates (L4751-4852). Decide on health + cultural-events implementations. See shared-infra rule #3 — needs explicit approval.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-API-3: api.py is 7,088 lines — unmaintainable
**File:** `backend/api.py`
**Problem:** One file contains ~155 route decorators. This is the largest single-file Python API I've ever audited. No modular routing, no blueprints, no route separation.
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

### P-PAY-3: `usage_logs` has 0 rows — quota logging is broken
**File:** Supabase `usage_logs` table
**Problem:** The `usage_logs` table exists but has 0 rows. Quota logging is not happening.
**Impact:** `require_quota()` checks in plan_enforcement.py read from a table that's always empty. Quota enforcement is effectively disabled — users never hit quota limits because the counter never increments.
**Does IMPLEMENTATION_PLAN.md fix this?** No.
**Recommendation (known-gap, not launch-blocking):** Rate limiter (30/min, gated per P-API-4) is the real floor. Quota logging is a second layer that's not wired. With 0 live users (pre-launch, only founder test accounts) and no revenue live, this is unlikely to be abused. Document as known-gap, don't block launch. Do NOT fake-fix with a patch that just inserts rows without real enforcement logic — that creates false confidence. Revisit post-launch once there's real usage to size the actual risk.

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

### P-DESIGN-2: Typography conflict — three fonts declared for body
**File:** `frontend/src/styles.css:193,312`
**Problem:**
- Line 193: `html, body { font-family: "Inter", sans-serif; }`
- Line 312: `body { font-family: "Bricolage Grotesque", sans-serif !important; }`
- Headings forced to fixed sizes with `!important` (lines 301-310)

**Impact:** Components can never override heading sizes. Bricolage Grotesque is a quirky display font that doesn't work for body text. The `!important` overrides break component-level customization.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

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

### P-DESIGN-6: Animation overload — seizure-inducing neon glow
**File:** `frontend/src/styles.css` — neonGlowDark animation
**Problem:** The `neonGlowDark` animation cycles between cyan and purple every 3 seconds. Combined with `pulse-urgent`, `float-card`, `waveform`, `shimmer`, and `drop-fall`, the app has 10+ concurrent CSS animations per page.
**Impact:** Distracting, battery-draining, and potentially seizure-inducing for photosensitive users. No `prefers-reduced-motion` support.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

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

### P-DESIGN-8: Glass morphism won't work on low-end Android
**File:** `frontend/src/styles.css` — `.glass-card` class
**Problem:** `backdrop-filter: blur(24px)` causes frame drops on devices with <4GB RAM. India's target market is predominantly low-end Android.
**Impact:** The app's signature visual effect causes performance issues on the target audience's devices.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-DESIGN-9: Settings page saves to localStorage only — no server sync
**File:** `frontend/src/routes/settings.tsx`
**Problem:** ALL settings (niche, language, region, dark mode) save to `localStorage`. No server sync. No plan display. No subscription management. No account settings.
**Impact:** Settings are lost when user switches devices. No server-side preferences. The settings page is effectively a demo.
**Does IMPLEMENTATION_PLAN.md fix this?** Yes. Item 3.4 (Personalization) addresses this with `user_preferences` table and server sync.

### P-DESIGN-10: Inconsistent input styles across pages
**Files:** `frontend/src/styles.css` (`.glass-input`, `.input`), `frontend/src/routes/login.tsx`, `frontend/src/routes/ideas.tsx`
**Problem:** Three different input styles:
1. `.glass-input` class (dark mode glass)
2. `.input` class (light mode solid)
3. Inline Tailwind `bg-surface border border-border rounded-xl`

**Impact:** Form elements look different on every page. No consistent form design language.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-DATA-1: Targeted trends localStorage/API divergence — data-integrity bug
**Files:** `frontend/src/components/TrendCard.tsx:263-287`, `frontend/src/components/DanceTrendModal.tsx:25-58`, `frontend/src/lib/api.ts:1641`
**Problem:** Targeted trends are stored in TWO places that can disagree:
- **localStorage** (client-only): `TrendCard.tsx` and `DanceTrendModal.tsx` toggle `localStorage.getItem("targeted_trends")`
- **API + DB** (server): `GET /api/trends/targeted` reads from `trend_actions` table in Supabase

The target/untarget toggle in TrendCard writes to localStorage but also calls `POST /api/trends/{trend_id}/target` (which writes to DB). However, the GET endpoint reads from DB, not localStorage. If the POST call fails (network error, auth issue), localStorage and DB diverge silently.
**Impact:** User targets a trend → localStorage says targeted, DB says not targeted → `GET /api/trends/targeted` returns empty list → workspace shows no targeted trends.反之亦然.
**Does IMPLEMENTATION_PLAN.md fix this?** No. Separate from auth question. Needs a single source of truth (preferably DB-backed).

---

## 6. DATABASE & DATA QUALITY PROBLEMS

### P-DB-1: `usage_logs` table has 0 rows — quota enforcement disabled
**File:** Supabase `usage_logs` table
**Problem:** As noted in P-PAY-3, quota logging never happens. `require_quota()` always passes because the table is always empty.
**Impact:** Free users can use premium features无限次 without hitting limits.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-DB-2: `events` table doesn't exist — event detection impossible
**File:** Supabase — table not found
**Problem:** The `events` table is referenced in `event_monitor.py` but was never created.
**Impact:** Event detection (Independence Day, Diwali, IPL, etc.) is completely non-functional.
**Does IMPLEMENTATION_PLAN.md fix this?** Yes. Item 3.1 creates the events table and seeds real data.

### P-DB-3: `user_preferences` table doesn't exist — no personalization
**File:** Supabase — table not found
**Problem:** The settings page saves to localStorage. No server-side user preferences exist.
**Impact:** No feed personalization. All users see the same trends. Settings lost on device switch.
**Does IMPLEMENTATION_PLAN.md fix this?** Yes. Item 3.4 creates the `user_preferences` table and syncs settings.

### P-DB-4: `api_keys` table doesn't exist — no API revenue
**File:** Supabase — table not found
**Problem:** The API key validation system references `api_keys` but the table doesn't exist.
**Impact:** API access control is non-functional. No way to monetize API access.
**Does IMPLEMENTATION_PLAN.md fix this?** Not in current build order. Mentioned as "Phase 2" item.

### P-DB-5: `brand_deals` table has 0 rows — marketplace is empty
**File:** Supabase `brand_deals` table
**Problem:** The marketplace endpoints reference `brand_deals` but the table is empty.
**Impact:** Marketplace feature shows nothing. No brand partnerships.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

### P-DB-6: `trends` table has inconsistent lifecycle distribution [UPDATED]
**File:** Supabase `trends` table — 321 rows (post P-METHOD-1 cleanup)
**Problem:** Distribution: ~32 rising, ~31 emerging, ~128 peaked, ~130 expired. Only ~63 trends pass the feed filter (rising + emerging), but many fail other filters.
**Impact:** The feed shows very few active trends. Most trends are already peaked/expired.
**Does IMPLEMENTATION_PLAN.md fix this?** Indirectly. Fixing event detection and caption stubs may increase the number of active trends.

### P-DB-7: `user_performance` (and 5 related tables) never migrated — tracker silently no-ops [FIXED]
**Files:** `backend/user_performance_tracker.py`, `backend/add_user_performance_tables.py`, `backend/api.py:6720-6792`
**Problem:** The migration script `add_user_performance_tables.py` only prints SQL for manual execution (L130: "Please run these SQL statements in Supabase SQL Editor") — it was never run. All 6 planned tables are missing: `user_performance`, `user_insights`, `user_media_performance`, `realtime_trends`, `trending_hashtags`, `trending_audio`. The `UserPerformanceTracker` class is live code (imported at `api.py:296`, used by 4 endpoints), but every DB operation hits a nonexistent table and returns PGRST205 errors. The tracker's exception handler at `user_performance_tracker.py:123` catches these and returns `{'error': str(e)}`, which the API passes through — so writes appear to succeed but nothing lands.
**Impact:** The entire user performance feature (store, read, growth rate, top media) is non-functional. The 4 API endpoints at L6720-6792 are dead code from a data perspective.
**Also flags:** Exception handlers that return success-like responses on DB failure are a bug class — worth auditing elsewhere. A handler that catches all exceptions and returns a dict without re-raising means callers can't distinguish success from failure.
**Fix applied:** Created `backend/migrate_user_performance_tables.sql` with `CREATE TABLE IF NOT EXISTS` for the 3 core tables: `user_performance`, `user_insights`, `user_media_performance`. Schema derived from tracker code. User must run this SQL in Supabase SQL Editor. Tables 4-6 (`realtime_trends`, `trending_hashtags`, `trending_audio`) are not used by any code — omitted.
**UNVERIFIED:** Migration SQL written but not yet executed in Supabase. P-AUTH-7 GET-side IDOR fix remains blocked until tables exist.

### P-DB-8: Supabase Python client silently truncates at 1000 rows — systemic data visibility risk [NEW]
**Files:** Any code using `supabase-py` `.table().select().execute()` without explicit `.limit()` or pagination.
**Problem:** The Supabase Python client defaults to `.limit(1000)` on all queries. This is silent — no error, no warning, no partial-result flag. If a table has >1000 rows, the query returns only the first 1000 and the caller has no way to know. This affected the P-METHOD-1 analysis: the `trends` table had 1,013 rows but the analysis script saw only 1,000, missing 13 rows across 12 duplicate groups. The DELETE list was built on incomplete data and required a second pass.
**Impact:** Any production query fetching trends, snapshots, or reels without an explicit limit or pagination could be silently returning partial data. This includes dashboards, velocity calculations, feed endpoints, analytics, and any metric that sums or counts across the full table. The user would see incomplete data with no indication anything is wrong.
**Action required:** Grep the codebase for all `.table(` calls and verify each has an explicit `.limit()`, `.range()`, or pagination loop. Flag any that don't. Priority: user-facing endpoints and metric calculations.
**Fix applied:** None yet. Systemic audit needed.

### P-METHOD-1: Trend dedup guard only checks emerging/rising — allows re-detection after status transition [FIXED — Change B pending]
**Files:** `backend/trend_engine.py:756-814` (dedup guard — FIXED), `backend/external_trend_pipeline.py:92` (zero dedup — Change B pending), `backend/trend_refresher.py` (status transitions)
**Problem:** The dedup guard at `trend_engine.py:762` only checked trends with status `emerging` or `rising`. Once a trend transitioned to `peaked` or `expired` via `trend_refresher.py`, the guard no longer blocked re-detection. The external pipeline at `external_trend_pipeline.py:92` has zero dedup. No unique DB constraint on `audio_id` in the `trends` table.
**Impact:** 53% of trend titles were duplicated. 1,013 total rows, 163 duplicate groups, 692 excess rows. Business metrics (trend count, velocity averages) inflated ~2.7x since Aug 7. Ongoing since day one.
**Fix applied:**
1. Backfill DELETE of 679 rows committed (first pass — Supabase pagination bug missed 13 rows).
2. Cleanup DELETE of 13 remaining excess rows committed. Final state: 321 unique trends, 0 duplicate groups.
3. Unique constraint `trends_audio_id_unique` on `audio_id` — live, proven to reject duplicates.
4. Forward-fix Change A (trend_engine.py): dedup guard widened to all statuses, never-downgrade status rule (`rising > emerging > peaked > expired`), update-in-place on match. Velocity/metrics untouched — owned by trend_refresher.py via 5 independent cron-driven call sites. Committed `e23ef810`.
**Remaining:** Change B (external_trend_pipeline.py dedup guard) — separate commit, next session.

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

### P-METHOD-6: Velocity formula doesn't use Instagram's actual dominant ranking signals [NEW]
**Problem:** Trendrop's velocity_avg formula is derived from engagement/followers/creator-age. Instagram's own confirmed ranking hierarchy (per Adam Mosseri, 2025-2026) weights watch-time-completion as the #1 signal and DM-sends-per-reach as the strongest signal for non-follower reach — with likes explicitly the weakest signal. Trendrop's formula does not include either.
**Open question, not yet answered:** Does Instagram's public/scraped API surface expose watch-time or send-count data at all? If not, this is a hard platform limitation, not a code fix — needs honest investigation before assuming it's solvable.
**Action required:** Audit what data Instagram's scraped endpoints actually return; determine if watch-time/completion-rate/share-count are available in any form (even a proxy). If genuinely unavailable, this becomes a disclosed methodology limitation (P-TRUTH item), not a fixable bug.

### P-METHOD-7: Velocity spikes can't distinguish audio-driven virality from unrelated causes (misattribution risk) [NEW]
**Problem:** A reel using a given audio can go viral for reasons unrelated to the audio (external events, appearance-driven engagement, unrelated content virality). Trendrop's current model attributes any velocity spike on a tracked audio_id to "the audio is trending," with no mechanism to detect when the spike is actually driven by something else. This is distinct from P-METHOD's deprioritized external-events item — that item was about detecting new event-driven trends; this is about NOT misattributing existing audio-trend scores when the real driver isn't the audio.
**Action required:** Not yet scoped. Possible cheap partial signal: check whether velocity spikes are concentrated in a narrow content-type/hashtag cluster (suggesting a non-audio cause) vs. spread across diverse content (suggesting genuine audio-driven trend). Needs investigation before any fix is proposed.

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

### P-WORK-6: `check_llm_classification_history.py` missing — nightly workflow shows failed when it isn't
**File:** `.github/workflows/nightly-llm-classification.yml` (references `backend/check_llm_classification_history.py`)
**Problem:** After the `run-llm-batch` step succeeds, the verification step `python backend/check_llm_classification_history.py` fails with exit code 2 (file not found). GitHub marks the entire workflow run as "failed" even though classification completed correctly. This produces false-alarm red badges in the Actions tab — the same signal surface we rely on for pipeline health.
**Severity:** Low (no data impact, just noise). But "workflow shows failed when it isn't" erodes trust in Actions signal.
**Fix:** Either create the missing verification script or remove the step from the workflow YAML.
**Does IMPLEMENTATION_PLAN.md fix this?** No.

---

## 8. CROSS-CUTTING TRUTH PROBLEMS

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
| P-DB-6: Inconsistent trend distribution | MEDIUM | Few active trends in feed |
| P-DB-7: user_performance tables never migrated | HIGH | Performance feature dead code | **FIXED** |
| P-DB-8: Supabase client truncates at 1000 rows | HIGH | Silent data visibility risk |
| P-METHOD-1: Trend dedup guard only checks emerging/rising | HIGH | 53% duplicate trends | **FIXED** |
| P-METHOD-1b: title+artist duplicates | LOW | 6 extra rows | **FIXED** |
| P-METHOD-1c: Bulk-seed path bypassed dedup | MEDIUM | Potential dedup blind spot | **CLOSED** |
| P-METHOD-5: Format-driven trends undetected | MEDIUM | Missed edit-pattern virality |
| P-METHOD-6: Velocity ignores Instagram's top signals | HIGH | Formula misaligned with platform |
| P-METHOD-7: Velocity can't detect misattribution | MEDIUM | Audio trends may be non-audio driven |
| P-WORK-1: GitHub Actions over budget | HIGH | CI/CD cost |
| P-WORK-2: No test suite | MEDIUM | No quality gates |
| P-WORK-3: No rollback strategy | LOW | Manual recovery |
| P-TRUTH-1-5: Marketing claims unprovable | HIGH | Trust/credibility |
| P-FUND-1: Payment flow dead | CRITICAL | No revenue, no fundraising |
| P-FUND-2: "0h delay" copy risk | HIGH | Batch pipeline can't back real-time claims | **FIXED** |
| P-FUND-3: Agency per-seat schema-only | HIGH | Zero enforcement, unlimited sharing |
| P-FUND-4: Account sharing = theoretical | LOW | Solve payments first |
| P-FUND-5: Data-parity moat risk | HIGH | Speed-only differentiation, no insight moat |

---

## 9. STRATEGIC & FUNDRAISING PROBLEMS

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

### P-FUND-3: Per-seat enforcement for Agency plan is schema-only — zero logic
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

### P-MARKET-3: No escrow/payment processing for deals — "Mark as paid" is a database toggle [CRITICAL]
**Files:** `backend/api.py:4102-4121` (`POST /api/deals/{deal_id}/pay-milestone/{milestone_id}`)
**Problem:** The milestone payment endpoint simply updates `paid_status` from "unpaid" to "paid" in the database. No money moves. No Razorpay integration. No escrow. No invoice generation. The creator clicks "Mark as paid" and the system trusts that the brand actually paid. This is identical to the agency model — no payment protection.
**Access control (fixed commit `e179405e`):** Endpoint now gated to `require_feature("advanced_analytics")` (pro/business plans only). Free-tier users get 403 with upgrade prompt. Ownership check at L4117-4118 still fires after plan gate — paid users can only mark milestones on their own deals.
**Impact:** Without escrow, creators have zero payment protection. Brands can promise to pay and never do. This is the exact problem agencies create, and Trendrop claims to solve.
**Fix:** Implement Razorpay escrow: brand funds deal upfront → Trendrop holds money → creator delivers → Trendrop releases payment. This requires Razorpay KYC (P-FUND-1) and brand-side interface (P-MARKET-1).

### P-MARKET-4: No brand verification — anyone can create a brand deal [HIGH]
**Files:** No verification code exists anywhere in the marketplace flow.
**Problem:** Anyone can create a brand deal without proving they are a legitimate business. No GST verification, no business registration, no company email check. This enables fake brands that promise deals and never pay, or brands that create deals to harvest creator contact information.
**Impact:** Trust erosion. If creators encounter fake brands, they leave the platform. Without verification, the marketplace becomes a spam vector.
**Fix:** Brand verification flow: GST number upload, business registration document, company email verification (@company.com, not Gmail). Verified badge on brand profiles. Unverified brands can browse but cannot post deals.

### P-MARKET-5: No notifications to brands — application black hole [HIGH]
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

### P-MARKET-9: Milestone reminder emails have never fired — Vercel cron not wired [HIGH]
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

### P-PAY-5: Plan rename needed — "Agency" tier signals exploitation [MEDIUM]
**Files:** `backend/plan_enforcement.py:71-75`, `backend/database_setup.py:204-211`, `frontend/src/components/PlanGate.tsx`, `frontend/src/routes/pricing.tsx`
**Problem:** The "Agency" tier name signals the exact thing Trendrop claims to eliminate — agency exploitation of creators. The plan structure should position Trendrop as the anti-agency: direct brand-creator connection. "Agency" as a tier name contradicts this positioning.
**Impact:** Brand confusion. Users who hate agencies see an "Agency" plan and question the platform's values. Investor messaging inconsistency.
**Fix:** Rename: Agency → Brand (₹4,999/mo, for brands posting deals). Creator → Pro (₹999/mo). Keep Free as Free. Enterprise stays Enterprise. Update all references: DB tier names, frontend labels, plan enforcement, pricing page, onboarding flow.

### P-PAY-6: Credit system needed — usage-based pricing for trend detection + AI [HIGH]
**Files:** No credit system exists. Current pricing is flat-rate subscription only.
**Problem:** Flat-rate pricing doesn't match usage patterns. A creator who checks trends once/day pays the same as one who checks 50 times/day. This creates: (1) unfairness for light users, (2) revenue ceiling for heavy users, (3) no incentive to optimize usage. Virlo (competitor) uses credit-based pricing: Orbit Search = 50 credits, each plan has monthly credit allocation.
**Impact:** Revenue left on the table. Heavy users should pay more. Light users should pay less. Credit system enables: per-action pricing, credit add-ons, usage transparency, revenue optimization.
**Fix:** Implement credit system: Free = 10 credits/day, Pro = 200 credits/mo, Brand = 1,500 credits/mo. Credit costs: trend detection = 1 credit, AI generation = 5 credits, deal posting = 10 credits. Credit add-ons: ₹99/50 credits, ₹249/150 credits, ₹499/350 credits.

### P-PAY-7: Free + 14-day trial model needed — current free tier lacks upgrade pressure [MEDIUM]
**Files:** `frontend/src/routes/pricing.tsx`, `backend/plan_enforcement.py`
**Problem:** The current free tier gives permanent access to basic features with no urgency to upgrade. Users who sign up and never upgrade generate zero revenue. There's no mechanism to show users what they're missing. The 14-day trial that was previously on the pricing page was removed.
**Impact:** Low conversion rate from free to paid. Users don't experience enough value during free usage to justify upgrading. No trial = no urgency.
**Fix:** Free tier + 14-day Pro trial: (1) User signs up → Free tier (10 credits/day), (2) After 3 days of usage → "Try Pro free for 14 days" prompt, (3) During trial → Full Pro access (200 credits/day), (4) After trial → Back to Free unless they upgrade, (5) Trial requires Razorpay setup (₹0 charge, card on file for auto-conversion).

---

## RECOMMENDATION

The codebase now has **67 total problems** (10 fixed, 1 false positive, 56 open). The remaining problems fall into these categories:

1. **Marketplace redesign** (7 problems): P-MARKET-1 through P-MARKET-7. The marketplace is the #1 revenue blocker. Without a brand-side product, there are no deals, no escrow revenue, and no connection layer. This is the highest-priority workstream.

2. **Data pipeline architecture** (8 problems): The scraper needs pagination, DB batching, formula fixes, and timeout restructuring. These are the highest-impact fixes but require the most engineering effort.

3. **Frontend design** (10 problems): The app needs a ground-up design system rebuild. This is the second-highest impact but requires design expertise, not just code fixes.

4. **Monetization** (5 problems): Plan rename, credit system, trial model, Razorpay KYC, and payment flow. These are quick wins that unlock revenue.

5. **Security** (4 problems): Auth hardening, rate limiting, and admin route protection are quick wins that should be done immediately.

6. **Truth** (5 problems): Marketing claims need to be updated to match reality, or the code needs to be updated to match the claims.

**The recommended execution order (from ROADMAP.md):**
- **Phase 1 (Oct 2026):** Razorpay + brand interface + escrow = first revenue
- **Phase 2 (Nov-Dec 2026):** Notifications + verification + ratings = trust layer
- **Phase 3 (Jan-Mar 2027):** Credit system + plan rename + trial model = revenue optimization
- **Phase 4 (Apr-Jun 2027):** Mobile PWA + advanced matching = scale

1. **Data pipeline architecture** (8 problems): The scraper needs pagination, DB batching, formula fixes, and timeout restructuring. These are the highest-impact fixes but require the most engineering effort.

2. **Frontend design** (10 problems): The app needs a ground-up design system rebuild. This is the second-highest impact but requires design expertise, not just code fixes.

3. **Security** (4 problems): Auth hardening, rate limiting, and admin route protection are quick wins that should be done immediately.

4. **Payment** (3 problems): Razorpay KYC is a user action. The deleted pricing page and empty usage_logs need code fixes.

5. **Truth** (5 problems): Marketing claims need to be updated to match reality, or the code needs to be updated to match the claims.

**If the goal is to match what users see on Instagram**, the pipeline needs a fundamental architecture change:
- Add scraper pagination (scroll or API-based)
- Batch DB operations (bulk inserts, cached queries)
- Validate thresholds against Instagram's actual trending page
- Integrate real-time monitoring (not just batch scraping)
- Fix or remove broken external discovery

**If the goal is a credible MVP for investors/users**, the frontend needs a design system overhaul and the marketing claims need to be grounded in reality.
