# Tab Data Retention & Scraper Alignment — Recommendation

> Research-only. Based on actual code inspection of `routes/trends.py`, `trend_refresher.py`, `frontend/src/routes/index.tsx`. No code changes made.

---

## What the Code Actually Does Right Now

| Tab | API query | DB age gate | Frontend staleTime | refetchInterval |
|---|---|---|---|---|
| **Emerging** | `status=emerging`, `window_hours_remaining>0`, `limit=100` | None — any age qualifies | 3 min | 5 min |
| **Rising** | `status=rising`, `window_hours_remaining>0`, `limit=100` | None for Pro; 48h `first_detected_at` cutoff for free users | 3 min | 5 min |
| **Peaked** | `status=peaked`, `limit=100`, ordered `first_detected_at desc` | ❌ None — peaked trends from weeks ago show up | 3 min | 5 min |
| **Expired** | `status=expired`, `limit=200`, ordered `first_detected_at desc` | ❌ None — expired trends from months ago show up | 3 min | 5 min |

**Critical observation:** Every tab polls every 5 minutes and treats data as stale after 3 minutes — identical settings regardless of how volatile the data actually is. A trend that expired 3 months ago is being polled at the same frequency as an emerging trend that changes every 30 minutes. That's wasted API calls and the wrong UX signal.

The refresher sets `window_hours_remaining` and decrements by 3h each cycle (or extends by 12h when new reels appear), but there's **no ceiling date** stopping old peaked/expired trends from appearing in those tabs forever.

---

## The Intent of Each Tab (what a user expects)

| Tab | What the user expects | Time pressure |
|---|---|---|
| **Emerging** | "Brand new signals — things nobody has posted about yet in India" | Very high — stale data in this tab is actively misleading |
| **Rising** | "Things picking up right now — safe to post today/tomorrow" | High — data older than 3 days is noise |
| **Peaked** | "Trends I missed — can I get late-mover value? Has it actually peaked?" | Medium — useful for 1–2 weeks post-peak |
| **Expired** | "Archive / research — what worked, what patterns repeat" | Low — useful for weeks/months, not a live feed |

---

## Recommended Retention Per Tab

### Tab 1: Emerging

**What it means:** Detected within the last 48h, `window_hours_remaining > 0`, fewer than ~5 creators adopted.

**Problem today:** No upper age gate on `first_detected_at`. An "emerging" trend that first appeared 6 days ago and just recovered from expired is shown at the top of this list alongside something detected 2 hours ago. Both display identically — no "new" badge, no age visible. To a user both look the same but one is stale by days.

**Recommended retention:**
- **Show in Emerging tab: max 48 hours** from `first_detected_at`
- After 48h, if still "emerging" (never rose), force it to "expired" — the window_hours_remaining logic already handles this in most cases (`TREND_VISIBILITY_MIN_HOURS = 72h`) but recovered trends bypass this
- **DB display gate:** `first_detected_at >= NOW() - INTERVAL '48 hours'` in the API query (not just `window_hours_remaining > 0`)
- **Frontend cache:** Reduce `staleTime` from 3 min → **30 seconds**, `refetchInterval` from 5 min → **2 minutes**. Emerging is the most volatile tab — a new trend that appeared 10 minutes ago should show up fast
- **Scraper alignment:** Every scrape cycle (every ~8h) that completes should trigger a push notification/badge on this tab. The scraper already writes `scraped_at` — the frontend should show "3 new trends detected 45 min ago" rather than silently inserting into a list the user may or may not be watching

---

### Tab 2: Rising

**What it means:** Promoted from emerging (2+ creators, or 3+ reels, or velocity spike), `window_hours_remaining > 0`.

**Problem today:** Free users get a 48h `first_detected_at` gate. Pro users get no gate at all (`limit=100`, no age filter). A rising trend that's been "rising" for 6 days could be shown to Pro users alongside one that rose 2 hours ago. The sort is `window_hours_remaining asc` which is correct (most urgent first) — but window_hours can be extended repeatedly, so a trend could be "rising" with 40h remaining for many consecutive days.

**Recommended retention:**
- **Show in Rising tab: max 7 days** from `first_detected_at` (both free and Pro)
- A trend that's been "rising" for 7 days has either peaked or is in a prolonged slow-burn — either way it shouldn't be in the urgent "Rising" feed
- **DB display gate:** `first_detected_at >= NOW() - INTERVAL '7 days'`
- **Frontend cache:** Keep `staleTime` at **3 min**, `refetchInterval` at **5 min** — this is fine for Rising. The data changes meaningfully every scrape cycle (~8h) but the refresher runs every 2h so status can change
- **Scraper alignment:** No change needed beyond what the refresher already does. Just apply the age gate in the API query

---

### Tab 3: Peaked

**What it means:** Velocity dropped >40% from peak. Audio is still recognizable, still circulating, but the growth curve broke. This is the "late-mover" or "avoid duplicating saturated content" information tab.

**Problem today:**
1. No age gate — peaked trends from August 7 (when the system started) appear here
2. `refetchInterval: 5 min` — peaked trends almost never change status (they either recover to emerging or eventually expire); polling every 5 min for data that changes at most once per day is pure waste
3. `limit=100` with no age filter means this tab fills up with ancient data

**Recommended retention:**
- **Show in Peaked tab: 14 days** from `first_detected_at`
- After 14 days, a peaked trend has no actionable value — the audio is either dead or recovered. Move it to expired in the DB
- **DB display gate:** `first_detected_at >= NOW() - INTERVAL '14 days'`
- **Frontend cache:** Increase `staleTime` to **15 min**, `refetchInterval` to **30 min**. Peaked data is not time-critical. Polling it every 5 min is noise
- **Sort change:** Currently sorted by `first_detected_at desc` — correct. But also add a secondary sort by `velocity_avg desc` so most recently peaked AND highest-velocity trends float to top (the ones where "still some value left" is most likely)
- **Scraper alignment:** The refresher should apply the 14-day gate when deciding to age a trend out of "peaked" to "expired". Currently `TREND_VISIBILITY_MIN_HOURS = 72h` applies to emerging/rising — peaked needs its own ceiling. Peaked trends that are 14+ days old should be batch-expired in the refresher, not just left as peaked forever

---

### Tab 4: Expired

**What it means:** A historical record. Audio that had its moment. Useful for:
- "I remember seeing this trend — when exactly was it peaking?"
- Pattern analysis ("dance trends always expire in 10 days; this music genre repeats every 3 weeks")
- Confirming a trend is dead before posting about it

**Problem today:**
1. `limit=200` with no age filter — the entire history of every trend ever scraped is surfaced
2. Same 5-min polling as other tabs — expired data changes by definition never (it expired)
3. No way to distinguish "expired 2 days ago, still fresh enough to reference" from "expired 4 months ago, ancient history"

**Recommended retention:**
- **Show in Expired tab: 30 days** from `first_detected_at`
- Older data should be soft-archived (a separate "archive" query or just filterable by date range in a future UI)
- **DB display gate:** `first_detected_at >= NOW() - INTERVAL '30 days'`
- **Frontend cache:** Increase `staleTime` to **30 min**, `refetchInterval` to **never** (or **60 min**). No user expects expired data to change. Polling it every 5 min is pure API waste
- **Scraper alignment:** Zero scraper changes needed for expired. The refresher correctly sets status=expired — just need the API query to filter by age

---

## Summary: Retention Table

| Tab | DB display window | Frontend staleTime | refetchInterval | Sort |
|---|---|---|---|---|
| **Emerging** | 48h from `first_detected_at` | 30 sec | 2 min | `first_detected_at desc` (newest first) |
| **Rising** | 7 days from `first_detected_at` | 3 min | 5 min | `window_hours_remaining asc` (most urgent) ← already correct |
| **Peaked** | 14 days from `first_detected_at` | 15 min | 30 min | `first_detected_at desc`, secondary `velocity_avg desc` |
| **Expired** | 30 days from `first_detected_at` | 30 min | 60 min (or disabled) | `first_detected_at desc` |

---

## Three Scraper/Refresher Changes Needed (Research Only)

### Change 1: Add Age Gate to Peaked → Expired Promotion

The refresher currently expires trends based on `window_hours_remaining <= 0` or `age_hours >= TREND_VISIBILITY_MIN_HOURS`. But `TREND_VISIBILITY_MIN_HOURS = 72h` applies to the generic path. Peaked trends that sit in peaked status for 14+ days never get cleared by this logic because once peaked, `window_hours_remaining` may still be > 0 (it was last set when velocity dropped).

**What's needed:** In the refresher's peaked branch, add a check: if `age_hours > 14 * 24` → force to expired, regardless of `window_hours_remaining`.

### Change 2: Write `status_changed_at` on Every Transition

Currently there's no `status_changed_at` column. The refresher logs transitions (`[PEAKED] 'audio_title'`) but doesn't persist when it happened. Without this, you can't show "peaked 3 days ago" vs "peaked 2 hours ago" in the UI — both appear identically in the Peaked tab.

**What's needed:** Migration adding `status_changed_at TIMESTAMPTZ` to `trends`, written by `_update_status()` in `trend_refresher.py` on every call. No schema permission to apply directly — this is a migration file task.

### Change 3: Emerging Tab Needs Its Own Hard Cap

The refresher's `TREND_VISIBILITY_MIN_HOURS = 72h` prevents any trend from living more than 72h in active states. But recovered trends (expired→emerging) bypass this because their `created_at` gets reset to `now` at recovery time (L130–131 of `trend_refresher.py`). This means a trend first detected August 13, which expired, then recovered on August 31, effectively gets a fresh 72h clock — showing up in Emerging from Aug 31 as if brand new.

**What's needed:** A separate `first_detected_at` gate in the API query for the Emerging tab (`first_detected_at >= NOW() - INTERVAL '48 hours'`) that's independent of `window_hours_remaining`. Recovered trends older than 48h `first_detected_at` should be shown as "Recovered" not "Emerging" — or filtered to a separate bucket.

---

## What "Seamless, No Irritation" Actually Means Per Tab

- **Emerging** irritation comes from: stale data appearing alongside fresh data with no visual difference, and no alert when genuinely new things arrive. Fix: 48h gate + 30sec cache + "N new trends" banner.
- **Rising** irritation comes from: too many trends (100 limit with no age filter), oldest at the bottom but still visible, no urgency signal. Fix: 7-day gate reduces noise; `window_hours_remaining` sort already creates urgency.
- **Peaked** irritation comes from: ancient data (months old) filling the tab, 5-min polling for static data eating the user's bandwidth. Fix: 14-day gate + 30-min poll.
- **Expired** irritation comes from: completely unbounded list of 200 expired trends going back to app launch, no way to tell "recently expired" from "ancient". Fix: 30-day gate + pagination or date filter.
