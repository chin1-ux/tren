"""
Database Migration: Add cancellation reasons tracking
Phase: Capture cancellation reasons
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
    """Run the database migration to add cancellation reasons tracking"""
    
    if psycopg2:
        # Direct PostgreSQL connection for better DDL control
        try:
            conn = psycopg2.connect(SUPABASE_DB_URL)
            conn.autocommit = True
            cursor = conn.cursor()
            
            print("Connected to PostgreSQL. Running migration...")
            
            # Add cancellation_reason column to users table
            print("\nAdding cancellation_reason column to users table...")
            alter_cancellation_query = """
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS cancellation_reason text;
            """
            
            try:
                cursor.execute(alter_cancellation_query)
                print("  [OK] Added cancellation_reason column")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            # Add cancellation_date column to users table
            print("\nAdding cancellation_date column to users table...")
            alter_date_query = """
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS cancellation_date timestamp with time zone;
            """
            
            try:
                cursor.execute(alter_date_query)
                print("  [OK] Added cancellation_date column")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            cursor.close()
            conn.close()
            
            print("\n✅ Cancellation reasons migration completed successfully!")
            
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