"""
Database Migration: Add user_id for watermarking
Phase: Watermark/personalize trend data
"""
import os
import sys
import random
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
    """Run the database migration to add user_id for watermarking"""
    
    if psycopg2:
        # Direct PostgreSQL connection for better DDL control
        try:
            conn = psycopg2.connect(SUPABASE_DB_URL)
            conn.autocommit = True
            cursor = conn.cursor()
            
            print("Connected to PostgreSQL. Running migration...")
            
            # Add user_id column to users table
            print("\nAdding user_id column to users table...")
            alter_users_query = """
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS user_id text;
            """
            
            try:
                cursor.execute(alter_users_query)
                print("  [OK] Added user_id column")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            # Generate user_id for existing users
            print("\nGenerating user_id for existing users...")
            generate_ids_query = """
            UPDATE users 
            SET user_id = '#' || (floor(random() * 9000 + 1000)::text)
            WHERE user_id IS NULL OR user_id = '';
            """
            
            try:
                cursor.execute(generate_ids_query)
                print("  [OK] Generated user_id for existing users")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            # Create index for user_id queries
            print("\nCreating index for user_id...")
            create_index_query = """
            CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
            """
            
            try:
                cursor.execute(create_index_query)
                print("  [OK] Created user_id index")
            except Exception as e:
                print(f"  [ERROR] {e}")
            
            cursor.close()
            conn.close()
            
            print("\n✅ User ID watermarking migration completed successfully!")
            
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