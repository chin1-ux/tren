import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing from environment variables.")
    exit(1)

print("Connecting to Supabase...")
sb = create_client(url, key)

print("Creating user_notification_prefs table via SQL...")

# Use raw SQL execution via Supabase
# Note: Supabase Python client doesn't support raw SQL directly for DDL
# We'll need to use the REST API or psycopg2
# For now, let's use the Supabase SQL editor approach via RPC

print("Note: This script requires direct SQL execution.")
print("Please run the following SQL in Supabase SQL Editor:")
print("""
CREATE TABLE IF NOT EXISTS user_notification_prefs (
    id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    user_email text NOT NULL UNIQUE,
    notify_trend_alerts boolean DEFAULT true,
    notify_daily_ideas boolean DEFAULT true,
    notify_brand_deals boolean DEFAULT true,
    notify_weekly_report boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

ALTER TABLE user_notification_prefs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS user_notification_prefs_owner_policy ON user_notification_prefs;

CREATE POLICY user_notification_prefs_owner_policy ON user_notification_prefs
FOR ALL USING (user_email = auth.jwt() ->> 'email');

CREATE INDEX IF NOT EXISTS idx_user_notification_prefs_email ON user_notification_prefs(user_email);
""")
