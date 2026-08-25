"""
Database Migration: Add subscription grace period tracking
Phase: Subscription cancellation/failed renewal handling
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
    """Run the database migration to add subscription grace period tracking"""
    
    if psycopg2:
        # Direct PostgreSQL connection for better DDL control
        try:
            conn = psycopg2.connect(SUPABASE_DB_URL)
            conn.autocommit = True
            cursor = conn.cursor()
            
            print("Connected to PostgreSQL. Running migration...")
            
            # Add subscription tracking columns to users table
            print("\nAdding subscription tracking columns to users table...")
            alter_users_query = """
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS subscription_status text,
            ADD COLUMN IF NOT EXISTS grace_period_ends_at timestamp;
            """
            
            try:
                cursor.execute(alter_users_query)
                print("  [OK] Added subscription_status and grace_period_ends_at columns")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            # Create index for subscription status queries
            print("\nCreating index for subscription status queries...")
            create_index_query = """
            CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users(subscription_status);
            CREATE INDEX IF NOT EXISTS idx_users_grace_period ON users(grace_period_ends_at);
            """
            
            try:
                cursor.execute(create_index_query)
                print("  [OK] Created subscription status indexes")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            cursor.close()
            conn.close()
            
            print("\n✅ Subscription grace period tracking migration completed successfully!")
            
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