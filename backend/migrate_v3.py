import os
import sys
import psycopg2
from dotenv import load_dotenv

# Ensure backend directory is in the import path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()
load_dotenv(".env")
load_dotenv("backend/.env")

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
if not SUPABASE_DB_URL:
    print("Error: SUPABASE_DB_URL not found in environment variables.")
    sys.exit(1)

MIGRATIONS = [
    # 1. Add news-correlation columns to trends table
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS exogenous_correlation JSONB;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS virality_type TEXT DEFAULT 'unknown';",
    
    # 2. Add tone tagging column to reels and trends tables
    "ALTER TABLE reels ADD COLUMN IF NOT EXISTS content_tone TEXT DEFAULT 'unknown';",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS content_tone TEXT DEFAULT 'unknown';",
    
    # 3. Create news cache table
    """
    CREATE TABLE IF NOT EXISTS news_api_cache (
        query TEXT PRIMARY KEY,
        response JSONB,
        created_at TIMESTAMPTZ DEFAULT now()
    );
    """,
    
    # 4. Enable RLS on news cache table
    "ALTER TABLE news_api_cache ENABLE ROW LEVEL SECURITY;",
    
    # 5. Create service_role policy for news cache table
    "DROP POLICY IF EXISTS news_api_cache_service_role ON news_api_cache;",
    "CREATE POLICY news_api_cache_service_role ON news_api_cache FOR ALL TO service_role USING (true) WITH CHECK (true);"
]

def run_migration():
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cur = conn.cursor()
        print("Connected successfully!")
        
        for idx, stmt in enumerate(MIGRATIONS, 1):
            try:
                print(f"Running step {idx}...")
                cur.execute(stmt)
                print("  Success!")
            except Exception as stmt_err:
                print(f"  Failed step {idx}: {stmt_err}")
                
        cur.close()
        conn.close()
        print("Migration v3 completed.")
    except Exception as e:
        print(f"Connection or execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
