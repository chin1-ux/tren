# TRENDROP — Full Frontend Inventory Audit

**Date:** August 31, 2026
**Scope:** Entire frontend codebase — every route, component, API call, string, and cross-reference with backend
**Status:** READ-ONLY audit. No modifications made.

---

## Table of Contents

1. [Tech Stack](#1-tech-stack)
2. [Full Sitemap](#2-full-sitemap)
3. [Page-by-Page Audit](#3-page-by-page-audit)
4. [Component Inventory](#4-component-inventory)
5. [API Layer & Backend Cross-Reference](#5-api-layer--backend-cross-reference)
6. [Feature Flags](#6-feature-flags)
7. [State Management](#7-state-management)
8. [Styling System](#8-styling-system)
9. [User-Facing Strings](#9-user-facing-strings)
10. [Backend Endpoints with NO Frontend](#10-backend-endpoints-with-no-frontend)
11. [Bugs, TODOs, Dead Code](#11-bugs-todos-dead-code)

---

## 1. Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19 + TanStack Start (SSR, Vite-based) |
| Build | Vite 7.3 with `@lovable.dev/vite-tanstack-config` |
| Routing | TanStack Router (file-based, `@tanstack/react-router` v1.168) |
| State | Zustand v5 + React Query v5.83 |
| Auth/SDK | Supabase JS v2 (`@supabase/supabase-js`) |
| Styling | Tailwind CSS v4.2 (`@tailwindcss/vite`), CSS custom properties, Framer Motion |
| UI Library | 48 shadcn/ui primitives + 32 custom components |
| Forms | React Hook Form + Zod validation |
| Charts | Recharts |
| PWA | vite-plugin-pwa (service worker, manifest, offline) |
| HTTP | Native `fetch` via custom `http()` helper + `apiFetch()` |
| TypeScript | v5.8 |
| Backend | FastAPI (Python 3.11+), Supabase (PostgreSQL), Razorpay (INR) |
| Deployment | Vercel (serverless via Mangum + Nitro) |

---

## 2. Full Sitemap

### Primary Routes

| Route | File | Auth Gate | Plan Gate |
|-------|------|-----------|-----------|
| `/` | `frontend/src/routes/index.tsx` | No (public read) | Emerging tab → `pro` |
| `/login` | `frontend/src/routes/login.tsx` | No (redirects if authed) | No |
| `/signup` | `frontend/src/routes/signup.tsx` | No (redirects if authed) | No |
| `/dashboard` | `frontend/src/routes/dashboard.tsx` | Yes (via AuthWrapper) | Some tabs → `pro` |
| `/generate` | `frontend/src/routes/generate.tsx` | Yes | `pro` (entire page) |
| `/ideas` | `frontend/src/routes/ideas.tsx` | Yes | `pro` (entire page), Calendar → `FEATURES.CALENDAR_ENABLED` |
| `/pricing` | `frontend/src/routes/pricing.tsx` | No | No |
| `/settings` | `frontend/src/routes/settings.tsx` | Yes | No |
| `/stats` | `frontend/src/routes/stats.tsx` | Yes | No |
| `/studio` | `frontend/src/routes/studio.tsx` | Yes | `pro` (entire page) |
| `/marketplace` | `frontend/src/routes/marketplace.tsx` | Yes | `FEATURES.MARKETPLACE_ENABLED` (currently false) |
| `/trend/$id` | `frontend/src/routes/trend.$id.tsx` | No | Some sections → `pro` |
| `/proof` | `frontend/src/routes/proof.tsx` | No | No |
| `/deals/` | `frontend/src/routes/deals.index.tsx` | Yes | `FEATURES.DEALS_ENABLED` (currently false) |
| `/deals/new` | `frontend/src/routes/deals.new.tsx` | Yes | `FEATURES.DEALS_ENABLED` (currently false) |
| `/data-rights` | `frontend/src/routes/data-rights.tsx` | No | No |
| `/privacy` | `frontend/src/routes/privacy.tsx` | No | No |
| `/terms` | `frontend/src/routes/terms.tsx` | No | No |
| `/reset-password` | `frontend/src/routes/reset-password.tsx` | No | No |
| `/update-password` | `frontend/src/routes/update-password.tsx` | No | No |
| `/verify-phone` | `frontend/src/routes/verify-phone.tsx` | No | No |

### Admin Routes

| Route | File | Auth Gate |
|-------|------|-----------|
| `/admin/login` | `frontend/src/routes/admin.login.tsx` | No (this IS the login) |
| `/admin/users` | `frontend/src/routes/admin.users.tsx` | Yes (`beforeLoad` + `/api/admin/validate-token`) |
| `/admin/plans` | `frontend/src/routes/admin.plans.tsx` | Yes (`beforeLoad` + `/api/admin/validate-token`) |
| `/admin/audit` | `frontend/src/routes/admin.audit.tsx` | Yes (`beforeLoad` + `/api/admin/validate-token`) |
| `/admin/analytics` | `frontend/src/routes/admin.analytics.tsx` | Yes (`beforeLoad` + `/api/admin/validate-token`) |

### Pseudo-Routes (Modals/Drawers)

| Pseudo-Route | Triggered From | Component |
|-------------|----------------|-----------|
| DanceTrendModal | TrendCard "How To Film" | `DanceTrendModal.tsx` |
| TrendPreviewModal | TrendCard (set state) | `TrendPreviewModal.tsx` |
| Follow-up Modal | Deal milestone "Follow-up" | `deals.index.tsx:466` |
| Feedback Modal | Contract download | `deals.index.tsx:537` |
| User Details Modal | Admin "Details" button | `admin.users.tsx:292` |
| Plan Edit Modal | Admin "Edit" button | `admin.plans.tsx:233` |
| Collab Request Modal | Marketplace "Collab" | `marketplace.tsx:431` |
| OnboardingFlow | First visit | `OnboardingFlow.tsx` |
| OnboardingTour | Dashboard "Tour" button | `OnboardingTour.tsx` |
| FeatureTutorial | First visit (commented out) | `FeatureTutorial.tsx` |
| InstallBanner | PWA install prompt | `InstallBanner.tsx` |

### Root Layout

- **File:** `frontend/src/routes/__root.tsx`
- **Components rendered:** `QueryClientProvider` → `AuthProvider` → `AuthWrapper` → `<Outlet />` + `BottomTabBar` + `InstallBanner` + `Toaster`
- **Page transitions:** Framer Motion `AnimatePresence` keyed on route path (fade+slide, 0.25s)
- **Max width:** `max-w-lg lg:max-w-2xl xl:max-w-4xl 2xl:max-w-5xl pb-24` (no constraint for `/admin`)

---

## 3. Page-by-Page Audit

### 3.1 `/` — Main Trends Feed

**File:** `frontend/src/routes/index.tsx` (563 lines)

**Route Config (L23-32):** `createFileRoute("/")` with SEO head, `errorComponent: RouteErrorBoundary`. No loader/beforeLoad.

**State (L62-78):**
- `language` (default: not set)
- `feedTab` (default: `"rising"`) — one of: `"rising" | "emerging" | "workspace" | "peaked" | "expired"`
- `sortMode` (default: `"velocity"`) — **typed as `any`** (L65)
- `danceTrend` (selected trend for modal)
- `searchQuery`
- `showFilterDrawer` — **declared but never used** (L68)
- `now` (tick timer for countdown)
- `selectedNiche` (default: `"all"`) — persisted to `localStorage("trendrop_pref_niche")`

**Data Fetching (useQuery hooks):**

| Query | Endpoint | Enabled When | staleTime | refetchInterval |
|-------|----------|-------------|-----------|-----------------|
| `fetchTrends(language, sortMode, selectedNiche)` | `GET /api/trends` | Always | 3min | 5min |
| `fetchEmergingTrends(language)` | `GET /api/trends/emerging` | `userPlan === "pro"` | 3min | 5min |
| `fetchPeakedTrends(language)` | `GET /api/trends/peaked` | Always | 3min | 5min |
| `fetchExpiredTrends(language)` | `GET /api/trends/expired` | Always | 3min | 5min |
| `fetchTargetedTrends()` | `GET /api/trends/targeted` | Always | 10s | No |

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Notification bell | 278-297 | Switches to Emerging tab, shows toast with count |
| Theme toggle | 300 | `<ThemeToggle />` component |
| User avatar | 303-311 | Navigates to `/settings`, shows first letter of email or "T" |
| 5 Tab buttons | 326-361 | Rising, Emerging, Workspace, Peaked, Expired — each sets `feedTab` |
| Search input | 367-379 | Client-side filter on `song`, `artist`, `contentType` |
| Niche chips (8) | 384-401 | Sets `selectedNiche`, persists to localStorage |
| Language chips | 404-424 | **COMMENTED OUT** |
| "Try again" button | 468 | Calls `refetch()` |
| TrendCard click | (in TrendCard) | Expands card, shows details |
| TrendCard "How To Film" | (in TrendCard) | Opens DanceTrendModal |

**Cross-tab Deduplication (L170-205):** By `audioId` (or `song-artist` fallback). Priority: rising(4) > emerging(3) > peaked(2) > expired(1).

**Fallback Logic (L208-212):** If rising is empty but peaked has data, shows peaked in rising tab with "warming up" banner.

**Notification Toast (L157-166):** When emerging count increases, shows toast with "N new emerging trend(s) just detected!" + action to switch tab.

**Conditional Renders:**

| Condition | Lines | What Shows |
|-----------|-------|------------|
| Rising fallback | 429-435 | Amber banner: "Trends are warming up" |
| Emerging info | 436-442 | Info banner about emerging |
| Peaked info | 443-449 | Info banner about peaked |
| Expired info | 450-456 | Info banner about expired |
| Workspace info | 457-463 | Info banner about workspace |
| Error | 465-472 | `ApiErrorBanner` + "Try again" |
| Loading | 474-479 | 3 `<SkeletonCard />` |
| Empty | 480-493 | Different message for workspace vs others |
| Emerging tab | 494-511 | Wrapped in `<PlanGate feature="Early Detection Feed" requiredPlan="pro">` |
| Normal list | 512-521 | TrendCard list |

**Hardcoded Strings:**
- Tab labels: "Rising", "Emerging", "Workspace", "Peaked", "Expired"
- Toast: "🚨 {count} new emerging trend(s) just detected!"
- Rising fallback banner: "Trends are warming up — showing peaked content while fresh data loads"
- Niche chips: "All", "Fitness", "Food", "Comedy", "Fashion", "Business", "Travel", "Beauty"
- Info banners per tab with static descriptive text

**Styling:** Tailwind, `glass-card` pattern, `gradient-text`, dark mode support, `motion.div` for page transitions.

**Known Issues:**
- L65: `sortMode` typed as `any`
- L68: `showFilterDrawer` state declared, never used
- L404-424: Entire language filter UI commented out
- L11-12: `OnboardingFlow`, `FeatureTutorial` imports commented out
- No `beforeLoad` or `loader` defined
- NICHES constant differs from signup.tsx (8 vs 9 entries, different values)

---

### 3.2 `/login` — Login Page

**File:** `frontend/src/routes/login.tsx` (151 lines)

**Route Config (L10-18):** `createFileRoute("/login")` with SEO head. No auth guard.

**Form Behavior (L28-45):** `handleSubmit` calls `login(email, password)` from `useAuth()`. AuthContext handles navigation.

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Email input | 75-84 | `type="email"`, required, placeholder "you@example.com" |
| Password input | 104-113 | `type="password"`, required, placeholder "•••••••••" |
| "Forgot password?" | 94-100 | Navigates to `/reset-password` |
| Submit button | 126-133 | Calls `handleSubmit`, shows "Logging in..." when loading |
| "Sign up" link | 139-145 | Navigates to `/signup` |

**Conditional Renders:** Error alert (L118-123) when `error` is truthy.

**Hardcoded Strings:** "Welcome Back", "Login to your Trendrop account", "Email", "Password", "Forgot password?", "Don't have an account?", "Sign up", "Logging in..."

**Styling:** Tailwind gradient background, framer-motion fade-in+slide-up (0.5s), `Button` and `Input` from shadcn/ui.

---

### 3.3 `/signup` — Signup Page

**File:** `frontend/src/routes/signup.tsx` (317 lines)

**Route Config (L32-40):** `createFileRoute("/signup")` with SEO head.

**Constants:**
- `NICHES` (L10-20): 9 entries — dance, fashion, travel, food, comedy, motivation, fitness, current_affairs, all
- `LANGUAGES` (L22-30): 7 entries — en, hi, kn, ta, te, bn, mr

**Form Fields:** email, password, confirmPassword, phoneNumber, niche (select), language (select), state (select, optional, 13 Indian states), tier (select: nano/micro/macro/mega)

**Validation (L56-78):** Passwords match, password ≥ 6 chars, phone ≥ 10 chars.

**Submission (L82):** `signup(email, password, phoneNumber, niche, language, stateName, tier)` — all 7 params.

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Email input | 123-132 | type email, required, placeholder "you@example.com" |
| Phone input | 142-150 | type tel, required, placeholder "+91 98765 43210" |
| Password input | 160-170 | required, minLength 6 |
| Confirm password | 180-190 | required, minLength 6 |
| Niche select | 201-213 | Native HTML select |
| Language select | 222-234 | Native HTML select |
| State select | 242-262 | Optional, 13 hardcoded Indian states |
| Tier select | 270-280 | 4 options with labels |
| Submit button | 292-299 | Disabled during loading |
| "Login" link | 305-311 | Navigates to `/login` |

**Hardcoded Strings:** "Create Account", "Join Trendrop to discover trending content", State names, Tier labels ("nano (0-10K followers)", etc.)

**Notable:** No OAuth/Google sign-in. Phone required at signup. NICHES list differs from index.tsx.

---

### 3.4 `/dashboard` — Creator Dashboard

**File:** `frontend/src/routes/dashboard.tsx` (156 lines)

**Route Config (L16-19):** `createFileRoute("/dashboard")`, `errorComponent: RouteErrorBoundary`.

**State:** `userNiche` from Zustand. `isCurrentAffairsCreator = userNiche === "current_affairs"`. `defaultTab` = "breaking-news" for current affairs, "early-detection" otherwise.

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| "Tour" button | 73-81 | Calls `startOnboarding` from `useOnboarding()` |
| Tabs (up to 7) | 84-116 | Switches `activeTab` |

**Tab Content:**

| Tab | Component | Condition |
|-----|-----------|-----------|
| Breaking News | `NewsFeedPanel` | Only for `current_affairs` niche |
| Early Detection | `EarlyDetectionPanel` | Always |
| Video Analysis | `VideoAnalysisPanel` | Always |
| Festivals | `RegionalFestivalPanel` | Always |
| Analytics | `CreatorAnalyticsDashboard` | Always |
| AI Generator | `AIContentGenerator` | Always |
| India Features | `IndiaFeaturesDashboard` | Only for non-current-affairs |

**All data fetching delegated to child components.**

---

### 3.5 `/generate` — AI Video Generation Studio

**File:** `frontend/src/routes/generate.tsx` (1001 lines)

**Route Config (L21-31):** `createFileRoute("/generate")` with `validateSearch: z.object({ trendId: z.string().optional() })`. Plan-gated: `<PlanGate feature="AI Generation Studio" requiredPlan="pro">`.

**Constants:**
- `NARRATIVE_PRESETS` (L42-63): 4 presets — before_after, transformation, reveal, countdown
- `NICHES` (L65-71): 5 niches — motivation, finance, tech, fitness, travel

**Tabs:** `"photos" | "narrative" | "faceless" | "repurpose"`
**Stages:** `"upload" | "progress" | "result" | "error"`

**Data Fetching:** `fetchTrends()` to find active trend by `trendId` search param.

**Generation Handlers:**

| Handler | Line | API Call | Requirements |
|---------|------|----------|-------------|
| `handleCreateReel` | 242-257 | `generateReel({files, trendId, userEmail, style})` | ≥ 3 photos + activeTrend |
| `handleCreateNarrative` | 259-275 | `generateNarrative({files, trendId, userEmail, narrativeType, textOverlays})` | ≥ 2 narrative photos + activeTrend |
| `handleCreateFaceless` | 277-292 | `generateFaceless({trendId, userEmail, niche, contentDescription})` | contentDescription + activeTrend |
| `handleRepurpose` | 294-308 | `repurposeVideo({file, trendId, userEmail})` | video file |

**Email source:** `localStorage.getItem("trendrop_user_email")` with fallback `"anonymous@trendrop.app"` (L245, 263, 280, 297) — **inconsistent with other pages using Zustand**.

**Polling (L183-230):** `jobStatus(jobId)` every 2 seconds. Dynamic status messages at 4 progress stages.

**Scoring (L878-967):** "Score This Video" button calls `scoreReel()` on demand.

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Tab buttons (4) | 332+ | Switches `activeTab` |
| Photo upload | varies | Accepts FileList, limit 15 for photos, 10 for narrative |
| Style selector (4) | photos tab | cinematic, fast, glitch, zoom |
| "Create Reel" button | photos tab | Calls `handleCreateReel` |
| Narrative preset buttons (4) | narrative tab | Sets `narrativeType` |
| Narrative image upload | narrative tab | Accepts images |
| Text overlay inputs | narrative tab | Editable overlays |
| "Generate Narrative Reel" button | narrative tab | Calls `handleCreateNarrative` |
| Niche chips (5) | faceless tab | Sets `niche` |
| Description textarea | faceless tab | Sets `contentDescription` |
| "Generate Faceless Video" button | faceless tab | Calls `handleCreateFaceless` |
| Video upload | repurpose tab | MP4/MOV, limit 1 |
| Trend sound selector | repurpose tab | Dropdown of active trends |
| "Repurpose with Beat Sync" button | repurpose tab | Calls `handleRepurpose` |
| Progress cancel button | progress stage | Cancels polling |
| Download button | result stage | Creates anchor tag |
| Share button | result stage | Web Share API with clipboard fallback |
| "Score This Video" | result stage | Calls `scoreReel` |
| "Create Another Video" | result stage | Resets to upload stage |
| "Go Back & Retry" | error stage | Resets to upload stage |

**Conditional Renders:** Loading (progress stage), error (error stage), result (result stage), upload (upload stage).

**Hardcoded Strings:** Style labels, preset descriptions, status messages, niche labels.

**Known Issues:**
- Email from localStorage directly instead of Zustand — potential inconsistency
- No `loader` or `beforeLoad`
- Photo drag reorder uses raw HTML5 drag/drop

---

### 3.6 `/ideas` — Ideation Hub

**File:** `frontend/src/routes/ideas.tsx` (1000 lines)

**Route Config (L41-50):** Feature-gated behind `FEATURES.IDEAS_ENABLED`.

**Tabs:** `"daily" | "score" | "hooks" | "calendar"`

**Tab 1: Daily Idea Drop (L368-494)**
- API: `fetchDailyIdeas(email)` → `GET /api/daily-ideas/{email}`
- "Refresh" button calls `getIdeas(userEmail)`
- Idea cards: difficulty badge, title, description, hook, audio suggestion, posting time
- "Use This Idea" button pre-fills score tab
- **Fallback ideas warning** when using fallback data

**Tab 2: Pre-Post Reel Scorer (L498-743)**
- Form: Audio Title, Niche, Posting Time, Caption
- "Score My Reel" → `scoreReel({audio, caption, posting_time, niche})`
- Results: animated SVG gauge, grade badge, 5 score bars, top fixes
- **Fallback score on error: overall 75, grade "B", all sub-scores 70** (L186-199)

**Tab 3: Hook Generator (L747-836)**
- Form: Trend/topic, Content description
- "Generate 5 hooks" → `generateHooks({trend, content_description})`
- Hook cards: style badge, hook text, "Why it works", copy button
- **Fallback hooks** (3 hardcoded templates) on error (L221-225)

**Tab 4: Content Calendar (L840-993)**
- Gated behind `PlanGate` + `FEATURES.CALENDAR_ENABLED`
- "Generate Plan" → `generateCalendar(userEmail)`, persists to localStorage
- 30-day grid with festival indicators
- Selected day detail panel
- **Fallback calendar with fixed Indian holidays** (L244-269)

**Hardcoded Strings:** "personalized calendars are coming soon" (L858), fallback data.

**Known Issues:**
- Default email "anonymous@trendrop.app" (L79)
- Default niche "dance" (L80)
- 3 different NICHES constants across files with different entries

---

### 3.7 `/pricing` — Subscription Pricing

**File:** `frontend/src/routes/pricing.tsx` (156 lines)

**Route Config (L7-9):** No loader, no beforeLoad, no head/meta.

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Free CTA (unauthenticated) | 73-79 | Navigates to `/signup` |
| Free CTA (authenticated, free) | 81-87 | Disabled, "Current Plan" |
| Free CTA (authenticated, pro) | 88-96 | "Downgrade to Free", navigates to `/` |
| Pro CTA (non-pro) | 141-148 | **STUB** — toast: "Pro upgrade will be available soon via Razorpay!" |
| Pro CTA (pro/agency) | 132-139 | Disabled, "Current Plan" |

**TODO (L32):** `// TODO: Wire Razorpay checkout flow`

**Hardcoded Strings:** "Simple, Transparent Pricing", "Browse trends for free. Pay for AI-powered content generation.", "Free", "₹0 / month", "₹999 / month", "Best Value", all feature lists.

**Known Issues:**
- `import { toast } from "sonner"` at bottom of file (L156) — unconventional placement
- No error boundary

---

### 3.8 `/settings` — User Settings

**File:** `frontend/src/routes/settings.tsx` (680 lines)

**Route Config (L13-21):** `head()` with meta title.

**Constants:**
- `ALL_LANGUAGES` (L23-31): 7 languages with emoji flags
- `NICHES` (L33-52): 18 niche strings
- `STATES` (L54-72): 17 Indian states + "Select State"
- `TIERS` (L74-79): 4 creator tiers

**State (L86-113):** fontSize, themeColor, theme, email, instagramHandle, followers, 4 notification booleans, selectedLanguage/Niche/State/Tier, savingPrefs, langSearch, customNiche, showLangDropdown.

**API Call:** `saveSettings()` sends `PUT /api/users/preferences` with full preference payload.

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Language dropdown (custom searchable) | 309-351 | Toggle, search, select |
| Niche input + suggestion chips | 357-387 | Free-text + 18 clickable chips |
| State select | 394-402 | Native HTML select |
| Tier grid buttons (4) | 413-429 | Active state styling |
| Font size buttons (3) | 444-458 | Apply to `document.documentElement.style.fontSize` |
| Theme color buttons (3) | 464-480 | Apply CSS custom properties |
| Dark/light toggle | 495-501 | Toggles `dark` class, saves to localStorage |
| Reset Tutorial button | 510-516 | Clears tutorial state, redirects to `/` |
| Notification toggles (4) | 527-554 | 2 gated by feature flags |
| Email input | 567-573 | Text input |
| Instagram handle input | 579-585 | Gated by `FEATURES.INSTAGRAM_OAUTH_ENABLED` |
| Follower count input | 589-595 | Gated by `FEATURES.INSTAGRAM_OAUTH_ENABLED` |
| Logout button | 602-608 | Calls `logout()`, navigates to `/login` |
| Privacy/Terms/DPDP links | 621-629 | `<Link>` to pages |
| Save Settings button | 635-641 | Calls `saveSettings()` |

**Hardcoded Strings:** Language names, niche labels, state names, tier labels, notification descriptions.

---

### 3.9 `/stats` — Diagnostics Dashboard

**File:** `frontend/src/routes/stats.tsx` (265 lines)

**Route Config (L12-21):** `errorComponent: RouteErrorBoundary`.

**Tabs:** `"diagnostics" | "niche"`

**API Queries:**
- `fetchCreatorDiagnostics(email)` — `GET /api/creator/diagnostics`
- `fetchCreatorNicheHealth(email)` — `GET /api/creator/niche-health`

**Data Displayed:**
- Flop Audit: baseline_avg_plays, flops_detected/total_posts_analyzed, flops list with media_id/caption/plays_count/permalink
- Remedy tracks: audio_title, audio_artist, why_this_works, transfer_instructions
- Niche Health: niche_health_score (0-1), alignment_drift_detected, primary_niche, secondary_niches, recommendations

**Hardcoded Strings:** "Instagram sync is coming soon" (L113, L195), niche score labels.

**Known Issues:** All data from real API but gated behind Instagram sync which doesn't exist yet.

---

### 3.10 `/studio` — Creator Studio

**File:** `frontend/src/routes/studio.tsx` (529 lines)

**Route Config:** Plan-gated: `<PlanGate feature="Creator Studio" requiredPlan="pro">`.

**Tabs:** `"prepost" | "hooks" | "seo"`

**API Calls:**

| Endpoint | Method | Trigger |
|----------|--------|---------|
| `/api/prepost-score` | POST | Pre-Post form submit |
| `/api/generate-hooks` | POST | Hook generator submit |
| `/api/seo-caption` | POST | SEO caption submit |

All manually add `Authorization: Bearer <token>` header.

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Tab buttons (3) | 212-238 | Switch active tool |
| Pre-Post form (6 inputs) | 244-317 | Submit calls `handleAnalyze` |
| Hook Generator form | 386-412 | Submit calls `handleGenerateHooks` |
| SEO form | 447-474 | Submit calls `handleGenerateSeo` |
| Copy hook/caption/alt-text | various | Clipboard API |

**Hardcoded Strings:** Input placeholders, default postTime "18:30", default seoPlatform "instagram".

**Known Issues:**
- `is_simulated` flag (L34) — rule-based fallback when LLM fails
- Default postTime hardcoded

---

### 3.11 `/marketplace` — Creator Marketplace

**File:** `frontend/src/routes/marketplace.tsx` (468 lines)

**Route Config:** Gated behind `FEATURES.MARKETPLACE_ENABLED` — **currently false, redirects to `/`**.

**Tabs:** `"discover" | "matches"`

**API Calls:**
- `fetchCreatorProfiles(nicheFilter)` → `GET /api/marketplace/profiles`
- `fetchCollabMatchesForUser(userEmail)` → `GET /api/collab-matches/{email}`
- `sendCollabReq()` → `POST /api/send-collab-request`

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Discover/Matches tabs | 159-180 | Switch active tab |
| Search input | 190-196 | Client-side filter |
| Niche filter chips | 200-215 | Re-fetches profiles |
| "Collab" button | 294-302 | Opens collab modal |
| Portfolio link | 303-313 | External `<a>` |
| "Send Collab Request" | 403-414 | Opens collab modal |
| Collab modal textarea | 446-451 | Message input |
| Collab modal submit | 453-461 | Calls `collabMutation` |

**Hardcoded Strings:** Niche labels with emojis.

**Known Issue:** Entire feature is disabled via feature flag.

---

### 3.12 `/trend/$id` — Trend Detail Page

**File:** `frontend/src/routes/trend.$id.tsx` (608 lines)

**Route Config (L17-26):** `errorComponent: RouteErrorBoundary`. Param: `$id`.

**API Queries (5 parallel):**

| Query | Endpoint |
|-------|----------|
| `fetchTrendById(id)` | `GET /api/trends/{id}` |
| `fetchCaptionKit(id)` | `GET /api/trends/{id}/caption` |
| `fetchSimilarTrends(id)` | `GET /api/trends/{id}/similar` |
| `fetchTrendReels(id)` | `GET /api/trends/{id}/reels` |
| `fetchTrendDecision(id)` | `GET /api/trends/{id}/decision` |

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Back button | 101-103, 127-132 | Navigates to `/` |
| Copy caption button | 370-377 | Copies caption text by vibe index |
| Copy hashtags button | 384-390 | Copies all hashtags |
| Share on WhatsApp | 241-247 | Opens `wa.me` with pre-filled text |
| "Generate Reel →" | 249-254 | Navigates to `/generate?trendId=...` |
| Similar trend buttons | 559-574 | Navigate to `/trend/$id` |
| Bottom "Generate My Reel" | 581-587 | Same as above |
| Vibe tab buttons | 352-365 | Set `selectedVibe` index |

**Conditional Renders:**
- Loading skeleton (L98-108)
- "Trend not found" (L111-119)
- "Under Radar" badge if `discoverySource === "unexpected_candidate"` (L141-145)
- "Creator Breakout" badge if outlier reel (L146-150)
- Language badge (L151-157)
- Semantic niches (L185-193)
- Niche relevance scores (L208-232)
- Decision Layer (gated by PlanGate) (L287-312)
- Audio cue section (L315-329)
- Caption Kit (gated by PlanGate) (L332-407)
- Keywords Strategy (L410-475)
- Source Reels (gated by PlanGate) (L490-552)
- Similar Past Trends (L555-577)

**Hardcoded Strings:** WhatsApp share text template with `trendrop.ai` URL, waveform bar heights `[7,4,9,6,10,5,8,3,7,5]`.

**Known Issues:**
- L14: Unused `zod` import
- "Caption generation is coming soon" placeholder text

---

### 3.13 `/proof` — Early Detection Proof

**File:** `frontend/src/routes/proof.tsx` (166 lines)

**API:** `GET /api/proof` — returns `{ proof: ProofItem[] }`. staleTime 5min.

**Data Displayed:** Total trends tracked, detected early, already peaked. Individual proof items with title, audio_name, status badge, artist, niche, language, detected_at, peak_at, hours_early.

**Hardcoded Strings:** "Early Detection Proof", "We detect trends before they peak", error/empty states.

**No interactive elements beyond navigation.** Purely informational.

---

### 3.14 `/data-rights` — Data Rights (DPDP Act)

**File:** `frontend/src/routes/data-rights.tsx` (346 lines)

**API Calls:**
- `supabase.from("consent_records").insert(...)` — logs consent changes
- `supabase.from("users").select("*")` — user profile
- `supabase.from("jobs").select("*")` — jobs history
- `supabase.from("consent_records").select("*")` — consent records
- Downloads compiled data as JSON blob
- Deletes from 3 Supabase tables on account deletion

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Back arrow | 167-172 | Navigates to `/settings` |
| "Download My Data Package" | 200-206 | Fetches 3 tables, compiles JSON, triggers download |
| Trend Alerts toggle | 225-236 | Flips localStorage, logs consent to Supabase |
| Daily Ideas toggle | 245-256 | Same pattern |
| Brand Deals toggle | 265-276 | Same pattern |
| ToS & Privacy toggle | 285-296 | Triggers `window.confirm`, then account deletion |
| "Erase All My Data" | 325-332 | Double `window.confirm`, deletes 3 tables, signs out |
| "Return to Settings" | 337-342 | Navigates to `/settings` |

**Hardcoded Strings:** "Digital Personal Data Protection Act, 2023 (India)", IP fallback "127.0.0.1".

**Known Issues:**
- L72: `type.replace("_", " ")` only replaces first underscore
- `termsConsent` always `true`, no sync from backend
- No auth guard — page accessible to unauthenticated users

---

### 3.15 `/privacy` — Privacy Policy

**File:** `frontend/src/routes/privacy.tsx` (129 lines)

**Purely presentational.** No state, no API calls.

**Hardcoded Strings:** "Last updated: June 25, 2026", DPO name "Data Protection Officer", email `privacy@trendrop.app`, "AWS Mumbai Region, ap-south-1", all legal text.

---

### 3.16 `/terms` — Terms of Service

**File:** `frontend/src/routes/terms.tsx` (105 lines)

**Purely presentational.** No state, no API calls.

**Hardcoded Strings:** "Last updated: June 25, 2026", all legal text, "zero-tolerance policy", "Safe Search Moderation".

---

### 3.17 `/reset-password` — Password Reset Request

**File:** `frontend/src/routes/reset-password.tsx` (140 lines)

**API:** `resetPassword(email)` → `POST /api/auth/reset-password`

**Interactive Elements:** Email input, Submit button ("Send Reset Link"), Error banner, Success state with "Return to Login" button.

**Hardcoded Strings:** "Enter your email and we'll send you a link", "Send Reset Link" / "Sending...", success message template.

---

### 3.18 `/update-password` — Password Update

**File:** `frontend/src/routes/update-password.tsx` (149 lines)

**API:** `supabase.auth.updateUser({ password })` — direct Supabase client call.

**Session Detection:** Checks for `access_token` in URL hash or existing Supabase session.

**Interactive Elements:** Password input (minLength 8), Submit button ("Update Password"), Error banner, Success state with "Go to Login" button.

**Known Issues:** Silent failure if hash token is invalid (L34-36).

---

### 3.19 `/verify-phone` — Phone Verification (OTP)

**File:** `frontend/src/routes/verify-phone.tsx` (199 lines)

**Search Params:** `phone` from query string.

**API Calls:**
- `POST /api/auth/verify-phone` — body: `{ phone_number, code }`
- `POST /api/auth/send-otp` — body: `{ phone_number }`

**Interactive Elements:** Code input (6 digits, numeric, strips non-digits), Submit button, Resend button with 30s cooldown.

**Known Issues:**
- `useAuth` imported but never used (L9) — dead import
- No phone number format validation

---

### 3.20 `/deals/` — Brand Deals Dashboard

**File:** `frontend/src/routes/deals.index.tsx` (605 lines)

**Feature Gate:** `FEATURES.DEALS_ENABLED` — **currently false**, shows "Deals Launch After Beta" placeholder.

**API Calls:**
- `apiFetch("/api/deals")` — GET deals list
- `apiFetch("/api/deals/${dealId}/pay-milestone/${milestoneId}", { method: "POST" })` — mark paid
- `apiFetch("/api/deals/${dealId}/download")` — download contract PDF
- `logAnalyticsEvent("contract_downloaded")` — analytics
- `submitCreatorFeedback()` — feedback submission

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| "New Deal" button | 251-256 | Navigates to `/deals/new` |
| Tab: All/Active/Overdue | 277-294 | Filters deal list |
| "Mark as Paid" | 416-424 | POST to mark milestone paid |
| "Follow-up" | 425-433 | Opens follow-up modal |
| "Download Contract" | 450-458 | Downloads PDF, triggers feedback modal |
| Follow-up modal close | 483-488 | Closes modal |
| Hinglish/English copy | 496-525 | Copies template text |
| Feedback modal skip/useful/not_useful | 554-577 | Rating selection |
| Feedback comment textarea | 582-588 | Comment input |
| Submit feedback | 591-597 | Submits feedback |

**Hardcoded Strings:** "Deals Launch After Beta", INR currency `₹`, follow-up templates (Hinglish + English), "Contract finalized" (always shown regardless of status).

**Known Issues:**
- Dead imports: `ExternalLink`, `DollarSign`, `TrendingUp`
- `rate_amount` and `currency` never displayed
- No pagination

---

### 3.21 `/deals/new` — Create Brand Deal

**File:** `frontend/src/routes/deals.new.tsx` (59 lines)

**Pure stub/placeholder page.** Auth-gated + feature-gated.

**Hardcoded Strings:** "Create Campaign Deal", "Fill details to auto-generate contract PDF" (STUB), "Coming Soon", "Deal creation will be available once the marketplace launches."

---

### 3.22 `/admin/login` — Admin Login

**File:** `frontend/src/routes/admin.login.tsx` (147 lines)

**API:** `POST /api/admin/login` with `{ email, password }`. Expects `{ access_token, email, role }`.

**On Success:** Stores `admin_token`, `admin_email`, `admin_role` in localStorage. Navigates to `/admin/users`.

**Interactive Elements:** Email input, Password input, Submit button ("Sign In" / "Signing in..."), "Return to Dashboard" button.

---

### 3.23 `/admin/users` — Admin User Management

**File:** `frontend/src/routes/admin.users.tsx` (416 lines)

**Auth Guard (L16-52):** `beforeLoad` — checks `admin_token` in localStorage, validates via `POST /api/admin/validate-token`.

**API Calls:**
- `getAdminUsers(search, planFilter)` → `GET /api/admin/users`
- `getAdminUserDetails(email)` → `GET /api/admin/users/{email}`
- `updateAdminUserPlan(email, newPlan, "Admin update")` → `POST /api/admin/users/{email}/plan`
- `lockAdminUserAccount(email, "Admin lock")` → `POST /api/admin/users/{email}/lock`
- `unlockAdminUserAccount(email, "Admin unlock")` → `POST /api/admin/users/{email}/unlock`

**Interactive Elements:**

| Element | Line | Behavior |
|---------|------|----------|
| Back button | 165-170 | Navigates to `/` |
| Search input | 186-192 | Triggers re-fetch |
| Plan filter select | 196-206 | Options: all/free/pro |
| "Details" button | 257-264 | Opens user detail modal |
| Lock/Unlock button | 265-283 | Toggles account lock |
| Modal close | 301-308 | Closes modal |
| "Free" plan button | 343-350 | Changes plan |
| "Pro" plan button | 351-358 | Changes plan |

**User Details Modal (L292-413):** Shows account info, change plan buttons, usage statistics, registered devices.

**Known Issues:**
- All state typed as `any`
- No confirmation dialog on destructive operations
- Copy-pasted `beforeLoad` across all 4 admin routes (~120 lines of duplication)

---

### 3.24 `/admin/plans` — Admin Plan Management

**File:** `frontend/src/routes/admin.plans.tsx` (336 lines)

**Auth Guard:** Same pattern as admin/users.

**API Calls:**
- `getAdminPlanFeatures()` → `GET /api/admin/plan-features`
- `createAdminPlanFeature({...})` → `POST /api/admin/plan-features`

**Interactive Elements:** Edit button per plan, Modal with editable fields (display_name, monthly_price, yearly_price, api_limit_per_day, trend_views_per_day, features textarea), Save button.

**Known Issues:**
- Uses CREATE endpoint for edits (upsert pattern)
- `plan_name` input disabled but has onChange handler (dead code)
- No delete plan functionality
- No validation on number inputs

---

### 3.25 `/admin/audit` — Admin Audit Log

**File:** `frontend/src/routes/admin.audit.tsx` (260 lines)

**Auth Guard:** Same pattern.

**API:** `getAdminAuditLog(debouncedSearch, actionFilter, 100, dateFrom, dateTo)` → `GET /api/admin/audit-log`.

**Interactive Elements:** Search input (500ms debounce), Action filter select (all/plan_change/account_lock/account_unlock/login_attempt), Date from/to inputs, Export CSV button.

**CSV Export:** Generates CSV with columns: ID, Admin Email, Action, Target User, IP Address, Timestamp, Details.

**Known Issues:**
- `filteredLogs` variable assigned but never used (dead code, L112)
- `log.action.replace("_", " ")` only replaces first underscore
- No pagination (hardcoded limit 100)
- Unused import: `Calendar`

---

### 3.26 `/admin/analytics` — Admin Analytics

**File:** `frontend/src/routes/admin.analytics.tsx` (182 lines)

**Auth Guard:** Same pattern.

**API:** `getAdminAnalyticsSummary()` → `GET /api/admin/analytics-summary`.

**Data Displayed:** 4 hardcoded event keys with descriptions:
- `deal_created`, `contract_downloaded`, `milestone_set`, `reminder_clicked`

**Interactive Elements:** Refresh button.

**Known Issues:**
- `eventDescriptions` is hardcoded — new events silently ignored
- 403 detection uses string match `err.message?.includes("403")` (fragile)
- Unused import: `BarChart2`
- Same single-replacement bug on `replace("_", " ")`

---

## 4. Component Inventory

### Custom Components (`frontend/src/components/`)

| Component | File | Props | Used In | Purpose |
|-----------|------|-------|---------|---------|
| `TrendCard` | `TrendCard.tsx` (972 lines) | `trend: UiTrend, onDanceTap, selectedNiche?` | index.tsx | Main trend display card with expand/collapse, 3D tilt, all trend data |
| `TrendCardVideo` | `TrendCardVideo.tsx` (27 lines) | `reel, trendId?, opportunityScore?` | TrendCard | Wrapper for AudioIdentityCard |
| `TrendPreviewModal` | `TrendPreviewModal.tsx` (214 lines) | `trend, isOpen, onClose` | TrendCard | Dialog with trend preview, Instagram deep-links |
| `BottomTabBar` | `BottomTabBar.tsx` (113 lines) | None | __root.tsx | Fixed bottom navigation, feature-flag gated tabs |
| `AuthGuard` | `AuthGuard.tsx` (36 lines) | `children` | (available) | Redirects to /login if unauthenticated |
| `AuthWrapper` | `AuthWrapper.tsx` (89 lines) | `children` | __root.tsx | Handles auth redirects, listens for trendrop:unauthorized events |
| `PlanGate` | `PlanGate.tsx` (67 lines) | `feature, requiredPlan, currentPlan?, children, onUpgrade?` | generate, studio, ideas, trend.$id, dashboard tabs | Pro plan gate with blur overlay |
| `FilterPills` | `FilterPills.tsx` (31 lines) | `active, onChange` | (available) | Horizontal scrollable category pills |
| `SkeletonCard` | `SkeletonCard.tsx` (36 lines) | None | index.tsx | Shimmer loading skeleton |
| `AIContentGenerator` | `AIContentGenerator.tsx` (414 lines) | None | dashboard.tsx | 4-tab AI tool (caption/ideas/hooks/script) |
| `AlgorithmInsightsPanel` | `AlgorithmInsightsPanel.tsx` (230 lines) | `analysis?, loading?, onAnalyze?` | TrendCard | Virality analysis display |
| `CreatorAnalyticsDashboard` | `CreatorAnalyticsDashboard.tsx` (307 lines) | `creatorEmail` | dashboard.tsx | Charts, metrics, recommendations |
| `IndiaFeaturesDashboard` | `IndiaFeaturesDashboard.tsx` (296 lines) | None | dashboard.tsx | Regional timing, festivals, patterns |
| `EarlyDetectionPanel` | `EarlyDetectionPanel.tsx` (382 lines) | None | dashboard.tsx | Early trends + cultural events |
| `NewsFeedPanel` | `NewsFeedPanel.tsx` (134 lines) | None | dashboard.tsx | Breaking news trend cards |
| `NewsTrendCard` | `NewsTrendCard.tsx` (163 lines) | `trend, userNiche, index?` | NewsFeedPanel | Individual news trend card |
| `DanceTrendModal` | `DanceTrendModal.tsx` (245 lines) | `trend, onClose` | index.tsx | Production playbook modal |
| `AudioIdentityCard` | `AudioIdentityCard.tsx` (128 lines) | `audioId?, audioTitle?, audioArtist?, audioUseCount?, trendId?, opportunityScore?` | TrendCardVideo | Audio waveform + sparkline + IG link |
| `VideoAnalysisPanel` | `VideoAnalysisPanel.tsx` (190 lines) | None | dashboard.tsx | **STUB** — video virality prediction |
| `TrendProofSection` | `TrendProofSection.tsx` (97 lines) | `trendId, isPeaking` | TrendCard | Timeline + velocity chart |
| `RegionalFestivalPanel` | `RegionalFestivalPanel.tsx` (246 lines) | None | dashboard.tsx | Cultural events + festivals |
| `OnboardingFlow` | `OnboardingFlow.tsx` (351 lines) | `onComplete` | (available, commented out) | 4-step onboarding wizard |
| `OnboardingTour` | `OnboardingTour.tsx` (214 lines) | `onComplete, open` | dashboard.tsx | 4-step feature tour |
| `FeatureTutorial` | `FeatureTutorial.tsx` (134 lines) | `onClose` | (available, commented out) | 5-step tutorial overlay |
| `InstallBanner` | `InstallBanner.tsx` (105 lines) | None | __root.tsx | PWA install prompt, 30s delay |
| `ParticleBackground` | `ParticleBackground.tsx` (150 lines) | None | (available) | Three.js WebGL particles |
| `PremiumCard` | `PremiumCard.tsx` (49 lines) | `glowColor?, delayIndex?, hoverEffect?` + `HTMLMotionProps<"div">` | (available) | Animated card wrapper |
| `RouteErrorBoundary` | `RouteErrorBoundary.tsx` (32 lines) | `error, reset` | Multiple routes | Error UI with retry |
| `ApiErrorBanner` | `ApiErrorBanner.tsx` (10 lines) | `message?` | index.tsx | Static error banner |
| `ThemeToggle` | `ThemeToggle.tsx` (61 lines) | None | index.tsx | Dark/light theme toggle |
| `SparklineChart` | `SparklineChart.tsx` (55 lines) | `data, color?, height?` | AudioIdentityCard | SVG polyline chart |
| `TrenddropLogo` | `TrenddropLogo.tsx` (62 lines) | `iconOnly?, size?, animate?, variant?, className?` | (available) | Logo with SVG icon |

### shadcn/ui Primitives (`frontend/src/components/ui/`)

48 files: accordion, alert-dialog, alert, aspect-ratio, avatar, badge, breadcrumb, button, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, dialog, drawer, dropdown-menu, form, hover-card, input-otp, input, label, menubar, navigation-menu, pagination, popover, progress, radio-group, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, SkeletonSystem (custom), slider, sonner, switch, table, tabs, textarea, ToastSystem (custom), toggle-group, toggle, tooltip.

**Custom UI components:**
- `SkeletonSystem.tsx`: `Skeleton`, `TrendCardSkeleton`, `MetricSkeleton`, `ProfileSkeleton`
- `ToastSystem.tsx`: `showToast.success/error/warning/info/trendAlert` with custom borders

---

## 5. API Layer & Backend Cross-Reference

### Frontend API Functions (`frontend/src/lib/api.ts`, 1687 lines)

**Exported Constants:**
- `API_URL` (L7): From `VITE_API_URL`, fallback `http://localhost:8000` in dev, `""` in prod
- `VIRAL_SCALE_FACTOR` (L426): `10000` (hardcoded, must match backend)
- `VIRAL_DISPLAY_MULTIPLIER` (L427): `10` (hardcoded)
- `inMemoryToken` (L431): Module-level token cache

**Internal Helpers:**
- `http<T>` (L473-499): Attaches Bearer token, 15s AbortController timeout, dispatches `trendrop:unauthorized` on 401
- `apiFetch` (L501-526): Same pattern for raw Response returns

**All Exported Functions:**

| Function | Method | Endpoint | Frontend Usage |
|----------|--------|----------|----------------|
| `fetchTrends` | GET | `/api/trends` | index.tsx |
| `fetchEmergingTrends` | GET | `/api/trends/emerging` | index.tsx |
| `fetchPeakedTrends` | GET | `/api/trends/peaked` | index.tsx |
| `fetchExpiredTrends` | GET | `/api/trends/expired` | index.tsx |
| `fetchAllActiveTrends` | GET | `/api/trends/all-active` | (available) |
| `fetchTrendById` | GET | `/api/trends/{id}` | trend.$id.tsx |
| `fetchSimilarTrends` | GET | `/api/trends/{id}/similar` | trend.$id.tsx |
| `fetchCaptionKit` | GET | `/api/trends/{id}/caption` | trend.$id.tsx |
| `fetchTrendReels` | GET | `/api/trends/{id}/reels` | trend.$id.tsx, TrendCard |
| `fetchTrendDecision` | GET | `/api/trends/{id}/decision` | trend.$id.tsx |
| `fetchAudioHistory` | GET | `/api/trends/{id}/audio-history` | AudioIdentityCard |
| `analyzeContentForVirality` | GET | `/api/algorithm/analyze` | TrendCard |
| `getOptimalPostingTimes` | GET | `/api/algorithm/posting-times` | (available) |
| `getHashtagStrategy` | GET | `/api/algorithm/hashtag-strategy` | (available) |
| `getActiveEvents` | GET | `/api/events/active` | (available) |
| `getEventOpportunities` | GET | `/api/events/{id}/opportunities` | (available) |
| `detectHashtagSpikes` | GET | `/api/events/hashtag-spikes` | (available) |
| `getHashtagVelocity` | GET | `/api/hashtags/velocity` | (available) |
| `getTrendingHashtags` | GET | `/api/hashtags/trending` | (available) |
| `getTopicClusters` | GET | `/api/topics/clusters` | (available) |
| `detectConversations` | GET | `/api/conversations/detect` | (available) |
| `getCreatorMetrics` | GET | `/api/creator/metrics` | CreatorAnalyticsDashboard |
| `getTrendAdoptionHistory` | GET | `/api/creator/trend-adoption` | CreatorAnalyticsDashboard |
| `getContentPerformanceOverTime` | GET | `/api/creator/performance-over-time` | CreatorAnalyticsDashboard |
| `getSuccessRecommendations` | GET | `/api/creator/recommendations` | CreatorAnalyticsDashboard |
| `generateCaption` | GET | `/api/ai/generate-caption` | AIContentGenerator |
| `generateContentIdeas` | GET | `/api/ai/content-ideas` | AIContentGenerator |
| `generateAIHooks` | GET | `/api/ai/generate-hooks` | AIContentGenerator |
| `generateScriptOutline` | GET | `/api/ai/script-outline` | AIContentGenerator |
| `getRegionalTrends` | GET | `/api/india/regional-trends` | IndiaFeaturesDashboard |
| `getRegionalTimingOptimization` | GET | `/api/india/regional-timing` | IndiaFeaturesDashboard |
| `getCulturalEventAutomation` | GET | `/api/india/cultural-events` | EarlyDetectionPanel, RegionalFestivalPanel |
| `detectLanguageCrossover` | POST | `/api/india/detect-language` | IndiaFeaturesDashboard |
| `getRegionalHashtagStrategy` | GET | `/api/india/hashtag-strategy` | IndiaFeaturesDashboard |
| `getCreatorPatternAnalysis` | GET | `/api/india/creator-patterns` | IndiaFeaturesDashboard |
| `generateReel` | POST | `/api/generate-reel` | generate.tsx |
| `generateNarrative` | POST | `/api/generate-narrative` | generate.tsx |
| `generateFaceless` | POST | `/api/generate-faceless` | generate.tsx |
| `repurposeVideo` | POST | `/api/repurpose` | generate.tsx |
| `jobStatus` | GET | `/api/job-status/{id}` | generate.tsx |
| `reelStatus` | — | delegates to `jobStatus` | (available) |
| `fetchDailyIdeas` | GET | `/api/daily-ideas/{email}` | ideas.tsx |
| `scoreReel` | POST | `/api/score-reel` | ideas.tsx, generate.tsx |
| `generateHooks` | POST | `/api/generate-hooks` | ideas.tsx |
| `generateCalendar` | GET | `/api/generate-calendar/{email}` | ideas.tsx |
| `subscribe` | POST | `/api/subscribe` | OnboardingFlow |
| `login` | POST | `/api/auth/login` | login.tsx |
| `signup` | POST | `/api/auth/signup` | signup.tsx |
| `logout` | POST | `/api/auth/logout` | AuthContext |
| `verifySession` | POST | `/api/auth/verify` | AuthContext |
| `resetPassword` | POST | `/api/auth/reset-password` | reset-password.tsx |
| `createPaymentOrder` | POST | `/api/payment/create-order` | (available, not wired) |
| `verifyPayment` | POST | `/api/payment/webhook` | (available, not wired) |
| `getUserPlan` | GET | `/api/user/plan` | (available) |
| `getUserCredits` | GET | `/api/user/credits` | (available) |
| `getAdminUsers` | GET | `/api/admin/users` | admin.users.tsx |
| `getAdminUserDetails` | GET | `/api/admin/users/{email}` | admin.users.tsx |
| `updateAdminUserPlan` | POST | `/api/admin/users/{email}/plan` | admin.users.tsx |
| `lockAdminUserAccount` | POST | `/api/admin/users/{email}/lock` | admin.users.tsx |
| `unlockAdminUserAccount` | POST | `/api/admin/users/{email}/unlock` | admin.users.tsx |
| `getAdminBusinessMetrics` | GET | `/api/admin/business-metrics` | (available) |
| `getAdminAuditLog` | GET | `/api/admin/audit-log` | admin.audit.tsx |
| `getAdminPlanFeatures` | GET | `/api/admin/plan-features` | admin.plans.tsx |
| `createAdminPlanFeature` | POST | `/api/admin/plan-features` | admin.plans.tsx |
| `getAdminAnalyticsSummary` | GET | `/api/admin/analytics-summary` | admin.analytics.tsx |
| `submitFeedback` | POST | `/api/feedback` | (available) |
| `fetchBrandDeals` | GET | `/api/brand-deals/{email}` | deals.index.tsx (via apiFetch) |
| `applyToBrandDeal` | POST | `/api/apply-deal` | (available) |
| `fetchCollabMatches` | GET | `/api/collab-matches/{email}` | marketplace.tsx (via apiFetch) |
| `sendCollabRequest` | POST | `/api/send-collab-request` | marketplace.tsx (via apiFetch) |
| `fetchUserFeed` | GET | `/api/reels/feed` | (available) |
| `fetchCreatorDiagnostics` | GET | `/api/creator/diagnostics` | stats.tsx |
| `fetchCreatorNicheHealth` | GET | `/api/creator/niche-health` | stats.tsx |
| `logAnalyticsEvent` | POST | `/api/analytics/log` | deals.index.tsx |
| `submitCreatorFeedback` | POST | `/api/creator/feedback` | deals.index.tsx |
| `toggleTrendTarget` | POST | `/api/trends/{id}/target` | TrendCard, DanceTrendModal |
| `fetchTargetedTrends` | GET | `/api/trends/targeted` | index.tsx |

**API Functions with NO frontend page calling them (defined but unused):**

| Function | Endpoint |
|----------|----------|
| `fetchAllActiveTrends` | `GET /api/trends/all-active` |
| `getOptimalPostingTimes` | `GET /api/algorithm/posting-times` |
| `getHashtagStrategy` | `GET /api/algorithm/hashtag-strategy` |
| `getActiveEvents` | `GET /api/events/active` |
| `getEventOpportunities` | `GET /api/events/{id}/opportunities` |
| `detectHashtagSpikes` | `GET /api/events/hashtag-spikes` |
| `getHashtagVelocity` | `GET /api/hashtags/velocity` |
| `getTrendingHashtags` | `GET /api/hashtags/trending` |
| `getTopicClusters` | `GET /api/topics/clusters` |
| `detectConversations` | `GET /api/conversations/detect` |
| `reelStatus` | delegates to jobStatus |
| `createPaymentOrder` | `POST /api/payment/create-order` |
| `verifyPayment` | `POST /api/payment/webhook` |
| `getUserPlan` | `GET /api/user/plan` |
| `getUserCredits` | `GET /api/user/credits` |
| `getAdminBusinessMetrics` | `GET /api/admin/business-metrics` |
| `submitFeedback` | `POST /api/feedback` |
| `applyToBrandDeal` | `POST /api/apply-deal` |
| `fetchUserFeed` | `GET /api/reels/feed` |
| `logAnalyticsEvent` | `POST /api/analytics/log` |
| `submitCreatorFeedback` | `POST /api/creator/feedback` |
| `resetPassword` | `POST /api/auth/reset-password` |

---

## 6. Feature Flags

**File:** `frontend/src/lib/features.ts` (13 lines)

```typescript
export const FEATURES = {
  GENERATE_ENABLED: true,
  IDEAS_ENABLED: true,
  DEALS_ENABLED: false,
  MARKETPLACE_ENABLED: false,
  INSTAGRAM_OAUTH_ENABLED: false,
  CALENDAR_ENABLED: true,
} as const;
```

| Flag | Value | Controls |
|------|-------|----------|
| `GENERATE_ENABLED` | `true` | Generate tab in BottomTabBar, "Generate Reel" buttons in TrendCard and trend.$id.tsx |
| `IDEAS_ENABLED` | `true` | Ideas tab in BottomTabBar, "Daily Content Ideas" notification toggle in settings, Ideas page feature gate |
| `DEALS_ENABLED` | `false` | Deals tab in BottomTabBar, deals.index.tsx entire page, deals.new.tsx entire page, "Brand Collaboration Alerts" toggle in settings |
| `MARKETPLACE_ENABLED` | `false` | Marketplace tab in BottomTabBar, marketplace.tsx entire page redirect |
| `INSTAGRAM_OAUTH_ENABLED` | `false` | Instagram handle + follower count inputs in settings |
| `CALENDAR_ENABLED` | `true` | Calendar tab in ideas.tsx, Events tab in EarlyDetectionPanel |

---

## 7. State Management

### Zustand Stores (`frontend/src/store/useAppStore.ts`, 149 lines)

**`useUserStore`:**

| Field | Initial | Persisted Key |
|-------|---------|---------------|
| `email` | `null` | `trendrop_user_email` |
| `niche` | `null` | `trendrop_niche` |
| `language` | `null` | `trendrop_language` |
| `plan` | `null` | `trendrop_user_plan` |
| `authToken` | `null` | `trendrop_token` |
| `isOnboarded` | `false` | `trendrop_onboarded` |

Actions: `initializeFromLocalStorage()`, `setUser(updates)`, `logout()` (clears 7 localStorage keys).

**`useTrendsStore`:**
- `activeCategory: "all"`, `searchQuery: ""`, `sortBy: "velocity"`
- Actions: `setActiveCategory`, `setSearchQuery`, `setSortBy`

**`useGenerateStore`:**
- `files: []`, `currentJobId: null`, `generationProgress: 0`, `generationStatus: "idle"`, `history: []`
- Actions: `setFiles`, `setCurrentJobId`, `setGenerationProgress`, `setGenerationStatus`, `addHistoryItem`, `clearFiles`

### Auth Context (`frontend/src/contexts/AuthContext.tsx`, 265 lines)

**State:** `user: {email, niche, language, plan} | null`, `loading: boolean`.

**Functions:**
- `checkAuth()` — reads `trendrop_session_token`, POSTs to `/api/auth/verify` with 8s timeout
- `login()` — `supabase.auth.signInWithPassword()`, then `/api/auth/verify` for profile
- `signup()` — POSTs to `/api/auth/signup`, handles 3 paths (phone verification, auto-login, redirect to login)
- `logout()` — POSTs to `/api/auth/logout`, clears 12 localStorage keys

**Fallback on network error:** Restores user from localStorage cache (niche=`"all"`, language=`"en"`, plan=`"free"`).

### Custom Hooks

| Hook | File | Purpose |
|------|------|---------|
| `useIsMobile` | `frontend/src/hooks/use-mobile.tsx` | Responsive mobile breakpoint detection |
| `useSaturationCount` | `frontend/src/hooks/useSaturationCount.ts` | Supabase Realtime subscription on `trend_actions` table for live saturation count |
| `useOnboarding` | `OnboardingTour.tsx:201-214` | Returns `{ isOpen, startOnboarding, closeOnboarding }` |

---

## 8. Styling System

**Primary:** Tailwind CSS v4.2 with `@tailwindcss/vite` plugin.

**Custom CSS:** `frontend/src/styles.css` (616 lines) — custom CSS variables, theme system (light/dark), brand colors, glass-card styles.

**Theme:** Dark mode via `data-theme="dark"` on body/html. Persisted to `localStorage("trendrop_theme")`.

**CSS Custom Properties Used:**
- `--primary`, `--color-primary` (theme color buttons)
- `--surface`, `--border`, `--text-100`, `--font-sans` (used in Toaster)

**Animation Libraries:**
- Framer Motion for page transitions, card animations, modals
- CSS `@keyframes` for waveform bars, particle effects
- `tw-animate-css` for Tailwind animations

**Consistent Patterns:**
- `glass-card` — glassmorphic card styling
- `gradient-text` — gradient text effect
- `shimmer` — loading skeleton animation
- `no-scrollbar` — hidden scrollbar overflow
- Design tokens: `bg-background`, `bg-card`, `border-border`, `text-primary`, `text-muted-foreground`

---

## 9. User-Facing Strings

### Navigation & Layout

| String | Location | Line |
|--------|----------|------|
| "Trendrop — India's Trend Intelligence" | __root.tsx `<title>` | 77 |
| "Trends" | BottomTabBar | 41 |
| "Dashboard" | BottomTabBar | 42 |
| "Generate" | BottomTabBar | 43 |
| "Ideas" | BottomTabBar | 44 |
| "Marketplace" | BottomTabBar | 45 |
| "Deals" | BottomTabBar | 46 |
| "Settings" | BottomTabBar | 47 |
| "Login" | BottomTabBar | 47 |
| "404" | __root.tsx NotFoundComponent | 26 |
| "Page not found" | __root.tsx NotFoundComponent | 27 |
| "Go home" | __root.tsx NotFoundComponent | 28 |
| "Something went wrong" | RouteErrorBoundary | 13 |
| "We ran into an issue loading this section. Our team has been notified." | RouteErrorBoundary | 14 |
| "Try again" | RouteErrorBoundary | 24 |
| "Loading..." | AuthGuard | 25 |

### Trends Feed (`/`)

| String | Location | Line |
|--------|----------|------|
| "Rising" | TabButton | 538 |
| "Emerging" | TabButton | 538 |
| "Workspace" | TabButton | 538 |
| "Peaked" | TabButton | 538 |
| "Expired" | TabButton | 538 |
| "🚨 {count} new emerging trend(s) just detected!" | index.tsx toast | 163 |
| "Trends are warming up — showing peaked content while fresh data loads" | index.tsx banner | 431 |
| "All", "Fitness", "Food", "Comedy", "Fashion", "Business", "Travel", "Beauty" | index.tsx niche chips | 49 |
| "Service temporarily unavailable" | ApiErrorBanner default | 7 |

### Auth Pages

| String | Location | Line |
|--------|----------|------|
| "Welcome Back" | login.tsx | 59 |
| "Login to your Trendrop account" | login.tsx | 62 |
| "Email" | login.tsx | 71 |
| "Password" | login.tsx | 91 |
| "Forgot password?" | login.tsx | 99 |
| "Logging in..." | login.tsx | 131 |
| "Don't have an account?" | login.tsx | 138 |
| "Sign up" | login.tsx | 144 |
| "Create Account" | signup.tsx | 107 |
| "Join Trendrop to discover trending content" | signup.tsx | 110 |
| "Enter your email and we'll send you a link" | reset-password.tsx | 61 |
| "Send Reset Link" | reset-password.tsx | 102 |
| "Sending..." | reset-password.tsx | 102 |
| "Enter your new secure password" | update-password.tsx | 82 |
| "Update Password" | update-password.tsx | 124 |
| "Updating..." | update-password.tsx | 124 |
| "Verify your phone" | verify-phone.tsx | 137 |
| "We sent a 6-digit code to {phone}" | verify-phone.tsx | 140 |
| "Verify & Continue" | verify-phone.tsx | 179 |
| "Verifying..." | verify-phone.tsx | 179 |
| "Resend code" | verify-phone.tsx | 191 |
| "Missing Phone Number" | verify-phone.tsx | 120 |

### Pricing

| String | Location | Line |
|--------|----------|------|
| "Simple, Transparent Pricing" | pricing.tsx | 40 |
| "Browse trends for free. Pay for AI-powered content generation." | pricing.tsx | 43 |
| "Free" | pricing.tsx | 52 |
| "₹0 / month" | pricing.tsx | 55 |
| "₹999 / month" | pricing.tsx | 109 |
| "Best Value" | pricing.tsx | 101 |
| "Current Plan" | pricing.tsx | 84, 135 |
| "Downgrade to Free" | pricing.tsx | 91 |
| "Pro upgrade will be available soon via Razorpay!" | pricing.tsx | 33 |

### Settings

| String | Location | Line |
|--------|----------|------|
| "Save Settings" | settings.tsx | 637 |
| "Saving..." | settings.tsx | 638 |
| "Logout" | settings.tsx | 604 |
| "Reset Tutorial" | settings.tsx | 512 |

### Generate

| String | Location | Line |
|--------|----------|------|
| "Create Reel" | generate.tsx | photos tab |
| "Generate Narrative Reel" | generate.tsx | narrative tab |
| "Generate Faceless Video" | generate.tsx | faceless tab |
| "Repurpose with Beat Sync" | generate.tsx | repurpose tab |
| "Cancel Generation" | generate.tsx | progress stage |
| "Download" | generate.tsx | result stage |
| "Share" | generate.tsx | result stage |
| "Score This Video" | generate.tsx | result stage |
| "Create Another Video" | generate.tsx | result stage |
| "Go Back & Retry" | generate.tsx | error stage |

### Ideas

| String | Location | Line |
|--------|----------|------|
| "Refresh" | ideas.tsx | 383 |
| "Use This Idea" | ideas.tsx | 472 |
| "Score My Reel" | ideas.tsx | 571 |
| "Generate 5 hooks" | ideas.tsx | 787 |
| "Generate Plan" | ideas.tsx | 862 |
| "personalized calendars are coming soon" | ideas.tsx | 858 |

### Dashboard

| String | Location | Line |
|--------|----------|------|
| "Tour" | dashboard.tsx | 75 |
| "Breaking News" | dashboard.tsx | 89 |
| "Early Detection" | dashboard.tsx | 95 |
| "Video Analysis" | dashboard.tsx | 98 |
| "Festivals" | dashboard.tsx | 102 |
| "Analytics" | dashboard.tsx | 106 |
| "AI Generator" | dashboard.tsx | 109 |
| "India Features" | dashboard.tsx | 112 |

### TrendCard

| String | Location | Line |
|--------|----------|------|
| "📈 Rising" | TrendCard.tsx | 426 |
| "⚡ Emerging" | TrendCard.tsx | 427 |
| "📉 Peaked" | TrendCard.tsx | 428 |
| "⏰ Expired" | TrendCard.tsx | 429 |
| "🔥 MEGA" | TrendCard.tsx | 434 |
| "🚀 BREAKOUT" | TrendCard.tsx | 439 |
| "🌐 CROSSOVER" | TrendCard.tsx | 444 |
| "Act now — window closing fast" | TrendCard.tsx | 398 |
| "Still time to jump in" | TrendCard.tsx | 399 |
| "Saturating — post today" | TrendCard.tsx | 400 |
| "Too late for this trend" | TrendCard.tsx | 401 |
| "Trend added to Workspace 🎯" | TrendCard.tsx | 270 |
| "Removed from Workspace" | TrendCard.tsx | 281 |
| "Trend saved! 🔖" | TrendCard.tsx | 290 |
| "Trend removed from saved collection" | TrendCard.tsx | 296 |
| "Caption copied! 📋" | TrendCard.tsx | 371 |

### PlanGate

| String | Location | Line |
|--------|----------|------|
| "{feature} requires a Pro plan" | PlanGate.tsx | 42 |
| "Unlock this feature and more with a Pro subscription — ₹999/month" | PlanGate.tsx | 46 |
| "Pro Feature" | PlanGate.tsx | 52 |
| "Upgrade to Pro" | PlanGate.tsx | 59 |

### Legal Pages

| String | Location | Line |
|--------|----------|------|
| "Last updated: June 25, 2026" | privacy.tsx, terms.tsx | 27 |
| "Digital Personal Data Protection Act, 2023 (India)" | data-rights.tsx | 101 |
| "Data Protection Officer" | privacy.tsx | 111 |
| "privacy@trendrop.app" | privacy.tsx | 113 |
| "zero-tolerance policy" | terms.tsx | 38 |
| "Safe Search Moderation" | terms.tsx | 73 |

### Deals/Marketplace

| String | Location | Line |
|--------|----------|------|
| "Deals Launch After Beta" | deals.index.tsx | 71 |
| "Create Campaign Deal" | deals.new.tsx | 41 |
| "Coming Soon" | deals.new.tsx | 51 |
| "Deal creation will be available once the marketplace launches." | deals.new.tsx | 52 |

### Admin

| String | Location | Line |
|--------|----------|------|
| "Admin Login" | admin.login.tsx | 9 |
| "Signing in..." | admin.login.tsx | 129 |
| "Access Restricted" | admin.users.tsx | 149 |
| "No users found" | admin.users.tsx | 218 |
| "No audit logs found" | admin.audit.tsx | 205 |

### InstallBanner

| String | Location | Line |
|--------|----------|------|
| "Install Trendrop on your home screen" | InstallBanner.tsx | 70 |
| "Get instant trend alerts" | InstallBanner.tsx | 72 |
| "Not now" | InstallBanner.tsx | 88 |
| "Install" | InstallBanner.tsx | 94 |

### ThemeToggle

| String | Location | Line |
|--------|----------|------|
| "☀ light" | ThemeToggle.tsx | 58 |
| "◐ dark" | ThemeToggle.tsx | 58 |

---

## 10. Backend Endpoints with NO Frontend

### Critical Invisible Features (user-facing, likely intended)

| Endpoint | Method | Likely Purpose |
|----------|--------|----------------|
| `POST /api/auth/verify-phone` | POST | Phone OTP verification (frontend has verify-phone.tsx but calls this via raw fetch) |
| `POST /api/auth/send-otp` | POST | Resend OTP during signup |
| `POST /api/instagram/auth-url` | POST | Instagram OAuth initiation |
| `GET /api/instagram/callback` | GET | Instagram OAuth redirect handler |
| `POST /api/instagram/callback` | POST | Instagram OAuth token exchange |
| `GET /api/instagram/insights` | GET | Instagram account analytics |
| `DELETE /api/instagram/disconnect` | DELETE | Disconnect Instagram account |
| `POST /api/phone/send-code` | POST | Authenticated phone verification |
| `POST /api/phone/verify` | POST | Authenticated phone code verify |
| `GET /api/phone/status` | GET | Check phone verification status |
| `POST /api/trends/{trend_id}/memory` | POST | Save trend content plan memory |
| `GET /api/trends/niche/{niche_name}` | GET | Niche-specific trend feed |
| `GET /api/trends/audio-scores` | GET | Audio trend scoring dashboard |
| `GET /api/trends/by-language/{lang}` | GET | Language-filtered trends |
| `GET /api/trends/peaking` | GET | Peaking trend detection |
| `GET /api/trends/{trend_id}/timeline` | GET | Trend velocity timeline chart (used by TrendProofSection via raw apiFetch) |
| `POST /api/prepost-score` | POST | Pre/post analysis tool (used by studio.tsx via raw fetch) |
| `POST /api/seo-caption` | POST | SEO caption generator (used by studio.tsx via raw fetch) |
| `POST /api/video/analyze-metadata` | POST | FFmpeg video analysis |
| `POST /api/video/analyze-visual` | POST | OpenCV visual analysis |
| `POST /api/video/predict-virality` | POST | Video virality prediction (used by VideoAnalysisPanel via raw fetch) |
| `POST /api/video/improvements` | POST | Video improvement suggestions |
| `POST /api/user/cancellation-reason` | POST | Churn feedback collection |
| `GET /api/marketplace/profiles` | GET | Browse creator profiles (used by marketplace.tsx via raw apiFetch) |
| `POST /api/marketplace/profile` | POST | Create/edit own creator profile |
| `POST /api/deals` | POST | Create brand deal with contract PDF |
| `GET /api/deals` | GET | List own brand deals (used by deals.index.tsx via raw apiFetch) |
| `GET /api/deals/{deal_id}/download` | GET | Download contract PDF |
| `POST /api/deals/{deal_id}/pay-milestone/{milestone_id}` | POST | Mark milestone paid |
| `POST /api/user/performance/store` | POST | Store Instagram performance data |
| `GET /api/user/performance` | GET | View performance data |
| `GET /api/user/performance/growth` | GET | View growth rate |
| `GET /api/user/performance/top-media` | GET | View top performing media |
| `POST /api/admin/change-password` | POST | Admin password change |
| `POST /api/admin/validate-token` | POST | Admin token validation (used by admin beforeLoad via raw fetch) |
| `GET /api/business/metrics` | GET | Business KPIs |
| `GET /api/business/user-metrics` | GET | User acquisition metrics |
| `GET /api/business/revenue` | GET | Revenue breakdown |
| `GET /api/business/mrr` | GET | Monthly recurring revenue |
| `GET /api/business/subscription-breakdown` | GET | Subscription tiers |
| `GET /api/business/cac-ltv` | GET | CAC/LTV analysis |
| `GET /api/case-studies` | GET | Case study templates |
| `GET /api/pitch-deck` | GET | Pitch deck (JSON) |
| `GET /api/pitch-deck/markdown` | GET | Pitch deck (Markdown) |
| `GET /api/india/cultural-events/{event_name}` | GET | Event content suggestions |
| `GET /api/india/cultural-events/{event_name}/optimal-timing` | GET | Event posting timing |
| `GET /api/india/caption/generate` | GET | Regional caption generator |
| `GET /api/india/content-ideas/generate` | GET | India content ideas |
| `GET /api/india/cultural-event/{event_name}` | GET | Cultural event data |
| `GET /api/early-detection/trends` | GET | Early detection feed |
| `GET /api/early-detection/predict/{trend_id}` | GET | Trend viral prediction |
| `POST /api/virality/predict` | POST | Content virality predictor |
| `GET /api/virality/improvements` | GET | Virality improvement tips |
| `GET /api/reels/cross-cultural` | GET | Cross-cultural reels feed |
| `GET /api/reels/stream/{db_id}` | GET | Reel video stream proxy |
| `GET /api/users/preferences` | GET | Read user preferences |
| `PUT /api/users/preferences` | PUT | Update user preferences (used by settings.tsx via raw apiFetch) |
| `GET /api/content-trends` | GET | Content trend signals (used by NewsFeedPanel via raw apiFetch) |
| `GET /api/proof` | GET | Public proof of detection (used by proof.tsx via raw apiFetch) |

### Cron/Infra-only (intentionally no frontend)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/cron/trigger` | Full pipeline trigger |
| `GET /api/cron/refresh` | Trend status refresh |
| `POST /api/run-scraper` | Manual scraper trigger |
| `POST /api/deals/run-reminders` | Milestone reminder cron |
| `POST /api/payment/subscription-webhook` | Razorpay subscription webhook |
| `GET /health` | Health check |
| `GET /api/health` | Health check |

### Frontend-Backend URL Mismatch

| Frontend Function | Frontend Calls | Backend Has |
|-------------------|---------------|-------------|
| `getAdminBusinessMetrics` | `GET /api/admin/business-metrics` | `GET /api/business/metrics` — **will 404** |

---

## 11. Bugs, TODOs, Dead Code

### Bugs

| File | Line | Issue |
|------|------|-------|
| `index.tsx` | 65 | `sortMode` typed as `any` — not type-safe |
| `data-rights.tsx` | 72 | `type.replace("_", " ")` only replaces first underscore |
| `admin.audit.tsx` | 222 | Same single-replacement bug |
| `admin.analytics.tsx` | 163 | Same single-replacement bug |
| `admin.analytics.tsx` | 64 | 403 detection uses fragile string match `err.message?.includes("403")` |
| `trend.$id.tsx` | 14 | Unused `zod` import |
| `verify-phone.tsx` | 9 | `useAuth` imported but never used |
| `deals.index.tsx` | 11,15,16 | Dead imports: `ExternalLink`, `DollarSign`, `TrendingUp` |
| `admin.audit.tsx` | 6 | Unused import: `Calendar` |
| `admin.analytics.tsx` | 6 | Unused import: `BarChart2` |
| `admin.plans.tsx` | 261 | `plan_name` input disabled but has onChange handler |
| `api.ts` | `getAdminBusinessMetrics` | Calls `/api/admin/business-metrics` but backend has `/api/business/metrics` — will 404 |
| `generate.tsx` | 245,263,280,297 | Email from `localStorage` directly instead of Zustand — potential inconsistency |
| `OnboardingFlow.tsx` | 236 | Step indicator says "Step 3 of 4" but there are 4 steps (step 1 says "1 of 3") |
| `pricing.tsx` | 156 | `import { toast } from "sonner"` at bottom of file — unconventional |
| `update-password.tsx` | 34-36 | Silent failure if hash token is invalid |
| `admin.users.tsx` | all | No confirmation dialog on destructive operations (lock/unlock/plan change) |

### TODOs

| File | Line | Content |
|------|------|---------|
| `api.ts` | 425 | `TODO: Expose these via API to avoid manual sync` (VIRAL_SCALE_FACTOR/VIRAL_DISPLAY_MULTIPLIER) |
| `pricing.tsx` | 32 | `// TODO: Wire Razorpay checkout flow` |
| `ideas.tsx` | 858 | "personalized calendars are coming soon" |
| `stats.tsx` | 113,195 | "Instagram sync is coming soon" |
| `trend.$id.tsx` | 402-404 | "Caption generation is coming soon" placeholder text |

### Dead Code

| File | Line | Issue |
|------|------|-------|
| `index.tsx` | 68 | `showFilterDrawer` state declared, never used |
| `index.tsx` | 404-424 | Entire language filter UI commented out |
| `index.tsx` | 11-12 | `OnboardingFlow`, `FeatureTutorial` imports commented out |
| `admin.audit.tsx` | 112 | `filteredLogs` variable assigned, never used |
| `admin.plans.tsx` | 261 | onChange handler on disabled input |
| `api.ts` | 434 | `createDefaultPreferences` is a noop |
| `TrendCard.tsx` | 230,942 | `showPreviewModal` state set but never set to `true` in visible code |

### Stub/Mock Data

| File | Line | Content |
|------|------|---------|
| `pricing.tsx` | 33 | Toast: "Pro upgrade will be available soon via Razorpay!" |
| `deals.new.tsx` | entire | "Coming Soon" placeholder page |
| `VideoAnalysisPanel.tsx` | 116-118 | "Full video analysis isn't live yet. This score is a canned sample value" |
| `ideas.tsx` | 186-199 | Fallback score: overall 75, grade "B", all sub-scores 70 |
| `ideas.tsx` | 221-225 | Fallback hooks: 3 hardcoded templates |
| `ideas.tsx` | 244-269 | Fallback calendar with fixed Indian holidays |
| `IndiaFeaturesDashboard.tsx` | 52-108 | Extensive hardcoded Indian regional fallback data |
| `EarlyDetectionPanel.tsx` | 127-148 | Hardcoded fallback festivals |
| `RegionalFestivalPanel.tsx` | 51-57 | `STATIC_FESTIVALS` fallback (5 festivals) |
| `OnboardingFlow.tsx` | 7-28 | Hardcoded niche/language/tier constants |
| `FeatureTutorial.tsx` | 9-35 | 5 hardcoded tutorial steps |
| `OnboardingTour.tsx` | 16-64 | 4 hardcoded tour steps |
| `TrendCard.tsx` | 29-39 | Language emoji map |
| `TrendCard.tsx` | 398-402 | Opportunity status texts |
| `NewsTrendCard.tsx` | 28-34 | `URGENCY_WINDOWS` hardcoded per niche |
| `danceTrendModal.tsx` | 66-70 | Default storyboard: "Visual Hook", "Action Sequence", "End Scene" |
| `AlgorithmInsightsPanel.tsx` | 101-109 | Factor labels: "Watch Time", "Engagement Rate", etc. |
| `AIContentGenerator.tsx` | 157-176 | Tone options, niche options, counts |
| `BottomTabBar.tsx` | 17 | `PUBLIC_ROUTES` array |
| `AuthWrapper.tsx` | 7-21 | `PUBLIC_ROUTES` array |
| `privacy.tsx` | 27 | "Last updated: June 25, 2026" |
| `terms.tsx` | 27 | "Last updated: June 25, 2026" |

### Inconsistencies

| Issue | Files |
|-------|-------|
| 3 different NICHES constants with different entries | index.tsx, signup.tsx, studio.tsx |
| Email sourced from localStorage vs Zustand vs AuthContext | generate.tsx, ideas.tsx, index.tsx |
| localStorage key `trendrop_niche` vs `trendrop_user_niche` | settings.tsx vs AuthContext |
| Copy-pasted `beforeLoad` auth guard (~120 lines) | admin.users/plans/audit/analytics |
| All admin state typed as `any` | All 4 admin route files |
| Kannada emoji is `🎯` (non-standard) | settings.tsx L26 |

---

*End of Audit. All claims backed by file path + line references as documented above.*
