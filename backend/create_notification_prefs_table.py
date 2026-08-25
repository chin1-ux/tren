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
        
        # Create user_notification_prefs table
        print("Creating user_notification_prefs table...")
        cursor.execute("""
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
        """)
        print("✓ Created user_notification_prefs table")
        
        # Enable RLS
        print("Enabling Row Level Security (RLS)...")
        cursor.execute("ALTER TABLE user_notification_prefs ENABLE ROW LEVEL SECURITY;")
        print("✓ Enabled RLS on user_notification_prefs")
        
        # Create RLS policy
        print("Creating RLS policy...")
        cursor.execute("DROP POLICY IF EXISTS user_notification_prefs_owner_policy ON user_notification_prefs;")
        cursor.execute("""
            CREATE POLICY user_notification_prefs_owner_policy ON user_notification_prefs
            FOR ALL USING (user_email = auth.jwt() ->> 'email');
        """)
        print("✓ Applied owner policy for user_email matching auth.jwt() ->> 'email'")
        
        # Create index for faster lookups
        print("Creating index...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_notification_prefs_email ON user_notification_prefs(user_email);")
        print("✓ Created index on user_email")
        
        cursor.close()
        conn.close()
        print("\n✓ Notification preferences table setup completed successfully!")
        
    except Exception as e:
        print(f"Failed to setup notification preferences table: {e}")

if __name__ == "__main__":
    main()