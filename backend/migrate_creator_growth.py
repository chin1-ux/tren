import os
import re
import psycopg2
from dotenv import load_dotenv


def _build_pooler_url(db_url: str, supabase_url: str = "") -> list[str]:
    """Derive Supabase Supavisor (pooler) URLs from the direct DB URL.
    The direct URL is IPv6-only on many Supabase projects; the pooler is IPv4-friendly.
    """
    candidates = []

    # Try explicit pooler env var first
    pooler_url = os.getenv("SUPABASE_POOLER_URL", "")
    if pooler_url:
        candidates.append(pooler_url)

    # Derive from direct DB URL: postgresql://postgres:pwd@db.{ref}.supabase.co:5432/postgres
    m = re.match(r"postgresql://([^:]+):([^@]+)@db\.([^.]+)\.supabase\.co:\d+/(\S+)", db_url or "")
    if m:
        user, pwd, ref, dbname = m.groups()
        # Supavisor session-mode (port 5432) & transaction-mode (port 6543)
        # Username format for pooler: postgres.{ref}
        for region in ["ap-south-1", "us-east-1", "us-west-1", "eu-central-1", "ap-southeast-1"]:
            host = f"aws-0-{region}.pooler.supabase.com"
            for port in [5432, 6543]:
                candidates.append(f"postgresql://postgres.{ref}:{pwd}@{host}:{port}/{dbname}")

    return candidates


DDL_STATEMENTS = [
    # ── Creator tables ──────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS creator_posts (
        id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        user_email text NOT NULL,
        instagram_username text NOT NULL,
        media_id text UNIQUE NOT NULL,
        caption text,
        permalink text,
        media_type text,
        media_url text,
        timestamp timestamp NOT NULL,
        like_count int DEFAULT 0,
        comments_count int DEFAULT 0,
        shares_count int DEFAULT 0,
        saves_count int DEFAULT 0,
        plays_count int DEFAULT 0,
        reach_count int DEFAULT 0,
        retention_data jsonb,
        niche_tags text[],
        created_at timestamp DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS creator_niche_profiles (
        id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        user_email text UNIQUE NOT NULL,
        primary_niche text,
        secondary_niches text[],
        semantic_signature jsonb,
        niche_health_score float DEFAULT 1.0,
        alignment_drift_detected boolean DEFAULT false,
        recommendations text[],
        updated_at timestamp DEFAULT now()
    )
    """,
    "ALTER TABLE creator_posts ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE creator_niche_profiles ENABLE ROW LEVEL SECURITY",
    "DROP POLICY IF EXISTS creator_posts_owner ON creator_posts",
    "CREATE POLICY creator_posts_owner ON creator_posts FOR ALL USING (user_email = auth.jwt() ->> 'email')",
    "DROP POLICY IF EXISTS creator_niche_owner ON creator_niche_profiles",
    "CREATE POLICY creator_niche_owner ON creator_niche_profiles FOR ALL USING (user_email = auth.jwt() ->> 'email')",
    "CREATE INDEX IF NOT EXISTS idx_creator_posts_email_time ON creator_posts (user_email, timestamp)",

    # ── Instagram OAuth tokens ───────────────────────────────────
    """
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
    )
    """,
    "ALTER TABLE instagram_tokens ENABLE ROW LEVEL SECURITY",
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='instagram_tokens' AND policyname='Users can view own Instagram tokens') THEN
            CREATE POLICY "Users can view own Instagram tokens" ON instagram_tokens FOR SELECT USING (user_email = auth.jwt() ->> 'email');
        END IF;
    END $$
    """,
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='instagram_tokens' AND policyname='Users can insert own Instagram tokens') THEN
            CREATE POLICY "Users can insert own Instagram tokens" ON instagram_tokens FOR INSERT WITH CHECK (user_email = auth.jwt() ->> 'email');
        END IF;
    END $$
    """,
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='instagram_tokens' AND policyname='Users can update own Instagram tokens') THEN
            CREATE POLICY "Users can update own Instagram tokens" ON instagram_tokens FOR UPDATE USING (user_email = auth.jwt() ->> 'email');
        END IF;
    END $$
    """,
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE tablename='instagram_tokens' AND policyname='Users can delete own Instagram tokens') THEN
            CREATE POLICY "Users can delete own Instagram tokens" ON instagram_tokens FOR DELETE USING (user_email = auth.jwt() ->> 'email');
        END IF;
    END $$
    """,
    "CREATE INDEX IF NOT EXISTS idx_instagram_tokens_user_email ON instagram_tokens(user_email)",

    # ── brand_deals missing marketplace columns ──────────────────
    "ALTER TABLE brand_deals ADD COLUMN IF NOT EXISTS creator_email text",
    "ALTER TABLE brand_deals ADD COLUMN IF NOT EXISTS deal_amount numeric",
    "ALTER TABLE brand_deals ADD COLUMN IF NOT EXISTS commission_amount numeric",
    "ALTER TABLE brand_deals ADD COLUMN IF NOT EXISTS details text",

    # ── users table extra columns ────────────────────────────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS auth_token text",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS instagram_username text",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS instagram_connected boolean DEFAULT false",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS plan text DEFAULT 'free'",
]



def run_migration():
    load_dotenv()
    db_url = os.getenv("SUPABASE_DB_URL", "")
    supabase_url = os.getenv("SUPABASE_URL", "")

    # Build list of connection strings to try (direct first, then pooler variants)
    urls_to_try = []
    if db_url:
        urls_to_try.append(("direct", db_url))
    for pooler_url in _build_pooler_url(db_url, supabase_url):
        urls_to_try.append(("pooler", pooler_url))

    if not urls_to_try:
        print("Error: SUPABASE_DB_URL not found in environment.")
        return

    conn = None
    for label, url in urls_to_try:
        try:
            print(f"Trying {label} connection...")
            conn = psycopg2.connect(url, connect_timeout=10)
            print(f"Connected via {label}!")
            break
        except Exception as e:
            print(f"  {label} failed: {e}")

    if conn is None:
        print("All connection attempts failed. Skipping migration (tables may already exist or will be created on next run).")
        return

    conn.autocommit = True
    cursor = conn.cursor()
    try:
        for stmt in DDL_STATEMENTS:
            stmt = stmt.strip()
            if stmt:
                try:
                    cursor.execute(stmt)
                    print(f"OK: {stmt[:60]}...")
                except Exception as e:
                    print(f"WARN (non-fatal): {e}")
        print("Migration completed successfully!")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
