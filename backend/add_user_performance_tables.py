"""
Add User Performance Tables to Supabase
Creates tables for tracking real user performance data
Phase 4: Real Data Integration
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=== Adding User Performance Tables ===")

# SQL to create tables
sql_statements = [
    # User performance table
    """
    CREATE TABLE IF NOT EXISTS user_performance (
        id BIGSERIAL PRIMARY KEY,
        user_email TEXT NOT NULL,
        instagram_id TEXT,
        username TEXT,
        followers_count INTEGER DEFAULT 0,
        following_count INTEGER DEFAULT 0,
        media_count INTEGER DEFAULT 0,
        biography TEXT,
        profile_picture_url TEXT,
        last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(user_email)
    );
    """,
    
    # User insights table
    """
    CREATE TABLE IF NOT EXISTS user_insights (
        id BIGSERIAL PRIMARY KEY,
        user_email TEXT NOT NULL,
        metric_name TEXT NOT NULL,
        metric_value NUMERIC,
        recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    
    # User media performance table
    """
    CREATE TABLE IF NOT EXISTS user_media_performance (
        id BIGSERIAL PRIMARY KEY,
        user_email TEXT NOT NULL,
        media_id TEXT UNIQUE,
        media_type TEXT,
        caption TEXT,
        like_count INTEGER DEFAULT 0,
        comments_count INTEGER DEFAULT 0,
        timestamp TIMESTAMP WITH TIME ZONE,
        permalink TEXT,
        recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    
    # Real-time trends table
    """
    CREATE TABLE IF NOT EXISTS realtime_trends (
        id BIGSERIAL PRIMARY KEY,
        platform TEXT NOT NULL,
        title TEXT NOT NULL,
        source TEXT,
        view_count INTEGER DEFAULT 0,
        like_count INTEGER DEFAULT 0,
        trend_score NUMERIC DEFAULT 0,
        type TEXT,
        published_at TIMESTAMP WITH TIME ZONE,
        detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    
    # Trending hashtags table
    """
    CREATE TABLE IF NOT EXISTS trending_hashtags (
        id BIGSERIAL PRIMARY KEY,
        hashtag TEXT NOT NULL,
        trend_score NUMERIC DEFAULT 0,
        source_platform TEXT,
        detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(hashtag, detected_at)
    );
    """,
    
    # Trending audio tracks table
    """
    CREATE TABLE IF NOT EXISTS trending_audio (
        id BIGSERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        artist TEXT,
        view_count INTEGER DEFAULT 0,
        trend_score NUMERIC DEFAULT 0,
        source TEXT,
        detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
]

print("\n=== SQL Statements for Manual Execution ===")
print("\nPlease run these SQL statements in Supabase SQL Editor:")

for i, sql in enumerate(sql_statements, 1):
    print(f"\n-- Table {i}")
    print(sql)

print("\n=== User Performance Tables Setup Complete ===")