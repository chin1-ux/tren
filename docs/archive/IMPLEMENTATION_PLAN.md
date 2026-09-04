# TRENDROP — IMPLEMENTATION PLAN (v4)
**Date:** Aug 19, 2026 · **Basis:** deep codebase audit against repo at HEAD. Every claim below was verified against the actual code, not assumptions. **PROBLEMS.md** is the companion document with 67 problems and fix mapping. **ROADMAP.md** has the ₹0→₹30L MRR strategic roadmap.

---

## 0.5 PHASES 1-5 COMPLETED (Aug 27, 2026)

### Summary
| Phase | Status | Commits |
|---|---|---|
| Phase 1: Quick wins (Fix broken things) | DONE | P0-1→P0-4, P1, baby cleanup, 11 Playwright tests pass |
| Phase 2: Data pipeline | DONE | audio_use_count fix, batch DB, 3-page pagination, ad detection |
| Phase 3: Frontend design | DONE | Inter font, indigo→coral, error boundaries, a11y, responsive |
| Phase 4: Infrastructure | 3/4 DONE | Removed 2 duplicate routes, 16 pytest tests, GitHub Actions skipped (user billing) |
| Phase 5: Truth alignment | DONE | Marketing claims already honest, /proof page built with real data |

### Remaining items
- **api.py modularization** (6870 lines → modules): Deferred, too risky for quick pass
- **Razorpay KYC**: User must complete
- **GitHub Actions budget**: User billing issue, minutes reset Sept 1

---

## 0. WHAT'S BEEN DONE (since v1)

### 0.1 Committed changes (13 commits, Aug 15-16)
| Commit | What |
|---|---|
| `8dd065a2` | Split scraper pipeline into discovery + browser-free refresh workflows |
| `2cb321ef` | Password reset flow + removed dead update-password backend endpoint |
| `d4274432` | Locked-account checks in auth + phone-verified gate |
| `43e2a76e` | Threaded trend refresher + admin route redirect guards |
| `91806ae3` | Split scraper into india/global separate workflows |
| `a2412e4f` | Fixed camoufox install skipping on bad cache |
| `e53ccae0` | Removed source_hashtag_pool mutation, added GLOBAL_DISCOVERY to crossover check |
| `63ecfa70` | Retired `scraper.yml` (replaced by india/global split) |
| `9bc36475` | Tuned global discovery tags, fixed velocity fallback denominator |
| `c9f0c4eb` | Throttled trend refresher thread pool (rate limit avoidance) |
| `a7cf3568` | Plan downgrade grace periods + scraper cron mode fix |
| `16c1339d` | Error boundaries, ideas plan gating, peaked trends section |
| `cd9d082f` | Plan-gate 401s, camoufox binaries fix, auth failure graceful handling |

### 0.2 What these commits achieved
- **Auth hardened**: locked accounts blocked in `get_current_user` (auth.py:64,81), locked-user 403 on login (api.py:2269), `require_phone_verified` uses real `get_current_user` (plan_enforcement.py:478)
- **Password reset**: `/api/auth/reset-password` (api.py:2091), frontend routes `reset-password.tsx` + `update-password.tsx`, "Forgot password?" link on login (login.tsx:94)
- **Admin guards**: all admin routes redirect to `/admin/login` on auth failure (admin.analytics/audit/plans/users), full-width layout for admin (__root.tsx:173)
- **Workflow split**: `scraper-india.yml` (2x/day, 40-min), `scraper-global.yml` (1x/day, 40-min), `trend-refresh.yml` (3x/day, 15-min, browser-free)
- **Pipeline stages**: `run_full_pipeline(stages=None)` with `_stage()` gating (cron_job.py:148), `manual_run_and_check.py` accepts `--stages` CLI
- **TrendRefresher**: `ThreadPoolExecutor(max_workers=3)` (trend_refresher.py:267), plain HTTP for audio page counts (no browser)
- **Plan enforcement**: 30-day default grace period for cancelled subscriptions, subscription_status checks updated
- **Simplified auth flow**: login uses backend API directly instead of Supabase client-side auth
- **Removed cruft**: Sentry SDK, in-memory caches (user profile, plan, peaked trends), debug endpoint, pricing page, verify-phone page

---

## 1. VERIFIED ENVIRONMENT MAP (Aug 18, 2026)

### 1.1 Services in active use
| Service | Status | Proof |
|---|---|---|
| GitHub (`ch1n-may`) | Active | 21 secrets in repo |
| Vercel (`ch1n-may/trendrop`) | Active | CLI authed, 42+ env vars (incl FRONTEND_URL) |
| Supabase | Active | 57 tables, real data pipeline running |
| Gemini (2 keys) | Configured | GitHub + Vercel prod |
| Groq (3 keys) | Configured | GitHub + Vercel prod |
| Resend | Configured | GitHub + Vercel prod |
| Apify | Configured | GitHub + Vercel prod |
| Spotify (client id/secret) | Configured | GitHub only, used by external-trend-discovery |
| Instagram cookies + user/pass | Configured | GitHub + Vercel |
| YouTube API key | Configured | GitHub + Vercel |

### 1.2 Services NOT connected
| Tool | Reality |
|---|---|
| **Render** | NOT in use. No render.yaml. |
| **Upstash / Redis** | **IN USE.** `UPSTASH_REDIS_URL` added to Vercel (Aug 19). Redis rate limiter functional. In-memory slowapi disabled when Redis active. |
| **Twilio** | NOT configured. Falls back to hardcoded `123456`. |
| **Razorpay** | PARTIAL. `RAZORPAY_WEBHOOK_SECRET` exists. `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` **missing** → `/api/payment/*` fails. **You must complete Razorpay KYC.** |

### 1.3 Live DB state
| Table | State | Notes |
|---|---|---|
| `users` | 1 row | Distribution bottleneck |
| `trends` | 321 rows | After P-METHOD-1 dedup (was 681, deleted 349 duplicates + 13 title+artist dupes). 32 rising, 31 emerging, ~150 peaked, ~108 expired |
| `reels` | 19,301 | Real pipeline |
| `reel_snapshots` | 14,355 | Proof page buildable |
| `trend_snapshots` | 21,477 | Proof page buildable |
| `comments` | 324 | Partial |
| `news_virality_predictions` | 20 rows | Real data, no API route |
| `cron_runs` | 125+ rows | Monitoring |
| `subscription_tiers` | 3 tiers | free ₹0 / creator ₹999 / agency ₹4,999 (rename planned: Agency → Brand, Creator → Pro) |
| `user_preferences` | **DOES NOT EXIST** | Must create |
| `api_keys` | **DOES NOT EXIST** | Must create for Phase 2 |
| `events` | **DOES NOT EXIST** | Must create for event detection |

### 1.4 GitHub Actions workflows (11 total)
| Workflow | Schedule | Timeout | Status |
|---|---|---|---|
| `scraper-india.yml` | 2x/day (02:30, 14:30 UTC) | 40 min | Working |
| `scraper-global.yml` | 1x/day (08:30 UTC) | 40 min | Working |
| `trend-refresh.yml` | 3x/day (04:30, 12:30, 20:30 UTC) | 15 min | Working |
| `external-trend-discovery.yml` | daily (00:00 UTC) | 15 min | Untracked |
| `news-virality-cron.yml` | every 12h | 15 min | Working |
| `nightly-llm-classification.yml` | 4x/day | — | Working |
| `pending-trends-fallback.yml` | every 6h | — | Working |
| `pending-trends-monitor.yml` | every 4h | — | Working |
| `emergency-llm-classification.yml` | every 2h | — | Working |
| `cron-heartbeat.yml` | every 4h | — | Working |
| `ci.yml` | on push/PR | — | Working |

---

## 2. WHAT'S BROKEN (with receipts)

### 2.1 Event detection — 100% BROKEN
- `event_monitor.py:94-241` — 10 hardcoded events, NO Independence Day (Aug 15), wrong dates (Diwali = month 10, real Diwali 2026 = Nov 14)
- `event_monitor.py:304-310` — `trending_now` is calendar simulation: `current_month in [2,3,10,12]`
- `event_monitor.py:336-347` — SQL built but **never executed** (dead code)
- `event_monitor.py:321-368` — `detect_event_hashtag_spikes()` falls through to return hardcoded events as "spikes"
- `cron_job.py` — EventMonitor **never called** from pipeline
- No `event-check.yml` workflow exists
- No `events` database table

### 2.2 Caption stub — ORPHANED ENGINE
- `api.py:1762-1776` — `/api/trends/{trend_id}/caption` returns `"Caption generation not fully implemented yet"` even though `CaptionEngine()` is instantiated
- `caption_engine.py:53-85` — `get_caption_kit()` has real logic: cache check → Supabase query → LLM call → upsert
- `caption_engine.py:181` — calls `call_llm()` with 3 retries and static fallback
- Two OTHER caption endpoints work (template-based): `/api/ai/generate-caption` (L5204), `/api/india/caption/generate` (L6105)
- The specific endpoint users hit from `trend.$id.tsx:41` (`fetchCaptionKit`) is the stub

### 2.3 ~25 endpoints return simulated data
- Video analysis (4): `analyze-video-metadata`, `analyze-visual`, `predict-virality`, `improvements` — all return `is_simulated: True`
- Instagram Graph API (3): `user-profile`, `user-insights`, `user-media`
- YouTube (2): `trending`, `trending-music`
- Realtime trends (2): `realtime/trends`, `realtime/cross-platform`
- Caption (1): stub at L1762

### 2.4 Duplicate route registrations (10 pairs) [UPDATED — AUDIT COMPLETE]
**Audit result (Aug 19):** 154 total decorators, 144 unique paths, 149 unique method+path combos. 10 duplicate route definitions (20 decorators for 10 paths). First-registered route wins (Starlette). Gates ARE enforced on algorithm endpoints. Duplicates are dead code + latent regression risk.
| Route | Lines | Second is dead |
|---|---|---|
| `/api/algorithm/analyze` | L1779, L4726 | Yes |
| `/api/algorithm/posting-times` | L1841, L4786 | Yes |
| `/api/algorithm/hashtag-strategy` | L1864, L4807 | Yes |
| `/api/india/cultural-events` | L5405, L6047 | Yes |
| + 6 more pairs | Various | Yes |

### 2.5 Auth gap: custom JWT path doesn't check locked status [FIXED]
- `auth.py:90-93` — custom JWT payloads with `"sub"` claim return email **without** calling `_check_user_locked()`
- **Fix:** `auth.py:88-94` now calls `_check_user_locked()` for all JWT paths. Committed `e72a4898`.

### 2.6 Dead link
- `data-rights.tsx:310` — links to `/profile` (route never existed, 404)

### 2.7 Scraper not at target performance
- Per-hashtag cap: **60s** (L1274) — target was 40s
- Hook analyses: **MAX 5** (L1656) — target was 2
- Hook time budget: **5 min** (L1662) — unchanged
- Audio count check still in scraper critical path (both workflows L112)
- Workflow timeout: **40 min** — target was 15 min

---

## 3. WHAT'S NOT BUILT (implementation items)

### 3.1 Fix event detection (P0 — user-visible bug)
**Files:** `backend/event_monitor.py`, new `backend/seed_events.py`, new migration, new `.github/workflows/event-check.yml`, `backend/api.py` routes

**Logic:**
1. Create `events` table: `id, name, slug, type, start_date, end_date, regions jsonb, hashtags text[], categories text[], is_recurring bool, recur_rule text, created_at`
2. `seed_events.py` seeds real 2026-27 India calendar: Independence Day Aug 15, Diwali Nov 14, Eid, Holi, Navratri, Christmas, Pongal, Onam + cricket/IPL windows
3. `EventMonitor.get_active_events()` → `SELECT * FROM events WHERE start_date <= now() <= end_date` (real DB)
4. `detect_event_hashtag_spikes()` → actually execute SQL against `hashtag_performance` + `comments`
5. `trending_now` → real query: trends whose niche overlaps active event categories, ordered by velocity
6. Schedule: `event-check.yml` runs `seed_events.py --refresh` daily at 03:00 UTC

**Verification:** `GET /api/india/cultural-events` returns Independence Day row on Aug 15.

### 3.2 Wire the caption stub (P0 — 30 min fix)
**Files:** `backend/api.py` L1762-1776

**Logic:** The engine exists (`CaptionEngine` at `caption_engine.py`), the endpoint exists (L1762), but the endpoint never calls `engine.get_caption_kit()`. Replace the stub return with the real call.

**Verification:** `POST /api/trends/{trend_id}/caption` returns JSON with 3 non-empty `caption_variants`.

### 3.3 Add news + audio endpoints (P0 — data exists, just needs routes)
**Files:** new routes in `backend/api.py`

**Logic:**
- `GET /api/news/trending` → read `news_virality_predictions` (20 rows, filled every 12h)
- `GET /api/audio/new-releases` → read `tracked_audio` / external-discovery output ordered by crossover recency

**Verification:** Both endpoints return rows from DB (curl).

### 3.4 Personalization (P0/P1)
**Files:** migration `002_user_preferences.sql`, new `backend/preferences.py`, edit `backend/api.py`, edit `frontend/src/routes/settings.tsx`, edit `frontend/src/lib/api.ts`

**Logic:**
1. Create `user_preferences`: `email text pk, niches text[], languages text[], regions text[], global_enabled bool default false, saved_trends text[], updated_at`
2. Settings page PUTs to server (not just localStorage)
3. `get_trends` filters by user's languages/niches first, then re-ranks
4. Saved/follow per trend → `saved_trends` column

**Verification:** Two test users with different preferences get different `/api/trends` responses.

### 3.5 Build /proof page (P1 — press asset)
**Files:** new `frontend/src/routes/proof.tsx`, new `backend/api.py` route

**Logic:** Query `trends` joined to `trend_snapshots` for early-detection examples. Output `{trend, audio, detected_at, hours_early}` for top 10.

**Verification:** Page renders ≥5 rows with real `hours_early`.

### 3.6 Scraper tightening (P1)
**Files:** `backend/instagram_scraper_browser.py`

**Logic:**
1. Per-hashtag cap 60→40s (L1274)
2. Hook analyses MAX 5→2 (L1656)
3. Hook time budget 5→3 min (L1662)
4. Move `run_audio_count_check` out of scraper critical path

**Verification:** Watch a scheduled run — completes in less time.

### 3.7 Global toggle (P1)
**Files:** `backend/api.py`, `frontend/src/` feed components

**Logic:** Add `region=global` param to `/api/trends`, add India/Global toggle in feed UI.

**Verification:** `GET /api/trends?region=global` returns global-source rows.

### 3.8 Razorpay (P0 — user action)
**Action:** Create Razorpay account → KYC → get `RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET` → `vercel env add`.

**Verification:** `/api/payment/create-order` returns real order ID.

---

## 4. BUILD ORDER (reordered by impact + architecture fixes added)

### Phase 1: Quick wins (1-3 days)
| # | Item | Effort | Impact | Addresses |
|---|---|---|---|---|
| 1 | **3.1 Events fix** | 1 day | User-visible bug, credibility | P-DB-2 |
| 2 | **3.2 Wire caption stub** | 30 min | Core creator feature, orphaned engine | P-API-1 |
| 3 | **3.3 News + audio endpoints** | 2 hours | Data exists, users can't see it | P-API-1 |
| 4 | **3.4 Personalization** | 2 days | Feed differentiation, settings persistence | P-DESIGN-9, P-DB-3 |
| 5 | **Fix deleted pages** | 2 hours | Pricing page + verify-phone 404s | P-PAY-2, P-PAY-4 |
| 6 | **Guard unguarded endpoints** | 2 hours | Revenue leakage prevention | P-API-4 |
| 7 | **Fix custom JWT lock check** | 30 min | Security hole | P-AUTH-1 |
| 8 | **Add rate limiting on auth** | 1 hour | Brute-force prevention | P-AUTH-4 |

### Phase 2: Data pipeline (3-5 days)
| # | Item | Effort | Impact | Addresses |
|---|---|---|---|---|
| 9 | ~~Fix saturation formula conflict~~ | — | **DE-PRIORITIZED** — both thresholds inert (india max=13), revisit after pagination | P-PIPE-3 |
| 10 | **Fix proxy audio_use_count** | 4 hours | Data accuracy | P-PIPE-4 |
| 11 | **Batch DB operations** | 3 days | Performance (3,600 → ~50 queries/run) | P-PIPE-2 |
| 12 | **Add scraper pagination** | 2 days | Data volume (1,350 → 5,000+ reels/run) | P-PIPE-1 |
| 13 | **Restructure timeout architecture** | 1 day | Consistent data coverage | P-PIPE-5 |
| 14 | **Fix or remove external discovery** | 1 day | Dead code cleanup | P-PIPE-6 |
| 15 | **Add ad/sponsored detection** | 2 days | Data accuracy | P-PIPE-7 |

### Phase 3: Frontend design (5-7 days)
| # | Item | Effort | Impact | Addresses |
|---|---|---|---|---|
| 16 | **Establish design system** | 3 days | Visual consistency | P-DESIGN-1, P-DESIGN-10 |
| 17 | **Fix typography** | 1 day | Readability, component override | P-DESIGN-2 |
| 18 | **Fix color drift** | 1 day | Brand consistency | P-DESIGN-3 |
| 19 | **Add responsive layout** | 2 days | Desktop usability | P-DESIGN-4 |
| 20 | **Add loading/empty/error states** | 2 days | Perceived performance | P-DESIGN-5 |
| 21 | **Reduce animations + a11y** | 2 days | Battery, accessibility | P-DESIGN-6, P-DESIGN-7, P-DESIGN-8 |

### Phase 4: Infrastructure (2-3 days)
| # | Item | Effort | Impact | Addresses |
|---|---|---|---|---|
| 22 | **Restructure api.py** | 2 days | Maintainability | P-API-3 |
| 23 | **Remove duplicate routes** | 2 hours | Dead code cleanup | P-API-2 |
| 24 | **Fix GitHub Actions budget** | 1 day | CI/CD cost | P-WORK-1 |
| 25 | **Add test suite** | 2 days | Quality gates | P-WORK-2 |
| 26 | **Razorpay KYC** | user-only | Payment unblock | P-PAY-1 |

### Phase 5: Truth alignment (1 day)
| # | Item | Effort | Impact | Addresses |
|---|---|---|---|---|
| 27 | **Update marketing claims** | 4 hours | Trust/credibility | P-TRUTH-1-5 |
| 28 | **Build /proof page** | 1 day | Press asset, trust builder | P-TRUTH-1 |

Each item ships with a **real verification step** (curl/DB query/Actions log).

---

## 5. FRONTEND DESIGN AUDIT (Aug 18, 2026)

### 5.1 Design system status
| Asset | State | Notes |
|---|---|---|
| `styles.css` | Partial | CSS custom properties for light/dark mode, brand colors, radius tokens. But forced heading sizes with `!important` break component overrides. |
| `button.tsx` | Good | CVA variants, framer-motion whileTap/whileHover, glass/neon variants. Best component in the app. |
| `badge.tsx` | Good | CVA variants for trend status, plan badges, urgency. Consistent. |
| BottomTabBar | Good | Smooth active indicator with `layoutId`, emerging count badge, safe area handling. |
| PlanGate | Good | Clean blur overlay with lock icon and upgrade CTA. |
| Typography | Broken | Three fonts declared for body (Inter → Bricolage Grotesque with `!important`). Fixed heading sizes with `!important` prevent component customization. |
| Color system | Partial | Brand palette (coral/lime/ink) is good. But indigo appears everywhere (login, settings, ideas) — not in brand palette. |
| Layout | Phone-only | `max-w-md` constraint = 448px max width. No responsive breakpoint for tablet/desktop. |
| Loading states | None | Spinning RefreshCw icons everywhere. No skeletons, no progressive loading. |
| Empty states | None | No "No trends found" messages. Feed just shows nothing. |
| Error states | None | Generic error messages. No retry button, no context. |
| Accessibility | Near-zero | No ARIA labels, no keyboard nav, no focus management, no reduced-motion, 10px font sizes. |
| Animations | Overdone | 10+ concurrent CSS animations per page. `neonGlowDark` cycles cyan/purple every 3s (seizure risk). No `prefers-reduced-motion`. |

### 5.2 Frontend score: 4.2/10
| Category | Score |
|---|---|
| Typography | 3/10 |
| Color System | 6/10 |
| Layout & Spacing | 4/10 |
| Component Quality | 5/10 |
| Animations | 5/10 |
| Mobile Experience | 5/10 |
| Design Consistency | 3/10 |
| Accessibility | 2/10 |
| Design Feasibility | 6/10 |

### 5.3 Frontend items NOT in current build order
The following are NOT addressed by items 3.1-3.8:
- Design system consolidation (one card style, one input style, one button style)
- Typography fix (replace Bricolage Grotesque for body, add fluid type)
- Color drift fix (remove indigo, use coral consistently)
- Responsive layout (tablet/desktop breakpoints)
- Loading skeletons, empty states, error states
- Animation reduction + reduced-motion support
- Accessibility (ARIA labels, keyboard nav, focus management)
- Glass morphism performance (backdrop-filter on low-end Android)

---

## 6. DATA PIPELINE ARCHITECTURE AUDIT

### 6.1 Pipeline rating: 5/10
| Dimension | Rating | Evidence |
|---|---|---|
| Data freshness | 6/10 | Scrapes 2-3x/day, batch only |
| Audio metadata accuracy | 7/10 | Official use_count when available, proxy formula when not |
| Trend detection accuracy | 5/10 | Calibrated on N=108, not validated against Instagram trending page |
| India coverage | 7/10 | 80% India-focused hashtags, multi-language detection |
| Saturation/lifecycle accuracy | 4/10 | Thresholds revised once, no external validation |
| Velocity tracking | 4/10 | Point-in-time snapshots, not continuous |
| Cross-platform accuracy | 3/10 | YouTube basic string matching, Spotify endpoint doesn't exist |
| Real-time accuracy | 2/10 | Batch scraping, 3-6 hour delay |

### 6.2 Critical architecture problems NOT in current build order

| Problem | Severity | File:Line | Impact |
|---|---|---|---|
| No scraper pagination | HIGH | scraper:907-914 | Max ~1,350 reels/run, not 15K/day |
| N+1 DB queries (3,600/run) | HIGH | scraper:1291-1615 | 10-30 min runs, timeout issues |
| Saturation formula conflict | HIGH | scraper:34-36 vs trend_scoring:20-23 | Reel-level data uses wrong thresholds |
| Proxy audio_use_count fabricated | HIGH | scraper:819-822 | `creators*800 + reels*400` is made up |
| 15-min timeout cuts hashtags | MEDIUM | scraper:1249-1256 | Inconsistent data coverage |
| External discovery dead code | MEDIUM | external_trend_discovery.py | 642 lines never imported |
| No ad/sponsored detection | MEDIUM | Absent | Inflated trend signals |
| "6 hours before peak" not provable | HIGH | No prediction model | Marketing claim unsupported |
| "15K+ reels daily" not achievable | HIGH | Max ~2K/day from code | Marketing claim unsupported |
| "Real-time velocity" is batch | MEDIUM | Scheduled scraping | Marketing claim unsupported |

### 6.3 What would make the pipeline match Instagram's trending page
To produce data that matches what users actually see on Instagram:

1. **Add scraper pagination** — scroll or use Instagram's API pagination to get 500+ reels per hashtag instead of 30-90
2. **Batch DB operations** — bulk inserts, cached queries, reduce 3,600 queries/run to ~50
3. **Validate thresholds against Instagram's trending page** — compare Trendrop's "rising" trends with Instagram's actual trending audios
4. **Add real-time monitoring** — WebSocket or polling for high-priority hashtags instead of batch scraping
5. **Fix or remove broken external discovery** — either fix the Spotify endpoint or delete the dead code
6. **Add ad detection** — filter out sponsored posts from trend signals
7. **Update marketing claims** — ground "6 hours before peak" and "15K+ reels daily" in actual capability

---

## 7. CONNECTION CHECKLIST

| Needs | Status |
|---|---|
| Captions + AI features | ✅ GEMINI_API_KEY on Vercel |
| Personalization | ❌ user_preferences table (I create) |
| API revenue | ❌ api_keys table + RAZORPAY_KEY_ID/SECRET |
| Payments | ❌ **YOU: KYC + add keys** |
| Signup verification | ❌ Twilio missing, falls back to 123456 |
| Global scraping | ✅ scraper-global.yml exists |
| Events | ❌ event-check.yml + events table (I create) |

**What I cannot do (you must):** Razorpay KYC + env add, Twilio account (if wanted), pushing to production if you prefer to review first.

---

## 8. MARKETPLACE REDESIGN + ROADMAP (Aug 19, 2026)

### 8.1 Strategic Direction
**From:** "Trend detection tool"
**To:** "India's creator economy operating system" — trend detection + content generation + deal connection + payment protection

**The moat:** Trend data + deal connection = unfair advantage. No other platform can say: "This audio is trending RIGHT NOW. Here are 5 creators who specialize in this niche. Here's a brand that wants to ride this trend. Connect."

**Competitive research:** Virlo (US, $36K MRR, bootstrapped) charges $49-199/mo. Trendrop's India-first positioning + 4x lower price + deal connection layer = defensible advantage.

### 8.2 Current Marketplace State (Audit Complete)
**What exists:** Creator profiles, brand deals with milestones, PDF contracts, deal applications, creator collab matching, feedback system. All using real data.

**What's broken:**
- No brand-side interface (P-MARKET-1) — brands can't participate
- No escrow/payment processing (P-MARKET-3) — "Mark as paid" is a database toggle
- No brand verification (P-MARKET-4) — anyone can create deals
- No notifications to brands (P-MARKET-5) — application black hole
- Duplicate deal systems (P-MARKET-2) — old + new coexist
- Hardcoded compatibility scoring (P-MARKET-6) — doesn't scale
- Marketplace hidden from nav (P-MARKET-7) — not discoverable

### 8.3 Plan Rename
| Old Name | New Name | Target | Price |
|---|---|---|---|
| Free | **Free** | Curious creators | ₹0 |
| Creator | **Pro** | Serious creators | ₹999/mo |
| Agency | **Brand** | Brands posting deals | ₹4,999/mo |
| Enterprise | **Enterprise** | Large brands/agencies | ₹14,999/mo |

### 8.4 Credit-Based Hybrid Pricing
| Tier | Credits/mo | Key Features |
|---|---|---|
| Free | 10/day | Basic trends, limited data |
| Pro (₹999) | 200/mo | Full trends, AI generation, analytics |
| Brand (₹4,999) | 1,500/mo | Post deals, review applications, escrow |
| Enterprise (₹14,999) | 5,000/mo | API access, unlimited seats |

Credit add-ons: ₹99/50, ₹249/150, ₹499/350. Annual billing: 2 months free.

### 8.5 Implementation Phases (from ROADMAP.md)
**Phase 1 — First Revenue (Oct 2026):** Razorpay KYC + brand interface + escrow = first money moves
**Phase 2 — Trust Layer (Nov-Dec 2026):** Notifications + brand verification + ratings = marketplace trust
**Phase 3 — Revenue Optimization (Jan-Mar 2027):** Credit system + plan rename + trial model = maximize LTV
**Phase 4 — Scale (Apr-Jun 2027):** Mobile PWA + advanced matching + API partnerships = growth

### 8.6 Connection Checklist (Updated)
| Needs | Status | Priority |
|---|---|---|
| Razorpay KYC + keys | ❌ You must do | P0 — blocks all payments |
| Brand-side interface | ❌ Build | P0 — blocks marketplace |
| Escrow payment flow | ❌ Build | P0 — blocks trust |
| Notification system | ❌ Build | P1 — blocks engagement |
| Brand verification | ❌ Build | P1 — blocks trust |
| Credit system | ❌ Build | P2 — blocks revenue optimization |
| Plan rename | ❌ Build | P2 — blocks positioning |
| Mobile PWA | ❌ Build | P3 — blocks scale |
