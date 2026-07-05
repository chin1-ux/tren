import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

def apply_rls_policies():
    if not SUPABASE_DB_URL:
        print("Error: SUPABASE_DB_URL not found in environment variables")
        return
    
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Applying RLS policies to tables missing policies...")
        print("=" * 60)
        
        # User-owned tables (auth.uid() / user_email matching)
        policies = [
            # calendar_plans
            ("calendar_plans_owner_policy", "calendar_plans", "ALL", "user_email = auth.jwt() ->> 'email'"),
            
            # creator_profiles
            ("creator_profiles_owner_policy", "creator_profiles", "ALL", "user_email = auth.jwt() ->> 'email'"),
            
            # creator_trend_memory
            ("creator_trend_memory_owner_policy", "creator_trend_memory", "ALL", "user_email = auth.jwt() ->> 'email'"),
            
            # pre_post_analyses
            ("pre_post_analyses_owner_policy", "pre_post_analyses", "ALL", "user_email = auth.jwt() ->> 'email'"),
            
            # trend_feedback
            ("trend_feedback_owner_policy", "trend_feedback", "ALL", "user_email = auth.jwt() ->> 'email'"),
            
            # trial_reel_plans
            ("trial_reel_plans_owner_policy", "trial_reel_plans", "ALL", "user_email = auth.jwt() ->> 'email'"),
            
            # user_preferences (uses user_id uuid)
            ("user_preferences_owner_policy", "user_preferences", "ALL", "user_id = auth.uid()"),
        ]
        
        for policy_name, table_name, cmd, using_expr in policies:
            try:
                # Drop existing policy if it exists
                cursor.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name};")
                
                # Create new policy
                cursor.execute(f"""
                    CREATE POLICY {policy_name} ON {table_name} 
                    FOR {cmd} USING ({using_expr});
                """)
                print(f"✓ Applied policy '{policy_name}' on table '{table_name}'")
            except Exception as e:
                print(f"✗ Error applying policy '{policy_name}' on '{table_name}': {e}")
        
        # Enable RLS on tables that currently have it disabled but need it
        print("\nEnabling RLS on tables that need it...")
        tables_to_enable = ["user_preferences", "youtube_shorts", "trend_lifecycle"]
        
        for table in tables_to_enable:
            try:
                cursor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
                print(f"✓ Enabled RLS on table '{table}'")
            except Exception as e:
                print(f"✗ Error enabling RLS on '{table}': {e}")
        
        # Public read policies
        print("\nApplying public read policies...")
        public_policies = [
            ("youtube_shorts_public_read_policy", "youtube_shorts", "SELECT", "true"),
            ("trend_lifecycle_public_read_policy", "trend_lifecycle", "SELECT", "true"),
        ]
        
        for policy_name, table_name, cmd, using_expr in public_policies:
            try:
                cursor.execute(f"DROP POLICY IF EXISTS {policy_name} ON {table_name};")
                cursor.execute(f"""
                    CREATE POLICY {policy_name} ON {table_name} 
                    FOR {cmd} TO authenticated USING ({using_expr});
                """)
                print(f"✓ Applied public read policy '{policy_name}' on table '{table_name}'")
            except Exception as e:
                print(f"✗ Error applying public read policy '{policy_name}' on '{table_name}': {e}")
        
        print("=" * 60)
        print("RLS policy application completed.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error applying RLS policies: {e}")

if __name__ == "__main__":
    apply_rls_policies()
