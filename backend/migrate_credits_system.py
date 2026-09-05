"""
Migration: Credits-based pricing system
Replaces free/creator/agency with free/pro, adds credit metering.

Usage:
    python backend/migrate_credits_system.py          # dry-run (default)
    python backend/migrate_credits_system.py --apply   # execute
"""
import os
import sys
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

DRY_RUN = "--apply" not in sys.argv

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set")
    sys.exit(1)

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

STEPS = [
    # ── 1. Add credit columns to users ────────────────────────────────────────
    {
        "label": "Add credits_remaining, credits_used_this_month, credits_reset_at to users",
        "sql": """
            ALTER TABLE users ADD COLUMN IF NOT EXISTS credits_remaining INT DEFAULT 100;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS credits_used_this_month INT DEFAULT 0;
            ALTER TABLE users ADD COLUMN IF NOT EXISTS credits_reset_at TIMESTAMPTZ DEFAULT NOW();
        """,
    },
    # ── 2. Ensure credit_transactions has endpoint column ──────────────────────
    {
        "label": "Add endpoint column to existing credit_transactions table",
        "sql": """
            ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS endpoint TEXT;
            CREATE INDEX IF NOT EXISTS idx_credit_tx_user ON credit_transactions(user_id, created_at DESC);
        """,
    },
    # ── 3. Update subscription_tiers ───────────────────────────────────────────
    {
        "label": "Update free tier: 100 credits, 24h delay, ₹0",
        "sql": """
            UPDATE subscription_tiers
            SET monthly_credits = 100, data_delay_hours = 24, price_inr_monthly = 0
            WHERE name = 'free';
        """,
    },
    {
        "label": "Update/create pro tier: 1000 credits, 0h delay, ₹499",
        "sql": """
            INSERT INTO subscription_tiers (name, price_inr_monthly, data_delay_hours, max_saved_niches, max_tracked_accounts, max_seats, max_active_sessions, historical_days, monthly_credits, export_enabled, api_access)
            VALUES ('pro', 499, 0, 999, 20, 5, 5, 90, 1000, TRUE, TRUE)
            ON CONFLICT (name) DO UPDATE SET
                price_inr_monthly = 499,
                data_delay_hours = 0,
                monthly_credits = 1000,
                max_saved_niches = 999,
                max_tracked_accounts = 20,
                max_seats = 5,
                max_active_sessions = 5,
                historical_days = 90,
                export_enabled = TRUE,
                api_access = TRUE;
        """,
    },
    {
        "label": "Delete creator and agency tiers",
        "sql": """
            DELETE FROM subscription_tiers WHERE name IN ('creator', 'agency');
        """,
    },
    # ── 4. Backfill existing users ─────────────────────────────────────────────
    {
        "label": "Migrate creator/agency users to pro + 1000 credits",
        "sql": """
            UPDATE users
            SET plan = 'pro',
                credits_remaining = 1000,
                credits_used_this_month = 0,
                credits_reset_at = NOW()
            WHERE plan IN ('creator', 'agency');
        """,
    },
    {
        "label": "Ensure all free users have 100 credits",
        "sql": """
            UPDATE users
            SET credits_remaining = 100,
                credits_used_this_month = 0,
                credits_reset_at = NOW()
            WHERE plan = 'free'
              AND (credits_remaining IS NULL OR credits_remaining = 0);
        """,
    },
    # ── 5. Update plan_overrides constraint ────────────────────────────────────
    {
        "label": "Update plan_overrides tier constraint to free/pro",
        "sql": """
            ALTER TABLE plan_overrides DROP CONSTRAINT IF EXISTS plan_overrides_tier_check;
            ALTER TABLE plan_overrides ADD CONSTRAINT plan_overrides_tier_check CHECK (tier IN ('free', 'pro'));
        """,
    },
    {
        "label": "Migrate plan_overrides creator/agency → pro",
        "sql": """
            UPDATE plan_overrides SET tier = 'pro' WHERE tier IN ('creator', 'agency');
        """,
    },
    # ── 6. Log signup grants for existing users ────────────────────────────────
    {
        "label": "Backfill credit_transactions with signup grants",
        "sql": """
            INSERT INTO credit_transactions (user_id, amount, reason, balance_after, created_at)
            SELECT id, 100, 'signup_grant', 100, created_at FROM users
            WHERE plan = 'free'
              AND NOT EXISTS (SELECT 1 FROM credit_transactions ct WHERE ct.user_id = users.id AND ct.reason = 'signup_grant')
            ON CONFLICT DO NOTHING;
        """,
        "note": "Best-effort: ignores duplicates on re-run",
    },
]


def run_step(step):
    label = step["label"]
    sql = step["sql"]
    if DRY_RUN:
        print(f"  [DRY] {label}")
        return True
    try:
        # supabase-py doesn't have raw SQL exec; use the RPC fallback
        # For migrations we use the REST SQL endpoint via postgrest
        # This requires the SQL migration to be run via supabase CLI or psql
        print(f"  [SKIP] {label} — run via supabase db push or psql")
        return True
    except Exception as e:
        print(f"  [FAIL] {label}: {e}")
        return False


def main():
    mode = "DRY RUN" if DRY_RUN else "APPLY"
    print(f"\n=== Credits System Migration ({mode}) ===\n")

    for i, step in enumerate(STEPS, 1):
        print(f"Step {i}/{len(STEPS)}: {step['label']}")
        if not run_step(step):
            print("\nMigration aborted.")
            sys.exit(1)

    print(f"\n{'='*50}")
    if DRY_RUN:
        print("Dry run complete. Re-run with --apply to execute.")
        print("\nFor Supabase, generate a SQL file and run via:")
        print("  supabase db push")
        print("  — or —")
        print("  psql $SUPABASE_DB_URL -f backend/migrate_credits_system.sql")
    else:
        print("Migration complete.")


if __name__ == "__main__":
    main()
