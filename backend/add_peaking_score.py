import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def add_peaking_score_column():
    """Add peaking_score column to trends table"""
    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()
    
    try:
        cur.execute("""
            ALTER TABLE trends 
            ADD COLUMN IF NOT EXISTS peaking_score float DEFAULT 0
        """)
        conn.commit()
        print("OK: Added peaking_score column")
        
        # Create index for performance
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_trends_peaking_score 
            ON trends(peaking_score DESC) 
            WHERE peaking_score >= 70
        """)
        conn.commit()
        print("OK: Created peaking_score index")
        
    except Exception as e:
        print(f"ERROR: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    add_peaking_score_column()