-- Migration: Credits-based pricing system
-- Replaces free/creator/agency with free/pro, adds credit metering.
-- Run: psql $SUPABASE_DB_URL -f backend/migrate_credits_system.sql
-- Idempotent: uses IF NOT EXISTS / ON CONFLICT throughout.

-- ── 1. Add credit columns to users ────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS credits_remaining INT DEFAULT 100;
ALTER TABLE users ADD COLUMN IF NOT EXISTS credits_used_this_month INT DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS credits_reset_at TIMESTAMPTZ DEFAULT NOW();

-- ── 2. Ensure credit_transactions has endpoint column ──────────────────────────
-- Table already exists (created by prior migration) with schema:
--   id UUID PK, user_id INT FK, amount INT, reason TEXT, balance_after INT NOT NULL, created_at TIMESTAMPTZ
-- We just need to add the endpoint column if missing.
ALTER TABLE credit_transactions ADD COLUMN IF NOT EXISTS endpoint TEXT;
CREATE INDEX IF NOT EXISTS idx_credit_tx_user ON credit_transactions(user_id, created_at DESC);

-- ── 3. Update subscription_tiers ───────────────────────────────────────────────
UPDATE subscription_tiers
SET monthly_credits = 100, data_delay_hours = 24, price_inr_monthly = 0
WHERE name = 'free';

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

DELETE FROM subscription_tiers WHERE name IN ('creator', 'agency');

-- ── 4. Backfill existing users ─────────────────────────────────────────────────
-- Migrate paid users to pro
UPDATE users
SET plan = 'pro',
    credits_remaining = 1000,
    credits_used_this_month = 0,
    credits_reset_at = NOW()
WHERE plan IN ('creator', 'agency');

-- Ensure free users have credits
UPDATE users
SET credits_remaining = 100,
    credits_used_this_month = 0,
    credits_reset_at = NOW()
WHERE plan = 'free'
  AND (credits_remaining IS NULL OR credits_remaining = 0);

-- ── 5. Update plan_overrides ──────────────────────────────────────────────────
ALTER TABLE plan_overrides DROP CONSTRAINT IF EXISTS plan_overrides_tier_check;
ALTER TABLE plan_overrides ADD CONSTRAINT plan_overrides_tier_check CHECK (tier IN ('free', 'pro'));

UPDATE plan_overrides SET tier = 'pro' WHERE tier IN ('creator', 'agency');

-- ── 6. Backfill credit_transactions (signup grants) ───────────────────────────
-- balance_after is NOT NULL on the existing table — set to 100 (the free tier grant)
INSERT INTO credit_transactions (user_id, amount, reason, balance_after, created_at)
SELECT id, 100, 'signup_grant', 100, created_at FROM users
WHERE plan = 'free'
  AND NOT EXISTS (SELECT 1 FROM credit_transactions ct WHERE ct.user_id = users.id AND ct.reason = 'signup_grant')
ON CONFLICT DO NOTHING;
