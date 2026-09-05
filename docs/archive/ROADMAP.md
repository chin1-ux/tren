# Trendrop Roadmap: ₹0 → ₹30 Lakh MRR
**Timeline:** October 2026 — December 2027 (15 months)
**Target:** ₹30,00,000 MRR = 2,600 paying users

---

## Pricing Tiers (Credit-Based Hybrid Model)

### How Credits Work

**1 credit = 1 "action" on the platform.** Different features cost different amounts based on their compute/API cost.

**Credit costs per action:**

| Action | Credits | Why this cost |
|---|---|---|
| View trending feed (1 page) | 1 | Read-only, low compute |
| Search trends (1 search) | 3 | Involves query + filtering |
| View trend detail (1 trend) | 2 | Fetches snapshots, reels, timeline |
| View similar trends | 2 | Computationally expensive |
| View audio history | 1 | Read-only |
| AI hooks generation | 5 | LLM call (costs ₹0.50-1.00 per call) |
| AI caption generation | 5 | LLM call |
| AI content ideas (daily batch) | 5 | LLM call |
| AI script outline | 8 | Heavier LLM call |
| Creator analytics | 3 | Multi-source aggregation |
| Early detection alert | 1 | Background process |
| Export data (CSV) | 2 | Compute + storage |
| Track a niche (per niche/day) | 1 | Background monitoring |
| Run Orbit Search (deep scan) | 10 | Heavy compute, multiple API calls |

### Plan Details

---

#### FREE TIER — ₹0/month
**Target:** Curious creators, students, hobbyists
**Goal:** Hook them → upgrade to Creator within 30 days

| Feature | Limit |
|---|---|
| **Credits** | 10/day (300/month, non-rollover) |
| **Trending feed** | ✅ View only (latest 20 trends) |
| **Niche tracking** | ❌ Not available |
| **Trend detail** | ✅ 5 views/day |
| **AI generation** | ❌ Not available |
| **Creator analytics** | ❌ Not available |
| **Early detection** | ❌ Not available |
| **Export** | ❌ Not available |
| **Alerts** | ❌ Not available |
| **Support** | Community only |

**What they see:** Basic trending feed, limited trend details, "Upgrade to unlock AI" prompts everywhere.

**Upgrade trigger:** After 3-5 days of using the free tier, they hit credit limits. The AI features are gated — they see blurred previews but can't generate.

---

#### CREATOR TIER — ₹999/month (₹833/mo annual)
**Target:** Solo creators, freelancers, small businesses
**Goal:** Retain through value → upgrade to Agency when they grow

| Feature | Limit |
|---|---|
| **Credits** | 200/month (rollover up to 50) |
| **Trending feed** | ✅ Full access (rising, emerging, peaked) |
| **Niche tracking** | ✅ 5 niches |
| **Trend detail** | ✅ Unlimited |
| **AI hooks** | ✅ 10/day (50 credits) |
| **AI captions** | ✅ 10/day (50 credits) |
| **AI content ideas** | ✅ Daily batch (5 credits) |
| **AI script outline** | ✅ 2/day (16 credits) |
| **Creator analytics** | ✅ Basic (own account only) |
| **Early detection** | ✅ 3 alerts |
| **Similar trends** | ✅ Unlimited |
| **Export** | ✅ 5/month |
| **Alerts** | Email only |
| **Support** | Email (48hr response) |

**Credit math (typical user):**
- 10 searches/day × 3 credits × 30 days = 900 credits (WAY over budget)

**Wait — that's too many credits consumed. Let me recalibrate.**

Actually, the credit system should be designed so that a Creator user can do **meaningful work** but hits limits when they try to do **everything**.

**Revised credit allocation:**

| Action | Credits | Daily budget (200/30 = 6.6/day) |
|---|---|---|
| View trending feed | 0 (free, always) | — |
| Search trends | 1 | 3 searches/day |
| View trend detail | 1 | 3 details/day |
| View similar trends | 2 | 1 similar/day |
| AI hooks generation | 3 | 1 hook set/day |
| AI caption generation | 3 | 1 caption/day |
| AI content ideas | 3 | 1 batch/day |
| Creator analytics | 2 | 1 analytics view/day |
| Export data | 3 | 0-1 exports/day |
| Track a niche | 0 (5 niches included) | — |
| Early detection alert | 0 (3 alerts included) | — |

**Typical daily usage:**
- 3 searches (3 credits)
- 3 trend details (3 credits)
- 1 similar trends (2 credits)
- 1 AI hook generation (3 credits)
- 1 AI caption (3 credits)
- 1 analytics view (2 credits)
- **Total: 16 credits/day = 480/month**

**That's over the 200 limit.** The user would need to choose: do I search or do I generate?

**The intended behavior:** Users prioritize their most valuable actions. Some days they search more, some days they generate more. This creates natural upgrade pressure.

**Upgrade trigger:** After 2 weeks, users realize they can't do everything they want. They either:
1. Upgrade to Agency (₹4,999) for more credits
2. Buy credit add-ons (₹99 for 50 extra credits)

---

#### AGENCY TIER — ₹4,999/month (₹4,166/mo annual)
**Target:** Marketing agencies, brand teams, multi-creator managers
**Goal:** Lock in annual contracts, expand seats

| Feature | Limit |
|---|---|
| **Credits** | 1,500/month (rollover up to 200) |
| **Seats** | 3 (expandable to 10 at ₹999/seat) |
| **Trending feed** | ✅ Full access |
| **Niche tracking** | ✅ 25 niches |
| **Trend detail** | ✅ Unlimited |
| **AI hooks** | ✅ 30/day |
| **AI captions** | ✅ 30/day |
| **AI content ideas** | ✅ 3 batches/day |
| **AI script outline** | ✅ 5/day |
| **Creator analytics** | ✅ Full (multiple accounts) |
| **Early detection** | ✅ 15 alerts |
| **Slack/Discord alerts** | ✅ Yes |
| **Webhook alerts** | ✅ Yes |
| **Zapier/n8n integration** | ✅ Yes |
| **Export** | ✅ Unlimited |
| **Meta Ads Intelligence** | ✅ Yes |
| **Content calendar** | ✅ Yes |
| **Support** | Priority (12hr response) |

**Credit math (typical agency):**
- 50 searches/day × 1 × 30 = 1,500 credits (exactly at limit)
- Plus AI generation, analytics, exports = over limit

**The intended behavior:** Agencies with 3 people doing research + generation hit the 1,500 limit by day 15-20. They need Enterprise or seat add-ons.

**Upgrade trigger:** Agencies with growing teams hit seat limits (3 seats) or credit limits (1,500). They either:
1. Add seats at ₹999/seat
2. Upgrade to Enterprise (₹14,999)

---

#### ENTERPRISE TIER — ₹14,999/month (₹12,499/mo annual)
**Target:** Large agencies, media companies, brands with multiple teams
**Goal:** API access, custom integrations, annual contracts

| Feature | Limit |
|---|---|
| **Credits** | 5,000/month (rollover up to 500) |
| **Seats** | 10 (expandable at ₹999/seat) |
| **Everything in Agency** | ✅ Yes |
| **API access** | ✅ Yes |
| **MCP server** | ✅ Yes |
| **Custom integrations** | ✅ Yes |
| **Dedicated account manager** | ✅ Yes |
| **Custom reports** | ✅ Yes |
| **SLA** | 99.9% uptime |
| **Support** | Instant (Slack channel) |

---

### Credit Add-Ons (One-Time Purchases)

| Add-On | Price | Credits |
|---|---|---|
| **Starter Pack** | ₹99 | 50 credits |
| **Pro Pack** | ₹249 | 150 credits |
| **Power Pack** | ₹499 | 350 credits |

**These are purchased when users run out of monthly credits.** No subscription required — just top up.

---

### Annual Billing Discounts

| Plan | Monthly | Annual (per month) | Savings |
|---|---|---|---|
| Creator | ₹999 | ₹833 | 17% (2 months free) |
| Agency | ₹4,999 | ₹4,166 | 17% (2 months free) |
| Enterprise | ₹14,999 | ₹12,499 | 17% (2 months free) |

**Indian market reality:** Annual billing locks in revenue and reduces churn. Offer "2 months free" as the incentive.

---

### Revenue Projections

| Phase | Users | Mix | MRR |
|---|---|---|---|
| **Oct-Dec 2026** | 50 | 80% Free, 15% Creator, 5% Agency | ₹2-5L |
| **Jan-Mar 2027** | 200 | 60% Free, 30% Creator, 10% Agency | ₹10-15L |
| **Apr-Jun 2027** | 500 | 50% Free, 35% Creator, 12% Agency, 3% Enterprise | ₹25-35L |
| **Jul-Dec 2027** | 1,000+ | 40% Free, 40% Creator, 15% Agency, 5% Enterprise | ₹50L-1Cr+ |

---

### Credit System Implementation Notes

**Backend changes needed:**
1. `users` table: add `credits_remaining`, `credits_used_this_month`, `plan` columns
2. `credit_transactions` table: log every credit consumption (user_id, action, credits, timestamp)
3. `credit_packages` table: available add-on packs
4. Middleware: check credits before executing action, deduct on success
5. Billing integration: Razorpay subscription + one-time credit purchases

**Frontend changes needed:**
1. Credit balance display (header bar)
2. Credit consumption indicators (show credits cost before action)
3. "Out of credits" modal with upgrade + add-on options
4. Credit history page

**Anti-abuse:**
1. Daily credit cap (even if monthly balance is high)
2. Rate limiting per action
3. Credit deduction on action START, not completion (prevent exploits)
