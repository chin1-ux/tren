# Trend Lifecycle Analysis - What Happens to Expired/Peaked Trends?

## Question: Do expired/peaked trends stay in the frontend or get removed?

## Short Answer: THEY STAY IN THE DATABASE - THEY ARE NOT DELETED

---

## Detailed Analysis

### Trend Status Lifecycle

Based on the code in `trend_refresher.py`, trends go through these statuses:

1. **emerging** - New trend detected, velocity spike
2. **rising** - Trend is actively growing, shown in main feed
3. **peaked** - Velocity dropped >40% from peak
4. **expired** - Older than 360 hours (15 days) OR window_hours_remaining <= 0

### What Happens When a Trend Peaks

**Process:**
1. `trend_refresher.py` runs periodically (via cron job)
2. It checks all trends with status "emerging" or "rising"
3. If velocity drops below 60% of peak velocity → status changes to "peaked"
4. The trend stays in the database
5. The trend is still accessible via `/api/trends/peaked` endpoint

**Code Reference (trend_refresher.py, lines 150-160):**
```python
if velocity_for_check < peak_velocity * 0.60 and peak_velocity > 0:
    self._update_status(trend_id, "peaked", {
        "window_hours_remaining": new_window,
        "velocity_avg": velocity_for_check,
        "reel_count": total_reels_count,
        "high_confidence": bool(trend.get("high_confidence", False)),
        "promotion_reason": trend.get("promotion_reason"),
    })
    logger.info(f"[PEAKED] '{audio_title}' (was {peak_velocity:.2f}, now {velocity_for_check:.2f})")
    summary["peaked"] += 1
```

### What Happens When a Trend Expires

**Process:**
1. `trend_refresher.py` checks trend age
2. If age >= 360 hours (15 days) OR window_hours_remaining <= 0 → status changes to "expired"
3. The trend stays in the database
4. The trend is still accessible via `/api/trends/expired` endpoint

**Code Reference (trend_refresher.py, lines 114-124):**
```python
min_visible_hours = float(os.getenv("TREND_VISIBILITY_MIN_HOURS", str(15 * 24)))
if age_hours >= min_visible_hours or window_hours <= 0:
    self._update_status(trend_id, "expired", {
        "window_hours_remaining": 0,
        "reel_count": total_reels_count,
        "high_confidence": bool(trend.get("high_confidence", False)),
        "promotion_reason": trend.get("promotion_reason"),
    })
    logger.info(f"[EXPIRED] '{audio_title}' (age={age_hours:.1f}h)")
    summary["expired"] += 1
```

### What the Frontend Shows

**Main Trend Feed (/api/trends):**
- Shows ONLY trends with status "rising"
- Does NOT show peaked or expired trends
- This is the default feed users see

**API Endpoints Available:**
- `/api/trends` - Shows only "rising" trends (main feed)
- `/api/trends/emerging` - Shows "emerging" trends (early access)
- `/api/trends/peaked` - Shows "peaked" trends (still active but declining)
- `/api/trends/expired` - Shows "expired" trends (historical)
- `/api/trends/all-active` - Shows "emerging" + "rising" combined

**Code Reference (api.py):**
```python
# Main feed - only rising
@app.get("/api/trends")
def get_trends(...):
    q = supabase.table("trends").select("*").eq("status", "rising")...

# Peaked trends
@app.get("/api/trends/peaked")
def get_peaked_trends(...):
    q = supabase.table("trends").select("*").eq("status", "peaked")...

# Expired trends
@app.get("/api/trends/expired")
def get_expired_trends(...):
    q = supabase.table("trends").select("*").eq("status", "expired")...
```

### Is There Any Deletion Logic?

**NO** - I searched for deletion/cleanup logic and found:

**Search Results:**
- No patterns for "delete.*trend"
- No patterns for "cleanup.*trend"
- No patterns for "archive.*trend"
- No code that removes trends from database

**Conclusion:** Trends are NEVER deleted from the database. They only change status.

---

## Impact on Database Size

### Current Behavior

**Trends Accumulate:**
- Every trend detected stays in database forever
- Peaked trends stay in database
- Expired trends stay in database
- No cleanup, no deletion, no archiving

**Database Growth:**
- Trends table will grow indefinitely
- Reels table will grow indefinitely
- No automatic cleanup

**Estimated Growth:**
- If 10 new trends per day = 3,650 trends per year
- If 100 new reels per trend = 365,000 reels per year
- Database will grow linearly over time

---

## Recommendations

### Option 1: Keep Current Behavior (Do Nothing)

**Pros:**
- Historical data preserved
- Can analyze past trends
- Can show "trending 6 months ago"
- No data loss

**Cons:**
- Database grows indefinitely
- Query performance may degrade over time
- Storage costs increase (if using paid database)
- May need to paginate or filter by date

**When to Choose:**
- If you want historical data
- If database is large enough
- If storage costs are acceptable

### Option 2: Archive Old Trends (Recommended)

**Implementation:**
1. Create `trends_archive` table
2. Move trends older than 90 days to archive table
3. Keep archive separate from active trends
4. Can still query archive if needed

**Pros:**
- Active database stays small
- Historical data preserved
- Query performance stays fast
- Can still access historical data

**Cons:**
- Need to implement archival logic
- Need to update queries to check archive
- Slightly more complex

**When to Choose:**
- If you want to keep historical data
- If database performance is important
- If you want best of both worlds

### Option 3: Delete Old Trends (Aggressive)

**Implementation:**
1. Delete trends older than 90 days
2. Delete associated reels
3. No archival, just deletion

**Pros:**
- Database stays small
- Query performance optimal
- Storage costs minimal

**Cons:**
- No historical data
- Cannot analyze past trends
- Data loss

**When to Choose:**
- If you don't care about historical data
- If database size is critical
- If storage costs are high

---

## What I Recommend

### For MVP: Keep Current Behavior

**Reason:**
- Database is not large yet
- Historical data might be valuable
- No need to over-engineer
- Can implement archival later if needed

### For Production: Implement Archival

**Implementation Plan:**
1. Create `trends_archive` table (same structure as `trends`)
2. Create `reels_archive` table (same structure as `reels`)
3. Add cron job to archive trends older than 90 days
4. Move trends + reels to archive tables
5. Keep archive for 1 year, then delete

**Cron Job Frequency:**
- Run once per week
- Archive trends older than 90 days
- Delete archive older than 1 year

---

## Summary

**What Happens to Expired/Peaked Trends:**
- ✅ They stay in the database
- ✅ They are NOT deleted
- ✅ They are still accessible via API endpoints
- ✅ They are just not shown in the main feed
- ❌ There is NO deletion/cleanup logic

**What the Frontend Shows:**
- Main feed: Only "rising" trends
- Peaked endpoint: "peaked" trends
- Expired endpoint: "expired" trends
- Emerging endpoint: "emerging" trends

**Database Impact:**
- Trends accumulate indefinitely
- No automatic cleanup
- Database grows linearly over time

**Recommendation:**
- Keep current behavior for MVP
- Implement archival for production (90-day retention)
- Delete archive older than 1 year

This is a reasonable approach for an MVP. You can implement archival later when database size becomes an issue.