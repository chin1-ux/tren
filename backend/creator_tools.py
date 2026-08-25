import os
import json
import random
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

try:
    from llm import call_llm
except ImportError:
    try:
        from backend.llm import call_llm
    except ImportError:
        from .llm import call_llm

try:
    from .llm import _collect_env_keys
except ImportError:
    from llm import _collect_env_keys

try:
    logging.basicConfig(
        filename="creator_tools.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass
logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
except Exception as e:
    logger.warning(f"Supabase library import failed in creator_tools: {e}")
    create_client = None
    Client = None




class CreatorTools:
    def __init__(self):
        load_dotenv()
        if not os.getenv("SUPABASE_URL"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            load_dotenv(os.path.join(script_dir, ".env"))

        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        # Remove Gemini key; rely on Groq or generic LLM API keys
        self.gemini_key = None

        if not _collect_env_keys(("GROQ_API_KEY", "GEMINI_API_KEY", "LLM_API_KEY")):
            logger.warning("No LLM API keys configured (GROQ_API_KEY*, GEMINI_API_KEY*, or LLM_API_KEY* must be set). LLM features disabled.")
            self.gemini_key = None


        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials missing; Supabase-dependent features disabled.")
            self.supabase = None
        else:
            try:
                self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                logger.warning(f"Failed to create Supabase client: {e}. Supabase-dependent features disabled.")
                self.supabase = None

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> dict:
        """Helper to invoke LLM API and return a JSON dictionary."""
        try:
            try:
                from llm import call_llm
            except ImportError:
                try:
                    from backend.llm import call_llm
                except ImportError:
                    from .llm import call_llm
            result = call_llm(system_prompt, user_prompt, timeout=30)
            if not result:
                logger.warning("LLM returned empty result")
            return result
        except Exception as e:
            logger.error(f"LLM prompt invocation failed: {e}", exc_info=True)
            return {}

    def get_pre_post_score(self, niche: str, hook: str, audio_title: str, caption: str, hashtags: list, post_time: str) -> dict:
        """
        Evaluate a draft social media post and provide a 0-100 score + actionable fixes.
        """
        system_prompt = "You are a professional social media audit agent. Score the post out of 100 and provide constructive criticism to optimize engagement."
        user_prompt = f"""
Analyze this draft post for an Instagram Reel / YouTube Short:
Niche: {niche}
Hook text: {hook}
Audio being used: {audio_title}
Caption: {caption}
Hashtags: {", ".join(hashtags)}
Scheduled Time: {post_time}

Evaluate the following categories:
1. Hook Strength & Type (First 3 seconds scroll-stopper. Does it fit Pain, Curiosity, Authority, or Contrarian archetypes?)
2. Keyword Alignment & SEO (Are keywords aligned across the hook, on-screen text, and caption to build clear category signals?)
3. Retention & Viral Structure (Does it design for watch time and shares? Is there a loop/replay trigger? Is there only one single CTA?)
4. Hashtag Quality & Selection (Mix of broad, niche, regional)
5. Timing (Based on Indian audience peaks)

Return ONLY a JSON response in the following format:
{{
  "overall_score": 85,
  "breakdown": {{
    "hook_strength": 80,
    "audio_match": 90,
    "seo_and_caption": 85,
    "hashtags": 75,
    "timing": 95
  }},
  "fixes": [
    "Identify as a Contrarian Hook: Challenge expectations to hook users immediately.",
    "Keyword strategy fix: Place your primary target keyword in the first 3 seconds of spoken audio and on-screen text.",
    "Simplify your CTA: Keep it to one action (e.g. Save) to boost completion rate."
  ],
  "estimated_reach_multiplier": "1.5x"
}}
"""
        result = self._call_gemini(system_prompt, user_prompt)
        if not result:
            # Fallback — LLM call failed, returning estimated defaults.
            # is_simulated: True so the frontend can show a clear warning.
            result = {
                "overall_score": 75,
                "breakdown": {"hook_strength": 70, "audio_match": 80, "seo_and_caption": 70, "hashtags": 80, "timing": 80},
                "fixes": [
                    "Keep the first 3 seconds extremely fast-paced to hold attention.",
                    "Optimize the caption with 5-10 targeted keywords for search indexing.",
                    "Align your voiceover and on-screen text with the same primary keyword."
                ],
                "estimated_reach_multiplier": "1.2x",
                "is_simulated": True
            }
        else:
            # LLM returned real analysis — mark as real
            if isinstance(result, dict):
                result.setdefault("is_simulated", False)
        return result

    def generate_hooks(self, niche: str, topic: str) -> dict:
        """
        Generate high-performing, viral hooks based on the niche and target topic.
        """
        system_prompt = "You are an expert copywriter specializing in viral hooks for Instagram Reels, YouTube Shorts, and TikTok."
        user_prompt = f"""
Generate 5 high-converting, scroll-stopping hooks for:
Niche: {niche}
Topic: {topic}

Provide different styles strictly matching the playbook:
- Pain Hook (problem recognition / pain relief)
- Curiosity Hook (creates a knowledge gap)
- Authority Hook (signals quick credibility / stats / claims)
- Contrarian Hook (challenges expectation / surprise)
- Relatability Hook (shared truth)

Also explain why each works, and provide the primary keywords to display on screen.

Return ONLY a JSON response in the following format:
{{
  "hooks": [
    {{
      "style": "Pain Hook",
      "text": "The hook text...",
      "why_it_works": "Why it works...",
      "on_screen_keyword": "Target keyword for screen"
    }}
  ]
}}
"""
        result = self._call_gemini(system_prompt, user_prompt)
        if not result:
            result = {
                "hooks": [
                    {"style": "Pain Hook", "text": f"Stop failing at {topic} because of this one mistake...", "why_it_works": "Direct problem recognition", "on_screen_keyword": topic},
                    {"style": "Curiosity Hook", "text": f"The hidden secret to mastering {topic} in 24 hours...", "why_it_works": "Creates a knowledge gap", "on_screen_keyword": f"Secret {topic}"},
                    {"style": "Authority Hook", "text": f"How I got 71.4K followers using this exact {topic} strategy...", "why_it_works": "Builds instant trust with proof", "on_screen_keyword": f"{topic} strategy"},
                    {"style": "Contrarian Hook", "text": f"Everything you've heard about {topic} is completely wrong...", "why_it_works": "Challenges consensus to stop scrolling", "on_screen_keyword": f"{topic} lies"}
                ]
            }
        return result

    def generate_seo_caption(self, description: str, platform: str = "instagram") -> dict:
        """
        Generate SEO-optimized captions.
        """
        system_prompt = "You are an SEO specialist and social media copywriter. Write captions optimized for search engines (Google & in-app search)."
        user_prompt = f"""
Create an SEO-optimized caption for a {platform} post about: {description}.
Include:
1. A hook-focused opening line placing the primary keyword in the first sentence naturally.
2. A keyword-rich middle section containing a natural bulleted list of 5-10 search keywords.
3. Natural, highly targeted hashtags.
4. Suggested Alt Text for the video/image.

Return ONLY a JSON response in the following format:
{{
  "caption": "The full generated caption text goes here...",
  "keywords_targeted": ["keyword1", "keyword2"],
  "alt_text": "Detailed descriptive alt text for accessibility and search indexing",
  "hashtag_strategy": "Explain the hashtag selection strategy."
}}
"""
        result = self._call_gemini(system_prompt, user_prompt)
        if not result:
            result = {
                "caption": f"💡 Here is a quick guide on {description}. Learn how to make the most of it today! #tips #guide",
                "keywords_targeted": [description],
                "alt_text": f"A clean, professional presentation on {description}",
                "hashtag_strategy": "Broad and specific niche tags combined."
            }
        return result

    def get_daily_ideas(self, user_email: str) -> list:
        """
        Generates 3 personalized, trend-backed ideas for a user based on their registered niche.
        """
        # Fetch user details
        if not self.supabase:
            logger.warning("Supabase client not configured; returning empty daily ideas.")
            return []
        user_res = self.supabase.table("users").select("niche, language_preference").eq("email", user_email).execute()
        if not user_res.data:
            niche = "lifestyle"
            lang = "en"
        else:
            niche = user_res.data[0].get("niche", "lifestyle")
            lang = user_res.data[0].get("language_preference", "en")

        # Fetch recent trends in this language/niche to contextualize
        trends_res = self.supabase.table("trends").select("*").eq("language", lang).order("velocity_avg", desc=True).limit(3).execute()
        trends_context = ""
        if trends_res.data:
            trends_context = "Current active trends: " + ", ".join([f"'{t['audio_title']}' ({t['content_type']})" for t in trends_res.data])

        system_prompt = "You are a creative director for a top creator agency. Pitch highly viral, actionable video ideas."
        user_prompt = f"""
Generate 3 highly personalized, specific video ideas for a creator in the '{niche}' niche speaking in '{lang}'.
{trends_context}

For each idea, provide:
1. Title/Concept
2. The specific hook to use (visual & verbal)
3. Step-by-step description of what to record/do
4. Best audio suggestion (incorporate some of the active trends if applicable)
5. Best time to post

Return ONLY a JSON response in the following format:
{{
  "ideas": [
    {{
      "title": "Concept Title",
      "description": "What to do in this video",
      "hook": "Wait till the end to see...",
      "audio_suggestion": "Audio name or type",
      "posting_time": "7:00 PM"
    }}
  ]
}}
"""
        result = self._call_gemini(system_prompt, user_prompt)
        if isinstance(result, dict) and "ideas" in result:
            result = result["ideas"]

        if not isinstance(result, list):
            result = [
                {"title": f"The Ultimate {niche} Hack", "description": "Show a 15-second hack of something in your niche.", "hook": "Stop doing it the hard way!", "audio_suggestion": "Upbeat trending pop", "posting_time": "6:30 PM"},
                {"title": "Day in the Life of a Creator", "description": "B-roll of your daily routine with text overlay.", "hook": "What my typical day actually looks like...", "audio_suggestion": "Chill Lofi", "posting_time": "8:00 PM"},
                {"title": "My Biggest Mistake in " + niche, "description": "Share a relatable mistake and how you solved it.", "hook": "Don't make this mistake I made...", "audio_suggestion": "Dramatic build-up", "posting_time": "7:15 PM"}
            ]
        return result

    def generate_calendar(self, user_email: str, niche: str, language: str, frequency: str) -> dict:
        """
        Generate a full 30-day posting calendar packed with trend-aligned post concepts.
        """
        system_prompt = "You are a master content manager. Build a comprehensive, highly detailed 30-day social media calendar."
        user_prompt = f"""
Create a 30-day content calendar for a creator with the following:
Niche: {niche}
Language: {language}
Frequency: {frequency} (e.g., '1 post per day', '3 posts per week')

For each active day, provide:
- Day Number (1-30)
- Topic / Concept
- Hook text
- Audio/Music Style
- Hashtags
- Recommended posting time

Return ONLY a JSON object with a single key "calendar" containing an array of day objects:
{{
  "calendar": [
    {{
      "day": 1,
      "topic": "Introduction / hook",
      "hook": "Here is why you need to...",
      "audio_style": "Upbeat synth",
      "hashtags": ["#intro", "#niche"],
      "posting_time": "6:00 PM"
    }}
  ]
}}
"""
        result = self._call_gemini(system_prompt, user_prompt)
        if not result or "calendar" not in result:
            # Fallback
            result = {
                "calendar": [
                    {"day": i, "topic": f"Day {i} challenge/tip", "hook": f"Here is tip #{i}...", "audio_style": "Trending audio", "hashtags": [f"#{niche}"], "posting_time": "6:00 PM"}
                    for i in range(1, 31)
                ]
            }
        return result

    def run_flop_diagnostics(self, user_email: str) -> dict:
        """Run diagnostics on synced creator posts to detect flops and suggest remedies using current active trends."""
        if not self.supabase:
            return {"status": "error", "message": "Supabase client not initialized"}
        
        try:
            # Fetch last 30 posts for user
            posts_res = self.supabase.table("creator_posts").select("*").eq("user_email", user_email).order("timestamp", desc=True).limit(30).execute()
            posts = posts_res.data or []
            if not posts:
                return {"status": "no_data", "message": "No synced posts found. Make sure Instagram OAuth is connected."}
            
            # Calculate baseline averages
            total_plays = sum(p.get("plays_count", 0) for p in posts)
            avg_plays = total_plays / len(posts)
            
            flops = []
            for post in posts:
                plays = post.get("plays_count", 0)
                if plays > 0 and plays < (avg_plays * 0.5):
                    # Flag as flop if plays are less than 50% of the baseline average
                    flops.append({
                        "media_id": post.get("media_id"),
                        "permalink": post.get("permalink"),
                        "caption": post.get("caption"),
                        "plays_count": plays,
                        "engagement": post.get("like_count", 0) + post.get("comments_count", 0)
                    })
            
            # Match top 3 flops against trending audio
            trends_res = self.supabase.table("trends").select("*").order("velocity_avg", desc=True).limit(3).execute()
            trends = trends_res.data or []
            
            diagnostics = {
                "baseline_avg_plays": round(avg_plays, 1),
                "total_posts_analyzed": len(posts),
                "flops_detected": len(flops),
                "flops": flops[:3],
                "suggested_remedy_tracks": [
                    {
                        "audio_title": t.get("audio_title"),
                        "audio_artist": t.get("audio_artist"),
                        "why_this_works": t.get("why_this_works"),
                        "transfer_instructions": t.get("transfer_instructions")
                    } for t in trends
                ]
            }
            return {"status": "success", "data": diagnostics}
        except Exception as e:
            err_str = str(e)
            # Table doesn't exist yet (PGRST205) — return no_data instead of 500
            if "PGRST205" in err_str or "Could not find" in err_str:
                logger.warning(f"creator_posts table missing — migration pending: {e}")
                return {"status": "no_data", "message": "Creator analytics table is being set up. Please connect your Instagram account first."}
            logger.error(f"Error in run_flop_diagnostics: {e}")
            return {"status": "error", "message": err_str}

    def run_niche_health_audit(self, user_email: str) -> dict:
        """Analyze category focus and semantic consistency across creator's historical posts."""
        if not self.supabase:
            return {"status": "error", "message": "Supabase client not initialized"}
        
        try:
            posts_res = self.supabase.table("creator_posts").select("caption").eq("user_email", user_email).limit(15).execute()
            captions = [p.get("caption") or "" for p in (posts_res.data or []) if p.get("caption")]
            
            if not captions:
                return {"status": "no_data", "message": "Insufficient caption data to determine niche profile."}
            
            sample_text = " | ".join(captions[:10])
            system_prompt = "You are a professional creator niche audit specialist. Evaluate category consistency."
            user_prompt = f"""
            Analyze these recent post captions from a single creator account:
            {sample_text}
            
            Determine:
            1. What is the primary niche?
            2. Are there secondary niches causing category dilution?
            3. On a scale of 0.0 to 1.0, what is the Niche Health Score? (1.0 = completely consistent topic focus, 0.2 = scattered content/confused algorithm).
            
            Return ONLY a valid JSON response in this format:
            {{
              "primary_niche": "fitness",
              "secondary_niches": ["travel", "personal finance"],
              "niche_health_score": 0.65,
              "alignment_drift_detected": true,
              "recommendations": [
                "Focus purely on workout routines for the next 4 posts",
                "Remove unrelated travel highlights from your grid to stop algorithm confusion"
              ]
            }}
            """
            
            audit_result = self._call_gemini(system_prompt, user_prompt)
            if not audit_result:
                audit_result = {
                    "primary_niche": "general",
                    "secondary_niches": [],
                    "niche_health_score": 0.8,
                    "alignment_drift_detected": False,
                    "recommendations": ["Keep focus on consistent thematic styling."]
                }
                
            # Persist profile (skip if niche_profiles table also missing)
            try:
                profile = {
                    "user_email": user_email,
                    "primary_niche": audit_result.get("primary_niche"),
                    "secondary_niches": audit_result.get("secondary_niches"),
                    "niche_health_score": audit_result.get("niche_health_score"),
                    "alignment_drift_detected": audit_result.get("alignment_drift_detected"),
                    "recommendations": audit_result.get("recommendations"),
                    "updated_at": datetime.now().isoformat()
                }
                self.supabase.table("creator_niche_profiles").upsert(profile, on_conflict="user_email").execute()
            except Exception as persist_err:
                logger.warning(f"Could not persist niche profile (table may be missing): {persist_err}")
            
            return {"status": "success", "data": audit_result}
        except Exception as e:
            err_str = str(e)
            # Table doesn't exist yet (PGRST205) — return no_data instead of 500
            if "PGRST205" in err_str or "Could not find" in err_str:
                logger.warning(f"creator_posts table missing — migration pending: {e}")
                return {"status": "no_data", "message": "Creator analytics table is being set up. Please connect your Instagram account first."}
            logger.error(f"Error in run_niche_health_audit: {e}")
            return {"status": "error", "message": err_str}
