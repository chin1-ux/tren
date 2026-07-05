import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logging.basicConfig(
    filename="create_instagram_tokens_table.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

def create_instagram_tokens_table():
    """
    Create the instagram_tokens table to store Instagram OAuth tokens.
    """
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
    
    -- Enable RLS
    ALTER TABLE instagram_tokens ENABLE ROW LEVEL SECURITY;
    
    -- Policy: Users can only see their own tokens
    CREATE POLICY "Users can view own Instagram tokens"
        ON instagram_tokens FOR SELECT
        USING (user_email = auth.jwt() ->> 'email');
    
    -- Policy: Users can insert their own tokens
    CREATE POLICY "Users can insert own Instagram tokens"
        ON instagram_tokens FOR INSERT
        WITH CHECK (user_email = auth.jwt() ->> 'email');
    
    -- Policy: Users can update their own tokens
    CREATE POLICY "Users can update own Instagram tokens"
        ON instagram_tokens FOR UPDATE
        USING (user_email = auth.jwt() ->> 'email');
    
    -- Policy: Users can delete their own tokens
    CREATE POLICY "Users can delete own Instagram tokens"
        ON instagram_tokens FOR DELETE
        USING (user_email = auth.jwt() ->> 'email');
    
    -- Index for faster lookups
    CREATE INDEX IF NOT EXISTS idx_instagram_tokens_user_email ON instagram_tokens(user_email);
    """
    
    try:
        # Execute the SQL directly via Supabase client
        # Note: Supabase Python client doesn't support raw SQL execution directly
        # We need to use the REST API or execute via a different method
        # For now, we'll log the SQL and instruct the user to run it manually
        
        logger.info("Instagram tokens table SQL generated. Please execute the following SQL in your Supabase SQL Editor:")
        logger.info(create_table_sql)
        
        print("=" * 80)
        print("Instagram Tokens Table SQL")
        print("=" * 80)
        print(create_table_sql)
        print("=" * 80)
        print("\nPlease copy and execute the above SQL in your Supabase SQL Editor.")
        print("\nThis will create the instagram_tokens table with RLS policies enabled.")
        
    except Exception as e:
        logger.error(f"Failed to create instagram_tokens table: {e}")
        raise

if __name__ == "__main__":
    create_instagram_tokens_table()
