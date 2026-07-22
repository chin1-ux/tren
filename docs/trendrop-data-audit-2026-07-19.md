# Trendrop Data Audit

Date: 2026-07-19

This is a verification pass, not a fix pass. It separates:
- Stored data that appears consistent with the frontend
- Stored data that is likely wrong upstream
- Frontend render logic that is brittle or potentially misleading
- Items I could not fully re-query live in this sandbox because direct Supabase network access from the shell was blocked

## 1) Live data inventory

Latest live counts previously pulled from Supabase REST:

- `reels_total`: 4783
- `trends_total`: 41
- `trends_emerging`: 2
- `trends_rising`: 0
- `trends_peaked`: 17
- `trends_expired`: 22
- `llm_completed`: 32
- `llm_pending`: 3
- `llm_skipped`: 6
- `origin_IN`: 1585
- `origin_KR`: 95
- `origin_US`: 524
- `origin_unknown`: 2342

- `cross_true`: 355
- `cross_false`: 4428

Notes:
- `trend_origin` is still heavily skewed to `unknown`.
- `is_cross_cultural=true` is a small subset of total reels.

## 2) Frontend category mapping

### India tab / main feed

Code path:
- [frontend/src/routes/index.tsx](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/routes/index.tsx)
- Query: `fetchTrends(language, sortMode, selectedNiche)`
- API: `/api/trends`

Observed logic:
- Main feed swaps between rising trends and the global rail only in the visible tab state.
- Search filtering lowercases `song`, `artist`, and `contentType` with `(field ?? "").toLowerCase()`, so the main page search path is guarded.

### Global tab / cross-cultural rail

Code path:
- [frontend/src/routes/index.tsx](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/routes/index.tsx)
- Query: `fetchCrossCulturalTrends()`
- API: `/api/reels/cross-cultural`

Backend filter:
- [backend/api.py](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/api.py)
- `is_cross_cultural = true`
- `is_original_audio = false`
- `audio_title` not null and not `"Original audio"`
- `caption_language in ["en", "english"]`
- `trend_origin` not IN/in/unknown/UNKNOWN/null
- `velocity_score > 0.3`
- `view_count > 2000`
- `scraped_at >= now - 60h`
- `india_saturation_pct < 40`
- `limit(10)`

### Emerging section

Code path:
- [frontend/src/routes/index.tsx](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/routes/index.tsx)
- Query: `fetchEmergingTrends(language)`
- API: `/api/trends/emerging`

## 3) Trend card rendering checks

Relevant files:
- [frontend/src/components/TrendCard.tsx](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/TrendCard.tsx)
- [frontend/src/components/TrendCardVideo.tsx](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/TrendCardVideo.tsx)

What the UI does:
- Instagram reel deep links come from `reel.reel_id` in `TrendCardVideo`.
- If `reel_id` is missing, the card shows `Instagram unavailable` instead of constructing `/reel//`.
- The audio link on the main page falls back to an Instagram hashtag search when `audio_id` is missing.

This is a good guard in the frontend, but it also means missing `reel_id` is a real stored-data gap if the button has to fall back.

## 4) Stored-data quality notes

What looks consistent:
- The backend cross-cultural filter intentionally excludes India-origin rows, so the Global rail is not supposed to show India-origin audio.
- The main feed and emerging feed are separate backend queries, not frontend-only filters.

What looks upstream-wrong:
- `origin_unknown` is very large relative to known origin buckets.
- That strongly suggests `trend_origin` is still underclassified for a meaningful chunk of the dataset.

What looks like a frontend/data contract risk:
- `TrendCardVideo` now safely handles missing `reel_id`, but that also makes it easy for incomplete rows to masquerade as a normal content card with a dead media affordance removed.

## 5) Items I could not finish live in this sandbox

I was able to inspect code paths and earlier live count snapshots, but the sandbox blocked direct outbound shell access to Supabase when I tried to repeat the raw REST queries.

Because of that, I could not reliably complete these live-only checks in this pass:
- Re-pull the exact DB rows for the currently visible cards
- Recompute orphaned rows against all frontend filters
- Recompute duplicate groups across the full dataset
- Reconfirm the live rendered page state by querying the browser DOM directly

Those should be rerun from an environment with outbound DB access before triage.

## 6) Code references

- [frontend/src/routes/index.tsx](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/routes/index.tsx)
- [frontend/src/components/TrendCard.tsx](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/TrendCard.tsx)
- [frontend/src/components/TrendCardVideo.tsx](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/components/TrendCardVideo.tsx)
- [frontend/src/lib/api.ts](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/frontend/src/lib/api.ts)
- [backend/api.py](/C:/Users/Chinmay/OneDrive/Desktop/trendrop/backend/api.py)

## 7) Completion pass

These items were blocked in the earlier partial pass and are now confirmed from live DB reads.

### A. `trend_origin='unknown'` is both historical debt and an active issue

Confirmed by live queries:
- `reels_total`: 4783
- `unknown_total`: 2342
- `unknown_recent_since_1500_IST`: 24
- `unknown_cultural_candidate` from manual sample review: 38

Interpretation:
- This is not just old data left behind before a normalization fix.
- New unknown-origin rows are still being created in the current scrape window.
- The unknown pool is large enough to materially hide cross-cultural content from the Global rail, because the Global API explicitly excludes `trend_origin IN/unknown/null`.

Observed causes:
- `trend_origin` is initially produced by the scrape/classification prompt path in `backend/instagram_scraper.py`.
- It is then normalized by `_normalize_trend_origin(...)`.
- `trend_engine.py` also computes a trend-level origin by majority vote across reel origins.
- The live sample shows two failure modes:
  - truly missing audio/title/artist context, where `unknown` is reasonable
  - clearly classifiable Indian or foreign audio still ending up as `unknown`

### B. Current visible Global row is still the cross-cultural Korean audio row

Live DB row:
- `Song for Denise` / `Piano Fantasia`
- `trend_origin=KR`
- `is_cross_cultural=true`

This is still a legitimate Global-rail candidate and still appears in the current live data snapshot.

### C. Current India / Emerging rows

Live `trends` rows currently active:
- `Main Tera Boyfriend` / `Arijit Singh, Neha Kakkar, Meet Bros`
  - `status=emerging`
  - `trend_origin=IN`
  - `llm_classification_status=pending`
- `Musicaltunnel`
  - `status=emerging`
  - `trend_origin=IN`
  - `llm_classification_status=skipped_local_fallback`

### D. Duplicate groups

Full-dataset live query over all reels:
- `dup_groups_total`: 293
- `dup_groups_mixed`: 123

Meaning:
- There are many repeated audio groups.
- A substantial subset has mixed `trend_origin` or `is_cross_cultural` values across rows, which matches the earlier `Song for Denise` / mixed-origin pattern.

### E. Orphaned rows

The live `trends` table has 41 rows total and only 2 are currently active (`emerging` or `rising`).

That means:
- `orphan_trends_count`: 39

These are not visible in the main/India feed or the Emerging section under the current frontend filters.

### F. Live render verification status

I was able to confirm the live DB state for the current visible row sets, but the sandbox blocked browser automation with:
- `EPERM: operation not permitted, lstat 'C:\\Users\\Chinmay\\AppData\\Local\\OpenAI\\Codex'`

So:
- live DB confirmation: yes
- live browser screenshot/DOM confirmation: still blocked in this sandbox

This completion pass is therefore complete for DB-backed verification, but browser-level proof remains pending until a browser-capable environment is available.
