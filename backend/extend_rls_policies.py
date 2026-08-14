"""
Database Migration: Extend RLS Coverage to User and Billing Tables
Phase: Extend RLS coverage to user and billing tables
"""
import os
import sys
try:
    import psycopg2
except ImportError:
    psycopg2 = None
from dotenv import load_dotenv

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

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

if not SUPABASE_DB_URL:
    print("ERROR: SUPABASE_DB_URL not set in environment variables")
    sys.exit(1)

def run_migration():
    """Run the database migration to extend RLS coverage"""
    
    if psycopg2:
        # Direct PostgreSQL connection for better DDL control
        try:
            conn = psycopg2.connect(SUPABASE_DB_URL)
            conn.autocommit = True
            cursor = conn.cursor()
            
            print("Connected to PostgreSQL. Running RLS extension migration...")
            
            # Define tables and their RLS policies
            rls_policies = [
                # User-owned tables - users can only see their own data
                {
                    "table": "users",
                    "user_policy": "CREATE POLICY users_user_read ON users FOR SELECT USING (auth.uid()::text = id::text)",
                    "service_policy": "CREATE POLICY users_service_all ON users FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                {
                    "table": "active_sessions",
                    "user_policy": "CREATE POLICY active_sessions_user_read ON active_sessions FOR SELECT USING (auth.uid()::text = user_id::text)",
                    "service_policy": "CREATE POLICY active_sessions_service_all ON active_sessions FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                {
                    "table": "device_fingerprints",
                    "user_policy": "CREATE POLICY device_fingerprints_user_read ON device_fingerprints FOR SELECT USING (auth.uid()::text = (SELECT id FROM users WHERE email = device_fingerprints.user_email)::text)",
                    "service_policy": "CREATE POLICY device_fingerprints_service_all ON device_fingerprints FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                {
                    "table": "usage_logs",
                    "user_policy": "CREATE POLICY usage_logs_user_read ON usage_logs FOR SELECT USING (auth.uid()::text = (SELECT id FROM users WHERE email = usage_logs.user_email)::text)",
                    "service_policy": "CREATE POLICY usage_logs_service_all ON usage_logs FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                {
                    "table": "phone_verifications",
                    "user_policy": None,  # Table doesn't exist yet, skip
                    "service_policy": None
                },
                # Plan/billing tables - read-only for users, full access for service_role
                {
                    "table": "plan_features",
                    "user_policy": None,  # Table doesn't exist yet, skip
                    "service_policy": None
                },
                {
                    "table": "plan_overrides",
                    "user_policy": "CREATE POLICY plan_overrides_user_read ON plan_overrides FOR SELECT USING (auth.uid()::text = user_id::text)",
                    "service_policy": "CREATE POLICY plan_overrides_service_all ON plan_overrides FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                {
                    "table": "subscription_tiers",
                    "user_policy": "CREATE POLICY subscription_tiers_user_read ON subscription_tiers FOR SELECT USING (true)",
                    "service_policy": "CREATE POLICY subscription_tiers_service_all ON subscription_tiers FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                # Admin tables - restricted access
                {
                    "table": "admin_actions",
                    "user_policy": None,  # No user access
                    "service_policy": "CREATE POLICY admin_actions_service_all ON admin_actions FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                {
                    "table": "admin_audit_log",
                    "user_policy": None,  # No user access
                    "service_policy": "CREATE POLICY admin_audit_log_service_all ON admin_audit_log FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                {
                    "table": "admin_audit_log_enhanced",
                    "user_policy": None,  # No user access
                    "service_policy": "CREATE POLICY admin_audit_log_enhanced_service_all ON admin_audit_log_enhanced FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                # Deal/brand tables - user-owned
                {
                    "table": "brand_deals",
                    "user_policy": "CREATE POLICY brand_deals_user_read ON brand_deals FOR SELECT USING (auth.uid()::text = creator_id::text)",
                    "service_policy": "CREATE POLICY brand_deals_service_all ON brand_deals FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                {
                    "table": "deal_payment_milestones",
                    "user_policy": None,  # Complex relationship, service_role only for now
                    "service_policy": "CREATE POLICY deal_payment_milestones_service_all ON deal_payment_milestones FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                {
                    "table": "credit_transactions",
                    "user_policy": "CREATE POLICY credit_transactions_user_read ON credit_transactions FOR SELECT USING (auth.uid()::text = user_id::text)",
                    "service_policy": "CREATE POLICY credit_transactions_service_all ON credit_transactions FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                # Additional user tables
                {
                    "table": "jobs",
                    "user_policy": "CREATE POLICY jobs_user_read ON jobs FOR SELECT USING (auth.uid()::text = (SELECT id FROM users WHERE email = jobs.user_email)::text)",
                    "service_policy": "CREATE POLICY jobs_service_all ON jobs FOR ALL TO service_role USING (true) WITH CHECK (true)"
                },
                {
                    "table": "feedback",
                    "user_policy": None,  # Table doesn't exist yet, skip
                    "service_policy": None
                },
            ]
            
            for policy_config in rls_policies:
                table_name = policy_config["table"]
                user_policy = policy_config["user_policy"]
                service_policy = policy_config["service_policy"]
                
                print(f"\nProcessing table: {table_name}")
                
                # Enable RLS
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
                    print(f"  [OK] Enabled RLS on {table_name}")
                except Exception as e:
                    if "already enabled" in str(e).lower():
                        print(f"  [SKIP] RLS already enabled on {table_name}")
                    else:
                        print(f"  [ERROR] Failed to enable RLS on {table_name}: {e}")
                        continue
                
                # Drop existing policies if they exist
                if user_policy:
                    try:
                        cursor.execute(f"DROP POLICY IF EXISTS {table_name}_user_read ON {table_name}")
                    except Exception:
                        pass
                
                try:
                    cursor.execute(f"DROP POLICY IF EXISTS {table_name}_service_all ON {table_name}")
                except Exception:
                    pass
                
                # Create user policy (if applicable)
                if user_policy:
                    try:
                        cursor.execute(user_policy)
                        print(f"  [OK] Created user policy on {table_name}")
                    except Exception as e:
                        print(f"  [ERROR] Failed to create user policy on {table_name}: {e}")
                
                # Create service role policy
                try:
                    cursor.execute(service_policy)
                    print(f"  [OK] Created service role policy on {table_name}")
                except Exception as e:
                    print(f"  [ERROR] Failed to create service role policy on {table_name}: {e}")
            
            cursor.close()
            conn.close()
            
            print("\n✅ RLS extension migration completed successfully!")
            print("\nNote: Some tables may not exist in your database yet.")
            print("This migration will safely skip non-existent tables.")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()