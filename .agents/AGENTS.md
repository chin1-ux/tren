# Trendrop Project Agent Rules

## DB Migration Pattern

**Rule: Never rely on `CREATE TABLE IF NOT EXISTS` to add new columns to existing tables.**

When a migration script targets a table that may already exist in production:
- Use `ALTER TABLE <table> ADD COLUMN IF NOT EXISTS <col> <type>` for each new column.
- `CREATE TABLE IF NOT EXISTS` silently no-ops when the table exists — new columns in the DDL are ignored.
- This caused a telemetry gap in `cron_runs` (columns `groq_keys_detected`, `gemini_keys_detected`, `classification_failed_429`, etc. were NULL for all rows until a separate ALTER TABLE pass was run).

**Correct pattern for migration scripts:**
```python
# Always separate "create table" from "add columns"
cur.execute("CREATE TABLE IF NOT EXISTS foo (...original_cols...)")
new_columns = [
    "ALTER TABLE foo ADD COLUMN IF NOT EXISTS bar TEXT",
    "ALTER TABLE foo ADD COLUMN IF NOT EXISTS baz INTEGER",
]
for stmt in new_columns:
    cur.execute(stmt)
```

## Secret Hygiene

- Never print a secret or token inline in a command string. Always load from environment variable or `.env` file.
- Reference GitHub tokens via `$env:GH_TOKEN` (PowerShell) or `$GH_TOKEN` (bash), never hardcoded in a command.
- If a token has been exposed in a conversation or command history, flag it for immediate revocation before any further use.

## Standing Rule: Database Credential Access

- **Never connect directly**: Agents must NEVER connect directly to `SUPABASE_DB_URL`, any raw Postgres connection string, or any direct database credential (psycopg2, raw SQL client, etc.) without explicit per-instance permission from Chinmay, granted in that specific conversation, for that specific action.
- **No exceptions**: This applies regardless of justification — including "just to unblock a local test," "just to verify a fix," or any other framing that treats it as low-stakes because it's temporary or reversible.
- **Schema changes are manual**: All schema changes (new tables, columns, constraints, indexes, RLS policies) must be delivered as a `.sql` migration file for Chinmay to review and apply himself via the Supabase UI. Agents do not apply schema changes directly, ever — not to production, not "just to test," not even idempotently.
- **Stop on blockers**: If the agent's own test/verification process requires a schema change to proceed, the correct action is to STOP, report the blocker, and propose the migration — not silently apply it and continue.
- **Impulse to bypass is a signal to stop**: If an agent ever finds itself about to use a direct DB credential to move faster, that impulse is itself the signal to stop and ask, not a justification to proceed.

## Consolidated Key Working Rules (Persistent)

- Never accept "done"/"fixed"/"verified" without actual pasted evidence — curl responses, raw SQL query results, raw logs. Summaries alone get pushed back on.
- Never DROP or TRUNCATE a database table under any justification.
- Never change hosting/deployment/auth architecture without flagging Chinmay first and getting explicit approval — this includes things that look like "small" internal refactors (e.g. swapping how a client/session object is instantiated) if they touch shared state or auth flow.
- **Hosting Architecture Rule**: Railway and Render are NOT used. Do not assume or reference active Railway/Render background worker hosting.
- **Scraper Account Rule**: Exactly 1 Instagram account / cookie set is used (`INSTAGRAM_COOKIES_B64` or `backend/cookies.json`). Do not assume or require secondary Instagram accounts (`INSTAGRAM_COOKIES_B64_2`).
- Never connect directly to any raw DB credential (SUPABASE_DB_URL, psycopg2, direct Postgres connection) without explicit per-instance permission — regardless of justification, including "just to unblock a test." All schema changes come as a .sql migration file for Chinmay to review and apply himself via the Supabase UI.
- Absence of errors in a log is NOT proof something works correctly — push for verification that the actual outcome (data, security behavior) is correct, not just that nothing crashed.
- One or two fix items at a time, with check-ins — not giant unsupervised batches, and no self-approving into the next task before Chinmay responds.
- Don't accept an explanation for unexpected/suspicious results (e.g. "0 successes because X") without evidence — treat unverified explanations the same as unverified fixes.
- Before reporting anything as "done," confirm against actual current session state — don't re-report already-closed items as outstanding, and don't assume a prior claim was accepted without checking.
- Test/seed scripts must target a non-prod environment, or if none exists, must use an obviously-tagged, auto-cleaned dataset and confirm cleanup as part of the same task — not as a follow-up once caught.

## GitHub Actions Scraper Architecture & Quota Rule

- **Main Account Workflows Disabled**: All 10 GitHub Actions workflows on the main account (`ch1n-may/trendrop`) are manually disabled to preserve GitHub Actions quota (reached 90% limit).
- **Dedicated Scraper Account Active**: Background scraping continues automatically on the dedicated scraper repository (`chin1-ux/tren`), where `Scraper (Dedicated Account - 3h)` (ID: `342411740`) is active.
- **Do not re-enable main account workflows** unless explicitly requested by Chinmay.
- **Standing Quota-Blocked Sync Rule**: For the remainder of the billing cycle, `sync-to-tren1.yml` on `ch1n-may/trendrop` will fail due to main account quota. Attempt `sync-to-tren1.yml` once. If it fails with the known billing error, do NOT retry or poll — immediately report the failure and ask Chinmay whether to use the one-time direct-push exception for that specific reviewed commit.

## Scraper Freeze & Breakage Protection Rule (Golden Checkpoint v1.0)

**Tag**: `golden-scraper-v1.0` (Commit: `1632591` in `trendrop`, `631a7fb` in `trendrop_tren`)

**Rule**:
- **NO UNAPPROVED MODIFICATIONS TO SCRAPER CORE**: Agents must NEVER modify `backend/instagram_scraper_browser.py`, `backend/trend_engine.py`, or `backend/spotify_fetcher.py` without explicitly notifying Chinmay first.
- **WARNING REQUIRED BEFORE ANY SCRAPER CHANGE**: Before proposing or executing any edit to scraper logic, the agent MUST present an explicit warning note detailing:
  1. What exact lines/functions are proposed to change.
  2. Why the change is requested.
  3. The potential risks/breakages to the current high-confidence data ingestion pipeline.
  4. Ask Chinmay for explicit approval before touching any scraper code.
- **REVERT PROTOCOL**: If any future change introduces regressions, Chinmay or the agent can instantly restore the golden working state via: `git checkout golden-scraper-v1.0 -- backend/instagram_scraper_browser.py backend/trend_engine.py backend/spotify_fetcher.py`.

## Production Ready Golden Checkpoint (prod-ready-v1.0)

**Tag**: `prod-ready-v1.0`
- **Main Repo (`ch1n-may/trendrop`)**: Commit `0792128` (Tag: `prod-ready-v1.0`)
- **Scraper Repo (`chin1-ux/tren`)**: Commit `a2f5799` (Tag: `prod-ready-v1.0`)
- **Date**: Oct 2, 2026

**Verified Core Systems in this Checkpoint**:
1. **Unified Dynamic Feed**: Emerging, rising, resurging, peaked, and expired trends rendered in a single intelligent stream with priority ordering.
2. **Targeted Workspace Quick Filter**: 1-tap chip toggle giving users instant access to their targeted/saved audios and back to the unified feed.
3. **Dual-Date Timeline**: Trend cards render both "First caught" (initial discovery date) and "Last verified" (latest rescrape check) to prevent multi-day peaking date ambiguity.
4. **Why-This-Works Niche Engine**: High-accuracy semantic creator use-case matching (~85% real accuracy) on `why_this_works` and `used_for_note` powering instant niche filters (Fitness, Food, Dance, Fashion, Travel, etc.).
5. **Zero-Leak Language Engine**: Strict `language_final` priority on backend and frontend with Romanized Hindi/Punjabi vocabulary pre-rules.
6. **2:1 Balanced Interleaving**: Indian and Global audio balance in top rail feeds.
7. **Native Multi-Country Scraper Clusters**: Dedicated scraper crawling native hashtags across Brazil (pt), South Korea (ko), Latin/Spain (es), Russia (ru), and Global Edits (en).

## Production Ready Golden Checkpoint (prod-ready-v2.0)

**Tag**: `prod-ready-v2.0`
- **Main Repo (`ch1n-may/trendrop`)**: Commit `e34c82f` (Tag: `prod-ready-v2.0`)
- **Scraper Repo (`chin1-ux/tren`)**: Commit `caedd45` (Tag: `prod-ready-v2.0`)
- **Date**: Nov 23, 2026

**Verified Core Systems in this Checkpoint**:
1. **Global Scraper Hashtag Rotation**: 3-slot rotation system (`run_count % 3`) in `cron_job.py` — Slot 0 (Brazil/Latin), Slot 1 (Korea/Asia/Africa), Slot 2 (Europe/Mideast/Pop) — permanently breaks the "cached top-posts" Instagram staleness loop that caused `0 new reels` per global run.
2. **India Scraper Hashtag Rotation**: Same rotation system — Slot 0 (Bollywood/Punjabi), Slot 1 (South India — Telugu/Tamil/Kannada/Malayalam), Slot 2 (North/West regional + lifestyle) — proactively prevents future staleness as DB fills.
3. **FYP 500 Error Guard**: `backend/routes/fyp.py` safely guards `None` decision_metrics on niche queries — no more Fashion/Fitness 500 crashes.
4. **Dynamic How-to-Use Resolution**: `_resolve_how_to_use()` in discover.py prioritises `used_for_note` → `ideal_content_description` → `hook_brief` → niche templates — no more hardcoded boilerplate copy.
5. **Mobile Responsiveness**: DiscoverCategoryGrid horizontal snap rail on mobile, iOS safe-area insets in BottomTabBar, overflow-x-hidden on root — fully usable on all screen sizes.
6. **Instagram Connect Hardened**: `backend/routes/creator.py` — TooManyRedirects fixed; public account profiling working end-to-end.
7. **Global Trends Verified in DB**: IDs 11221–11234 confirmed: `window_hours_remaining=46-47`, `language_final` populated, `why_this_works` populated via safety-net classifier, `status=emerging/rising`. All 12 valid global trends visible in `/discover` (10 of top 15 results are global-language).
8. **Pipeline RCA Completed**: Root cause of "0 new global reels" definitively traced to Instagram mega-hashtag "Top Posts" section serving the same cached viral reels across days. Fix: rotate to mid-tier sub-genre tags (1M-30M posts) that Instagram refreshes faster.
9. **cron_job UnboundLocalError Fixed**: `InstagramScraper` duplicate inline import at line 706 removed — no more pipeline crash on Step 2b audio backfill.
10. **Safety-Net LLM Classifier**: `run_unclassified_safety_net_pass(limit=30)` runs at end of every pipeline — ensures no trend is left without `why_this_works` / `language_final` even when LLM API quota is 0.

**Revert Protocol**:
```bash
# Revert main repo to this checkpoint
git checkout prod-ready-v2.0 -- backend/cron_job.py backend/routes/fyp.py backend/routes/discover.py backend/routes/creator.py

# Revert scraper repo (via GitHub API or direct clone)
# Tag: prod-ready-v2.0 on chin1-ux/tren @ caedd45
```

**What is NOT under golden checkpoint protection in v2.0** (safe to modify):
- `backend/cron_job.py` — hashtag pools, pipeline orchestration, alert thresholds
- `backend/routes/*.py` — all API endpoints
- `frontend/src/**` — all frontend code

**Golden Checkpoint files (still require Chinmay approval before ANY edit)**:
- `backend/instagram_scraper_browser.py`
- `backend/trend_engine.py`
- `backend/spotify_fetcher.py`
