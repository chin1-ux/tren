import os
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
env_path = r"c:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\.env"
load_dotenv(env_path)

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key)

mock_trends = [
    {
        "audio_title": "Espresso",
        "audio_artist": "Sabrina Carpenter",
        "platform": "instagram",
        "trend_type": "trend",
        "velocity_avg": 12.0,
        "reel_count": 25,
        "is_dance": False,
        "needs_filming": True,
        "edit_style": "slow_dissolve",
        "narrative_structure": "none",
        "text_overlay_template": None,
        "language": "en",
        "cultural_context": "everyday",
        "ideal_content_description": "Slow cinematic clips of morning coffee rituals, golden hour light through windows, hands stirring foam.",
        "camera_style": "handheld",
        "window_hours_remaining": 18,
        "confidence": 0.95,
        "status": "rising"
    },
    {
        "audio_title": "Aaj Ki Raat",
        "audio_artist": "Sachin-Jigar",
        "platform": "instagram",
        "trend_type": "mega_trend",
        "velocity_avg": 28.0,
        "reel_count": 140,
        "is_dance": True,
        "needs_filming": True,
        "edit_style": "fast_cuts",
        "narrative_structure": "transformation",
        "text_overlay_template": "POV: Aaj Ki Raat mood",
        "language": "hi",
        "cultural_context": "celebration",
        "ideal_content_description": "Group dance with the signature hook step at the chorus drop. Bright outfits, festive setting.",
        "camera_style": "wide_shot",
        "window_hours_remaining": 6,
        "confidence": 0.98,
        "status": "rising"
    },
    {
        "audio_title": "Beautiful Things",
        "audio_artist": "Benson Boone",
        "platform": "instagram",
        "trend_type": "trend",
        "velocity_avg": 8.0,
        "reel_count": 18,
        "is_dance": False,
        "needs_filming": True,
        "edit_style": "smooth_transition",
        "narrative_structure": "reveal",
        "text_overlay_template": None,
        "language": "en",
        "cultural_context": "everyday",
        "ideal_content_description": "Montage of travel moments — boarding passes, mountain peaks, candid laughter, sunsets over water.",
        "camera_style": "handheld",
        "window_hours_remaining": 36,
        "confidence": 0.92,
        "status": "rising"
    },
    {
        "audio_title": "Bachpan Ka Pyaar",
        "audio_artist": "Sahdev Dirdo",
        "platform": "instagram",
        "trend_type": "trend",
        "velocity_avg": 15.0,
        "reel_count": 42,
        "is_dance": True,
        "needs_filming": True,
        "edit_style": "zoom_pulse",
        "narrative_structure": "none",
        "text_overlay_template": "Nostalgia hits different...",
        "language": "kn",
        "cultural_context": "everyday",
        "ideal_content_description": "Solo dance with playful lip-sync, school-throwback aesthetic, simple footwork.",
        "camera_style": "selfie",
        "window_hours_remaining": 12,
        "confidence": 0.89,
        "status": "rising"
    },
    {
        "audio_title": "Paint The Town Red",
        "audio_artist": "Doja Cat",
        "platform": "instagram",
        "trend_type": "trend",
        "velocity_avg": 10.0,
        "reel_count": 30,
        "is_dance": False,
        "needs_filming": True,
        "edit_style": "color_flash",
        "narrative_structure": "transformation",
        "text_overlay_template": "Walk like you own the town",
        "language": "en",
        "cultural_context": "everyday",
        "ideal_content_description": "Outfit transitions in bold red looks, mirror flips, confident walk-toward-camera shots.",
        "camera_style": "static",
        "window_hours_remaining": 24,
        "confidence": 0.94,
        "status": "rising"
    },
    {
        "audio_title": "Cinnamon Girl",
        "audio_artist": "Lana Del Rey",
        "platform": "instagram",
        "trend_type": "trend",
        "velocity_avg": 6.0,
        "reel_count": 12,
        "is_dance": False,
        "needs_filming": True,
        "edit_style": "slow_dissolve",
        "narrative_structure": "none",
        "text_overlay_template": None,
        "language": "en",
        "cultural_context": "everyday",
        "ideal_content_description": "Warm, slow food shots — cinnamon dusting, dough kneading, steam rising from a fresh bake.",
        "camera_style": "close_up",
        "window_hours_remaining": 48,
        "confidence": 0.88,
        "status": "rising"
    },
    {
        "audio_title": "Tum Hi Ho",
        "audio_artist": "Arijit Singh",
        "platform": "instagram",
        "trend_type": "trend",
        "velocity_avg": 22.0,
        "reel_count": 89,
        "is_dance": False,
        "needs_filming": True,
        "edit_style": "slow_dissolve",
        "narrative_structure": "before_after",
        "text_overlay_template": "Then vs Now",
        "language": "hi",
        "cultural_context": "celebration",
        "ideal_content_description": "Emotional photo montage with text overlays — moments with loved ones, candid smiles, slow fades.",
        "camera_style": "static",
        "window_hours_remaining": 9,
        "confidence": 0.96,
        "status": "rising"
    }
]

print("Deleting old trends to clean up...")
# Clean existing mock/test data
res_del = supabase.table("trends").delete().neq("id", 0).execute()
print(f"Deleted existing trends.")

print("Inserting new trending songs...")
for trend in mock_trends:
    res = supabase.table("trends").insert(trend).execute()
    if res.data:
        print(f"Inserted: {trend['audio_title']} by {trend['audio_artist']}")

print("All done!")
