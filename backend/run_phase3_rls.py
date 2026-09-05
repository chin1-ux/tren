"""
Phase 3 RLS Policies Execution Script
Executes the security-definer RLS policies for admin system
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
    """Execute the Phase 3 RLS policies migration"""
    
    if not psycopg2:
        print("ERROR: psycopg2 not installed. Please install it: pip install psycopg2-binary")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Connected to PostgreSQL. Executing Phase 3 RLS policies...\n")
        
        # ============================================
        # 1. Create security-definer function to check user role
        # ============================================
        print("1. Creating security-definer function: is_user_admin...")
        create_is_admin = """
        CREATE OR REPLACE FUNCTION is_user_admin(user_email TEXT)
        RETURNS BOOLEAN
        SECURITY DEFINER
        SET search_path = public
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN EXISTS (
                SELECT 1 FROM users 
                WHERE email = user_email AND role = 'admin'
            );
        END;
        $$;
        """
        try:
            cursor.execute(create_is_admin)
            print("   [OK] Created is_user_admin function")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        # ============================================
        # 2. Create security-definer function to get user ID from email
        # ============================================
        print("\n2. Creating security-definer function: get_user_id_from_email...")
        create_get_id = """
        CREATE OR REPLACE FUNCTION get_user_id_from_email(user_email TEXT)
        RETURNS BIGINT
        SECURITY DEFINER
        SET search_path = public
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RETURN (
                SELECT id FROM users 
                WHERE email = user_email 
                LIMIT 1
            );
        END;
        $$;
        """
        try:
            cursor.execute(create_get_id)
            print("   [OK] Created get_user_id_from_email function")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        # ============================================
        # 3. Drop temporary service-role policies
        # ============================================
        print("\n3. Dropping temporary service-role policies...")
        drop_policies = [
            "DROP POLICY IF EXISTS \"Service role can manage admin_actions\" ON admin_actions;",
            "DROP POLICY IF EXISTS \"Service role can manage plan_overrides\" ON plan_overrides;"
        ]
        for policy in drop_policies:
            try:
                cursor.execute(policy)
                print(f"   [OK] Dropped policy")
            except Exception as e:
                print(f"   [ERROR] {e}")
        
        # ============================================
        # 4. Create admin-bypass policies for admin_actions
        # ============================================
        print("\n4. Creating admin-bypass policies for admin_actions...")
        actions_policies = [
            """CREATE POLICY "Admins can read all audit logs" ON admin_actions
                FOR SELECT
                USING (is_user_admin(auth.jwt() ->> 'email'));""",
            """CREATE POLICY "Users can read their own audit logs" ON admin_actions
                FOR SELECT
                USING (target_user_id = get_user_id_from_email(auth.jwt() ->> 'email'));""",
            """CREATE POLICY "Service role can insert audit logs" ON admin_actions
                FOR INSERT
                WITH CHECK (auth.role() = 'service_role');""",
            """CREATE POLICY "Service role can manage audit logs" ON admin_actions
                FOR ALL
                USING (auth.role() = 'service_role');"""
        ]
        for policy in actions_policies:
            try:
                cursor.execute(policy)
                policy_name = policy.split('"')[1]
                print(f"   [OK] Created policy: {policy_name}")
            except Exception as e:
                print(f"   [ERROR] {e}")
        
        # ============================================
        # 5. Create admin-bypass policies for plan_overrides
        # ============================================
        print("\n5. Creating admin-bypass policies for plan_overrides...")
        overrides_policies = [
            """CREATE POLICY "Admins can read all plan overrides" ON plan_overrides
                FOR SELECT
                USING (is_user_admin(auth.jwt() ->> 'email'));""",
            """CREATE POLICY "Users can read their own plan overrides" ON plan_overrides
                FOR SELECT
                USING (user_id = get_user_id_from_email(auth.jwt() ->> 'email'));""",
            """CREATE POLICY "Service role can manage plan overrides" ON plan_overrides
                FOR ALL
                USING (auth.role() = 'service_role');"""
        ]
        for policy in overrides_policies:
            try:
                cursor.execute(policy)
                policy_name = policy.split('"')[1]
                print(f"   [OK] Created policy: {policy_name}")
            except Exception as e:
                print(f"   [ERROR] {e}")
        
        # ============================================
        # 6. Create admin-bypass policy for users table
        # ============================================
        print("\n6. Creating admin-bypass policies for users table...")
        users_policies = [
            """CREATE POLICY "Admins can read all users" ON users
                FOR SELECT
                USING (is_user_admin(auth.jwt() ->> 'email'));""",
            """CREATE POLICY "Admins can update users" ON users
                FOR UPDATE
                USING (is_user_admin(auth.jwt() ->> 'email'));""",
            """CREATE POLICY "Users can read own data" ON users
                FOR SELECT
                USING (email = auth.jwt() ->> 'email');"""
        ]
        for policy in users_policies:
            try:
                cursor.execute(policy)
                policy_name = policy.split('"')[1]
                print(f"   [OK] Created policy: {policy_name}")
            except Exception as e:
                print(f"   [ERROR] {e}")
        
        # ============================================
        # 7. Verification queries
        # ============================================
        print("\n7. Running verification queries...")
        
        # Verify security-definer functions exist
        print("\n   [Verification] Security-definer functions:")
        cursor.execute("""
            SELECT routine_name, security_type 
            FROM information_schema.routines 
            WHERE routine_name IN ('is_user_admin', 'get_user_id_from_email');
        """)
        func_results = cursor.fetchall()
        for row in func_results:
            print(f"      {row}")
        
        # Verify RLS policies on admin_actions
        print("\n   [Verification] RLS policies on admin_actions:")
        cursor.execute("""
            SELECT schemaname, tablename, policyname, permissive, roles, cmd 
            FROM pg_policies 
            WHERE tablename = 'admin_actions';
        """)
        actions_policies_result = cursor.fetchall()
        for row in actions_policies_result:
            print(f"      {row}")
        
        # Verify RLS policies on plan_overrides
        print("\n   [Verification] RLS policies on plan_overrides:")
        cursor.execute("""
            SELECT schemaname, tablename, policyname, permissive, roles, cmd 
            FROM pg_policies 
            WHERE tablename = 'plan_overrides';
        """)
        overrides_policies_result = cursor.fetchall()
        for row in overrides_policies_result:
            print(f"      {row}")
        
        # Verify RLS policies on users
        print("\n   [Verification] Admin-related RLS policies on users:")
        cursor.execute("""
            SELECT schemaname, tablename, policyname, permissive, roles, cmd 
            FROM pg_policies 
            WHERE tablename = 'users' AND policyname LIKE '%Admin%';
        """)
        users_policies_result = cursor.fetchall()
        for row in users_policies_result:
            print(f"      {row}")
        
        cursor.close()
        conn.close()
        print("\n✅ Phase 3 RLS policies migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
