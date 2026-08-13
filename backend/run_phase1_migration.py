"""
Phase 1 Migration Execution Script
Executes the admin/role system schema migration
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
    """Execute the Phase 1 migration"""
    
    if not psycopg2:
        print("ERROR: psycopg2 not installed. Please install it: pip install psycopg2-binary")
        sys.exit(1)
    
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Connected to PostgreSQL. Executing Phase 1 migration...\n")
        
        # ============================================
        # 1. Add role column to users table
        # ============================================
        print("1. Adding role column to users table...")
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'user';")
            print("   [OK] Added role column")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        try:
            cursor.execute("ALTER TABLE users ADD CONSTRAINT users_role_check CHECK (role IN ('user', 'admin'));")
            print("   [OK] Added role check constraint")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        # ============================================
        # 2. Create admin_actions table
        # ============================================
        print("\n2. Creating admin_actions table...")
        create_admin_actions = """
        CREATE TABLE IF NOT EXISTS admin_actions (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            admin_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
            target_user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
            action TEXT NOT NULL,
            details JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        try:
            cursor.execute(create_admin_actions)
            print("   [OK] Created admin_actions table")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_admin_actions_admin_id ON admin_actions(admin_id);",
            "CREATE INDEX IF NOT EXISTS idx_admin_actions_target_user_id ON admin_actions(target_user_id);",
            "CREATE INDEX IF NOT EXISTS idx_admin_actions_created_at ON admin_actions(created_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_admin_actions_action ON admin_actions(action);"
        ]
        for idx in indexes:
            try:
                cursor.execute(idx)
                print(f"   [OK] Created index: {idx.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                print(f"   [ERROR] {e}")
        
        # ============================================
        # 3. Create plan_overrides table
        # ============================================
        print("\n3. Creating plan_overrides table...")
        create_plan_overrides = """
        CREATE TABLE IF NOT EXISTS plan_overrides (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
            tier TEXT NOT NULL,
            granted_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        try:
            cursor.execute(create_plan_overrides)
            print("   [OK] Created plan_overrides table")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        # Create indexes
        plan_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_plan_overrides_user_id ON plan_overrides(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_plan_overrides_expires_at ON plan_overrides(expires_at);",
            "CREATE INDEX IF NOT EXISTS idx_plan_overrides_tier ON plan_overrides(tier);"
        ]
        for idx in plan_indexes:
            try:
                cursor.execute(idx)
                print(f"   [OK] Created index: {idx.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                print(f"   [ERROR] {e}")
        
        # Add constraint
        try:
            cursor.execute("ALTER TABLE plan_overrides ADD CONSTRAINT plan_overrides_tier_check CHECK (tier IN ('free', 'creator', 'agency'));")
            print("   [OK] Added tier check constraint")
        except Exception as e:
            print(f"   [ERROR] {e}")
        
        # ============================================
        # 4. Rename old admin tables
        # ============================================
        print("\n4. Renaming old admin tables...")
        renames = [
            "ALTER TABLE IF EXISTS admin_users RENAME TO admin_users_deprecated_20240813;",
            "ALTER TABLE IF EXISTS admin_audit_log RENAME TO admin_audit_log_deprecated_20240813;",
            "ALTER TABLE IF EXISTS admin_audit_log_enhanced RENAME TO admin_audit_log_enhanced_deprecated_20240813;"
        ]
        for rename in renames:
            try:
                cursor.execute(rename)
                table_name = rename.split('RENAME TO ')[1].replace(';', '')
                print(f"   [OK] Renamed to: {table_name}")
            except Exception as e:
                print(f"   [ERROR] {e}")
        
        # ============================================
        # 5. Enable RLS
        # ============================================
        print("\n5. Enabling Row Level Security...")
        for table in ["admin_actions", "plan_overrides"]:
            try:
                cursor.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
                print(f"   [OK] RLS enabled on {table}")
            except Exception as e:
                print(f"   [ERROR] {e}")
        
        # ============================================
        # 6. Create RLS policies
        # ============================================
        print("\n6. Creating RLS policies (service role only)...")
        policies = [
            "CREATE POLICY \"Service role can manage admin_actions\" ON admin_actions FOR ALL USING (auth.role() = 'service_role');",
            "CREATE POLICY \"Service role can manage plan_overrides\" ON plan_overrides FOR ALL USING (auth.role() = 'service_role');"
        ]
        for policy in policies:
            try:
                cursor.execute(policy)
                print(f"   [OK] Created policy")
            except Exception as e:
                print(f"   [ERROR] {e}")
        
        # ============================================
        # 7. Verification queries
        # ============================================
        print("\n7. Running verification queries...")
        
        # Verify role column
        print("\n   [Verification] Role column in users table:")
        cursor.execute("""
            SELECT column_name, data_type, column_default 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'role';
        """)
        role_result = cursor.fetchall()
        for row in role_result:
            print(f"      {row}")
        
        # Verify admin_actions table
        print("\n   [Verification] admin_actions table:")
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'admin_actions';")
        actions_result = cursor.fetchall()
        for row in actions_result:
            print(f"      {row}")
        
        # Verify plan_overrides table
        print("\n   [Verification] plan_overrides table:")
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'plan_overrides';")
        overrides_result = cursor.fetchall()
        for row in overrides_result:
            print(f"      {row}")
        
        # Verify deprecated tables
        print("\n   [Verification] Deprecated tables:")
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%deprecated%';")
        deprecated_result = cursor.fetchall()
        for row in deprecated_result:
            print(f"      {row}")
        
        cursor.close()
        conn.close()
        print("\n✅ Phase 1 migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
