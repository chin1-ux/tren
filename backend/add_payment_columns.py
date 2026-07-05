"""
add_payment_columns.py — add razorpay tracking columns to the users table.
Safe to run multiple times (uses ALTER TABLE IF NOT EXISTS pattern).
"""
import psycopg2
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DB_URL = os.getenv("SUPABASE_DB_URL")

STATEMENTS = [
    # plan column already exists with default 'free' — ensure it is there
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan text NOT NULL DEFAULT 'free'",
    # Store Razorpay IDs for audit trail
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_payment_id text",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_order_id text",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_updated_at timestamptz",
    # Index for fast plan lookup
    "CREATE INDEX IF NOT EXISTS idx_users_plan ON users(plan)",
]

def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    errors = 0
    for stmt in STATEMENTS:
        try:
            cur.execute(stmt + ";")
            print(f"OK  {stmt[:80]}...")
        except Exception as e:
            print(f"ERR {stmt[:80]}... => {e}")
            errors += 1
    cur.close()
    conn.close()
    if errors == 0:
        print("Done - payment columns added/verified with zero errors.")
    else:
        print(f"Done with {errors} error(s).")

if __name__ == "__main__":
    main()
