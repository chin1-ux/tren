"""
Database Migration: Add phone verification fields
Phase: Wire phone verification into signup/login
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
    """Run the database migration to add phone verification fields"""
    
    if psycopg2:
        # Direct PostgreSQL connection for better DDL control
        try:
            conn = psycopg2.connect(SUPABASE_DB_URL)
            conn.autocommit = True
            cursor = conn.cursor()
            
            print("Connected to PostgreSQL. Running migration...")
            
            # Add phone_number column to users table
            print("\nAdding phone_number column to users table...")
            alter_phone_query = """
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS phone_number text;
            """
            
            try:
                cursor.execute(alter_phone_query)
                print("  [OK] Added phone_number column")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            # Add phone_verified column to users table
            print("\nAdding phone_verified column to users table...")
            alter_verified_query = """
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS phone_verified boolean DEFAULT false;
            """
            
            try:
                cursor.execute(alter_verified_query)
                print("  [OK] Added phone_verified column")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            # Create index for phone_number queries
            print("\nCreating index for phone_number...")
            create_phone_index_query = """
            CREATE INDEX IF NOT EXISTS idx_users_phone_number ON users(phone_number);
            """
            
            try:
                cursor.execute(create_phone_index_query)
                print("  [OK] Created phone_number index")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            cursor.close()
            conn.close()
            
            print("\n✅ Phone verification fields migration completed successfully!")
            
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