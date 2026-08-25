import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv("backend/.env")
db_url = os.getenv("SUPABASE_DB_URL")

print("Connecting to DB...")
conn = psycopg2.connect(db_url)
cur = conn.cursor()

try:
    # 1. Create columns in subscription_tiers if they don't exist
    print("Adding columns to subscription_tiers...")
    cur.execute("""
    ALTER TABLE subscription_tiers ADD COLUMN IF NOT EXISTS api_limit_per_day INT DEFAULT 10;
    ALTER TABLE subscription_tiers ADD COLUMN IF NOT EXISTS trend_views_per_day INT DEFAULT 10;
    ALTER TABLE subscription_tiers ADD COLUMN IF NOT EXISTS features JSONB DEFAULT '[]'::jsonb;
    ALTER TABLE subscription_tiers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();
    """)

    # 2. Update existing tiers with correct values
    print("Seeding/updating subscription_tiers data...")
    
    # free
    free_features = json.dumps(["basic_trends", "algorithm_insights", "limited_analytics"])
    cur.execute("""
    UPDATE subscription_tiers
    SET api_limit_per_day = 5,
        trend_views_per_day = 10,
        features = %s::jsonb,
        updated_at = now()
    WHERE name = 'free';
    """, (free_features,))

    # creator
    creator_features = json.dumps(["unlimited_trends", "ai_generation", "early_detection", "advanced_analytics", "india_features", "video_analysis"])
    cur.execute("""
    UPDATE subscription_tiers
    SET api_limit_per_day = 100,
        trend_views_per_day = -1,
        features = %s::jsonb,
        updated_at = now()
    WHERE name = 'creator';
    """, (creator_features,))

    # agency
    agency_features = json.dumps(["unlimited_trends", "ai_generation", "early_detection", "advanced_analytics", "india_features", "video_analysis", "team_features", "api_access", "priority_support"])
    cur.execute("""
    UPDATE subscription_tiers
    SET api_limit_per_day = -1,
        trend_views_per_day = -1,
        features = %s::jsonb,
        updated_at = now()
    WHERE name = 'agency';
    """, (agency_features,))

    # 3. Clean up the users table (map plan name 'pro' to 'creator', 'business' to 'agency')
    print("Upgrading user plan names in the users table...")
    
    # Get ID of creator and agency tiers
    cur.execute("SELECT id, name FROM subscription_tiers")
    tier_map = {name: tid for tid, name in cur.fetchall()}
    
    if 'creator' in tier_map:
        cur.execute("""
        UPDATE users 
        SET plan = 'creator', tier_id = %s 
        WHERE plan = 'pro' OR plan = 'creator';
        """, (tier_map['creator'],))
        print(f"Updated creator users: {cur.rowcount}")

    if 'agency' in tier_map:
        cur.execute("""
        UPDATE users 
        SET plan = 'agency', tier_id = %s 
        WHERE plan = 'business' OR plan = 'agency';
        """, (tier_map['agency'],))
        print(f"Updated agency users: {cur.rowcount}")

    if 'free' in tier_map:
        cur.execute("""
        UPDATE users 
        SET plan = 'free', tier_id = %s 
        WHERE plan = 'free' OR tier_id IS NULL;
        """, (tier_map['free'],))
        print(f"Updated free users: {cur.rowcount}")

    # 4. Drop the legacy plan_features table if it exists
    print("Dropping legacy plan_features table...")
    cur.execute("DROP TABLE IF EXISTS plan_features CASCADE;")

    # Commit transactions
    conn.commit()
    print("Migration completed successfully!")
except Exception as e:
    conn.rollback()
    print(f"Error during migration: {e}")
finally:
    cur.close()
    conn.close()
