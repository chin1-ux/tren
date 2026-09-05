import os
import sys
import psycopg2
from dotenv import load_dotenv

def run_migration():
    load_dotenv()
    
    # Try getting DB connection URI from environment
    db_uri = os.getenv("DATABASE_URL")
    if not db_uri:
        # Fallback to parse individual settings if DATABASE_URL is not set directly
        supabase_db = os.getenv("SUPABASE_DB_URL")
        if supabase_db:
            db_uri = supabase_db
            
    if not db_uri:
        print("Error: No database connection details found in environment.")
        sys.exit(1)
        
    print("Connecting to Supabase Database...")
    try:
        conn = psycopg2.connect(db_uri)
        conn.autocommit = True
        cur = conn.cursor()
        
        # 1. Create reel_snapshots table
        print("Creating table reel_snapshots...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reel_snapshots (
                id              bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                reel_id         text NOT NULL,
                audio_id        text,
                snapshotted_at  timestamptz NOT NULL DEFAULT now(),
                view_count      int,
                like_count      int,
                comment_count   int,
                audio_use_count int
            )
        """)
        
        # Indices for efficient querying
        print("Creating indices on reel_snapshots...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reel_snapshots_reel_id ON reel_snapshots(reel_id, snapshotted_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_reel_snapshots_audio_id ON reel_snapshots(audio_id, snapshotted_at DESC)")
        
        # 2. Add delta tracking columns to reels table
        # We must follow the project rule: NEVER rely on CREATE TABLE IF NOT EXISTS to add columns.
        # Use ALTER TABLE ADD COLUMN IF NOT EXISTS for each new column.
        print("Adding delta columns to reels table...")
        new_columns = [
            "ALTER TABLE reels ADD COLUMN IF NOT EXISTS views_delta_last_run int DEFAULT 0",
            "ALTER TABLE reels ADD COLUMN IF NOT EXISTS likes_delta_last_run int DEFAULT 0",
            "ALTER TABLE reels ADD COLUMN IF NOT EXISTS audio_delta_last_run int DEFAULT 0",
        ]
        for stmt in new_columns:
            cur.execute(stmt)
            
        # 3. Add regional crossover columns to trends table
        print("Adding regional crossover columns to trends table...")
        trend_columns = [
            "ALTER TABLE trends ADD COLUMN IF NOT EXISTS opportunity_score float DEFAULT 0",
            "ALTER TABLE trends ADD COLUMN IF NOT EXISTS is_regional_crossover boolean DEFAULT false",
            "ALTER TABLE trends ADD COLUMN IF NOT EXISTS crossover_from_language text",
            "ALTER TABLE trends ADD COLUMN IF NOT EXISTS crossover_message text",
        ]
        for stmt in trend_columns:
            cur.execute(stmt)
            
        print("Migration completed successfully!")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
