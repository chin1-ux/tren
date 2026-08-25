import os
import sys
import psycopg2
from dotenv import load_dotenv

# Load env variables
load_dotenv()
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, ".env"))

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
        
        print("Connected to PostgreSQL database. Running Phase 2 migration...")

        # 1. Create alert_queue table
        print("Creating alert_queue table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS alert_queue (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
          trend_id BIGINT REFERENCES trends(id) ON DELETE CASCADE,
          niche_name TEXT,
          status TEXT NOT NULL DEFAULT 'pending',
          created_at TIMESTAMPTZ DEFAULT now(),
          processed_at TIMESTAMPTZ
        );
        """)
        
        # 2. Create credit_balances table
        print("Creating credit_balances table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS credit_balances (
          user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          balance INT NOT NULL DEFAULT 0,
          updated_at TIMESTAMPTZ DEFAULT now()
        );
        """)

        # 3. Create credit_transactions table
        print("Creating credit_transactions table...")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS credit_transactions (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
          amount INT NOT NULL,
          reason TEXT NOT NULL,
          balance_after INT NOT NULL,
          created_at TIMESTAMPTZ DEFAULT now()
        );
        """)

        # 4. Create or replace the deduct_credit_atomic function
        print("Creating deduct_credit_atomic PostgreSQL function...")
        cur.execute("""
        CREATE OR REPLACE FUNCTION deduct_credit_atomic(p_user_id BIGINT, p_amount INT, p_reason TEXT)
        RETURNS JSON AS $$
        DECLARE
          new_balance INT;
        BEGIN
          UPDATE credit_balances
          SET balance = balance - p_amount, updated_at = now()
          WHERE user_id = p_user_id AND balance >= p_amount
          RETURNING balance INTO new_balance;

          IF new_balance IS NULL THEN
            RETURN json_build_object('success', false);
          END IF;

          INSERT INTO credit_transactions (user_id, amount, reason, balance_after)
          VALUES (p_user_id, -p_amount, p_reason, new_balance);

          RETURN json_build_object('success', true, 'balance', new_balance);
        END;
        $$ LANGUAGE plpgsql;
        """)

        # 5. Seed initial balances for existing creator/agency users
        print("Seeding initial balances for existing users...")
        cur.execute("""
        INSERT INTO credit_balances (user_id, balance)
        SELECT id, (SELECT monthly_credits FROM subscription_tiers WHERE id = users.tier_id)
        FROM users
        WHERE tier_id IS NOT NULL
        ON CONFLICT (user_id) DO NOTHING;
        """)

        conn.commit()
        print("Phase 2 migration completed successfully.")

    except Exception as e:
        print(f"ERROR: Migration failed: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
