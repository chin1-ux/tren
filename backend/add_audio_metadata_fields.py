"""
Add audio metadata fields to the trends table for better old song detection and display differentiation.
This script adds fields to track release date, original popularity, and trend classification.
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        sys.exit(1)
    
    return create_client(supabase_url, supabase_key)

def add_audio_metadata_fields(supabase: Client):
    """Add new columns to the trends table for audio metadata"""
    print("=== Adding Audio Metadata Fields to Trends Table ===\n")
    
    # SQL statements to add new columns
    alter_statements = [
        # Audio release information
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS audio_release_date DATE;",
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS audio_original_release_year INTEGER;",
        
        # Trend classification for display differentiation
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS trend_classification TEXT DEFAULT 'new_viral';", 
        # Options: 'new_viral', 'viral_revival', 'evergreen_popular', 'classic_hit'
        
        # Velocity pattern analysis
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS velocity_pattern TEXT DEFAULT 'sudden_spike';",
        # Options: 'sudden_spike', 'gradual_growth', 'steady_popular', 'declining'
        
        # Additional metadata for enrichment
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS audio_genre TEXT;",
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS audio_label TEXT;",
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS is_evergreen BOOLEAN DEFAULT FALSE;",
        
        # Trend age tracking for UI display
        "ALTER TABLE trends ADD COLUMN IF NOT EXISTS trend_age_hours INTEGER DEFAULT 0;",
    ]
    
    try:
        # Execute each ALTER TABLE statement
        for statement in alter_statements:
            try:
                # Note: Supabase client doesn't support raw SQL directly through the client
                # We'll need to use the REST API or direct PostgreSQL connection
                print(f"Would execute: {statement}")
            except Exception as e:
                print(f"Error with statement: {e}")
        
        print("\n=== Manual SQL Required ===")
        print("The Supabase Python client doesn't support raw SQL ALTER TABLE statements.")
        print("Please execute the following SQL in your Supabase SQL Editor:\n")
        
        for statement in alter_statements:
            print(statement)
        
        print("\n=== After Adding Columns ===")
        print("Update the trend_engine.py to populate these fields during trend detection")
        print("Update the UI to display different badges based on trend_classification")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    supabase = load_environment()
    add_audio_metadata_fields(supabase)