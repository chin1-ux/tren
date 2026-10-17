import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv("SUPABASE_DB_URL")
if not db_url:
    print("SUPABASE_DB_URL not found in environment.")
    exit(1)

os.makedirs("evidence/order85", exist_ok=True)
out_file = "evidence/order85/pg_stat_statements_result.txt"

q1 = """
select left(regexp_replace(query, '\\s+', ' ', 'g'), 140) as q,
       calls, rows, round(rows::numeric / nullif(calls,0)) as rows_per_call
from pg_stat_statements
order by rows desc
limit 20;
"""

q1_alt = """
select left(regexp_replace(query, '\\s+', ' ', 'g'), 140) as q,
       calls, rows, round(rows::numeric / nullif(calls,0)) as rows_per_call
from extensions.pg_stat_statements
order by rows desc
limit 20;
"""

q2 = """
select relname, seq_scan, seq_tup_read, idx_scan, idx_tup_fetch
from pg_stat_user_tables
order by seq_tup_read desc
limit 10;
"""

output_lines = []

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Query 1
    output_lines.append("=== QUERY 1: pg_stat_statements (Top 20 by rows) ===")
    try:
        cur.execute(q1)
        rows1 = cur.fetchall()
    except Exception as e:
        conn.rollback()
        output_lines.append(f"Query 1 failed ({e}), trying with extensions.pg_stat_statements...")
        cur.execute(q1_alt)
        rows1 = cur.fetchall()
        
    colnames1 = [desc[0] for desc in cur.description]
    output_lines.append(f"{colnames1[0]:<70} | {colnames1[1]:<10} | {colnames1[2]:<10} | {colnames1[3]:<10}")
    output_lines.append("-" * 110)
    for r in rows1:
        q_str = str(r[0]) if r[0] is not None else ""
        calls_str = str(r[1]) if r[1] is not None else ""
        rows_str = str(r[2]) if r[2] is not None else ""
        rpc_str = str(r[3]) if r[3] is not None else ""
        output_lines.append(f"{q_str[:68]:<70} | {calls_str:<10} | {rows_str:<10} | {rpc_str:<10}")
        
    output_lines.append("\n=== QUERY 2: pg_stat_user_tables (Top 10 by seq_tup_read) ===")
    cur.execute(q2)
    rows2 = cur.fetchall()
    colnames2 = [desc[0] for desc in cur.description]
    output_lines.append(f"{colnames2[0]:<25} | {colnames2[1]:<12} | {colnames2[2]:<15} | {colnames2[3]:<12} | {colnames2[4]:<12}")
    output_lines.append("-" * 85)
    for r in rows2:
        rel = str(r[0]) if r[0] is not None else ""
        seq_scan = str(r[1]) if r[1] is not None else ""
        seq_tup = str(r[2]) if r[2] is not None else ""
        idx_scan = str(r[3]) if r[3] is not None else ""
        idx_fetch = str(r[4]) if r[4] is not None else ""
        output_lines.append(f"{rel:<25} | {seq_scan:<12} | {seq_tup:<15} | {idx_scan:<12} | {idx_fetch:<12}")
        
    cur.close()
    conn.close()
    
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")
        
    print(f"SQL execution successful! Results written to {out_file}")
    for l in output_lines[:35]:
        print(l)
except Exception as e:
    print(f"Error executing SQL: {e}")
