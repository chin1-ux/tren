#!/usr/bin/env python3
"""
Add discovery_source column to trends table for tracking external discovery
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
if not url or not key:
    raise RuntimeError('Supabase credentials not set')
sb = create_client(url, key)

def add_discovery_source_column():
    """Add discovery_source column to trends table if it doesn't exist"""
    
    try:
        # Check if column exists by attempting a query
        test_result = sb.table('trends').select('discovery_source').limit(1).execute()
        print("discovery_source column already exists")
        return True
        
    except Exception as e:
        # Column likely doesn't exist, add it
        print(f"discovery_source column check failed: {e}")
        print("Attempting to add discovery_source column...")
        
        try:
            # Use direct SQL to add column
            from database_setup import psycopg2
            
            db_url = os.getenv('SUPABASE_DB_URL')
            if not db_url:
                raise RuntimeError('SUPABASE_DB_URL not set')
            
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor()
            
            # Add the column
            cursor.execute("""
                ALTER TABLE trends 
                ADD COLUMN IF NOT EXISTS discovery_source TEXT;
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print("Successfully added discovery_source column to trends table")
            return True
            
        except ImportError:
            print("psycopg2 not available, using Supabase RPC...")
            # Fallback: try to use Supabase SQL editor
            print("Please manually add discovery_source column to trends table:")
            print("ALTER TABLE trends ADD COLUMN IF NOT EXISTS discovery_source TEXT;")
            return False
        except Exception as sql_error:
            print(f"Failed to add column via SQL: {sql_error}")
            print("Please manually add discovery_source column to trends table:")
            print("ALTER TABLE trends ADD COLUMN IF NOT EXISTS discovery_source TEXT;")
            return False

if __name__ == '__main__':
    add_discovery_source_column()
