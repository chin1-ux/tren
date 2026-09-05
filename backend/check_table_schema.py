"""
Check table schema to determine correct column names for RLS policies
"""
import os
import sys
try:
    import psycopg2
except ImportError:
    psycopg2 = None
from dotenv import load_dotenv

load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

if psycopg2 and SUPABASE_DB_URL:
    conn = psycopg2.connect(SUPABASE_DB_URL)
    cur = conn.cursor()
    
    tables_to_check = [
        "device_fingerprints",
        "usage_logs",
        "phone_verifications",
        "plan_features",
        "feedback",
        "jobs",
        "deal_payment_milestones"
    ]
    
    for table in tables_to_check:
        try:
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
            """)
            columns = [row[0] for row in cur.fetchall()]
            print(f"{table}: {columns}")
        except Exception as e:
            print(f"{table}: Table does not exist")
    
    cur.close()
    conn.close()
else:
    print("Cannot check schema - psycopg2 or DB URL not available")