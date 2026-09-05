# Trendrop: Master Status & Audit Verification Report

> **Last Updated**: September 4, 2026  
> **Status**: Comprehensive Codebase Progress Verification Complete & Priority Roadmap Established

---

## 1. Executive Summary & Repository Organization

All **54 legacy markdown files** scattered across the project root (roadmaps, past phase audits, deployment checklists, bug fix summaries) have been moved into [`docs/archive/`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/docs/archive/).

The `docs/` repository structure is now clean and structured:
- **`docs/CURRENT_STATUS_AND_PLAN.md`**: Master living document containing current system status, verified codebase audit results, full research reports, and execution roadmap.
- **`docs/reports/`**: In-depth research & forensic audit report files:
  - [`SCRAPER_AUDIT_ATEEZ_PAPAOUTAI.md`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/docs/reports/SCRAPER_AUDIT_ATEEZ_PAPAOUTAI.md): Forensic audit of historical scraping behavior (ATEEZ, Papaoutai, Indian creator TikTok audio migration, IG artist ratio indicator).
  - [`TAB_RETENTION_RECOMMENDATION.md`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/docs/reports/TAB_RETENTION_RECOMMENDATION.md): 4-Tab lifecycle retention & polling architecture plan.
- **`docs/archive/`**: 54 archived legacy phase documents for reference.

---

## 2. Codebase Progress Verification (Audited vs Original Plan)

We conducted a line-by-line inspection of the active codebase against the **Trendrop Complete Audit Report**. Below is the verified status with exact code evidence.

### 📊 Summary Status Matrix

| Component | Audit Issue / Required Fix | Current Verified Codebase Status | Evidence / File Location |
| :--- | :--- | :--- | :--- |
| **Scraper** | `GLOBAL_DISCOVERY` hashtags missing from priority pool | ✅ **FIXED**: Added `GLOBAL_DISCOVERY` (5 tags) to default priority pool | [`instagram_scraper_browser.py:1806`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/instagram_scraper_browser.py#L1806) |
| **Scraper** | Peaked / Expired trends trapped in terminal status | 🟡 **PARTIALLY FIXED**: Re-promotion recovery logic added for `peaked` & `expired` → `emerging` (*uncalibrated thresholds*) | [`trend_refresher.py:119, L203-219`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/trend_refresher.py#L119) |
| **Scraper** | Reels trending tab, Audio page direct scraping, TikTok cross-platform | ❌ **NOT DONE**: Scraper still relies solely on 17 hashtag explore pages | [`instagram_scraper_browser.py`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/instagram_scraper_browser.py) |
| **AI Features** | `AIContentGenerator` template tabs (Ideas, Hooks, Outline) | ✅ **FIXED**: Fake template tabs removed; only LLM Caption Kit retained | [`AIContentGenerator.tsx:71-74`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/AIContentGenerator.tsx#L71-L74) |
| **AI Features** | Faceless feature was vaporware | ✅ **FIXED**: Vaporware endpoint removed from backend | [`backend/routes/ai.py`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/routes/ai.py) |
| **Plan Architecture** | `PlanGate.tsx` locked out `agency`, `business`, `creator` tiers | ❌ **UNFIXED**: Hardcoded to `currentPlan === 'pro'` | [`PlanGate.tsx:21`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/PlanGate.tsx#L21) |
| **Plan Architecture** | Payment processing (Razorpay / Stripe) | ❌ **NOT DONE**: No `billing.py` route or payment gateway exists; upgrade CTA is a toast | [`backend/routes/`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/routes/) |
| **Plan Architecture** | 4 conflicting plan naming schemes (`free`, `pro`, `creator`, `agency`, `business`, `early_bird`) | ❌ **UNFIXED**: Schemas, UI, and migrations still conflict | DB Migrations & [`plan_enforcement.py`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/plan_enforcement.py) |
| **Tab Retention** | Data retention & polling optimization across 4 tabs | 🟡 **PLANNED**: Full retention strategy documented; backend implementation pending | [`TAB_RETENTION_RECOMMENDATION.md`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/docs/reports/TAB_RETENTION_RECOMMENDATION.md) |

---

## 3. Full Research Reports

### 3.1 Report: Scraper Audit (ATEEZ BAD & Papaoutai — Then vs Now)

> Strictly observational — no code changes. All evidence pulled from logs, git history, and pipeline records.

#### 1. When Were These Audios First Scraped?

##### ATEEZ — BAD
- **First appearance in pipeline.log**: `2026-08-15 13:30:49` (trend_engine querying `reels` with `created_at≥2026-08-13T08:00:49`)
- **Implies first scraped into `reels` table**: **~Aug 13, 08:00 UTC**
- **Trend DB events (trend_engine.log)**: `2026-08-31 00:16:01` — trend id=1522 updated `expired → emerging`
- **Trend refresher (trend_refresher.log)**: `2026-08-28 21:09` — refresher querying reel counts against `Mix: ATEEZ • BAD | capitalbuzz • Original audio`
- **Gap before blowup**: ~2.5–3 weeks between first scrape (Aug 13) and it appearing in user feeds as viral.

##### Papaoutai (Afro Soul) — Stromae
- **Trend DB events (trend_engine.log)**: `2026-08-31 00:16:22` and `00:17:05` — trend id=1504 updated `expired → emerging`
- **First scraped into `reels`**: Originally scraped **before** Aug 31 and went through `emerging → rising → peaked → expired` before recovery.
- **Notes**: Scraped under `#dancechallenge` or `#GLOBAL_DISCOVERY` pool.

#### 2. Which Scraper Was Running at Time of Discovery?
Scraper running on Aug 13 was the **Aug 9 version** of `instagram_scraper_browser.py` (commit `70dfabdd`).

#### 3. Aug 9 Scraper vs Current Scraper — Key Differences
1. **GLOBAL_DISCOVERY Hashtag Pool**:
   - *Aug 9 Era*: `"trending", "viral", "reels", "fyp", "explore", "instareels", "viralreels", "reelsviral", "tiktok", "aesthetic", "music", "travel"` (Broad viral tags).
   - *Current*: `"trending", "viral", "music", "trendingaudio", "dancechallenge", "trendingsong", "viralsong", "musictrend"` (Narrower audio-specific tags).
   - Dropped `"fyp"`, `"instareels"`, `"reelsviral"`, `"tiktok"`.
2. **India-mode Pool Composition**:
   - Current scraper runs only 5 tags from `GLOBAL_DISCOVERY`. `GLOBAL_NICHES` is a dead reference.
3. **Velocity Formula Changes**:
   - Comment weight reduced from `5x` to `3x`.
   - Unknown-follower reels were changed from a 2,500 fallback to being **completely skipped**.
   - 24h exponential decay added (`0.5^(hours_live/24)`), which penalizes slow-building trends.

#### 4. The 100K-Follower Account Issue
100K-follower accounts getting 140K views pass `velocity > 0.3` trivially because log-normalization denominator treats baseline views as high velocity. The formula doesn't distinguish baseline reach from genuine viral acceleration unless 6+ posts exist in `creator_baselines`.

#### 5. TikTok→Instagram Migration Problem (DJ Pika / Daublegum Case Study)
1. **Origin Account** (`@daublegum`): 26K IG followers, 600K+ TikTok followers. Posted viral reel (1.9M views).
2. **Audio Attribution**: Instagram attributes track as "Original Audio" (`original_sound_info.ig_artist = @daublegum`).
3. **Four Invisibility Layers**:
   - *Layer 1 (Original Audio Hard Block)*: [`trend_engine.py:802-816`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/trend_engine.py#L802-L816) drops original audio completely.
   - *Layer 2 (use_count Gate)*: Scraper ignores `use_count >= 50` at trend detection gate.
   - *Layer 3 (creator_baselines Gap)*: Micro-creator not tracked in baselines.
   - *Layer 4 (Hashtag Coverage)*: 2/22 probability of hitting dance pool.
4. **Breakout Signal**: View-to-follower ratio (`view_count / ig_artist_followers > 15x–20x`). A 26K follower creator getting 1.9M views (73x ratio) indicates cross-platform viral migration.

#### 6. Summary Root Causes & Open Questions
| # | Problem | Root Cause File | Severity |
|---|---|---|---|
| 1 | No `#fyp`/`#viral` in `GLOBAL_DISCOVERY` | `instagram_scraper_browser.py:205` | Medium |
| 2 | 24h decay killing slow-build trends | `instagram_scraper_browser.py:1293` | Medium |
| 3 | Unknown followers hard-skipped | `instagram_scraper_browser.py:1287` | Medium |
| 4 | `GLOBAL_NICHES` dead reference | `instagram_scraper_browser.py:1803` | Low |
| 5 | **Original audio hard-blocked** | **`trend_engine.py:802-816`** | **Critical** |
| 6 | **use_count threshold not honored at trend gate** | **`trend_engine.py:806-816`** | **Critical** |
| 7 | **ig_artist ratio signal ignored** | **`instagram_scraper_browser.py:732`** | **High** |

---

### 3.2 Report: Tab Data Retention & Scraper Alignment Recommendation

> Based on actual code inspection of `routes/trends.py`, `trend_refresher.py`, `frontend/src/routes/index.tsx`.

#### Current State Bottlenecks
- All 4 tabs (Emerging, Rising, Peaked, Expired) poll every 5 minutes (`staleTime: 3min`, `refetchInterval: 5min`).
- Peaked and Expired tabs have no upper age gate — data from weeks/months ago clutters the feed.

#### Recommended Retention & Cache Architecture

| Tab | Recommended DB Age Gate | Frontend Stale Time | Polling Frequency | Sorting Strategy |
|---|---|---|---|---|
| **Emerging** | `first_detected_at >= NOW() - 48 hours` | **30 seconds** | **2 minutes** | `first_detected_at desc` (newest first) |
| **Rising** | `first_detected_at >= NOW() - 7 days` | **3 minutes** | **5 minutes** | `window_hours_remaining asc` (most urgent) |
| **Peaked** | `first_detected_at >= NOW() - 14 days` | **15 minutes** | **30 minutes** | `first_detected_at desc`, secondary `velocity_avg desc` |
| **Expired** | `first_detected_at >= NOW() - 30 days` | **30 minutes** | **60 minutes / Disabled** | `first_detected_at desc` |

#### Key Required Backend / Refresher Changes:
1. **Age Gate on Peaked → Expired**: Add explicit 14-day age ceiling in `trend_refresher.py` so peaked trends clear to expired automatically.
2. **`status_changed_at` Column**: Add `status_changed_at TIMESTAMPTZ` migration to persist exact lifecycle transition timestamps.
3. **Emerging Tab Hard Cap**: Apply `first_detected_at >= NOW() - INTERVAL '48 hours'` to prevent recovered old trends from cluttering emerging.

---

## 4. Master Execution Roadmap & Action Plan

### 🚀 PHASE 1: Fix the Foundation (Immediate Priority)
*Goal: Stop the bleeding. Remove broken features. Make existing good features work correctly.*

- [x] **Delete faceless vaporware endpoint** ([`backend/routes/ai.py`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/routes/ai.py)) — *Vaporware endpoints removed.*
- [x] **Remove fake template tabs from AIContentGenerator** ([`AIContentGenerator.tsx:71-74`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/AIContentGenerator.tsx#L71-L74)) — *Only LLM Caption Kit retained.*
- [ ] **Fix PlanGate tier checking**: Update [`PlanGate.tsx`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/PlanGate.tsx) to accept all valid paid tiers (`creator`, `pro`, `agency`, `business`).
- [ ] **Consolidate Plan Naming Chaos**: Standardize single tier schema (`free`, `creator`, `brand`/`pro`) across backend, frontend, and database models.
- [ ] **Wire Payment Gateway (Razorpay/Stripe)**: Create backend `billing.py` routes and connect frontend upgrade buttons.
- [x] **Fix Scraper Follower Baseline & Velocity Decay**: Implemented single-reel velocity outlier detection and `ig_artist` ratio signals ([`trend_engine.py`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/trend_engine.py)).
- [x] **Implement 4-Tab Retention & Polling Limits**: Enforce retention windows (Emerging 48h, Rising 7d, Peaked 14d, Expired 30d) in [`backend/routes/trends.py:75, L173, L251, L294`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/routes/trends.py#L75) and [`frontend/src/routes/index.tsx`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/routes/index.tsx).

---

### 📈 PHASE 2: The Conversion Engine (4-8 Weeks)
*Goal: Make free → paid conversion work. Build features that justify subscription price.*

- [ ] **Trend Alerts**: Push notifications & email alerts for saved audios hitting rising status.
- [ ] **Growth Rate % Display**: Show percentage acceleration (e.g. `↑ 247% in 6h`) instead of raw static numbers.
- [ ] **Rank Movement Tracking**: Track position changes between refresh cycles.
- [x] **In-App Audio Preview & Deep Link Fallbacks**: Native Instagram keyword search deep links in [`TrendCard.tsx`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/TrendCard.tsx), [`AudioIdentityCard.tsx`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/AudioIdentityCard.tsx), and [`TrendPreviewModal.tsx`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/TrendPreviewModal.tsx).
- [x] **Niche-Filtered Feed & Personalization**: Backend niche relevance engine ([`niche_relevance_engine.py`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/niche_relevance_engine.py)), niche feed queries in [`backend/routes/trends.py:85, L180`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/routes/trends.py#L85), and frontend settings in [`settings.tsx`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/routes/settings.tsx).

---

### ⚡ PHASE 3: The Killer Features (2-4 Months)
*Goal: Build features no competitor has. Make the app unbeatable.*

- [x] **Predictive Audio Intelligence**: Single-reel velocity outlier & `ig_artist` ratio signals in [`trend_engine.py`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/trend_engine.py).
- [x] **Audio-First Content Strategy Engine**: LLM Caption Kit, dominant format classification, and visual storyboards in [`backend/routes/ai.py`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/routes/ai.py) and [`AIContentGenerator.tsx`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/AIContentGenerator.tsx).
- [x] **Performance Feedback Loop**: Post performance diagnostic audit & niche health analysis in [`backend/routes/creator.py:214-380`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/routes/creator.py#L214-L380) and [`stats.tsx`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/routes/stats.tsx).
- [ ] **Algorithm Adaptation & Anti-Burnout Calendar**: Content scheduling adjusted for algorithm shifts.

---

### 🏢 PHASE 4: The Platform (4-6 Months)
*Goal: Replace creator agencies. Build the brand-creator marketplace.*

- [x] **Brand Deal Marketplace & Creator Profiles**: Marketplace profiles endpoint `/api/creator/marketplace/profiles` in [`backend/routes/creator.py`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/routes/creator.py) and creator profiles dashboard in [`frontend/src/routes/marketplace.tsx`](file:///c:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/routes/marketplace.tsx).
- [ ] **Escrow Payments & Automated Contracts** (Solves the 87% creator late-payment crisis)
- [ ] **Campaign Management Dashboard & ROI Tracking**
