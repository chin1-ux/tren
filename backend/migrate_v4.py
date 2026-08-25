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
    # 1. Add new columns to trends table
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS template_link TEXT;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS visual_storyboard JSONB;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS vibe_tag TEXT DEFAULT 'general';",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS is_voiceover BOOLEAN DEFAULT false;",
    "ALTER TABLE trends ADD COLUMN IF NOT EXISTS saturation_count INTEGER DEFAULT 0;",
    
    # 2. Create trend_actions table for tracking targeted trends
    """
    CREATE TABLE IF NOT EXISTS trend_actions (
        id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        user_id UUID, -- References auth.users(id) in Supabase
        trend_id bigint REFERENCES trends(id) ON DELETE CASCADE,
        action_type TEXT DEFAULT 'target', -- 'target', 'save', 'hide'
        created_at TIMESTAMPTZ DEFAULT now(),
        CONSTRAINT uq_user_trend_action UNIQUE (user_id, trend_id, action_type)
    );
    """,
    
    # 3. Enable Row Level Security (RLS) on trend_actions
    "ALTER TABLE trend_actions ENABLE ROW LEVEL SECURITY;",
    
    # 4. Create policies for RLS on trend_actions
    "DROP POLICY IF EXISTS trend_actions_service_role ON trend_actions;",
    "CREATE POLICY trend_actions_service_role ON trend_actions FOR ALL TO service_role USING (true) WITH CHECK (true);",
    
    # Allow users to manage their own actions
    "DROP POLICY IF EXISTS trend_actions_user_manage ON trend_actions;",
    "CREATE POLICY trend_actions_user_manage ON trend_actions FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);"
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
        print("Migration v4 completed.")
    except Exception as e:
        print(f"Connection or execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
