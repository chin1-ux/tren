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
- Never connect directly to any raw DB credential (SUPABASE_DB_URL, psycopg2, direct Postgres connection) without explicit per-instance permission — regardless of justification, including "just to unblock a test." All schema changes come as a .sql migration file for Chinmay to review and apply himself via the Supabase UI.
- Absence of errors in a log is NOT proof something works correctly — push for verification that the actual outcome (data, security behavior) is correct, not just that nothing crashed.
- One or two fix items at a time, with check-ins — not giant unsupervised batches, and no self-approving into the next task before Chinmay responds.
- Don't accept an explanation for unexpected/suspicious results (e.g. "0 successes because X") without evidence — treat unverified explanations the same as unverified fixes.
- Before reporting anything as "done," confirm against actual current session state — don't re-report already-closed items as outstanding, and don't assume a prior claim was accepted without checking.
- Test/seed scripts must target a non-prod environment, or if none exists, must use an obviously-tagged, auto-cleaned dataset and confirm cleanup as part of the same task — not as a follow-up once caught.

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
