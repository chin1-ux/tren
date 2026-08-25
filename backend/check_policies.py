import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

def check_policies():
    if not SUPABASE_DB_URL:
        print("Error: SUPABASE_DB_URL not found in environment variables")
        return
    
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("Checking existing RLS policies for all public tables...")
        print("=" * 80)
        
        query = """
        SELECT 
            schemaname,
            tablename,
            policyname,
            permissive,
            roles,
            cmd,
            qual,
            with_check
        FROM pg_policies 
        WHERE schemaname = 'public'
        ORDER BY tablename, policyname;
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("No RLS policies found in public schema.")
        else:
            print(f"{'Table':<25} {'Policy':<30} {'Command':<10}")
            print("-" * 80)
            
            for row in results:
                schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check = row
                roles_str = str(roles) if roles else "public"
                print(f"{tablename:<25} {policyname:<30} {cmd:<10}")
        
        print("=" * 80)
        print(f"\nTotal policies: {len(results)}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error checking policies: {e}")

if __name__ == "__main__":
    check_policies()
