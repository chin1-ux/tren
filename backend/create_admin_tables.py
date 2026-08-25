"""
Database migration script for admin authentication and audit logging.
Run this script to create the necessary tables for the admin system.
"""
import os
from dotenv import load_dotenv
from supabase import create_client
import bcrypt
from datetime import datetime, timezone

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def create_admin_users_table():
    """Create the admin_users table"""
    print("Creating admin_users table...")
    
    # Note: In Supabase, you typically create tables via SQL or the dashboard
    # This script will attempt to create it via SQL, but you may need to use the Supabase dashboard
    sql = """
    CREATE TABLE IF NOT EXISTS admin_users (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('super_admin', 'admin', 'read_only')),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        last_login TIMESTAMPTZ,
        failed_login_attempts INTEGER DEFAULT 0,
        locked_until TIMESTAMPTZ
    );
    """
    
    try:
        # Try to execute via Supabase SQL (may not work directly)
        # For Supabase, you typically need to use the SQL editor or REST API
        print("SQL to execute in Supabase SQL Editor:")
        print(sql)
        print("\nPlease execute this SQL in your Supabase SQL Editor.")
        return True
    except Exception as e:
        print(f"Error creating admin_users table: {e}")
        print("Please manually create the table using the SQL above in Supabase SQL Editor.")
        return False

def create_admin_audit_log_enhanced_table():
    """Create the enhanced admin audit log table"""
    print("\nCreating admin_audit_log_enhanced table...")
    
    sql = """
    CREATE TABLE IF NOT EXISTS admin_audit_log_enhanced (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        admin_email TEXT NOT NULL,
        action TEXT NOT NULL,
        target_user_email TEXT,
        details JSONB,
        ip_address TEXT,
        user_agent TEXT,
        timestamp TIMESTAMPTZ DEFAULT NOW()
    );
    
    -- Create index for faster queries
    CREATE INDEX IF NOT EXISTS idx_admin_audit_log_enhanced_admin_email ON admin_audit_log_enhanced(admin_email);
    CREATE INDEX IF NOT EXISTS idx_admin_audit_log_enhanced_timestamp ON admin_audit_log_enhanced(timestamp);
    CREATE INDEX IF NOT EXISTS idx_admin_audit_log_enhanced_action ON admin_audit_log_enhanced(action);
    """
    
    try:
        print("SQL to execute in Supabase SQL Editor:")
        print(sql)
        print("\nPlease execute this SQL in your Supabase SQL Editor.")
        return True
    except Exception as e:
        print(f"Error creating admin_audit_log_enhanced table: {e}")
        print("Please manually create the table using the SQL above in Supabase SQL Editor.")
        return False

def add_version_to_plan_features():
    """Add version field to plan_features table for optimistic locking"""
    print("\nAdding version field to plan_features table...")
    
    sql = """
    ALTER TABLE plan_features 
    ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
    """
    
    try:
        print("SQL to execute in Supabase SQL Editor:")
        print(sql)
        print("\nPlease execute this SQL in your Supabase SQL Editor.")
        return True
    except Exception as e:
        print(f"Error adding version field: {e}")
        print("Please manually execute the SQL above in Supabase SQL Editor.")
        return False

def create_initial_admin_user():
    """Create the initial admin user"""
    print("\nCreating initial admin user...")
    
    # Get admin email and password from environment or use defaults
    admin_email = os.getenv("INITIAL_ADMIN_EMAIL", "chinmay.feb03@gmail.com")
    admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "changeme123")
    
    # Hash the password
    password_hash = bcrypt.hashpw(admin_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    sql = f"""
    INSERT INTO admin_users (email, password_hash, role, created_at)
    VALUES ('{admin_email}', '{password_hash}', 'super_admin', NOW())
    ON CONFLICT (email) DO NOTHING;
    """
    
    try:
        print("SQL to execute in Supabase SQL Editor:")
        print(sql)
        print(f"\nInitial admin email: {admin_email}")
        print(f"Initial admin password: {admin_password}")
        print("PLEASE CHANGE THIS PASSWORD IMMEDIATELY AFTER FIRST LOGIN!")
        print("\nPlease execute this SQL in your Supabase SQL Editor.")
        return True
    except Exception as e:
        print(f"Error creating initial admin user: {e}")
        print("Please manually execute the SQL above in Supabase SQL Editor.")
        return False

def main():
    """Run all migrations"""
    print("=" * 60)
    print("Admin System Database Migration")
    print("=" * 60)
    
    print("\nThis script will generate SQL statements that you need to execute")
    print("in your Supabase SQL Editor to set up the admin system.")
    print("\nIMPORTANT: Set JWT_SECRET_KEY in your environment variables!")
    
    # Check for JWT secret
    jwt_secret = os.getenv("JWT_SECRET_KEY")
    if not jwt_secret:
        print("\nWARNING: JWT_SECRET_KEY is not set in environment variables!")
        print("Please set it before running the application:")
        print("export JWT_SECRET_KEY='your-secure-random-secret-key'")
    else:
        print("\nJWT_SECRET_KEY is configured")
    
    # Generate SQL statements
    create_admin_users_table()
    create_admin_audit_log_enhanced_table()
    add_version_to_plan_features()
    create_initial_admin_user()
    
    print("\n" + "=" * 60)
    print("Migration Complete")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Execute all SQL statements in your Supabase SQL Editor")
    print("2. Set JWT_SECRET_KEY in your environment variables")
    print("3. Change the initial admin password after first login")
    print("4. Update your frontend .env file to remove VITE_ADMIN_KEY")
    print("5. Deploy the updated backend and frontend")

if __name__ == "__main__":
    main()