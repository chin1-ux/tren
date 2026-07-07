import os
import logging
import psycopg2
from dotenv import load_dotenv

load_dotenv()

try:
    logging.basicConfig(
        filename="create_instagram_tokens_table.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass
logger = logging.getLogger(__name__)


def create_instagram_tokens_table():
    """
    Create the instagram_tokens table to store Instagram OAuth tokens.
    Uses SUPABASE_DB_URL (direct PostgreSQL connection) to execute DDL.
    """
    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise ValueError("SUPABASE_DB_URL is not set in .env")

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS instagram_tokens (
        id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        user_email text UNIQUE NOT NULL,
        access_token text NOT NULL,
        token_type text DEFAULT 'long-lived',
        expires_at timestamp NOT NULL,
        ig_account_id text,
        ig_username text,
        updated_at timestamp DEFAULT now(),
        created_at timestamp DEFAULT now()
    );
    """

    enable_rls_sql = "ALTER TABLE instagram_tokens ENABLE ROW LEVEL SECURITY;"

    policies_sql = [
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'instagram_tokens'
                AND policyname = 'Users can view own Instagram tokens'
            ) THEN
                CREATE POLICY "Users can view own Instagram tokens"
                    ON instagram_tokens FOR SELECT
                    USING (user_email = auth.jwt() ->> 'email');
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'instagram_tokens'
                AND policyname = 'Users can insert own Instagram tokens'
            ) THEN
                CREATE POLICY "Users can insert own Instagram tokens"
                    ON instagram_tokens FOR INSERT
                    WITH CHECK (user_email = auth.jwt() ->> 'email');
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'instagram_tokens'
                AND policyname = 'Users can update own Instagram tokens'
            ) THEN
                CREATE POLICY "Users can update own Instagram tokens"
                    ON instagram_tokens FOR UPDATE
                    USING (user_email = auth.jwt() ->> 'email');
            END IF;
        END $$;
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'instagram_tokens'
                AND policyname = 'Users can delete own Instagram tokens'
            ) THEN
                CREATE POLICY "Users can delete own Instagram tokens"
                    ON instagram_tokens FOR DELETE
                    USING (user_email = auth.jwt() ->> 'email');
            END IF;
        END $$;
        """,
    ]

    index_sql = """
    CREATE INDEX IF NOT EXISTS idx_instagram_tokens_user_email
        ON instagram_tokens(user_email);
    """

    print("=" * 60)
    print("Creating instagram_tokens table...")
    print("=" * 60)

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()

        # 1. Create table
        cur.execute(create_table_sql)
        print("[OK] Table 'instagram_tokens' created (or already exists)")
        logger.info("Table created or already exists")

        # 2. Enable RLS
        cur.execute(enable_rls_sql)
        print("[OK] RLS enabled on 'instagram_tokens'")
        logger.info("RLS enabled")

        # 3. Create policies (idempotent via DO blocks)
        policy_names = ["SELECT", "INSERT", "UPDATE", "DELETE"]
        for sql, op in zip(policies_sql, policy_names):
            cur.execute(sql)
            print(f"[OK] Policy applied: Users can {op.lower()} own Instagram tokens")
        logger.info("All RLS policies applied")

        # 4. Create index
        cur.execute(index_sql)
        print("[OK] Index created on user_email")
        logger.info("Index created")

        cur.close()
        conn.close()

        print("=" * 60)
        print("[DONE] instagram_tokens table is ready.")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Failed: {e}")
        print(f"[ERROR] {e}")
        raise


if __name__ == "__main__":
    create_instagram_tokens_table()
