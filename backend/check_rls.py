import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

def check_rls_status():
    if not SUPABASE_DB_URL:
        print("Error: SUPABASE_DB_URL not found in environment variables")
        return
    
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Checking RLS status for all public tables...")
        print("=" * 60)
        
        query = """
        SELECT tablename, rowsecurity 
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print(f"{'Table Name':<30} {'RLS Enabled':<15}")
        print("-" * 60)
        
        for tablename, rowsecurity in results:
            rls_status = "Yes" if rowsecurity else "No"
            print(f"{tablename:<30} {rls_status:<15}")
        
        print("=" * 60)
        print(f"\nTotal tables: {len(results)}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error checking RLS status: {e}")

if __name__ == "__main__":
    check_rls_status()
