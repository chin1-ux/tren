"""
P-METHOD-1 Step 2: Add UNIQUE constraint on audio_id + duplicate-insert test.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
import psycopg2

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise SystemExit("DATABASE_URL must be set")

conn = psycopg2.connect(DB_URL)
conn.autocommit = False
cur = conn.cursor()

try:
    # --- STEP 1: Run DDL ---
    print("STEP 1: ALTER TABLE trends ADD CONSTRAINT trends_audio_id_unique UNIQUE (audio_id)")
    cur.execute("ALTER TABLE trends ADD CONSTRAINT trends_audio_id_unique UNIQUE (audio_id)")
    conn.commit()
    print("  DDL committed successfully.\n")

    # --- STEP 2: Verify constraint exists via pg_constraint ---
    print("STEP 2: Verify constraint via pg_constraint")
    cur.execute("""
        SELECT conname, contype, conrelid::regclass
        FROM pg_constraint
        WHERE conname = 'trends_audio_id_unique'
    """)
    row = cur.fetchone()
    if row:
        print(f"  Constraint name: {row[0]}")
        print(f"  Constraint type: {row[1]} (u=unique)")
        print(f"  On table: {row[2]}")
        print("  PASS: constraint exists.\n")
    else:
        print("  FAIL: constraint not found in pg_constraint.\n")
        raise RuntimeError("Constraint verification failed")

    # --- STEP 3: Get a real audio_id for the test ---
    print("STEP 3: Pick existing audio_id for duplicate-insert test")
    cur.execute("SELECT id, audio_id FROM trends LIMIT 1")
    existing_id, existing_audio_id = cur.fetchone()
    print(f"  Using: id={existing_id}, audio_id={existing_audio_id}")
    print(f"  Row count before test: ", end="")
    cur.execute("SELECT COUNT(*) FROM trends")
    count_before = cur.fetchone()[0]
    print(f"{count_before}\n")

    # --- STEP 4: Attempt duplicate insert ---
    print("STEP 4: Attempt duplicate INSERT (expect constraint violation)")
    try:
        cur.execute("""
            INSERT INTO trends (audio_id, audio_title, status, velocity_avg)
            VALUES (%s, 'TEST_CONSTRAINT_DELETE_ME', 'emerging', 0)
        """, (existing_audio_id,))
        conn.commit()
        # If we get here, insert succeeded unexpectedly
        print("  FAIL: insert succeeded unexpectedly! Cleaning up...")
        cur.execute("DELETE FROM trends WHERE audio_title = 'TEST_CONSTRAINT_DELETE_ME'")
        conn.commit()
        print("  Cleanup: test row removed.")
        raise RuntimeError("Constraint did not reject duplicate insert!")
    except psycopg2.errors.UniqueViolation as e:
        conn.rollback()
        print(f"  CONSTRAINT VIOLATION (expected): {e.pgerror.strip()}")
        print("  PASS: duplicate insert rejected.\n")
    except RuntimeError:
        raise
    except Exception as e:
        conn.rollback()
        print(f"  UNEXPECTED ERROR: {e}")
        raise

    # --- STEP 5: Confirm no test row exists ---
    print("STEP 5: Confirm test row was NOT created in production")
    cur.execute("SELECT COUNT(*) FROM trends WHERE audio_title = 'TEST_CONSTRAINT_DELETE_ME'")
    test_rows = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM trends")
    count_after = cur.fetchone()[0]
    print(f"  Rows matching test title: {test_rows}")
    print(f"  Row count after test: {count_after} (same as before: {count_before})")
    if test_rows == 0 and count_after == count_before:
        print("  PASS: no test row in production.\n")
    else:
        print("  FAIL: test row exists or count changed!\n")
        raise RuntimeError("Test row contamination detected")

    print("ALL CHECKS PASSED. Constraint is live on production trends.audio_id.")

finally:
    cur.close()
    conn.close()
