#!/usr/bin/env python3
"""
Add created_at timestamp to trends table
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

def main():
    if not SUPABASE_DB_URL:
        print("Error: SUPABASE_DB_URL is missing from environment variables.")
        return

    print("Connecting to Supabase PostgreSQL database...")
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        # Add created_at column if it doesn't exist
        print("Adding created_at column to trends table...")
        cursor.execute("""
            ALTER TABLE trends
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
        """)
        print("[PASS] Added created_at column to trends table")

        # Update existing trends with approximate created_at based on ID
        print("Updating existing trends with approximate created_at...")
        cursor.execute("""
            UPDATE trends
            SET created_at = NOW() - (INTERVAL '1 day' * (171 - id))
            WHERE created_at IS NULL;
        """)
        print("[PASS] Updated existing trends with approximate created_at")

        # Verify the column was added
        print("Verifying created_at column...")
        cursor.execute("""
            SELECT COUNT(*) FROM trends WHERE created_at IS NOT NULL;
        """)
        count = cursor.fetchone()[0]
        print(f"[PASS] {count} trends now have created_at timestamp")

        cursor.close()
        conn.close()
        print("Database migration complete and successful!")

    except Exception as e:
        print(f"Failed to add created_at column: {e}")

if __name__ == "__main__":
    main()
