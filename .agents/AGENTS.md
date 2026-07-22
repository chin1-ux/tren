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
