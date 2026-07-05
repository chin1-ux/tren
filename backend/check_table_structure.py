import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

def check_table_structure():
    if not SUPABASE_DB_URL:
        print("Error: SUPABASE_DB_URL not found in environment variables")
        return
    
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check structure of tables without proper policies
        tables_to_check = [
            "calendar_plans",
            "creator_profiles", 
            "creator_trend_memory",
            "pre_post_analyses",
            "trend_feedback",
            "trial_reel_plans",
            "user_preferences",
            "trend_lifecycle",
            "youtube_shorts"
        ]
        
        for table in tables_to_check:
            print(f"\n=== Table: {table} ===")
            try:
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position;
                """)
                columns = cursor.fetchall()
                for col in columns:
                    print(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
            except Exception as e:
                print(f"  Error: {e}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error checking table structure: {e}")

if __name__ == "__main__":
    check_table_structure()
