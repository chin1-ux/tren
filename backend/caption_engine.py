import os
import json
import logging
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

try:
    logging.basicConfig(
        filename="caption_engine.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass
logger = logging.getLogger(__name__)
try:
    from .llm import call_llm
except ImportError:
    from llm import call_llm

try:
    from .llm import _collect_env_keys
except ImportError:
    from llm import _collect_env_keys


class CaptionEngine:
    """
    Generates AI-powered caption kits for trending audio using Gemini 2.5 Flash.
    Output includes 3 caption variants, 15 hashtags, audio cue, and posting strategy.
    Results are cached in the Supabase `trend_captions` table.
    """

    def __init__(self):
        load_dotenv()
        if not os.getenv("SUPABASE_URL"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            load_dotenv(os.path.join(script_dir, ".env"))

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        self.gemini_key = None

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials missing from .env")
        if not _collect_env_keys(("GROQ_API_KEY", "GEMINI_API_KEY", "LLM_API_KEY")):
            raise ValueError("No LLM API keys configured (GROQ_API_KEY*, GEMINI_API_KEY*, or LLM_API_KEY* must be set)")

        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def get_caption_kit(self, trend_id: int) -> dict:
        """
        Returns caption kit for a trend. Checks cache first, generates if not cached.
        """
        # 1. Check Supabase cache
        try:
            cached = self.supabase.table("trend_captions") \
                .select("*").eq("trend_id", trend_id).execute()
            if cached.data:
                logger.info(f"Caption kit cache hit for trend_id={trend_id}")
                return cached.data[0]["caption_data"]
        except Exception as e:
            logger.warning(f"Cache lookup failed for trend_id={trend_id}: {e}")

        # 2. Fetch trend data
        trend_res = self.supabase.table("trends").select("*").eq("id", trend_id).execute()
        if not trend_res.data:
            raise ValueError(f"Trend with id={trend_id} not found")
        trend = trend_res.data[0]

        # 3. Generate caption kit
        kit = self._generate_kit(trend)

        # 4. Save to cache
        try:
            self.supabase.table("trend_captions").upsert({
                "trend_id": trend_id,
                "caption_data": kit
            }, on_conflict="trend_id").execute()
        except Exception as e:
            logger.warning(f"Failed to cache caption kit for trend_id={trend_id}: {e}")

        return kit

    def _generate_kit(self, trend: dict) -> dict:
        """
        Calls Gemini to generate caption kit for the given trend dict.
        """
        audio_title = trend.get("audio_title", "Unknown")
        audio_artist = trend.get("audio_artist", "Unknown")
        language = trend.get("language", "en")
        content_type = trend.get("content_type", "trend")
        ideal_desc = trend.get("ideal_content_description", "")
        edit_style = trend.get("edit_style", "fast_cuts")
        is_dance = trend.get("is_dance", False)
        velocity_avg = trend.get("velocity_avg", 5.0)
        window_hours = trend.get("window_hours_remaining", 24)
        cultural_context = trend.get("cultural_context", "everyday")

        lang_instruction = {
            "hi": "Write captions in Hindi (Devanagari script) naturally mixed with English (Hinglish style).",
            "kn": "Write captions in Kannada naturally mixed with English.",
            "ta": "Write captions in Tamil naturally mixed with English.",
            "te": "Write captions in Telugu naturally mixed with English.",
            "bn": "Write captions in Bengali naturally mixed with English.",
            "mr": "Write captions in Marathi naturally mixed with English.",
        }.get(language, "Write captions in English.")

        prompt = f"""
You are a viral Instagram Reels content strategist for Indian creators.

Trend details:
- Audio: "{audio_title}" by {audio_artist}
- Language: {language} — {lang_instruction}
- Content type: {content_type}
- Is dance trend: {is_dance}
- Ideal content: {ideal_desc}
- Edit style: {edit_style}
- Cultural context: {cultural_context}
- Viral multiplier: {velocity_avg:.1f}x above normal
- Hours remaining in trend window: {window_hours}h

Generate a JSON caption kit with EXACTLY this structure (no markdown, raw JSON only):
{{
  "captions": [
    {{
      "vibe": "emotional",
      "text": "Full caption with emojis, 2-3 lines, hooks in the first line. Include a question or CTA at the end."
    }},
    {{
      "vibe": "funny",
      "text": "Funny/relatable version. Use desi humor, trending Indian slang if appropriate."
    }},
    {{
      "vibe": "aspirational",
      "text": "Inspirational/aspirational version. Motivational tone, dream-chasing energy."
    }}
  ],
  "hashtags": [
    5 broad trending hashtags,
    5 niche content-specific hashtags,
    5 language/regional hashtags relevant to the creator's audience
  ],
  "audio_cue": "Describe which specific moment in the song to start filming, e.g. 'Start at the 0:08 beat drop' or 'Begin filming from the first chorus'",
  "posting_strategy": {{
    "best_hour_ist": 20,
    "best_days": ["saturday", "sunday"],
    "platform_first": "instagram",
    "reasoning": "One sentence explaining why this timing maximizes reach for this trend type"
  }},
  "saturation_alert": "One line warning like 'Post in the next 6 hours — this trend peaks tomorrow morning' or 'You have 2 full days — take your time'",
  "keyword_strategy": {{
    "target_keywords": ["5-10 highly relevant niche and broad keywords for this trend"],
    "placement_guide": {{
      "spoken_audio": "Instruction on how to say these keywords in the voiceover naturally",
      "on_screen_text": "Instruction on which keyword to show on-screen in the first 3 seconds (scroll-stopper)",
      "caption": "How to weave these keywords into the caption first line naturally",
      "alt_text": "Detailed keyword-optimized alt-text for the reel details"
    }}
  }},
  "viral_pattern_script": {{
    "title": "Viral Pattern 30-Second Script Flow",
    "hook_style": "Specify one of Pain, Curiosity, Authority, Contrarian",
    "timeline": {{
      "0_3s_hook": "Scroll-stopper hook sentence using primary target keyword",
      "3_7s_promise": "Promise expansion / why this matters to the viewer",
      "7_20s_body": "Context + micro-story details containing secondary keywords",
      "20_25s_takeaway": "Specific high-value giveaway or action to save",
      "25_30s_loop_cta": "Actionable single-choice call to action with seamless loop transition back to the start"
    }}
  }}
}}
"""

        system_instruction = "You are a viral content strategist. Return ONLY valid JSON. No markdown. No code blocks."
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                kit = call_llm(system_instruction, prompt, timeout=30)
                logger.info(f"Caption kit generated for '{audio_title}'")
                return kit
            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    time.sleep(attempt * 3)

        # Fallback kit if Gemini fails
        logger.error(f"All attempts failed for caption kit of '{audio_title}'. Returning fallback.")
        return {
            "captions": [
                {"vibe": "emotional", "text": f"This song hits different 🎵✨ '{audio_title}' — save this for later 🙏"},
                {"vibe": "funny", "text": f"Me scrolling at 2AM and hearing '{audio_title}' 😭💀 #relatable"},
                {"vibe": "aspirational", "text": f"Every journey starts with a single step 🚀 Trending: '{audio_title}' 🔥"}
            ],
            "hashtags": ["#reels", "#trending", "#viral", "#instareels", "#fyp",
                         "#reelsindia", "#indiancreator", "#trendingreels",
                         "#viralreels", "#explore",
                         "#reelsviral", "#reelitfeelit", "#instagood", "#explorepage", "#trending2025"],
            "audio_cue": "Start filming from the first chorus for maximum impact",
            "posting_strategy": {
                "best_hour_ist": 20,
                "best_days": ["saturday", "sunday"],
                "platform_first": "instagram",
                "reasoning": "Evening hours (7-9 PM IST) typically see peak Indian Instagram engagement"
            },
            "saturation_alert": f"This trend has {window_hours}h remaining — post soon for best results",
            "keyword_strategy": {
                "target_keywords": [audio_title.lower(), "instagram reels", "trending audio", "content creator tips"],
                "placement_guide": {
                    "spoken_audio": f"Say '{audio_title}' in the first 3 seconds of the audio.",
                    "on_screen_text": "Put 'Listen to this trending audio' on screen.",
                    "caption": f"Use the trend name '{audio_title}' in the first sentence.",
                    "alt_text": f"Trending audio '{audio_title}' by {audio_artist} playing over a high retention reel."
                }
            },
            "viral_pattern_script": {
                "title": "Viral Pattern 30-Second Script Flow",
                "hook_style": "Curiosity",
                "timeline": {
                    "0_3s_hook": f"You won't believe what happens when you use '{audio_title}'...",
                    "3_7s_promise": "This new audio is blowing up accounts worldwide.",
                    "7_20s_body": "Creators are posting simple clips and getting 10x reach because of retention loops.",
                    "20_25s_takeaway": "Save this trend and post in the next 12 hours.",
                    "25_30s_loop_cta": "Click follow for the next early trend alert!"
                }
            }
        }


if __name__ == "__main__":
    import json
    import sys
    engine = CaptionEngine()
    # Test with trend_id=1 (adjust as needed)
    kit = engine.get_caption_kit(1)
    
    # Avoid console encoding issues on Windows
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(kit, indent=2, ensure_ascii=False))
