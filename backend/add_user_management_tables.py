"""
Database Migration: Add User Management, Anti-Abuse, and Plan Features Tables
Phase 1: Admin Dashboard & User Management
"""
import os
import sys
try:
    import psycopg2
except ImportError:
    psycopg2 = None
from dotenv import load_dotenv
from supabase import create_client, Client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

if not SUPABASE_DB_URL:
    print("ERROR: SUPABASE_DB_URL not set in environment variables")
    sys.exit(1)

def run_migration():
    """Run the database migration to add user management tables"""
    
    if psycopg2:
        # Direct PostgreSQL connection for better DDL control
        try:
            conn = psycopg2.connect(SUPABASE_DB_URL)
            conn.autocommit = True
            cursor = conn.cursor()
            
            print("Connected to PostgreSQL. Running migration...")
            
            # 1. Add new columns to users table if they don't exist
            print("\n1. Updating users table...")
            alter_users_queries = [
                """
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS device_fingerprint text,
                ADD COLUMN IF NOT EXISTS ip_address text,
                ADD COLUMN IF NOT EXISTS usage_count int DEFAULT 0,
                ADD COLUMN IF NOT EXISTS last_active timestamp,
                ADD COLUMN IF NOT EXISTS status text DEFAULT 'active',
                ADD COLUMN IF NOT EXISTS email_verified boolean DEFAULT false,
                ADD COLUMN IF NOT EXISTS trial_ends_at timestamp,
                ADD COLUMN IF NOT EXISTS subscription_id text
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_plan ON users(plan);
                CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
                """
            ]
            
            for query in alter_users_queries:
                try:
                    cursor.execute(query)
                    print(f"  [OK] Executed: {query[:50]}...")
                except Exception as e:
                    print(f"  [ERROR] {e}")
            
            # 2. Create device_fingerprints table
            print("\n2. Creating device_fingerprints table...")
            create_device_fingerprints = """
            CREATE TABLE IF NOT EXISTS device_fingerprints (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                user_email text REFERENCES users(email) ON DELETE CASCADE,
                fingerprint_hash text NOT NULL,
                user_agent text,
                screen_resolution text,
                timezone text,
                language text,
                ip_address text,
                is_primary boolean DEFAULT false,
                last_seen timestamp DEFAULT now(),
                created_at timestamp DEFAULT now()
            );
            
            CREATE INDEX IF NOT EXISTS idx_device_fingerprints_user ON device_fingerprints(user_email);
            CREATE INDEX IF NOT EXISTS idx_device_fingerprints_hash ON device_fingerprints(fingerprint_hash);
            """
            
            try:
                cursor.execute(create_device_fingerprints)
                print("  [OK] Created device_fingerprints table")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            # 3. Create usage_logs table
            print("\n3. Creating usage_logs table...")
            create_usage_logs = """
            CREATE TABLE IF NOT EXISTS usage_logs (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                user_email text REFERENCES users(email) ON DELETE CASCADE,
                feature_used text NOT NULL,
                plan_at_time text,
                timestamp timestamp DEFAULT now(),
                metadata jsonb
            );
            
            CREATE INDEX IF NOT EXISTS idx_usage_logs_user ON usage_logs(user_email);
            CREATE INDEX IF NOT EXISTS idx_usage_logs_timestamp ON usage_logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_usage_logs_feature ON usage_logs(feature_used);
            """
            
            try:
                cursor.execute(create_usage_logs)
                print("  [OK] Created usage_logs table")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            # 4. Create plan_features table
            print("\n4. Creating plan_features table...")
            create_plan_features = """
            CREATE TABLE IF NOT EXISTS plan_features (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                plan_name text UNIQUE NOT NULL,
                display_name text NOT NULL,
                price_monthly numeric DEFAULT 0,
                price_yearly numeric DEFAULT 0,
                api_limit_per_day int DEFAULT 10,
                trend_views_per_day int DEFAULT 10,
                features jsonb NOT NULL,
                is_active boolean DEFAULT true,
                created_at timestamp DEFAULT now()
            );
            
            CREATE INDEX IF NOT EXISTS idx_plan_features_name ON plan_features(plan_name);
            """
            
            try:
                cursor.execute(create_plan_features)
                print("  [OK] Created plan_features table")
            except Exception as e:
                print(f"  [ERROR] Error: {e}")
            
            # 5. Insert default plan tiers
            print("\n5. Inserting default plan tiers...")
            insert_plans = """
            INSERT INTO plan_features (plan_name, display_name, price_monthly, price_yearly, api_limit_per_day, trend_views_per_day, features) VALUES
            ('free', 'Free', 0, 0, 5, 10, '["basic_trends", "algorithm_insights", "limited_analytics"]'::jsonb),
            ('pro', 'Pro', 19, 190, 100, -1, '["unlimited_trends", "ai_generation", "early_detection", "advanced_analytics", "india_features", "video_analysis"]'::jsonb),
            ('business', 'Business', 49, 490, -1, -1, '["unlimited_trends", "ai_generation", "early_detection", "advanced_analytics", "india_features", "video_analysis", "team_features", "api_access", "priority_support"]'::jsonb)
            ON CONFLICT (plan_name) DO NOTHING;
            """
            
            try:
                cursor.execute(insert_plans)
                print("  [OK] Inserted default plan tiers")
            except Exception as e:
                print(f"  [ERROR] Error: {e}")
            
            # 6. Create suspicious_activity table
            print("\n6. Creating suspicious_activity table...")
            create_suspicious_activity = """
            CREATE TABLE IF NOT EXISTS suspicious_activity (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                user_email text REFERENCES users(email) ON DELETE CASCADE,
                activity_type text NOT NULL,
                description text,
                severity text DEFAULT 'medium',
                ip_address text,
                device_fingerprint text,
                is_resolved boolean DEFAULT false,
                resolved_at timestamp,
                created_at timestamp DEFAULT now()
            );
            
            CREATE INDEX IF NOT EXISTS idx_suspicious_activity_user ON suspicious_activity(user_email);
            CREATE INDEX IF NOT EXISTS idx_suspicious_activity_resolved ON suspicious_activity(is_resolved);
            """
            
            try:
                cursor.execute(create_suspicious_activity)
                print("  [OK] Created suspicious_activity table")
            except Exception as e:
                print(f"  [ERROR] Error: {e}")
            
            # 7. Create admin_audit_log table
            print("\n7. Creating admin_audit_log table...")
            create_admin_audit_log = """
            CREATE TABLE IF NOT EXISTS admin_audit_log (
                id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                admin_email text NOT NULL,
                action text NOT NULL,
                target_user_email text,
                details jsonb,
                ip_address text,
                timestamp timestamp DEFAULT now()
            );
            
            CREATE INDEX IF NOT EXISTS idx_admin_audit_log_admin ON admin_audit_log(admin_email);
            CREATE INDEX IF NOT EXISTS idx_admin_audit_log_timestamp ON admin_audit_log(timestamp);
            """
            
            try:
                cursor.execute(create_admin_audit_log)
                print("  [OK] Created admin_audit_log table")
            except Exception as e:
                print(f"  [ERROR] Error: {e}")
            
            # 8. Enable RLS on new tables
            print("\n8. Enabling Row Level Security...")
            tables_to_enable = [
                "device_fingerprints", "usage_logs", "plan_features",
                "suspicious_activity", "admin_audit_log"
            ]
            
            for table in tables_to_enable:
                try:
                    cursor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
                    print(f"  [OK] RLS enabled on {table}")
                except Exception as e:
                    print(f"  [ERROR] Error enabling RLS on {table}: {e}")
            
            # 9. Create RLS policies
            print("\n9. Creating RLS policies...")
            rls_policies = [
                # device_fingerprints
                """
                CREATE POLICY "Users can view their own device fingerprints"
                ON device_fingerprints FOR SELECT
                USING (auth.uid()::text = (SELECT id FROM users WHERE email = user_email));
                """,
                """
                CREATE POLICY "Service role can manage device fingerprints"
                ON device_fingerprints FOR ALL
                USING (true);
                """,
                # usage_logs
                """
                CREATE POLICY "Users can view their own usage logs"
                ON usage_logs FOR SELECT
                USING (auth.uid()::text = (SELECT id FROM users WHERE email = user_email));
                """,
                """
                CREATE POLICY "Service role can manage usage logs"
                ON usage_logs FOR ALL
                USING (true);
                """,
                # plan_features (public read, service write)
                """
                CREATE POLICY "Public can view plan features"
                ON plan_features FOR SELECT
                USING (is_active = true);
                """,
                """
                CREATE POLICY "Service role can manage plan features"
                ON plan_features FOR ALL
                USING (true);
                """,
                # suspicious_activity (admin only)
                """
                CREATE POLICY "Service role can manage suspicious activity"
                ON suspicious_activity FOR ALL
                USING (true);
                """,
                # admin_audit_log (admin only)
                """
                CREATE POLICY "Service role can manage admin audit log"
                ON admin_audit_log FOR ALL
                USING (true);
                """
            ]
            
            for policy in rls_policies:
                try:
                    cursor.execute(policy)
                    print(f"  [OK] Created RLS policy")
                except Exception as e:
                    print(f"  [ERROR] Error creating policy: {e}")
            
            cursor.close()
            conn.close()
            print("\n✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    else:
        print("psycopg2 not installed, using Supabase client instead")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Note: Full DDL requires direct PostgreSQL connection")
        print("Some features may be limited with Supabase client")

if __name__ == "__main__":
    run_migration()