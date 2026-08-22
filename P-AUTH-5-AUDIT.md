# P-AUTH-5: Guest-Open Endpoint Audit

**Date:** 2026-08-22
**Total endpoints in api.py:** ~151 route decorators
**Guest-open endpoints:** 44

---

## BUCKET A — Correctly Public (should stay open): 18

| # | Route | Method | Line | What it does | Why OK open |
|---|-------|--------|------|-------------|-------------|
| 1 | /health | GET | 1026 | Health check | Infrastructure |
| 2 | /api/health | GET | 507 | Health check | Infrastructure |
| 3 | /api/cron/trigger | GET | 515 | Trigger scheduled jobs | Cron |
| 4 | /api/cron/refresh | GET | 536 | Refresh trend cache | Cron |
| 5 | /api/auth/login | POST | 2294 | Authenticate user | Auth flow |
| 6 | /api/auth/signup | POST | 2108 | Create account | Auth flow |
| 7 | /api/auth/logout | POST | 2347 | Clear session | Auth flow |
| 8 | /api/auth/verify | POST | 2361 | Verify email | Auth flow |
| 9 | /api/auth/send-otp | POST | 2263 | Send OTP | Auth flow |
| 10 | /api/auth/verify-phone | POST | 2210 | Verify phone OTP | Auth flow |
| 11 | /api/auth/reset-password | POST | 2096 | Reset password | Auth flow |
| 12 | /api/admin/login | POST | 5529 | Admin auth | Auth flow |
| 13 | /api/payment/webhook | POST | 2527 | Razorpay callback | Webhook |
| 14 | /api/payment/subscription-webhook | POST | 2604 | Subscription callback | Webhook |
| 15 | /api/subscribe | POST | 2067 | Newsletter signup | Marketing |
| 16 | /api/marketplace/profiles | GET | 3901 | Browse creators | Public marketplace |
| 17 | /api/instagram/callback | GET | 4486 | OAuth redirect | OAuth flow |
| 18 | /api/phone/verify | POST | 7019 | Phone verify | Auth flow |

---

## BUCKET B — Should Require Auth (require_auth): 14

| # | Route | Method | Line | What it does | Why needs auth | Risk |
|---|-------|--------|------|-------------|---------------|------|
| 1 | /api/user/plan | GET | 2765 | Returns plan/credits for ANY email via query param | IDOR — anyone can query any user plan | HIGH — leaks plan + credits for any email |
| 2 | /api/user/credits | GET | 2789 | Credit balance + transaction history | User financial data | MEDIUM — returns guest data for guests |
| 3 | /api/instagram/insights | GET | 4629 | IG Insights for connected account | Personal IG metrics | LOW — 404s if no IG connected |
| 4 | /api/instagram/disconnect | DELETE | 4682 | Disconnect IG account | Write — removes IG binding | LOW — 404s if no IG connected |
| 5 | /api/creator/metrics | GET | 5133 | Creator analytics (views, likes, engagement) | Personal performance data | MEDIUM — scoped to current_user |
| 6 | /api/creator/trend-adoption | GET | 5171 | Trend adoption history | Personal data | MEDIUM — scoped to current_user |
| 7 | /api/creator/performance-over-time | GET | 5207 | Performance charts over time | Personal data | MEDIUM — scoped to current_user |
| 8 | /api/analytics/log | POST | 4706 | Log analytics event | Write to analytics_events | LOW — has inline guest check |
| 9 | /api/creator/feedback | POST | 4751 | Submit deal feedback | Write to creator_feedback | LOW — has inline guest check |
| 10 | /api/deals | POST | 3981 | Create brand deal | Write — inserts brand_deal | LOW — has inline guest check |
| 11 | /api/deals | GET | 4059 | List user deals | User deal data | LOW — has inline guest check |
| 12 | /api/deals/{id}/download | GET | 4083 | Download contract PDF | User contract + ownership check | LOW — has inline guest check |
| 13 | /api/trends/targeted | GET | 1657 | User targeted trends | Returns [] for guests | LOW — safe fallback |
| 14 | /api/trends/{id}/target | POST | 2027 | Toggle trend targeting | Write — requires _resolve_user | LOW — rejects unauthenticated |

---

## BUCKET C — Should Require Credits/Plan Gating: 12

| # | Route | Method | Line | What it does | Why needs gating | Current state |
|---|-------|--------|------|-------------|-----------------|---------------|
| 1 | /api/seo-caption | POST | 3802 | AI SEO caption generation | AI feature — costs Groq tokens | No credit check — FREE |
| 2 | /api/daily-ideas | GET | 3812 | AI daily content ideas | AI feature — costs Groq tokens | No credit check — FREE |
| 3 | /api/algorithm/analyze | GET | 4775 | Algorithm virality analysis | AI-powered analytics | Dead duplicate of #4 — **REMOVED** `61970766` |
| 4 | /api/algorithm/analyze | GET | 1784 | Live handler (gated: require_feature(algorithm_insights)) | AI-powered analytics | Gated — see Bucket C commits |
| 5 | /api/early-detection/trends | GET | 5929 | Pre-viral trend detection | Premium analytics | No credit check — FREE |
| 6 | /api/early-detection/predict/{id} | GET | 5950 | Virality prediction per trend | Premium analytics | No credit check — FREE |
| 7 | /api/virality/improvements | GET | 6022 | AI virality improvement suggestions | AI feature | No credit check — FREE |
| 8 | /api/india/caption/generate | GET | 6132 | AI India caption in regional language | AI feature — costs tokens | No credit check — FREE |
| 9 | /api/india/content-ideas/generate | GET | 6159 | AI India content ideas | AI feature — costs tokens | No credit check — FREE |
| 10 | /api/india/cultural-event/{name} | GET | 6194 | AI cultural event content | AI feature — uses ContentGenerator | No credit check — FREE |
| 11 | /api/youtube/trending | GET | 6586 | YouTube trending (SIMULATED) | Dead endpoint — returns fake data | **REMOVED** `cc277ee5` |
| 12 | /api/realtime/trends | GET | 6670 | Realtime trends (SIMULATED) | Dead endpoint — returns fake data | **REMOVED** `cc277ee5` |

**Note on simulated endpoints:** /api/youtube/trending (6586), /api/youtube/trending-music (6629), /api/realtime/trends (6670), /api/realtime/cross-platform (6712), /api/instagram/user-profile (6454), /api/instagram/user-insights (6500), /api/instagram/user-media (6543) all return hardcoded/simulated data and are marked NOT USER-FACING in their docstrings. These should either be wired to real APIs or removed.
**RESOLVED Aug 22, 2026:** all seven removed in `cc277ee5`. Zero callers confirmed across frontend/src, all local branches, and WIP stashes before removal.

---

## BUCKET C (continued) — Simulated/Dead endpoints (should remove or wire):

| # | Route | Method | Line | Current state |
|---|-------|--------|------|---------------|
| 13 | /api/youtube/trending-music | GET | 6629 | Simulated — NOT USER-FACING → **REMOVED** `cc277ee5` |
| 14 | /api/realtime/cross-platform | GET | 6712 | Simulated — NOT USER-FACING → **REMOVED** `cc277ee5` |
| 15 | /api/instagram/user-profile | GET | 6454 | Simulated — NOT USER-FACING → **REMOVED** `cc277ee5` |
| 16 | /api/instagram/user-insights | GET | 6500 | Simulated — NOT USER-FACING → **REMOVED** `cc277ee5` |
| 17 | /api/instagram/user-media | GET | 6543 | Simulated — NOT USER-FACING → **REMOVED** `cc277ee5` |

---

## Totals

| Bucket | Count | Action |
|--------|-------|--------|
| A — Correctly Public | 18 | No change |
| B — Needs require_auth | 14 | Add require_auth or inline guest check |
| C — Needs credits/plan gating | 12 | Add require_credits or require_feature |
| Dead/Simulated (subset of C) | 7 | Remove or wire to real APIs |
| **Total guest-open** | **44** | |

## Remediation Status (updated Aug 22, 2026)

All gating work COMPLETE. Commits: `4d44e855` (user/plan IDOR), `25ee5669` (instagram/disconnect), `c55325ec` (creator trio), `3ae52ec6` (user/credits + instagram/insights), `a3106a04` (early-detection pair, require_feature), `e09444cf` (seo-caption + daily-ideas), `e4a2a302` (virality/improvements + india/caption), `7eacb5a3` (india/content-ideas + india/cultural-event).

Side-fix: P-PAY-9 (`458173f8`) — require_credits deducts only on success now.

Closed Aug 22, 2026 (both were product-decision items, both approved):
- Dead-handler duplicate @api.py:4776 removed — `61970766`. Evidence: 2→1 route registrations; unauth 401 and free-plan 200 unchanged (algorithm_insights is in FREE_TIER_FEATURES).
- All 7 simulated endpoints removed — `cc277ee5`. Evidence: exactly 7 `-@app.get` in diff (316 del / 0 ins); 7→0 route registrations; openapi.json clean on restarted server; neighbors healthy.

Nothing remains open from this audit except the cosmetic Bucket-B inline-check standardization (Key Finding 4).

---

## Key Findings

1. **P-AUTH-5-CRITICAL: /api/user/plan is an IDOR** — takes `email` as query param, returns plan + credits for ANY user. No ownership check.
2. **12 endpoints leak AI features for free** — seo-caption, daily-ideas, algorithm/analyze, early-detection, virality/improvements, india/caption, india/content-ideas, india/cultural-event.
3. **7 endpoints return simulated/fake data** — all marked NOT USER-FACING in docstrings.
4. **Bucket B endpoints are inconsistent** — some have inline `if current_user == guest: raise 401` (deals, analytics, feedback) while others don't (user/plan, user/credits, creator/*). Standardizing to `require_auth` is cleaner.
5. **No data mutation leaks** — all Bucket C endpoints are GET-only reads, so no write operations are leaking.
