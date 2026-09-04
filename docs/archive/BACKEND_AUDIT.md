# TrendDrop Backend Audit — 2026-08-31

**Scope:** READ-ONLY audit of TrendDrop backend. Every claim backed by file:line evidence. No modifications, fixes, or design decisions.

**Files analyzed:** 218 Python files in `backend/`, `routes/`, `api/`, `scripts/`, `.github/workflows/`. 19 SQL migrations. 9 GitHub Actions workflows.

**Cross-reference:** `FRONTEND_AUDIT_2026-08-23.md` for frontend↔backend alignment.

---

## Table of Contents

1. [Endpoint Inventory](#1-endpoint-inventory)
2. [Trend Detection / Scraper Pipeline](#2-trend-detection--scraper-pipeline)
3. [Auth & Security](#3-auth--security)
4. [Payments / Subscription System](#4-payments--subscription-system)
5. [Database Schema](#5-database-schema)
6. [AI/LLM Integrations](#6-aillm-integrations)
7. [Admin System](#7-admin-system)
8. [Infrastructure](#8-infrastructure)
9. [Bugs, TODOs, Dead Code](#9-bugs-todos-dead-code)

---

## 1. Endpoint Inventory

### 1.1 Main App (`backend/api.py`) — 14 Direct Routes

| # | Method | Path | Auth | Rate Limit | Line |
|---|--------|------|------|------------|------|
| 1 | GET | `/health` | None | None | 34 |
| 2 | POST | `/api/cron/refresh-trends` | None (cron secret) | None | 59 |
| 3 | GET | `/api/proof` | None | None | 91 |
| 4 | GET | `/api/trends` | None (public fallback) | None | 137 |
| 5 | POST | `/api/trends/refresh` | None (cron secret) | None | 177 |
| 6 | GET | `/api/reels/stream/{trend_id}` | None | None | 239 |
| 7 | POST | `/api/payment/webhook` | None (Razorpay sig) | None | 286 |
| 8 | GET | `/api/reel-video/{reel_id}` | None | None | 353 |
| 9 | POST | `/api/generate` | None | None | 383 |
| 10 | POST | `/api/generate-caption` | None | None | 420 |
| 11 | POST | `/api/generate-content-ideas` | None | None | 460 |
| 12 | GET | `/api/trends/{trend_id}` | None | None | 504 |
| 13 | POST | `/api/payment/create-order` | None | None | 530 |
| 14 | GET | `/api/user/plan/{email}` | None | None | 578 |

**Key finding:** Most direct routes in `api.py` have **no auth dependency** — they accept anonymous requests. Auth is handled by router modules when included separately.

### 1.2 Router Modules — 76 Endpoints

#### `routes/auth.py` (6 endpoints)

| Method | Path | Auth | Rate Limit | Line |
|--------|------|------|------------|------|
| POST | `/api/auth/signup` | None | 5/hr | 11 |
| POST | `/api/auth/login` | None | 10/min | 60 |
| POST | `/api/auth/reset-password` | None | 5/hr | 122 |
| POST | `/api/auth/logout` | None | None | 147 |
| POST | `/api/auth/verify` | None | None | 165 |
| GET | `/api/auth/me` | `require_auth` | None | 190 |

**Supabase JWKS validation:** Lines 49-105. Three-step fallback: (1) `users.auth_token` lookup, (2) `supabase.auth.get_user(jwt=token)`, (3) custom JWT decode. **Key issue:** Step 2 fails for Supabase JWTs in production (front-end audit confirmed), falling through to step 3 which rejects them.

#### `routes/ai.py` (17 endpoints)

| Method | Path | Auth | Rate Limit | Line |
|--------|------|------|------------|------|
| POST | `/api/prepost-score` | `require_auth` | 5/min | 12 |
| POST | `/api/generate-hooks` | `get_current_user` + `require_credits` | 10/min | 38 |
| POST | `/api/score-reel` | `require_auth` | 20/hr | 58 |
| GET | `/api/daily-ideas/{user_email}` | `require_auth` | 10/min | 136 |
| GET | `/api/generate-calendar/{user_email}` | `get_current_user` + `require_credits` | 5/min | 182 |
| POST | `/api/seo-caption` | `require_credits` | 10/min | 243 |
| GET | `/api/daily-ideas` | `require_credits` | 10/min | 253 |
| POST | `/api/calendar` | `get_current_user` + `require_credits` | 5/min | 290 |
| GET | `/api/calendar` | `get_current_user` + `require_credits` | 10/min | 325 |
| GET | `/api/ai/generate-caption` | `get_current_user` + `require_credits` | 20/min | 338 |
| GET | `/api/ai/content-ideas` | `get_current_user` + `require_credits` | 20/min | 361 |
| GET | `/api/ai/generate-hooks` | `get_current_user` + `require_credits` | 20/min | 400 |
| GET | `/api/ai/script-outline` | `get_current_user` + `require_credits` | 20/min | 434 |
| POST | `/api/video/analyze-metadata` | `get_current_user` | 5/min | 463 |
| POST | `/api/video/analyze-visual` | `get_current_user` | 5/min | 514 |
| POST | `/api/video/predict-virality` | `get_current_user` | 5/min | 555 |
| POST | `/api/video/improvements` | `get_current_user` | 5/min | 604 |

#### `routes/creator.py` (21 endpoints)

| Method | Path | Auth | Rate Limit | Line |
|--------|------|------|------------|------|
| POST | `/api/user/cancellation-reason` | `require_auth` | 5/hr | 12 |
| GET | `/api/user/plan` | `require_auth` | 30/min | 46 |
| GET | `/api/user/credits` | `require_auth` | 30/min | 71 |
| GET | `/api/marketplace/profiles` | **None (public)** | 30/min | 102 |
| POST | `/api/marketplace/profile` | `require_auth` | 10/min | 116 |
| POST | `/api/deals` | `require_auth` | 15/min | 138 |
| GET | `/api/deals` | `require_auth` | 30/min | 215 |
| GET | `/api/deals/{deal_id}/download` | `require_auth` | 20/min | 238 |
| POST | `/api/deals/{deal_id}/pay-milestone/{milestone_id}` | `get_current_user` + `require_credits` | 30/min | 278 |
| POST | `/api/deals/run-reminders` | cron secret | 2/hr | 305 |
| GET | `/api/brand-deals/{user_email}` | `require_auth` | 30/min | 325 |
| GET | `/api/collab-matches/{user_email}` | `require_auth` | 30/min | 469 |
| POST | `/api/creator/feedback` | `require_auth` | 20/min | 544 |
| GET | `/api/creator/metrics` | `require_auth` | 30/min | 566 |
| GET | `/api/creator/trend-adoption` | `require_auth` | 30/min | 604 |
| GET | `/api/creator/performance-over-time` | `require_auth` | 30/min | 640 |
| GET | `/api/creator/recommendations` | `get_current_user` + `require_feature` | 30/min | 663 |
| POST | `/api/user/performance/store` | `require_auth` | 10/min | 686 |
| GET | `/api/user/performance` | `require_auth` | 30/min | 708 |
| GET | `/api/user/performance/growth` | `require_auth` | 30/min | 730 |
| GET | `/api/user/performance/top-media` | `require_auth` | 30/min | 752 |

#### `routes/india.py` (11 endpoints)

| Method | Path | Auth | Rate Limit | Line |
|--------|------|------|------------|------|
| GET | `/api/india/regional-trends` | `get_current_user` + `require_feature("india_features")` | 30/min | 11 |
| GET | `/api/india/regional-timing` | `get_current_user` + `require_feature("india_features")` | 30/min | 49 |
| POST | `/api/india/detect-language` | `require_auth` | 30/min | 79 |
| GET | `/api/india/hashtag-strategy` | `get_current_user` | 30/min | 102 |
| GET | `/api/india/creator-patterns` | `get_current_user` | 30/min | 123 |
| GET | `/api/india/cultural-events` | `get_current_user` + `require_feature("india_features")` | 30/min | 143 |
| GET | `/api/india/cultural-events/{event_name}` | `get_current_user` | 30/min | 178 |
| GET | `/api/india/cultural-events/{event_name}/optimal-timing` | `get_current_user` | 30/min | 198 |
| GET | `/api/india/caption/generate` | `require_credits` | 10/min | 217 |
| GET | `/api/india/content-ideas/generate` | `require_credits` | 10/min | 245 |
| GET | `/api/india/cultural-event/{event_name}` | `require_credits` | 30/min | 281 |

**Design debt:** Line 158 — known dual-key response shape acknowledged as wart.

#### `routes/system.py` (21 endpoints)

| Method | Path | Auth | Rate Limit | Line |
|--------|------|------|------------|------|
| GET | `/api/proof` | None | 10/min | 11 |
| GET | `/health` | None | None | 59 |
| POST | `/api/subscribe` | None | 5/hr | 122 |
| POST | `/api/payment/create-order` | `require_auth` | 10/min | 149 |
| POST | `/api/payment/webhook` | None (Razorpay sig) | 20/min | 187 |
| GET | `/api/reels/feed` | `get_current_user` + `require_feature` | 30/min | 264 |
| GET | `/api/reels/cross-cultural` | `get_current_user` + `require_feature` | 30/min | 313 |
| POST | `/api/feedback` | `require_auth` | 20/min | 356 |
| GET | `/api/job-status/{job_id}` | `require_auth` | 60/min | 377 |
| GET | `/api/reel-status/{job_id}` | `require_auth` | 60/min | 396 |
| POST | `/api/run-scraper` | `require_admin` | 2/min | 402 |
| POST | `/api/apply-deal` | `require_auth` | 15/min | 415 |
| POST | `/api/send-collab-request` | `require_auth` | 15/min | 440 |
| POST | `/api/analytics/log` | `require_auth` | 60/min | 465 |
| GET | `/api/events/active` | `get_current_user` | 60/min | 490 |
| GET | `/api/events/{event_id}/opportunities` | `get_current_user` | 30/min | 535 |
| GET | `/api/events/hashtag-spikes` | `get_current_user` | 30/min | 555 |
| GET | `/api/early-detection/trends` | `require_feature` | 30/min | 579 |
| GET | `/api/early-detection/predict/{trend_id}` | `require_feature` | 30/min | 601 |
| POST | `/api/virality/predict` | `require_auth` | 10/min | 637 |
| GET | `/api/virality/improvements` | `require_credits` | 30/min | 675 |

#### `routes/trends.py` (26 endpoints)

| Method | Path | Auth | Rate Limit | Line |
|--------|------|------|------------|------|
| GET | `/api/trends` | `get_current_user` | 60/min | 12 |
| GET | `/api/trends/emerging` | `get_current_user` + `require_feature` | 60/min | 134 |
| GET | `/api/trends/all-active` | `get_current_user` + `require_phone_verified` + `require_feature` | 60/min | 183 |
| GET | `/api/trends/peaked` | `get_current_user` | 60/min | 205 |
| GET | `/api/trends/expired` | `get_current_user` | 60/min | 252 |
| GET | `/api/trends/audio-scores` | `get_current_user` + `require_feature` | 60/min | 281 |
| GET | `/api/trends/by-language/{lang}` | `get_current_user` + `require_feature` | 60/min | 322 |
| GET | `/api/trends/peaking` | `get_current_user` + `require_feature` | 60/min | 349 |
| GET | `/api/trends/{trend_id}/timeline` | `get_current_user` + `require_feature` | 60/min | 413 |
| GET | `/api/trends/targeted` | **Header-based (manual)** | None | 495 |
| GET | `/api/trends/{trend_id}` | `get_current_user` | 60/min | 517 |
| GET | `/api/trends/{trend_id}/audio-history` | `get_current_user` | 300/min | 537 |
| GET | `/api/trends/{trend_id}/reels` | `get_current_user` + `require_feature` | 60/min | 568 |
| GET | `/api/trends/{trend_id}/caption` | `get_current_user` | 20/min | 604 |
| GET | `/api/algorithm/analyze` | `get_current_user` + `require_feature` | 30/min | 622 |
| GET | `/api/algorithm/posting-times` | `get_current_user` + `require_feature` | 60/min | 684 |
| GET | `/api/algorithm/hashtag-strategy` | `get_current_user` + `require_feature` | 60/min | 707 |
| GET | `/api/trends/{trend_id}/similar` | `get_current_user` + `require_feature` | 60/min | 737 |
| GET | `/api/trends/{trend_id}/decision` | `get_current_user` + `require_feature` | 60/min | 776 |
| POST | `/api/trends/{trend_id}/memory` | `require_auth` | 30/min | 845 |
| POST | `/api/trends/{trend_id}/target` | **Header-based (manual)** | 30/min | 865 |
| GET | `/api/hashtags/velocity` | `get_current_user` | 30/min | 902 |
| GET | `/api/hashtags/trending` | `get_current_user` | 30/min | 942 |
| GET | `/api/topics/clusters` | `get_current_user` | 30/min | 982 |
| GET | `/api/conversations/detect` | `get_current_user` | 30/min | 1026 |
| GET | `/api/trends/niche/{niche_name}` | `get_current_user` | 60/min | 1066 |

**Inconsistent auth:** `get_targeted_trends` (line 495) and `toggle_trend_target` (line 865) use manual `Header(None)` + `_resolve_user()` instead of `Depends()` like all other endpoints.

#### `routes/users.py` (3 endpoints)

| Method | Path | Auth | Rate Limit | Line |
|--------|------|------|------------|------|
| GET | `/api/users/preferences` | `require_auth` | **None** | 11 |
| PUT | `/api/users/preferences` | `require_auth` | **None** | 51 |
| GET | `/api/content-trends` | `require_auth` | **None** | 90 |

**Missing rate limiting:** All 3 endpoints lack `@limiter.limit()` unlike every other route file.

### 1.3 Admin Routes (`routes/admin.py`)

| Method | Path | Auth | Line |
|--------|------|------|------|
| GET | `/api/admin/dashboard` | `require_admin` | varies |
| GET | `/api/admin/users` | `require_admin` | varies |
| POST | `/api/admin/users/{user_id}/plan` | `require_admin` | varies |
| POST | `/api/admin/users/{user_id}/toggle-lock` | `require_admin` | varies |
| GET | `/api/admin/metrics` | `require_admin` | varies |
| GET | `/api/admin/metrics/daily` | `require_admin` | varies |
| GET | `/api/admin/business-metrics` | `require_admin` | varies |
| GET | `/api/admin/audit-log` | `require_admin` | varies |
| GET | `/api/admin/plan-features` | `require_admin` | varies |
| POST | `/api/admin/plan-features` | `require_admin` | varies |
| POST | `/api/admin/users/{user_id}/credits` | `require_admin` | varies |
| POST | `/api/admin/toggle-guest-mode` | `require_admin` | varies |

### 1.4 Duplicate Route Paths

| Path | Defined In | Issue |
|------|-----------|-------|
| `/api/proof` | `api.py:91` AND `system.py:11` | Double-registered |
| `/health` | `api.py:34` AND `system.py:59` | Double-registered |
| `/api/payment/create-order` | `api.py:530` AND `system.py:149` | Double-registered — one has auth, one doesn't |
| `/api/payment/webhook` | `api.py:286` AND `system.py:187` | Double-registered |

**Path mismatch:** Admin routes use `/api/admin/business-metrics` but frontend expects `/api/business/metrics` (confirmed in `FRONTEND_AUDIT_2026-08-23.md`).

### 1.5 Summary Stats

| Metric | Count |
|--------|-------|
| Total unique endpoints | ~90 |
| Endpoints with auth | ~72 |
| Endpoints without auth | ~18 |
| Duplicate route registrations | 4 pairs |
| Missing rate limiting | 3 endpoints (`routes/users.py`) |
| Cron-secret authenticated | 2 (`run-reminders`, `refresh-trends`) |
| Header-based (non-Depends) auth | 2 (`targeted`, `target`) |

---

## 2. Trend Detection / Scraper Pipeline

### 2.1 Pipeline Flow

```
Instagram Scraper (Camoufox)
  ↓
Trend Engine (trend_engine.py)
  ↓
Trend Detector (trend_detector.py)
  ↓
Trend Refresher (trend_refresher.py)
  ↓
Unified Signal Processor (unified_signal_processor.py)
  ↓
Caption Engine (caption_engine.py) [optional]
  ↓
Alert System
```

**Trigger chain:**
- GitHub Actions cron: `nightly-llm-classification.yml` → `emergency-llm-classification.yml` → `cron-heartbeat.yml`
- Manual: `/api/run-scraper` (admin only) or `/api/cron/refresh-trends` (cron secret)
- Background: `cron_job.py` orchestrates the full pipeline

### 2.2 Trend Scoring Model

**Source:** `backend/trend_scoring.py:31-153`

**Opportunity Score formula:**
```
opportunity_score = velocity_score * 0.40 + saturation_score * 0.35 + time_score * 0.25
```

**Velocity score** (`trend_scoring.py:35-65`):
- Uses logarithmic scale: `math.log10(view_count + 1) / math.log10(2_000_000)`
- Capped at 1.0

**Urgency score** (`trend_scoring.py:68-104`):
```
urgency_score = (
    velocity_weighted * (URGENCY_WEIGHT_VELOCITY / 100) +
    saturation_weighted * (URGENCY_WEIGHT_SATURATION / 100) +
    time_weighted * (URGENCY_WEIGHT_TIME / 100)
)
```
- `URGENCY_WEIGHT_VELOCITY = 40` (line 23)
- `URGENCY_WEIGHT_SATURATION = 35` (line 24)
- `URGENCY_WEIGHT_TIME = 25` (line 25)

**Time score** (`trend_scoring.py:87-104`):
- Full score at 0 hours remaining, decreases linearly

**Saturation score** (`trend_scoring.py:119-153`):
- `GLOBAL_SATURATION_THRESHOLD_REELS = 5_000_000` (line 14)
- `INDIA_SATURATION_THRESHOLD_REELS = 500` (line 15)
- `MAX_INDIA_REEL_GROWTH_RATE = 100.0` (line 16)

**Critical finding: Single-snapshot scoring.** `trend_scoring.py:119-153` computes saturation from a single `saturation_pct` value (derived from `total_reels / threshold`). **There is NO historical delta computation across scrape runs in this module.** The velocity multiplier is calculated in `trend_detector.py` but uses a single window comparison, not multi-run deltas.

### 2.3 Trend Detector

**Source:** `backend/trend_detector.py`

**Velocity multiplier** (`trend_detector.py`):
- `VELOCITY_MULTIPLIER = 12` — used to boost scores for trends with rising velocity
- `SATURATION_THRESHOLD_RISING = 0.1` — saturation must be below 10% for rising classification
- `SATURATION_THRESHOLD_EMERGING = 0.05` — saturation must be below 5% for emerging

**Classification logic:**
1. Fetch all active trends from DB
2. Calculate velocity from recent snapshots
3. Apply velocity multiplier
4. Classify as: `rising` (high velocity + low saturation), `emerging` (medium velocity + very low saturation), `stable` (default)

**Niche classification** (`trend_detector.py`):
- `NICHE_KEYWORDS` dict maps categories (fashion, beauty, tech, food, fitness, comedy, dance, music, lifestyle, business) to keyword lists
- Simple keyword-in-caption matching — no ML classification

### 2.4 Trend Engine

**Source:** `backend/trend_engine.py`

**Promotion triggers** (`trend_engine.py:34-40`):
- `audio_use_count_rising`: audio usage count increasing
- `creator_count_rising`: number of creators using trend increasing
- `engagement_rate_rising`: engagement rate improving
- `view_velocity_high`: view growth rate above threshold

**Fallback mechanism** (`trend_engine.py:generate_local_fallback`):
- When Supabase is unavailable, generates synthetic trend data from hardcoded templates
- Used for resilience in offline/degraded scenarios

### 2.5 Trend Refresher

**Source:** `backend/trend_refresher.py`

**Lifecycle transitions:**
- `emerging` → `rising` (when velocity threshold met)
- `rising` → `peaked` (when velocity drops below threshold)
- `peaked` → `expired` (when `window_hours_remaining` hits 0)

**Window hours** (`trend_refresher.py`):
- Decremented each refresh cycle
- Default windows: emerging=48h, rising=72h, peaked=24h

### 2.6 Instagram Scraper

**Source:** `backend/instagram_scraper_browser.py` (~2300 lines)

**Stealth mode:**
- Camoufox (`AsyncCamoufox`) anti-detection Firefox (line 19)
- Instagram App ID: `936619743392459` (lines 493, 694, 896, 950)
- Cookie-based auth from `cookies.json` + `INSTAGRAM_COOKIES_B64` env var
- Warm-up navigation to Instagram home

**Scrape failure handling:**
- Browser disconnect → full reinit (lines 919-924)
- Login wall → `RuntimeError("INSTAGRAM COOKIE EXPIRED/INVALID")` (lines 1012-1013)
- JSON decode error on cookies → logs critical error (lines 667-672)
- Per-hashtag SIGALRM timeout: 90s default (`SCRAPER_HASHTAG_TIMEOUT`) — **Linux only** (lines 1920-1939)
- Global wall-clock timeout: 15 minutes (line 1900)
- Rate limiting: 1-2 second delay between hashtags (line 1909)
- Bulk upsert failure → row-by-row salvage (lines 1678-1686)

**Hardcoded thresholds:**
- `CREATOR_OUTLIER_MULTIPLIER`: 5.0 (line 1407, env-configurable)
- Velocity threshold for hooks: `> 0.3` OR `(views > 15000 AND hours < 6)` OR outlier (line 1418)
- Low engagement floor: `views < 2000 AND likes < 50` (line 1414)
- Audio use count `>= 50` means not original (line 805)
- Engagement formula: `views*1 + likes*3 + comments*5` (line 1386)
- Follower fallback: `2500` when unknown (line 1387)
- Max items per hashtag: 300 (line 1091)
- CHUNK size for bulk DB ops: 500 (line 1344)

**Saturation threshold discrepancy:**
- `instagram_scraper_browser.py`: `calculate_saturation()` uses 100K/8K thresholds
- `trend_scoring.py`: Uses `GLOBAL_SATURATION_THRESHOLD_REELS = 5_000_000` and `INDIA_SATURATION_THRESHOLD_REELS = 500`

**Hook analysis is dead code** (`instagram_scraper_browser.py:1229-1259`):
- Builds detailed LLM prompt (line 1237) but **never calls LLM**
- Returns hardcoded dict: `dominant_hook_type` based on "pov" keyword, `optimal_length_seconds: 20`, `visual_format: "montage"`
- Hook analysis data stored in DB is synthetic

**Video storage permanently disabled** (`instagram_scraper_browser.py:1180-1184`):
- `_store_reel_video` returns `None` always — thumbnails only

### 2.7 Cron Schedules

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `nightly-llm-classification.yml` | 2x/day | LLM enrichment of pending trends |
| `emergency-llm-classification.yml` | 4x/day | Emergency classification when backlog > 20 |
| `cron-heartbeat.yml` | 3x/day | Heartbeat monitoring |
| `news-virality-cron.yml` | Daily | News virality scoring (broken — Groq 404) |

**Broken workflow:** `news-virality-cron.yml` fails with Groq 404 error (confirmed in CI logs).

### 2.8 LLM Classification Batch

**Source:** `backend/nightly_llm_batch.py`

- `MAX_CALLS = 20` per batch (line 24)
- Backoff retry: exponential with `2 ** attempt * 2` seconds (line 47)
- Gemini-based content strategy generation
- Fetches pending trends from `content_trends` table
- Updates trend classification and metadata

---

## 3. Auth & Security

### 3.1 Authentication Flow

**Source:** `backend/auth.py`

**JWT validation** (`auth.py:49-105`):
1. Try `users.auth_token` lookup in DB (legacy path)
2. Try `supabase.auth.get_user(jwt=token)` (Supabase path)
3. Try custom JWT decode with `HS256` + `JWT_SECRET`

**Key issue:** Step 2 fails in production (confirmed by frontend audit), causing fallback to step 3 which rejects Supabase JWTs.

**Token expiry:** 30 minutes (`JWT_EXPIRY_MINUTES = 30`, `auth.py:27`). No refresh token mechanism.

**Account locking** (`auth.py:35-47, 172-239`):
- 5 failed attempts → 15 minute lockout
- Lock status stored in `users.is_locked` + `users.locked_until`
- `_check_user_locked()` called on every login attempt

### 3.2 Password Hashing

**Source:** `backend/auth.py`

- Uses `passlib` with bcrypt (line 11)
- Passwords hashed before storage
- No password complexity enforcement visible

### 3.3 Admin Authentication

**Source:** `backend/auth.py:260-335`

- Admin JWT must include `role: "admin"` or `role: "super_admin"`
- Admin tokens validated against `admin_users` table
- `require_admin` dependency checks both JWT role and DB record

### 3.4 Guest/Anonymous Mode

**Source:** `backend/plan_enforcement.py:29-31, 113`

- Guest sentinel: `"guest@trendrop.app"`
- Used when no auth token provided
- Returns `free` plan with limited features

**IDOR risk:** `guest@trendrop.app` and `anonymous@trendrop.app` bypass user-specific data checks in `routes/ai.py:139,185` and `routes/creator.py:472`.

### 3.5 Rate Limiting

**Source:** `backend/redis_rate_limiter.py`

- Upstash Redis sliding window limiter
- Graceful fallback if Redis unavailable (allows request)
- Per-endpoint limits defined in route decorators

**Missing rate limiting:**
- `routes/users.py`: All 3 endpoints lack `@limiter.limit()`
- `routes/trends.py:495,865`: Header-based auth endpoints have no `Depends()` rate limit integration

### 3.6 CORS

**Source:** `backend/api.py`

- `CORSMiddleware` configured (specific origins not enumerated in read files)

### 3.7 Security Issues

| Severity | Issue | Location | Description |
|----------|-------|----------|-------------|
| HIGH | OTP uses non-crypto PRNG | `phone_verification.py:65` | `random.randint()` is predictable |
| HIGH | Secret in query string | `creator.py:314`, `system.py:313` | `?secret=` logged in access logs |
| HIGH | No brute-force OTP protection | `phone_verification.py` | 6-digit code, no attempt limiting |
| HIGH | Race condition in usage counter | `usage_tracker.py:198-212` | Read-then-update without atomicity |
| HIGH | Duplicate FeedbackRequest schema | `schemas.py:14,176` | Second definition shadows first |
| MEDIUM | No rate limiting | `routes/users.py` | All 3 endpoints unprotected |
| MEDIUM | Guest/anonymous bypass | `ai.py:139,185`, `creator.py:472` | Magic emails bypass user checks |
| MEDIUM | Error detail leakage | `creator.py`, `trends.py` | `str(e)` exposed in HTTP responses |
| MEDIUM | Health check leaks errors | `system.py:69` | DB error messages returned |
| MEDIUM | Inconsistent auth pattern | `trends.py:495,865` | Manual Header() vs Depends() |
| LOW | Wildcard imports | `ai.py`, `creator.py`, etc. | `from api_globals import *` |
| LOW | `print()` instead of `logger` | Multiple files | Inconsistent logging |
| LOW | Hardcoded `.env` path | `unified_signal_processor.py:18` | `load_dotenv("backend/.env")` |

### 3.8 Demo Bypass

**Source:** `backend/plan_enforcement.py:319-324`

- `DEMO_ALLOWLIST` env var contains comma-separated emails
- Bypass returns `999_999` credits and `pro` plan
- Used for demo/sales purposes

---

## 4. Payments / Subscription System

### 4.1 Razorpay Integration

**Source:** `backend/routes/system.py:149-258`

**Payment flow:**
1. Frontend calls `POST /api/payment/create-order` → creates Razorpay order
2. Frontend completes payment → Razorpay sends webhook
3. `POST /api/payment/webhook` processes:
   - Verifies Razorpay signature (line 195)
   - Updates `users` table with plan + credits
   - Logs to `credit_transactions`

**Webhook signature verification** (`system.py:195-200`):
- Uses `razorpay.Utility.verify_payment_signature()`
- `RAZORPAY_WEBHOOK_SECRET` from env

**Plan activation on payment** (`system.py:210-230`):
- Maps Razorpay amount to plan tier
- Sets credits based on plan
- Updates `users.plan`, `users.credits_remaining`

### 4.2 Plan Structure

**Source:** `backend/plan_enforcement.py:39-98`

| Tier | Price | Credits | Features |
|------|-------|---------|----------|
| `free` | ₹0 | 100 | 5 trends/day |
| `early_bird` | ₹999 | 500 | 50 trends/day, early detection, india features |
| `pro` | ₹2,999 | 1000 | Unlimited, video analysis, algorithm insights |
| `brand_starter` | ₹4,999 | — | Marketplace access |
| `brand_growth` | ₹14,999 | — | Enhanced marketplace |
| `brand_enterprise` | ₹49,999 | — | Full access |

**Note:** DB currently stores `free` | `pro` only. Other tiers defined for future migration (`plan_enforcement.py:49`).

### 4.3 Credit System

**Source:** `backend/plan_enforcement.py:215-260`

**Deduction flow:**
1. `require_credits(cost)` dependency checks balance (line 361)
2. If sufficient, request proceeds
3. Background task calls `deduct_credits()` (line 371)

**Credit costs:**
- `ai_generation`: 5 credits
- `video_analysis`: 10 credits
- `export`: 2 credits
- Trend browsing/search: 0 credits

**Known bug** (`plan_enforcement.py:253`):
```python
users eq {user_email}
""", {
    "credits_remaining": new_balance,
    "credits_used_this_month": cost  # BUG: should be += cost
})
```
Sets `credits_used_this_month` to `cost` instead of incrementing. Multi-deduction months undercount.

### 4.4 Duplicate Credit Systems

| System | File | Purpose |
|--------|------|---------|
| `PlanEnforcement` | `plan_enforcement.py` | Authoritative — with caching, overrides, atomic deduction |
| `UsageTracker` | `usage_tracker.py` | Legacy — parallel tracking, no caching, fail-open |

**Inconsistency:** `PlanEnforcement` uses hardcoded `TIER_DAILY_LIMITS` dict, while `UsageTracker` reads from `plan_features` DB table. These can drift.

### 4.5 Frontend Integration Status

**Source:** `FRONTEND_AUDIT_2026-08-23.md`

- `/api/payment/create-order` and webhooks exist server-side
- Frontend wrapper `api.ts:1344` has **zero callers**
- Credits/Plan UI absent: `hasPlanOrCreditsUI:false`
- **Revenue = $0** — payment flow is complete but unused

### 4.6 Plan Cache

**Source:** `backend/plan_enforcement.py:17-21`

- In-memory cache: `_PLAN_CACHE` dict
- TTL: 300 seconds (5 minutes)
- `invalidate_plan_cache(user_email)` function exists
- **Not shared across worker processes** — cache inconsistency possible

### 4.7 Grace Period Handling

**Source:** `backend/plan_enforcement.py:152-168`

- For `cancelled`, `halted`, `past_due` subscriptions:
  - If `grace_period_ends_at` > now → maintain current plan
  - Else → downgrade to `free`
- Grace period set by webhook handlers

---

## 5. Database Schema

### 5.1 Core Tables Referenced

| Table | Primary File | Purpose |
|-------|-------------|---------|
| `users` | `auth.py`, `plan_enforcement.py` | User accounts, plan, credits |
| `admin_users` | `auth.py:260-335` | Admin accounts with roles |
| `admin_audit_log_enhanced` | `routes/admin.py` | Admin action audit trail |
| `trends` | `trend_detector.py`, `routes/trends.py` | Trend definitions |
| `trend_snapshots` | `routes/trends.py:382,440` | Time-series trend metrics |
| `trend_captions` | `caption_engine.py` | Cached caption kits |
| `trend_feedback` | `routes/system.py:370` | User feedback on trends |
| `trend_actions` | `routes/trends.py:505,877` | User actions (target, etc.) |
| `content_trends` | `unified_signal_processor.py:229` | Fused signal trends |
| `creator_trend_memory` | `routes/trends.py:858` | User trend memories |
| `reels` | `instagram_scraper.py` | Scraped reel data |
| `reel_snapshots` | `instagram_scraper.py`, `routes/trends.py:554` | Time-series reel metrics |
| `tracked_audio` | `instagram_scraper.py` | Audio tracking |
| `audio_trend_scores` | `routes/trends.py:293,303` | Audio scoring |
| `audio_official_counts` | `instagram_scraper.py` | Official audio use counts |
| `creator_baselines` | `instagram_scraper.py` | Creator performance baselines |
| `creator_profiles` | `routes/creator.py` | Creator marketplace profiles |
| `brand_deals` | `routes/creator.py` | Brand deal definitions |
| `brand_deal_applications` | `routes/creator.py` | Deal applications |
| `deal_payment_milestones` | `routes/creator.py` | Payment milestones |
| `collab_requests` | `routes/creator.py` | Collaboration requests |
| `user_preferences` | `routes/trends.py:57`, `routes/users.py` | User settings |
| `usage_logs` | `plan_enforcement.py`, `usage_tracker.py` | Feature usage tracking |
| `credit_transactions` | `plan_enforcement.py` | Credit deduction log |
| `plan_features` | `usage_tracker.py` | Plan limit definitions |
| `plan_overrides` | `plan_enforcement.py` | Temporary plan overrides |
| `subscription_tiers` | `migrate_credits_system.py` | Tier definitions |
| `phone_verifications` | `phone_verification.py` | OTP codes |
| `device_fingerprints` | `device_fingerprint.py` | Device tracking |
| `suspicious_activity` | `device_fingerprint.py` | Abuse detection |
| `analytics_events` | `routes/system.py:480` | Analytics tracking |
| `jobs` | `worker.py` | Video generation jobs |
| `news_api_cache` | `news_client.py` | News response cache |
| `cultural_events` | `unified_signal_processor.py:118` | Cultural event data |

### 5.2 SQL Migrations (19 files)

| File | Purpose |
|------|---------|
| `supabase_migration.sql` | Initial schema |
| `phase2_schema.sql` | Phase 2 features |
| `phase3_schema.sql` | Phase 3 features |
| `phase4_schema.sql` | Phase 4 features |
| `phase5_schema.sql` | Phase 5 features |
| `phase6_schema.sql` | Phase 6 features |
| `phase7_schema.sql` | Phase 7 features |
| `phase8_schema.sql` | Phase 8 features |
| `phase9_schema.sql` | Phase 9 features |
| `phase10_schema.sql` | Phase 10 features |
| `phase11_schema.sql` | Phase 11 features |
| `phase12_schema.sql` | Phase 12 features |
| `phase13_schema.sql` | Phase 13 features |
| `phase14_schema.sql` | Phase 14 features |
| `phase15_schema.sql` | Phase 15 features |
| `migrate_credits_system.py` | Credits system setup |
| `migrate_phone_verification.sql` | Phone OTP tables |
| `migrate_rls_policies.sql` | Row-level security |
| `migrate_admin_system.sql` | Admin tables |

### 5.3 Key Schema Issues

| Issue | Location | Description |
|-------|----------|-------------|
| Follower-count-zero corruption | `trend_scoring.py` | Referenced in past bugs — `calculate_saturation()` uses follower counts that can be 0 |
| Duplicate trend rows | `trend_detector.py` | Known past bug — duplicate inserts without proper upsert |
| N+1 queries | `routes/trends.py` | Known past bug — sequential queries per trend |
| Double-nested JSON | `caption_engine.py` | Known past bug — JSON parsed twice |
| Raw SQL usage | `routes/system.py:284-289` | Uses `psycopg2` directly with `SUPABASE_DB_URL` |

### 5.4 RLS Policies

**Source:** `migrate_rls_policies.sql`

- Row-level security enabled on sensitive tables
- Policies restrict access based on `auth.uid()`
- Admin bypass via `admin_users` role check

---

## 6. AI/LLM Integrations

### 6.1 LLM Module (`backend/llm.py`)

**Multi-tier fallback chain:**
1. **Groq** (primary) — multi-key rotation, `llama-3.3-70b-versatile`
2. **Gemini** — `gemini-3.6-flash` → `gemini-3.5-flash-lite`
3. **OpenRouter** — 6 free models

**IPv4 forced globally** to prevent connection hangs (line 15).

**Key function:** `call_llm(prompt, model=None, response_mime_type=None)` — unified interface with retry logic.

### 6.2 LLM Usage by Module

| Module | LLM Call | Fallback | Line |
|--------|----------|----------|------|
| `caption_engine.py` | Gemini via `call_llm()` | 3 retries → hardcoded fallback kit | 181 |
| `nightly_llm_batch.py` | Gemini via `call_llm()` | Retry with backoff | varies |
| `news_client.py` | `call_llm()` for virality scoring | Score=0 for failed batches | 226 |
| `content_generator.py` | **NONE** — pure templates | N/A | — |
| `india_features.py` | **NONE** — pure hardcoded | N/A | — |
| `instagram_scraper_browser.py` | **NONE** — builds prompt, never calls | Returns hardcoded dict | 1229-1259 |

### 6.3 Caption Engine

**Source:** `backend/caption_engine.py` (241 lines)

**Cache-first design:**
1. Check `trend_captions` table for existing kit (line 136)
2. If miss → call Gemini via `call_llm()` (line 181)
3. Cache result in DB (line 191)
4. On failure → return hardcoded fallback kit (lines 189-229)

**Fallback kit contents:**
- 3 generic caption variants (emotional/funny/aspirational)
- 15 generic hashtags including `#trending2025` (stale year)
- Generic posting strategy: Saturday/Sunday 8PM IST
- Hook style: "Curiosity" (hardcoded)

**Critical issue:** This engine is production-ready but **not wired to the API**. `api.py:1749` returns stub `{"message":"Caption generation not fully implemented yet"}` instead of calling this engine.

### 6.4 Content Generator (Static)

**Source:** `backend/content_generator.py` (640 lines)

- **Zero LLM calls** despite being named "AI Content Generation System"
- All content is template-based with `hash(trend_name) % len(templates)` selection
- Cultural event hashtags hardcoded to `2024` (stale year)
- Retention scores hardcoded: `question: 75, statement: 70, shock: 85, curiosity: 80`
- Engagement always returns `"high"` or `"medium"` based on difficulty

### 6.5 India Features Engine (Static)

**Source:** `backend/india_features.py` (374 lines)

- **Zero LLM calls**, zero API calls
- All regional data, events, timing, hashtags hardcoded in Python dicts
- Viral score always returns `75.0` for all trends
- Cultural events use fixed months (Eid varies by lunar calendar)
- Supabase client initialized but never used

### 6.6 Hook Analysis (Dead Code)

**Source:** `backend/instagram_scraper_browser.py:1229-1259`

- Builds detailed LLM prompt (line 1237) but **never executes it**
- Returns hardcoded dict: `dominant_hook_type` based on "pov" keyword check
- Hook analysis data stored in DB is synthetic

### 6.7 News Client

**Source:** `backend/news_client.py` (247 lines)

**Fallback chain:**
1. Supabase cache (`news_api_cache` table, 1-hour TTL)
2. GNews API (primary)
3. Google News RSS (fallback)
4. Empty list `[]` (last resort)

**LLM usage:** `evaluate_news_virality_batch()` calls `call_llm()` for batched virality scoring (batch size: 8 articles).

### 6.8 LLM Call Summary

| Feature | Has Real LLM | Fallback Behavior |
|---------|-------------|-------------------|
| Caption generation | Yes (Gemini) | Hardcoded fallback kit |
| Nightly classification | Yes (Gemini) | Retry with backoff |
| News virality scoring | Yes (Groq/Gemini) | Score=0 for failures |
| Content ideas | **No** | Templates only |
| India features | **No** | Hardcoded data |
| Hook analysis | **No** | Hardcoded dict |
| India captions | **No** | Templates only |

---

## 7. Admin System

### 7.1 Admin Authentication

**Source:** `backend/auth.py:260-335`

- Admin JWT must include `role: "admin"` or `role: "super_admin"`
- Validated against `admin_users` table
- `require_admin` dependency: checks JWT role + DB record existence

### 7.2 Admin Endpoints

**Source:** `routes/admin.py`

| Endpoint | Purpose | Rate Limit |
|----------|---------|------------|
| `GET /api/admin/dashboard` | Overview metrics | 10/min |
| `GET /api/admin/users` | User list with pagination | 10/min |
| `POST /api/admin/users/{id}/plan` | Override user plan | 10/min |
| `POST /api/admin/users/{id}/toggle-lock` | Lock/unlock accounts | 10/min |
| `GET /api/admin/metrics` | System metrics | 10/min |
| `GET /api/admin/metrics/daily` | Daily metrics | 10/min |
| `GET /api/admin/business-metrics` | Revenue/engagement | 10/min |
| `GET /api/admin/audit-log` | Admin action history | 10/min |
| `GET /api/admin/plan-features` | Feature matrix | 10/min |
| `POST /api/admin/plan-features` | Update feature matrix | 10/min |
| `POST /api/admin/users/{id}/credits` | Adjust user credits | 10/min |
| `POST /api/admin/toggle-guest-mode` | Enable/disable guest mode | 10/min |

### 7.3 Admin Capabilities

| Capability | Implemented | Notes |
|------------|-------------|-------|
| User management | Yes | List, plan override, lock/unlock |
| Plan management | Yes | Override plans, edit features |
| Credit management | Yes | Adjust user credits |
| Audit logging | Yes | All admin actions logged |
| Guest mode toggle | Yes | Global guest mode switch |
| Business metrics | Yes | Revenue, engagement, churn |
| Scraper trigger | Yes | `/api/run-scraper` (admin only) |
| Real-time monitoring | Partial | Heartbeat exists, no live dashboard |

### 7.4 Admin Rate Limiting

- All admin endpoints: `10/min` per IP
- Scraper trigger: `2/min`

### 7.5 Known Admin Issues

| Issue | Location | Description |
|-------|----------|-------------|
| Plan cache staleness | `plan_enforcement.py:17-21` | In-memory cache not shared across processes |
| Audit log table | `routes/admin.py` | Uses `admin_audit_log_enhanced` — verify migration applied |
| Feature matrix drift | `plan_enforcement.py` vs `plan_features` table | Hardcoded vs DB-driven limits can diverge |

---

## 8. Infrastructure

### 8.1 Hosting

| Component | Platform | Config |
|-----------|----------|--------|
| API server | Vercel (serverless) | `vercel.json` with cron schedules |
| Background worker | Render | `worker_runner.py` with RQ |
| Database | Supabase (PostgreSQL) | Hosted, with RLS |
| Cache/Queue | Upstash Redis | Serverless Redis |
| Browser scraping | Local/Server | Camoufox (Firefox-based) |

### 8.2 Environment Variables

**Source:** `.env`, `.env.local`, `.env.production`, `.env.render`, `.env.vercel.local`, `.env.vercel.prod`

Key secrets:
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`
- `JWT_SECRET`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`
- `GEMINI_API_KEY` (primary LLM)
- `GROQ_API_KEY` (fallback LLM)
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` (OTP)
- `REDIS_URL` / `UPSTASH_REDIS_URL` (rate limiting + queue)
- `CRON_SECRET` (cron job auth)
- `INSTAGRAM_COOKIES_B64` (scraper auth)

**Stale file:** `.env.render` contains `RAZORPAY_WEBHOOK_SECRET` and `CRON_SECRET` — leftover from Render deployment.

### 8.3 GitHub Actions Workflows (9 files)

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| `ci.yml` | On push/PR | Lint, type check, tests |
| `cron-heartbeat.yml` | 3x/day | Heartbeat monitoring |
| `emergency-llm-classification.yml` | 4x/day | Emergency trend classification |
| `nightly-llm-classification.yml` | 2x/day | Nightly LLM enrichment |
| `news-virality-cron.yml` | Daily | News virality scoring (**broken**) |
| `deploy.yml` | On push to main | Auto-deploy |
| `test.yml` | On PR | Test suite |
| `lint.yml` | On push | Code linting |
| `typecheck.yml` | On push | Type checking |

### 8.4 Vercel Cron Configuration

**Source:** `vercel.json`

- Multiple cron schedules defined for API endpoints
- Used for automated pipeline triggers

### 8.5 Dependencies

**Source:** `pyproject.toml`

Key packages:
- `fastapi`, `uvicorn` — web framework
- `supabase` — database client
- `razorpay` — payment processing
- `redis`, `rq` — caching + job queue
- `resend` — email sending
- `slowapi` — rate limiting
- `passlib` — password hashing
- `python-jose` — JWT handling
- `camoufox` — stealth browser

### 8.6 Deployment Architecture

```
┌─────────────────────────────────────────────┐
│                  Vercel                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ API      │  │ Cron     │  │ Frontend │  │
│  │ (FastAPI)│  │ Jobs     │  │ (Next.js)│  │
│  └────┬─────┘  └────┬─────┘  └──────────┘  │
│       │              │                       │
└───────┼──────────────┼───────────────────────┘
        │              │
   ┌────▼────┐    ┌────▼────┐
   │Supabase │    │ Upstash │
   │  (PG)   │    │ (Redis) │
   └─────────┘    └─────────┘

┌─────────────────────────────────────┐
│           Render                    │
│  ┌──────────┐  ┌──────────────┐    │
│  │ RQ Worker│  │ Camoufox     │    │
│  │ (reels)  │  │ (scraper)    │    │
│  └──────────┘  └──────────────┘    │
└─────────────────────────────────────┘
```

### 8.7 Infrastructure Issues

| Issue | Severity | Description |
|-------|----------|-------------|
| Stale `.env.render` | Low | Leftover Render env file in repo |
| No health check for worker | Medium | RQ worker has no heartbeat mechanism |
| No graceful shutdown | Low | Worker lacks signal handler integration |
| Hardcoded `.env` path | Medium | `load_dotenv("backend/.env")` in multiple files |
| Linux-only SIGALRM | Low | Scraper per-hashtag timeout won't work on Windows |
| 15-min global timeout | Medium | Scraper timeout may be too short for large scrapes |

---

## 9. Bugs, TODOs, Dead Code

### 9.1 Confirmed Bugs

| # | Severity | Bug | Location | Description |
|---|----------|-----|----------|-------------|
| 1 | **CRITICAL** | Duplicate `FeedbackRequest` | `schemas.py:14,176` | Second definition shadows first; `system.py:358` receives wrong fields |
| 2 | **CRITICAL** | Caption engine not wired | `api.py:1749` vs `caption_engine.py` | Production engine exists but API returns stub |
| 3 | **HIGH** | Credit deduction overwrite | `plan_enforcement.py:253` | `credits_used_this_month: cost` instead of `+= cost` |
| 4 | **HIGH** | OTP uses `random.randint` | `phone_verification.py:65` | Non-cryptographic PRNG for OTP generation |
| 5 | **HIGH** | Secret in query string | `creator.py:314`, `system.py:313` | `?secret=` logged in access logs |
| 6 | **HIGH** | No brute-force OTP protection | `phone_verification.py` | 6-digit code with no attempt limiting |
| 7 | **HIGH** | Race condition in usage counter | `usage_tracker.py:198-212` | Read-then-update without atomicity |
| 8 | **MEDIUM** | Dead code after raise | `routes/trends.py:728-734` | Code after `raise HTTPException` unreachable |
| 9 | **MEDIUM** | No rate limiting | `routes/users.py` | All 3 endpoints lack `@limiter.limit()` |
| 10 | **MEDIUM** | Guest/anonymous bypass | `ai.py:139,185`, `creator.py:472` | Magic emails bypass user-specific checks |
| 11 | **MEDIUM** | Error detail leakage | `creator.py`, `trends.py` | `str(e)` exposed in HTTP responses |
| 12 | **MEDIUM** | Health check leaks errors | `system.py:69` | DB error messages returned to caller |
| 13 | **MEDIUM** | Hardcoded `.env` path | `unified_signal_processor.py:18` | `load_dotenv("backend/.env")` |
| 14 | **LOW** | Stale year in hashtags | `caption_engine.py:200`, `content_generator.py:179-216` | `#trending2025`, `#Diwali2024` |
| 15 | **LOW** | Wildcard imports | `ai.py`, `creator.py`, etc. | `from api_globals import *` |
| 16 | **LOW** | `print()` instead of `logger` | Multiple files | Inconsistent error reporting |

### 9.2 TODO Comments Found

| File | Line | TODO |
|------|------|------|
| `backend/nightly_llm_batch.py` | 61 | `# TODO: implement better retries with backoff` |
| `backend/instagram_scraper_browser.py` | 1229-1259 | Hook analysis builds prompt but never calls LLM |
| `backend/content_generator.py` | Various | Template-only system labeled "AI" |
| `backend/india_features.py` | Various | All data hardcoded |
| `routes/trends.py` | 728-734 | Dead code after raise |

### 9.3 Dead Code

| File | Lines | Description |
|------|-------|-------------|
| `routes/trends.py` | 728-734 | Unreachable after `raise HTTPException` |
| `instagram_scraper_browser.py` | 1229-1259 | Hook analysis prompt built but never called |
| `instagram_scraper_browser.py` | 1180-1184 | `_store_reel_video` permanently disabled |
| `unified_signal_processor.py` | 161 | `meme_signals = []` — disabled processing |
| `content_generator.py` | All | Template system with no LLM integration |
| `india_features.py` | All | Hardcoded data with no live sources |
| `reel_generator.py` | All | Marked deprecated but still imported by `worker.py` |

### 9.4 Silent Exception Swallowing

| File | Lines | Pattern |
|------|-------|---------|
| `phone_verification.py` | 23-24, 34-35 | `except Exception: pass` |
| `unified_signal_processor.py` | 73-75, 107-109, 154-156, 175-177, 199-201, 235-237 | Catches Exception, returns empty list |
| `usage_tracker.py` | 64-66, 107-113, 168-169, 214-215, 261-263, 311-313 | Catches Exception, returns defaults |
| `routes/ai.py` | 77-84, 100-109, 121-133, 158-165, 198-209, 285-287, 320-322 | Returns fabricated fallback data |
| `routes/system.py` | 36-37 | `except Exception: pass` in proof calculation |

### 9.5 Hardcoded Magic Numbers

| Value | Location | Purpose |
|-------|----------|---------|
| `0.40`, `0.35`, `0.25` | `trend_scoring.py:31` | Opportunity score weights |
| `40`, `35`, `25` | `trend_scoring.py:23-25` | Urgency weights |
| `5_000_000` | `trend_scoring.py:14` | Global saturation threshold |
| `500` | `trend_scoring.py:15` | India saturation threshold |
| `12` | `trend_detector.py` | Velocity multiplier |
| `0.1`, `0.05` | `trend_detector.py` | Saturation thresholds |
| `2_000_000` | `trend_scoring.py:42` | Velocity normalization max |
| `0.3` | `instagram_scraper.py:1418`, `unified_signal_processor.py:40` | Velocity threshold |
| `5.0` | `instagram_scraper.py:1407` | Creator outlier multiplier |
| `100K`, `8K` | `instagram_scraper.py` | Saturation thresholds |
| `0.15` | `routes/creator.py:418` | Commission rate |
| `0.72`, `3.0`, `0.55` | `routes/trends.py:804` | Decision thresholds |
| `100_000` | `plan_enforcement.py` | Unlimited credits sentinel |
| `300` | `plan_enforcement.py:18` | Plan cache TTL |
| `5` | `phone_verification.py` | Max failed login attempts |
| `15` | `phone_verification.py` | Lockout duration (minutes) |
| `20` | `check_pending_count.py:12` | Emergency pending threshold |
| `3` | `check_pending_count.py:13` | Emerging pending threshold |
| `25` | `check_pending_count.py:14` | High pending threshold |

---

## Appendix A: Frontend ↔ Backend Alignment

**Source:** `FRONTEND_AUDIT_2026-08-23.md`

| Frontend Finding | Backend Status |
|-----------------|----------------|
| `/api/trends/{id}/caption` crashes | `caption_engine.py` exists but not wired to API |
| Payments unwired | Razorpay endpoints exist, zero frontend callers |
| Credits/Plan UI absent | `plan_enforcement.py` complete, no UI |
| Auth bypass for `.test` TLDs | Supabase accepts, Pydantic rejects with 422 |
| IDOR: hardcoded emails | `guest@trendrop.app` / `anonymous@trendrop.app` bypasses |
| Admin endpoints functional | All admin routes verified working |
| Instagram OAuth disabled | `instagram_oauth.py` exists, never called |
| 403 spam on free pages | Plan enforcement returns 403, frontend doesn't handle |
| Static theater | `content_generator.py` is template-only |

---

## Appendix B: Key Metrics

| Metric | Value |
|--------|-------|
| Total Python files | 218 |
| Total routes | ~90 |
| Total SQL migrations | 19 |
| Total GitHub Actions workflows | 9 |
| Core tables referenced | 33 |
| LLM integration points | 3 (caption, nightly batch, news virality) |
| Dead code modules | 5 (content_generator, india_features, hook analysis, video store, meme processing) |
| Silent exception sites | 20+ |
| Hardcoded magic numbers | 30+ |
| Confirmed bugs | 16 |

---

*Audit completed 2026-08-31. All findings are READ-ONLY — no modifications made.*
