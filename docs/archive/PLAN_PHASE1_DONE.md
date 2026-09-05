# Phase 1 — FREE-FIXES-ONLY (COMPLETED)

> **Status: ALL 4 PRs SHIPPED AND VERIFIED.** This document is archived for reference.
> See `PLAN_PROMPT_A.md` for the active work plan.

---

## PR1: Kill topic_clustering — SHIPPED

`topic_clustering.py` deleted. Endpoints removed from `routes/trends.py`. Frontend stubs removed from `api.py`. Zero references remain.

## PR2: Language Detection Consolidation — SHIPPED

`backend/language_detection.py` created (179 lines). 4 callers updated. 14/14 test samples pass. 5 keywords added to `LANG_KEYWORD_MAP`.

## PR3: Niche Taxonomy 9 → 13 — SHIPPED

`motivation` keywords added to `NICHE_KEYWORDS`. `romance/relationship` → `romance_relationship` mapping verified. All 6 frontend `NICHES` arrays updated. 14 `NICHE_KEYWORDS` keys confirmed.

## PR4: Audio Title Normalization — SHIPPED

`backend/audio_title_normalize.py` created. `_trend_group_key()` updated. All 6 dedup/query sites updated. 30-day date filter added to unbounded reel-count query.

### Backfills Run

| Script | Result |
|--------|--------|
| `backfill_language_classification.py` | 82 trends reclassified from "en" → correct language |
| `backfill_normalize_trend_lifecycle.py` | 8172→8136 rows (34 merges, 218 renames) |
| `backfill_merge_trends.py` | 0 collisions in `trends` table (346 unique normalized tuples) |

### Minor Backlog

`audio_title_normalize.py` regex gap: compound suffixes like `(Instrumental Ultra Slowed)`, `(Super Slowed)`, `(Acoustic Mix)` not stripped. Currently moot (no live collision). Fix before it becomes one.
