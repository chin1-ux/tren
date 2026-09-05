import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# Insert a mock content trend
mock_trend = {
    "trend_type": "format",
    "trend_name": "POV Gym Format",
    "template_pattern": "pov_format",
    "topic_keywords": ["gym", "workout", "pov"],
    "reel_count": 15,
    "velocity_avg": 2.5,
    "confidence": 0.85,
    "status": "emerging",
    "window_hours_remaining": 22.0
}

res = supabase.table("content_trends").upsert(mock_trend, on_conflict="trend_type,template_pattern").execute()
print(f"Inserted mock trend: {res.data}")
