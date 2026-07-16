import os
import psycopg2
from dotenv import load_dotenv

def run_migration():
    load_dotenv()
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("Error: SUPABASE_DB_URL not found in environment.")
        return

    print("Connecting to Supabase Database...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        # Create creator_posts table
        print("Creating creator_posts table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_posts (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                user_email text NOT NULL,
                instagram_username text NOT NULL,
                media_id text UNIQUE NOT NULL,
                caption text,
                permalink text,
                media_type text,
                media_url text,
                timestamp timestamp NOT NULL,
                like_count int DEFAULT 0,
                comments_count int DEFAULT 0,
                shares_count int DEFAULT 0,
                saves_count int DEFAULT 0,
                plays_count int DEFAULT 0,
                reach_count int DEFAULT 0,
                retention_data jsonb,
                niche_tags text[],
                created_at timestamp DEFAULT now()
            );
        """)
        
        # Create creator_niche_profiles table
        print("Creating creator_niche_profiles table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS creator_niche_profiles (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                user_email text UNIQUE NOT NULL,
                primary_niche text,
                secondary_niches text[],
                semantic_signature jsonb,
                niche_health_score float DEFAULT 1.0,
                alignment_drift_detected boolean DEFAULT false,
                recommendations text[],
                updated_at timestamp DEFAULT now()
            );
        """)

        # Enable RLS policies
        print("Enabling Row Level Security...")
        cursor.execute("ALTER TABLE creator_posts ENABLE ROW LEVEL SECURITY;")
        cursor.execute("ALTER TABLE creator_niche_profiles ENABLE ROW LEVEL SECURITY;")

        cursor.execute("DROP POLICY IF EXISTS creator_posts_owner ON creator_posts;")
        cursor.execute("CREATE POLICY creator_posts_owner ON creator_posts FOR ALL USING (user_email = auth.jwt() ->> 'email');")

        cursor.execute("DROP POLICY IF EXISTS creator_niche_owner ON creator_niche_profiles;")
        cursor.execute("CREATE POLICY creator_niche_owner ON creator_niche_profiles FOR ALL USING (user_email = auth.jwt() ->> 'email');")

        # Indexes
        print("Creating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_creator_posts_email_time ON creator_posts (user_email, timestamp);")

        print("Migration executed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
