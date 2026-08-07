#!/usr/bin/env python3
"""
Migration script for early trend detection system
Creates the database tables needed for early signal detection
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv('SUPABASE_DB_URL')

if not db_url:
    raise RuntimeError('SUPABASE_DB_URL not set')

conn = psycopg2.connect(db_url)
conn.autocommit = True
cursor = conn.cursor()

print("Creating early trend detection tables...")

# 1. Create early_signals table
print("Creating early_signals table...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS early_signals (
        id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        signal_type VARCHAR(50) NOT NULL,
        reel_id VARCHAR(50) NOT NULL,
        audio_id VARCHAR(100),
        audio_title VARCHAR(500),
        signal_strength FLOAT NOT NULL,
        detection_tier VARCHAR(20) NOT NULL,
        creator_tier VARCHAR(20),
        creator_baseline_data JSONB,
        signal_data JSONB NOT NULL,
        geographic_spread JSONB,
        predicted_viral_probability FLOAT,
        confidence_score FLOAT,
        detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        validated_at TIMESTAMP WITH TIME ZONE,
        validation_result VARCHAR(50),
        trend_id BIGINT REFERENCES trends(id)
    );
""")

# 2. Create creator_baselines table
print("Creating creator_baselines table...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS creator_baselines (
        id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        username VARCHAR(100) UNIQUE NOT NULL,
        follower_count INTEGER,
        avg_engagement FLOAT,
        avg_velocity FLOAT,
        content_frequency FLOAT,
        niche_tendencies JSONB,
        creator_tier VARCHAR(20),
        baseline_period_start TIMESTAMP WITH TIME ZONE,
        baseline_period_end TIMESTAMP WITH TIME ZONE,
        last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
""")

# 3. Create audio_adoption_timeline table
print("Creating audio_adoption_timeline table...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS audio_adoption_timeline (
        id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        audio_id VARCHAR(100),
        audio_title VARCHAR(500),
        use_count INTEGER NOT NULL,
        unique_creators INTEGER NOT NULL,
        creator_tier_distribution JSONB,
        geographic_distribution JSONB,
        hour_bucket TIMESTAMP WITH TIME ZONE NOT NULL,
        acceleration_rate FLOAT,
        recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
""")

# 4. Create hashtag_performance table
print("Creating hashtag_performance table...")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS hashtag_performance (
        id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
        hashtag VARCHAR(100) UNIQUE NOT NULL,
        pool_name VARCHAR(50),
        avg_velocity FLOAT,
        early_signal_count INTEGER,
        viral_conversion_rate FLOAT,
        micro_creator_ratio FLOAT,
        geographic_diversity_score FLOAT,
        performance_score FLOAT,
        last_evaluated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        added_to_pool_at TIMESTAMP WITH TIME ZONE,
        status VARCHAR(20)
    );
""")

# 5. Add indexes for performance
print("Adding indexes...")
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_early_signals_audio_id ON early_signals(audio_id);
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_early_signals_detection_tier ON early_signals(detection_tier);
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_early_signals_detected_at ON early_signals(detected_at);
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_early_signals_strength ON early_signals(signal_strength);
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_creator_baselines_username ON creator_baselines(username);
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_audio_adoption_audio_id ON audio_adoption_timeline(audio_id);
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_audio_adoption_hour_bucket ON audio_adoption_timeline(hour_bucket);
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_hashtag_performance_hashtag ON hashtag_performance(hashtag);
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_hashtag_performance_status ON hashtag_performance(status);
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_hashtag_performance_score ON hashtag_performance(performance_score);
""")

# 6. Enable RLS on new tables
print("Enabling Row Level Security...")
cursor.execute("""
    ALTER TABLE early_signals ENABLE ROW LEVEL SECURITY;
""")

cursor.execute("""
    ALTER TABLE creator_baselines ENABLE ROW LEVEL SECURITY;
""")

cursor.execute("""
    ALTER TABLE audio_adoption_timeline ENABLE ROW LEVEL SECURITY;
""")

cursor.execute("""
    ALTER TABLE hashtag_performance ENABLE ROW LEVEL SECURITY;
""")

print("[PASS] Early trend detection database schema created successfully!")

cursor.close()
conn.close()