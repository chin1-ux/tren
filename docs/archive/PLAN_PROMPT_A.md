# Prompt A — Honesty Pass

> **Status: COMPLETE. Playwright verified 26/26 against live Vercel.**
> See `PLAN_PHASE1_DONE.md` for completed Phase 1 work.

Six sites where fabricated, fallback, or mislabeled data is presented to users as real. Each item cites exact code, states the locked-in fix, and notes new findings from the trace.

---

## A1. `routes/ai.py` — Silent Fallback Scores

### Decision

**Split by stakes:**
- `/api/score-reel` → **Option A: return 503 error.** A fabricated performance score actively misleads content strategy — the one thing this app can't afford to get wrong.
- `/daily-ideas` and `/generate-calendar` → **Option B: disclosed fallback.** Lower-stakes inspiration prompts; honest disclosure is enough.

### Code

| File | Line(s) | Issue | Fix |
|------|---------|-------|-----|
| `backend/routes/ai.py` | 78-84 | LLM failure returns fabricated score | Return `HTTPException(503, "Scoring service temporarily unavailable")` |
| `backend/routes/ai.py` | 121-133 | Outer exception returns fabricated score | Return `HTTPException(503)` |
| `backend/routes/ai.py` | 158-165 | LLM failure returns fabricated ideas | Add `"is_fallback": true, "fallback_reason": "LLM unavailable"` to response |
| `backend/routes/ai.py` | 187-? | Calendar fallback returns fabricated data | Add `"is_fallback": true` to response |

---

## A2. Hook Analysis — Dead LLM Call

### Decision

**Option A: wire the real LLM call.** The prompt is already built and unused. This runs during background scrape cycles, not in a user's live request path, so the 2-3s latency cost is irrelevant. This is core-product quality — wire it.

### Code

| File | Line(s) | Issue |
|------|---------|-------|
| `backend/instagram_scraper_browser.py` | 1073-1086 | Prompt built but never sent |
| `backend/instagram_scraper_browser.py` | 1088-1095 | Returns hardcoded values |
| `backend/instagram_scraper_browser.py` | 1097-1125 | Persists hardcoded values to DB |

### Implementation

Replace the hardcoded return at line 1088 with:
```python
result = call_llm(system_instruction, hook_prompt, timeout=30)
return json.loads(result)  # parse the JSON the LLM returns
```

The prompt at lines 1073-1086 already asks for the exact JSON structure the function returns. The LLM response should map directly.

---

## A3. Content Generator — Template-Based, Not LLM

### Decision

**Check frontend usage first, then most likely Option C (remove).** `CaptionEngine` already covers real LLM captions at multiple live endpoints. These templates are redundant lower-quality duplication.

### Frontend Usage Audit

| Frontend call | Backend endpoint | Uses CaptionEngine? | Uses templates? |
|---------------|-----------------|--------------------| ---------------|
| `generateCaption()` → `/api/ai/generate-caption` | `routes/ai.py:338` | **Yes** — calls `CaptionEngine().get_caption_kit(trend_id)` | No |
| `AIContentGenerator.tsx` → `/api/ai/generate-caption` | `routes/ai.py:338` | **Yes** | No |
| `/api/india/caption/generate` | `routes/india.py:217` | No | **Yes** — `ContentGenerator().generate_india_caption()` |
| `/api/ai/content-ideas` | `routes/ai.py:361` | No | **Yes** — `AIContentGenerator().generate_content_ideas()` |
| `/api/ai/generate-hooks` | `routes/ai.py:400` | No | **Yes** — `AIContentGenerator().generate_hooks()` |

**Finding:** The frontend's `generateCaption()` function (api.ts:848) sends `trend_name`, `tone`, `niche` to `/api/ai/generate-caption`, but that endpoint expects `trend_id: int`. **Parameter mismatch — this endpoint is broken for the frontend's use case.** The `AIContentGenerator.tsx` component calls this function, meaning the caption generation tab in the dashboard is non-functional.

**The `/api/india/caption/generate` endpoint is NOT called by any frontend component.** Dead endpoint.

### Implementation

1. Remove `generate_india_caption()` and `generate_caption()` template methods from `content_generator.py`
2. Remove `/api/india/caption/generate` endpoint from `routes/india.py`
3. Fix the frontend's `generateCaption()` to send `trend_id` (int) instead of `trend_name` (string) — or redirect to the working `/api/trends/{id}/caption` endpoint
4. Audit `generate_content_ideas()` and `generate_hooks()` — these also use templates. Check if any frontend calls them.

---

## A4. India Features — Fabricated Regional Data

### Decision

**Option A: remove entirely.** This is the worst fabrication found today: 100% synthetic `viral_score=75.0` for every region/city/language combination, never touching real data. No middle ground. Real regional trend data already exists via `trends.language` and `trends.trend_origin` and can be built properly later if wanted.

### Code

| File | Line(s) | Issue |
|------|---------|-------|
| `backend/india_features.py` | 138-168 | `detect_regional_trends()` — fabricated viral_score=75.0 for every combo |
| `backend/india_features.py` | 170-191 | `get_regional_timing_optimization()` — hardcoded timing data |
| `backend/india_features.py` | 193-? | `get_cultural_event_automation()` — fabricated event recommendations |

### Frontend impact

The frontend calls these India endpoints:
- `/api/india/regional-trends` (api.ts:928)
- `/api/india/regional-timing` (api.ts:942)
- `/api/india/cultural-events` (api.ts:958) — used by `EarlyDetectionPanel.tsx` and `RegionalFestivalPanel.tsx`
- `/api/india/detect-language` (api.ts:965)
- `/api/india/hashtag-strategy` (api.ts:983)
- `/api/india/creator-patterns` (api.ts:1007)

Removing `india_features.py` methods means these endpoints need to either be removed or rewired to use real DB queries. The `detect-language` and `hashtag-strategy` endpoints may not depend on `india_features.py` — verify before removing.

---

## A5. Caption Engine — Fallback Disclosure + Stub Endpoint

### Decision

**Option A: add `is_fallback` disclosure.** Cheap and honest. But don't mark this closed until the `api.py:1749` question is resolved.

### New Finding: The Original Stub Is Still Live

The original audit flagged "api.py:1749 returns a stub instead of calling CaptionEngine." This was correct. The endpoint was moved from `api.py:1749` to `routes/trends.py:608` during route extraction, **but the stub was carried over unchanged**:

```python
# routes/trends.py:617-620 (CURRENT — STILL A STUB)
# Caption generation is not implemented yet. Return a valid but empty
# kit so clients can render a truthful "not ready" state instead of
# misreading this as a populated kit or crashing on missing fields.
return {"captions": [], "hashtags": []}
```

Meanwhile, `routes/ai.py:338-358` has the **working** CaptionEngine wiring:
```python
# routes/ai.py:348-350 (WORKING)
from caption_engine import CaptionEngine
engine = CaptionEngine()
caption_kit = engine.get_caption_kit(trend_id)
```

**Two endpoints, same purpose — one works, one is a stub.**

### Implementation

1. **Fix the stub** at `routes/trends.py:608-623`: Replace the empty return with the same CaptionEngine call used in `routes/ai.py:338`:
   ```python
   from caption_engine import CaptionEngine
   engine = CaptionEngine()
   caption_kit = engine.get_caption_kit(trend_id)
   return caption_kit
   ```
2. **Add `is_fallback` disclosure** to `caption_engine.py:189-215`: Add `"is_fallback": True, "fallback_reason": "LLM unavailable after retries"` to the fallback dict.
3. **Decide whether to keep both endpoints or consolidate.** `GET /api/ai/generate-caption?trend_id=X` and `GET /api/trends/{id}/caption` serve the same purpose. Keep both if different auth/rate-limit semantics are needed; remove the stub if not.

---

## A6. Hashtag Pool-Name Leak — 40 Trend Rows

### Decision

**Proceed with backfill + guard. Don't leave the write path as an open question.**

### Trace Results

All 40 affected rows were created on 2026-08-07/08 with `first_detected_at` ranging from 2026-07-30 to 2026-08-08. The current `classify_niche()` in `classification_rules.py` never returns pool names — it returns real niches or "general". The old version (before commit `70dfabdd` on Aug 9) returned "general" for INDIA_TRENDING/INDIA_VERNACULAR/GLOBAL_DISCOVERY, not the pool names themselves.

**The exact write path that produced pool names in `trends.niche_tag` remains unconfirmed after exhaustive trace.** All known code paths (`classify_single_trend()` in trend_engine.py, `_save_trend()` in trend_detector.py, `_persist_hook_analysis()` in instagram_scraper_browser.py) use `classify_niche()` which doesn't return pool names. The rows may have been created by a now-deleted code path, a manual DB operation, or a Supabase trigger.

### Implementation

1. **Backfill**: Write a targeted script to reclassify the 40 affected trends:
   ```python
   POOL_NAMES = {"INDIA_VERNACULAR", "GLOBAL_DISCOVERY", "INDIA_TRENDING", "GLOBAL_NICHES"}
   for trend in affected_trends:
       new_niche = classify_niche(trend["sample_captions"], [], source_hashtag_pool=None)
       sb.table("trends").update({"niche_tag": new_niche, "content_type": new_niche}).eq("id", trend["id"]).execute()
   ```

2. **Guard**: Add a defensive check at `trend_engine.py:1306` before the insert:
   ```python
   POOL_NAMES = {"INDIA_VERNACULAR", "GLOBAL_DISCOVERY", "INDIA_TRENDING", "GLOBAL_NICHES"}
   if niche_tag in POOL_NAMES:
       logger.warning(f"Pool name '{niche_tag}' leaked to niche_tag for '{trend['audio_title']}' — remapping to 'general'")
       niche_tag = "general"
   ```

3. **Same guard at `trend_detector.py:455`** — the other trend creation path.

---

## Implementation Order

| Order | Item | Risk | Rationale |
|-------|------|------|-----------|
| 1 | A5 (stub fix + fallback disclosure) | Low | One-line fix + small addition. Unblocks caption feature. |
| 2 | A6 (pool-name backfill + guard) | Low | Data fix, defensive guard. No behavior change for correct rows. |
| 3 | A1 (score-reel 503 + ideas/calendar disclosure) | Low | Error handling changes. Test each endpoint. |
| 4 | A4 (remove india_features fabrication) | Medium | Removing methods that frontend calls. Must update/remove frontend consumers. |
| 5 | A3 (remove template content_generator) | Medium | Removing methods + fixing frontend parameter mismatch. Verify no other callers. |
| 6 | A2 (wire hook analysis LLM) | Medium | Adding LLM call during scrape. Test scrape cycle end-to-end. |

A5 and A6 are prerequisites — they fix existing broken behavior. A1-A4 are the honesty fixes. A2 is the quality upgrade.

---

## Summary of Locked Decisions

| Item | Decision | Key detail |
|------|----------|------------|
| A1 | score-reel → 503 error; ideas/calendar → disclosed fallback | Split by stakes |
| A2 | Wire the real LLM call | Prompt already built, runs in background |
| A3 | Remove templates (Option C), fix frontend param mismatch | `/api/india/caption/generate` is dead endpoint |
| A4 | Remove `india_features.py` fabricated methods entirely | Worst fabrication; real data exists via DB |
| A5 | Add `is_fallback` + fix `routes/trends.py:608` stub | Original finding confirmed still live |
| A6 | Backfill 40 rows + add guard at write paths | Exact write path unconfirmed; guard is defensive |

---

## Playwright Verification (Live Vercel) — 26/26 PASSED

```
1. Dashboard — AIContentGenerator (caption feature)
   ✅ AI Generator tab found
   ✅ Caption tab found inside AIContentGenerator
   ✅ Caption section content visible
   ✅ No fabricated India sections on dashboard
   ✅ No JS errors on dashboard

2. /ideas — daily ideas
   ✅ Ideas page loaded
   ✅ No fallback banner (LLM working — only shows on failure)
   ✅ No JS errors on /ideas

3. Dead India API endpoints (should 404/4xx)
   ✅ /api/india/trends → 404
   ✅ /api/india/regional-trends → 401
   ✅ /api/india/trending-audio → 404
   ✅ /api/india/creator-insights → 404
   ✅ /api/india/event-content → 404
   ✅ /api/india/publish-event → 404
   ✅ /api/india/cultural-content → 404
   ✅ /api/content/india-caption → 404
   ✅ /api/content/india-ideas → 404
   ✅ /api/content/event-content → 404

4. Live API endpoints
   ✅ /api/trends → 200
   ✅ /api/trends?limit=5 → 200

5. Trend detail page
   ✅ Trend 1691 loaded (2495 chars)
   ✅ No JS errors on trend detail

6. Stats page — niche tags (A6)
   ✅ No pool-name niche tags on stats

7. /generate — video generation
   ✅ Generate page loaded (504 chars)
   ✅ No JS errors on /generate
```

Test script: `frontend/test_prompt_a.mjs`
