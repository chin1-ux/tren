import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

def main():
    if not SUPABASE_DB_URL:
        print("Error: SUPABASE_DB_URL is missing from environment variables.")
        return

    print("Connecting to Supabase PostgreSQL database...")
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Add missing marketplace columns to brand_deals table
        print("Adding missing marketplace columns to brand_deals table...")
        
        columns_to_add = [
            "deal_amount numeric",
            "commission_amount numeric", 
            "details text"
        ]
        
        for column_def in columns_to_add:
            column_name = column_def.split()[0]
            try:
                cursor.execute(f"ALTER TABLE brand_deals ADD COLUMN IF NOT EXISTS {column_def};")
                print(f"✓ Added/checked column: {column_name}")
            except Exception as e:
                print(f"✗ Error adding column {column_name}: {e}")
        
        # Check if creator_email column exists and migrate data to creator_id if needed
        print("Checking for creator_email column migration...")
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'brand_deals' AND column_name = 'creator_email'
        """)
        
        creator_email_exists = cursor.fetchone()
        
        if creator_email_exists:
            print("creator_email column exists - migrating data to creator_id...")
            try:
                # Update any rows where creator_id is NULL but creator_email has value
                cursor.execute("""
                    UPDATE brand_deals 
                    SET creator_id = creator_email 
                    WHERE creator_id IS NULL AND creator_email IS NOT NULL
                """)
                print(f"✓ Migrated data from creator_email to creator_id")
                
                # Optional: Drop the creator_email column after successful migration
                # cursor.execute("ALTER TABLE brand_deals DROP COLUMN IF EXISTS creator_email;")
                # print("✓ Dropped creator_email column")
            except Exception as e:
                print(f"✗ Error migrating creator_email to creator_id: {e}")
        else:
            print("No creator_email column found - no migration needed")
        
        # Verify the schema
        print("\nCurrent brand_deals table schema:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'brand_deals'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
        
        cursor.close()
        conn.close()
        print("\n✓ Brand deals schema fix completed successfully!")
        
    except Exception as e:
        print(f"Failed to fix brand deals schema: {e}")

if __name__ == "__main__":
    main()