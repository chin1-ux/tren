import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

if not SUPABASE_DB_URL:
    print("ERROR: SUPABASE_DB_URL not set in environment variables")
    sys.exit(1)

def run_migration():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = False
        cur = conn.cursor()
        
        print("Connected to PostgreSQL database. Running migration...")

        # 1. Create subscription_tiers table
        print("Creating subscription_tiers table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS subscription_tiers (
          id SERIAL PRIMARY KEY,
          name TEXT UNIQUE NOT NULL,
          price_inr_monthly INT NOT NULL,
          data_delay_hours INT NOT NULL DEFAULT 24,
          max_saved_niches INT NOT NULL DEFAULT 0,
          max_tracked_accounts INT NOT NULL DEFAULT 0,
          max_seats INT NOT NULL DEFAULT 1,
          max_active_sessions INT NOT NULL DEFAULT 1,
          historical_days INT NOT NULL DEFAULT 1,
          monthly_credits INT NOT NULL DEFAULT 0,
          export_enabled BOOLEAN DEFAULT FALSE,
          api_access BOOLEAN DEFAULT FALSE
        );
        """)

        # Seed tiers
        print("Seeding subscription_tiers table...")
        cur.execute("""
        INSERT INTO subscription_tiers (name, price_inr_monthly, data_delay_hours, max_saved_niches, max_tracked_accounts, max_seats, max_active_sessions, historical_days, monthly_credits, export_enabled, api_access)
        VALUES
          ('free', 0, 24, 0, 0, 1, 1, 1, 0, FALSE, FALSE),
          ('creator', 999, 0, 3, 0, 1, 1, 7, 500, FALSE, FALSE),
          ('agency', 4999, 0, 999, 20, 5, 5, 90, 5000, TRUE, TRUE)
        ON CONFLICT (name) DO NOTHING;
        """)

        # 2. Add columns to users table
        print("Updating users table columns...")
        alter_queries = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number TEXT UNIQUE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS tier_id INT REFERENCES subscription_tiers(id);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'active';",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_renews_at TIMESTAMPTZ;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_customer_id TEXT;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active';"
        ]
        for q in alter_queries:
            cur.execute(q)

        # 3. Associate tier_id for default free tier users
        cur.execute("""
        UPDATE users 
        SET tier_id = (SELECT id FROM subscription_tiers WHERE name = 'free') 
        WHERE tier_id IS NULL;
        """)

        # 4. Create active_sessions table
        print("Creating active_sessions table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS active_sessions (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id bigint REFERENCES users(id) ON DELETE CASCADE,
          device_fingerprint TEXT NOT NULL,
          device_label TEXT,
          last_active_at TIMESTAMPTZ DEFAULT now(),
          created_at TIMESTAMPTZ DEFAULT now()
        );
        """)

        # 5. Create tracking table for rollback
        cur.execute("""
        CREATE TABLE IF NOT EXISTS _temp_migration_phase1_users (
          user_id bigint PRIMARY KEY
        );
        """)

        # Log pro/business users to temp table
        cur.execute("""
        INSERT INTO _temp_migration_phase1_users (user_id)
        SELECT id FROM users WHERE plan IN ('pro', 'business')
        ON CONFLICT DO NOTHING;
        """)

        # Update plans and tier_id
        cur.execute("""
        UPDATE users 
        SET plan = 'creator', tier_id = (SELECT id FROM subscription_tiers WHERE name = 'creator') 
        WHERE plan = 'pro';
        """)
        rows_creator = cur.rowcount

        cur.execute("""
        UPDATE users 
        SET plan = 'agency', tier_id = (SELECT id FROM subscription_tiers WHERE name = 'agency') 
        WHERE plan = 'business';
        """)
        rows_agency = cur.rowcount

        conn.commit()
        print(f"Migration successful! Updated: pro->creator: {rows_creator}, business->agency: {rows_agency}")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
