import os
import sys
import psycopg2
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env
load_dotenv()

# Supabase REST client configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# PostgreSQL Direct Connection configuration
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

# SQL queries to create the requested tables
TABLES_SQL = {
    "reels": """
        CREATE TABLE IF NOT EXISTS reels (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            platform text,
            reel_id text UNIQUE,
            view_count int,
            like_count int,
            comment_count int,
            share_count int,
            posted_at timestamp,
            owner_username text,
            owner_follower_count int,
            audio_title text,
            audio_artist text,
            hashtags text[],
            caption text,
            velocity_score float,
            content_type text,
            is_dance boolean,
            language text,
            video_url text,
            thumbnail_url text,
            created_at timestamp DEFAULT now()
        );
    """,
    "trends": """
        CREATE TABLE IF NOT EXISTS trends (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            audio_title text,
            audio_artist text,
            platform text,
            trend_type text,
            velocity_avg float,
            reel_count int,
            is_dance boolean,
            needs_filming boolean,
            edit_style text,
            narrative_structure text,
            text_overlay_template text,
            language text,
            cultural_context text,
            ideal_content_description text,
            camera_style text,
            window_hours_remaining int,
            confidence float,
            status text DEFAULT 'rising',
            first_detected_at timestamp DEFAULT now()
        );
    """,
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            email text UNIQUE,
            niche text,
            language_preference text,
            plan text DEFAULT 'free',
            push_token text,
            created_at timestamp DEFAULT now()
        );
    """,
    "jobs": """
        CREATE TABLE IF NOT EXISTS jobs (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            job_type text,
            status text DEFAULT 'pending',
            user_email text,
            progress int DEFAULT 0,
            input_data text,
            output_url text,
            error_message text,
            created_at timestamp DEFAULT now()
        );
    """,
    "youtube_shorts": """
        CREATE TABLE IF NOT EXISTS youtube_shorts (
            id bigint PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            video_id text UNIQUE,
            title text,
            channel_title text,
            channel_id text,
            view_count int,
            like_count int,
            comment_count int,
            published_at timestamp,
            tags text[],
            velocity_score float,
            region_code text,
            language text,
            created_at timestamp DEFAULT now()
        );
    """
}

def main():
    print("Connecting to Supabase...")
    
    # 1. Initialize Supabase python client
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Warning: SUPABASE_URL or SUPABASE_KEY is missing from environment variables.")
    else:
        try:
            # Check initialization
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("Successfully initialized Supabase Python client.")
        except Exception as e:
            print(f"Warning: Failed to initialize Supabase client: {e}")

    # 2. Check Database URL and execute DDL queries via direct PostgreSQL connection
    if not SUPABASE_DB_URL:
        print("Error: SUPABASE_DB_URL is missing from environment variables.")
        print("Please configure your .env file with the correct PostgreSQL connection string.")
        sys.exit(1)

    conn = None
    cursor = None
    all_success = True

    try:
        # Connect to Supabase Postgres database directly
        conn = psycopg2.connect(SUPABASE_DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()
        print("Successfully connected to Supabase PostgreSQL database.")
    except Exception as e:
        print(f"Database connection error: {e}")
        print("Please check your SUPABASE_DB_URL in the .env file.")
        sys.exit(1)

    # 3. Create tables one by one with individual error handling
    for table_name, sql_query in TABLES_SQL.items():
        try:
            print(f"Creating table '{table_name}'...")
            cursor.execute(sql_query)
            print(f"Table '{table_name}' checked/created successfully.")
        except Exception as e:
            print(f"Error creating table '{table_name}': {e}")
            all_success = False

    # Clean up connections
    if cursor:
        cursor.close()
    if conn:
        conn.close()

    if all_success:
        print("All tables created successfully")
    else:
        print("Some tables failed to create. Please check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
