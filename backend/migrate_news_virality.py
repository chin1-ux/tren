import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env")
load_dotenv("backend/.env")

def run_migration():
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("SUPABASE_DB_URL not found in env")
        return
        
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()
    
    # Create news_virality_predictions table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS news_virality_predictions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        title TEXT NOT NULL,
        description TEXT,
        url TEXT UNIQUE,
        source TEXT,
        published_at TIMESTAMPTZ,
        viral_potential_score INT NOT NULL,
        recommended_angle TEXT,
        target_niches TEXT[],
        created_at TIMESTAMPTZ DEFAULT now()
    );
    """)
    print("Table news_virality_predictions created or already exists")
    
    # Alter table and enable RLS
    cur.execute("ALTER TABLE news_virality_predictions ENABLE ROW LEVEL SECURITY;")
    print("RLS enabled")
    
    # Policy checks and creation
    # Drop existing policies to prevent conflict
    cur.execute("DROP POLICY IF EXISTS service_role_policy ON news_virality_predictions;")
    
    # Create policy for service_role access only
    # service_role can do all CRUD operations. In Supabase, the role is 'service_role'.
    cur.execute("""
    CREATE POLICY service_role_policy ON news_virality_predictions 
    FOR ALL 
    TO service_role 
    USING (true) 
    WITH CHECK (true);
    """)
    print("Policy service_role_policy created")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    run_migration()
