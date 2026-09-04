# Prompt B: Trend-Delta Scoring Rebuild

## Status: REVISED — blocked on infra cadence revert
## Date: 2026-09-01

---

## Evidence Collected

### 1. Revert Completeness (git diff 81f503b2 554a151b -- backend/trend_engine.py)

**The revert is NOT byte-identical.** Three residual differences remain. Each analyzed individually:

#### Residual A: Scraper outage bypass (line 724-726)

**What changed:** `return []` commented out, log message changed to "Proceeding anyway for manual backfill."

**What happens now on a genuine scraper outage:**
1. `new_reels_scraped = 0` (no reels in last 3h)
2. Logs warning, falls through to STEP 1 (line 728)
3. STEP 1 loads reels from last 48h via `gte("created_at", time_threshold_48h)` at line 745
4. These are EXISTING reels already in the DB — not new scrapes
5. For existing trends: dedup logic at line 862-888 catches them. `old_priority >= new_priority` (line 871) means no status change for trends already at "emerging" or higher. No window reset.
6. For new audio: needs 3+ high-velocity reels to pass the threshold at line 901. But these reels are from the last 48h — if the scraper has been failing, there are no new reels to form groups from.

**Verdict: LOW RISK.** On a genuine outage with no manual intervention, the engine processes nothing (no new reels to form groups from). The only scenario where this matters is manual backfill (intended use case). The dedup logic prevents re-processing of existing trends.

#### Residual B: window_hours_remaining=48 reset on re-detection (line 872-875)

**What changed:** When a trend's status changes, `window_hours_remaining` is reset to 48.

**When this fires:**
- `final_status` only changes to "emerging" if `old_priority < 2` (line 871)
- `STATUS_PRIORITY = {"expired": 0, "peaked": 1, "emerging": 2, "rising": 3}` (line 785)
- So the reset fires ONLY when an "expired" or "peaked" trend is re-detected and promoted back to "emerging"
- For trends already at "emerging" or "rising": `old_priority >= new_priority`, so `final_status = old_status`, no change, no reset

**Scenario analysis:**
- Trend expires (status="expired", window=0)
- Scraper picks up new reels for same audio → engine re-detects → status changes to "emerging" → window reset to 48h
- This is correct behavior for genuine re-emergence — the trend deserves another lifecycle
- The dedup logic and 3-reel threshold prevent stale data from triggering this

**Risk scenario:** Same title+artist but different audio_id. The dedup at line 855-860 matches by `(title, artist)` without considering `audio_id`. If a different audio has the same title and artist, it would match the existing "expired" trend and reset its window. Edge-case but possible.

**Verdict: LOW RISK.** Correct behavior for genuine re-emergence. The stale-data scenario requires an unlikely title+artist collision across different audio IDs.

#### Residual C: 3-reel threshold (line 896-903)

**What changed:** `if len(high_velocity_reels) < 3: continue` — requires 3+ high-velocity reels to confirm a trend.

**The bug:** The query at line 896 fetches ALL reels for the audio_id without a time filter:
```python
all_reels_for_audio_res = self.supabase.table("reels").select("*").eq("audio_id", representative_audio_id).execute()
```

This counts historical reels, not just recent ones. An audio with 3 high-velocity reels from 2 weeks ago would pass, even if none of those reels are recent.

**Inconsistency:** The main reel query at line 742-754 filters by `created_at >= 48h`. The 3-reel check at line 896-903 counts all historical reels. This means:
- Reels loaded for processing: only last 48h ✓
- Reels counted for 3-reel threshold: all history ✗

**Verdict: MEDIUM RISK.** This is a real bug. The 3-reel threshold should filter by `created_at >= time_threshold_48h` to match the main query. Without this fix, a trend could be created from stale historical data that passes the 3-reel count but has no recent activity.

**Recommendation:** Add `gte("created_at", time_threshold_48h)` to the `all_reels_for_audio_res` query at line 896. This is a one-line fix that aligns the threshold with the main query's time window.

---

### 2. Pipeline Gap (Aug 18 → Aug 27)

**Root cause: GitHub Actions emergency posture, NOT a code bug.**

Timeline:
- **Aug 7** (`a3f821aa`): Scraper reduced from 6h → 8h to stay under 2,000 min/month free tier
- **Aug 18**: Last successful pipeline run before gap (102 reels saved)
- **Aug 20** (`81f80b61`): Emergency posture — budget crisis (~200 min remaining with 12 days to Sept 1). Scraper changed to every 2 days. All crons reduced.
- **Aug 22** (`69b8fd65`, `69162acb`): Scraper still on 2-day schedule. Verify step was failing silently.
- **Aug 27** (`bad26ac6`): Scraper reverted to 6h schedule. Pipeline ran but saved **0 reels** (scraper failure — likely cookie expiry or IG blocking).
- **Aug 27-31**: GitHub Actions running on 6h schedule. Reels exist in DB (Aug 25-30, 1000 total). Pipeline.log doesn't capture GHA runs (only local runs).

**Current state (Sept 1):**
- Scraper: ✅ Reverted to 6h (`'0 */6 * * *'`)
- Trend refresh: ❌ Still on emergency 2x/day (`'30 4,20 * * *'`). Comment says "revert to 8h post-Sept 1 reset"
- Heartbeat: ❌ Still on emergency 3x/day (`'15 0,8,16 * * *'`). Comment says "revert to 4h post-Sept 1 reset"
- Other crons (LLM classification, pending-trends, news-virality): ❌ Still on emergency reduced schedules

**The trend-refresh workflow is the critical one for scoring.** It runs `manual_run_and_check.py --stages refresh,snapshots` which calls `TrendRefresher.refresh_all()`. At 2x/day, trends get at most 2 refresher cycles per day. With the 3-snapshot requirement, a trend needs 1.5+ days to accumulate enough snapshots for velocity-based promotion.

**This is not a scoring bug — it's an infrastructure cadence issue that makes the scoring bug more visible.** Fixing the scoring gate without reverting the trend-refresh cadence means trends will still starve on snapshots if the refresher only runs 2x/day.

### 3. Delta Signal: DEAD

**All delta columns are zero across all 1000 reels.**

```
views_delta_last_run: 0/1000 non-zero (0%)
likes_delta_last_run: 0/1000 non-zero (0%)  
audio_delta_last_run: 0/1000 non-zero (0%)
```

The columns exist (added by `migrate_reel_snapshots.py`) but **nothing writes to them**. The scraper doesn't compute deltas. The pipeline doesn't compute deltas. These columns are schema-only — no code populates them.

**Impact on Fix 2:** The original Fix 2 proposed using `audio_delta_last_run > 0` as a promotion signal. This signal is dead. Fix 2 must be redesigned to use data that actually exists.

---

## Revised Plan

### Pre-requisite: Revert emergency crons (DEPLOY FIRST, ALONE)

**Before implementing any scoring fixes, revert the trend-refresh workflow from emergency 2x/day to sustainable cadence (8h).**

**Action:** Revert `.github/workflows/trend-refresh.yml` from `'30 4,20 * * *'` (2x/day) to `'30 0,8,16 * * *'` (every 8h). Update comment to remove "EMERGENCY POSTURE" language.

**Also check:** Heartbeat and other crons may need the same treatment. Current state:
- Heartbeat: `'15 0,8,16 * * *'` (3x/day) — original was 4h → should revert to `'15 */4 * * *'`
- Trend refresh: `'30 4,20 * * *'` (2x/day) — original was 8h → should revert to `'30 0,8,16 * * *'`

**Deploy this alone. Give it 1-2 days to run before layering in scoring fixes.** This isolates the cadence effect from the scoring effect.

### Fix 0: 3-reel threshold time filter (NEW — from residual analysis)

**What:** Add time filter to the 3-reel threshold query so it only counts recent reels, not all historical reels.

**Where:** `trend_engine.py:896`

**Current:**
```python
all_reels_for_audio_res = self.supabase.table("reels").select("*").eq("audio_id", representative_audio_id).execute()
```

**New:**
```python
all_reels_for_audio_res = self.supabase.table("reels").select("*").eq("audio_id", representative_audio_id).gte("created_at", time_threshold_48h).execute()
```

**Why:** The main reel query at line 742-754 filters by `created_at >= 48h`. The 3-reel check should match. Without this, a trend could be created from stale historical data.

**File:** `trend_engine.py:896`
**Change:** Add `.gte("created_at", time_threshold_48h)` to the query.

### Fix 1: Wire `calculate_trend_state()` output to database

**No change from original.** Still valid.

**File:** `trend_engine.py:1232`
**Change:** Replace `"status": trend.get("initial_status", "rising")` with `"status": trend_state.lifecycle.value`

### Fix 2: Relax emerging→rising promotion (UNCALIBRATED)

**What:** Replace the 3-snapshot velocity requirement with simpler signals.

**Where:** `trend_refresher.py:197-245`

**Current rule:** `age_hours >= 12` AND `creator_count >= 3` OR `age_hours >= 18` with 3 non-decreasing snapshots above 1.5x baseline.

**New rule:** Promote emerging→rising if ANY of:
1. `creator_count >= 2` AND `age_hours >= 6` (creator adoption)
2. `reel_count >= 3` AND `age_hours >= 8` (volume signal)
3. `velocity_for_check > baseline * 1.2` AND `age_hours >= 8` AND `len(snapshots) >= 1` (velocity outlier)

**UNCALIBRATED — these are educated guesses, not data-derived.** No real lifecycle data exists to validate against. Thresholds must be re-tuned after first real beta data. Document this explicitly in code comments.

**Why these numbers (best-guess justification):**
- `creator_count >= 2`: At 1-2 reels per trend (current scale), requiring 3 creators is too high. 2 creators means 2 different people independently used the audio.
- `age_hours >= 6`: Lowered from 12h. A trend that survives 6 hours with 2+ creators is real.
- `reel_count >= 3`: If 3+ reels exist for an audio, it's being used regardless of creator count.
- `velocity > 1.2x baseline` with 1 snapshot: The 3-snapshot requirement was the primary blocker. 1 snapshot above 1.2x baseline is sufficient for emerging→rising.

**File:** `trend_refresher.py:197-245`

### Fix 3: Saturation thresholds — DROPPED

**The 5M threshold is correct.** Changed from 100K to 5M in `8ba11285` because `audio_use_count` is Instagram's platform-wide count. At 100K, every trend with 150K+ uses computed as >100% saturated and got immediately expired. Dropping this fix.

### Fix 4: Lower expired threshold

**No change from original.** Still valid.

**File:** `trend_refresher.py:148`
**Change:** `str(15 * 24)` → `str(3 * 24)` (15 days → 3 days, matching docstring)

---

## Deployment Sequence

1. **Phase 1 (deploy alone):** Revert `.github/workflows/trend-refresh.yml` to 8h cadence. Wait 1-2 days.
2. **Phase 2 (deploy together):** Fix 0 (3-reel time filter) + Fix 1 (wire lifecycle) + Fix 4 (expired threshold)
3. **Phase 3 (deploy after Phase 2 is verified):** Fix 2 (relaxed promotion)

Each phase deployed separately. Monitor trend count transitions between phases.

---

## Files Modified
1. `.github/workflows/trend-refresh.yml` — Cadence revert (Phase 1)
2. `trend_engine.py` — Fix 0 (3-reel time filter) + Fix 1 (wire lifecycle) (Phase 2)
3. `trend_refresher.py` — Fix 2 (relaxed promotion) + Fix 4 (expired threshold) (Phase 2/3)

## NOT Modified
- `trend_scoring.py` — Fix 3 dropped (5M threshold is correct)
- No delta columns — they're dead schema, not a scoring input

## Verification
- Phase 1: Confirm trend-refresh runs 3x/day for 1-2 days. Check `trend_refresher.log` for run timestamps.
- Phase 2: Verify new trends get correct initial status. Verify expired fires after 72h.
- Phase 3: Verify emerging→rising promotion fires within 6-12h for qualifying trends.
- Monitor trend count transitions over 24-48h per phase.

## Risk
All Fix 2 thresholds are educated guesses calibrated against zero real lifecycle data. They must be re-tuned after first real beta data. Document this explicitly in code comments.
