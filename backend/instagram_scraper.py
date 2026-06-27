import os
import re
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from apify_client import ApifyClient
from supabase import create_client, Client
from llm import call_llm

logging.basicConfig(
    filename="instagram_scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


class InstagramScraper:
    def __init__(self):
        load_dotenv()
        if not os.getenv("APIFY_API_TOKEN"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            load_dotenv(os.path.join(script_dir, ".env"))

        self.apify_token = os.getenv("APIFY_API_TOKEN")
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")

        if not self.apify_token:
            raise ValueError("APIFY_API_TOKEN missing from .env")
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials missing from .env")

        # Support multiple comma-separated tokens for rotation
        tokens = [t.strip() for t in self.apify_token.split(",") if t.strip()]
        self.apify_clients = [ApifyClient(t) for t in tokens]
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

        # India-focused hashtag groups — heavily weighted toward regional
        self.hashtag_groups = {
            "INDIA_TRENDING": [
                "trending", "reels", "viral", "fyp", "explore",
                "instareels", "reelsviral", "trendingreels", "reelsindia"
            ],
            "INDIAN_REGIONAL": [
                # Kannada
                "kannadareels", "kannada", "karnataka", "kannadiga",
                # Hindi
                "hindireels", "bollywood", "hindimusic", "hindustani",
                # Tamil
                "tamilreels", "kollywood", "tamilsong",
                # Telugu
                "telugureels", "tollywood", "telugusongs",
                # Bengali / Marathi / Punjabi
                "bengalireels", "marathireels", "punjabireel",
            ],
            "NICHE_CONTENT": [
                "glowup", "transformation", "beforeafter",
                "fashionreels", "foodreels", "travelreels",
                "motivationreels", "devotional", "festivalreels",
                "comedyreels", "studyreels", "fitnessreels",
                "dancecover", "lipsync", "aestheticreels"
            ]
        }

    def _call_apify_with_retry(self, hashtag: str, max_retries: int = 3, delay: int = 15):
        """Calls Apify Instagram Hashtag Scraper with retry logic and client rotation."""
        actor_id = "apify/instagram-hashtag-scraper"
        run_input = {
            "hashtags": [hashtag],
            "resultsLimit": 10,
            "addParentData": True
        }
        for attempt in range(1, max_retries + 1):
            # Rotate client on each attempt to distribute load
            client = self.apify_clients[(attempt - 1) % len(self.apify_clients)]
            try:
                logging.info(f"Apify call for #{hashtag} (attempt {attempt} using token index {(attempt - 1) % len(self.apify_clients)})")
                run = client.actor(actor_id).call(run_input=run_input)
                dataset_id = None
                if run:
                    if hasattr(run, "default_dataset_id"):
                        dataset_id = run.default_dataset_id
                    elif isinstance(run, dict):
                        dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
                    else:
                        dataset_id = getattr(run, "default_dataset_id", None) or getattr(run, "defaultDatasetId", None)
                if not dataset_id:
                    raise ValueError("Could not retrieve defaultDatasetId from Apify run")
                items = client.dataset(dataset_id).list_items().items
                logging.info(f"Scraped {len(items)} items for #{hashtag}")
                return items
            except Exception as e:
                logging.error(f"Apify attempt {attempt} failed for #{hashtag}: {e}")
                if attempt < max_retries:
                    time.sleep(delay)
                else:
                    logging.error(f"All {max_retries} attempts failed for #{hashtag}")
                    raise

    def detect_reel_metadata(self, reel: dict) -> dict:
        prompt = f"""
You are a metadata tagger for Instagram Reels. Analyse the following reel data
and return ONLY a valid JSON object, no markdown, no explanation.

Caption: "{reel.get('caption', '')}"
Audio name: "{reel.get('audio_title', '') or reel.get('audio_name', '')}"
Creator location hint: "unknown"

Return this exact JSON structure:
{{
  "caption_language": "english" | "hindi" | "other",
  "audio_language": "english" | "hindi" | "russian" | "portuguese" | "spanish" | "korean" | "other",
  "trend_origin": "IN" | "US" | "BR" | "RU" | "KR" | "GB" | "unknown",
  "creator_country": "IN" | "US" | "BR" | "RU" | "KR" | "GB" | "unknown",
  "is_cross_cultural": true | false,
  "confidence": 0.0 to 1.0
}}

Rules:
- is_cross_cultural = true if audio_language !== caption_language
- If caption is in Devanagari script → caption_language = "hindi"
- If caption is in Latin script and English → caption_language = "english"
- If audio name contains non-English/non-Hindi words → tag audio_language accordingly
- Only return the JSON, nothing else
"""
        try:
            return call_llm(
                system_prompt="You are a metadata tagger for Instagram Reels.",
                user_prompt=prompt,
                response_mime_type="application/json",
                timeout=15
            )
        except Exception as e:
            logging.error(f"Error in detect_reel_metadata: {e}")
            return {
                "caption_language": "unknown",
                "audio_language": "unknown",
                "trend_origin": "unknown",
                "creator_country": "unknown",
                "is_cross_cultural": False,
                "confidence": 0.0
            }

    def _update_trend_lifecycle(self, audio_title: str, creator_country: str, scraped_at: str):
        """Update trend lifecycle spread timeline and saturation counts."""
        if not audio_title:
            return
        try:
            existing = self.supabase.table("trend_lifecycle").select("*").eq("trend_id", audio_title).execute()
            if not existing.data:
                # First time seeing this trend
                self.supabase.table("trend_lifecycle").insert({
                    "trend_id": audio_title,
                    "first_seen_country": creator_country,
                    "first_seen_at": scraped_at,
                    "spread_timeline": [{"country": creator_country, "at": scraped_at}],
                    "saturation_by_region": {creator_country: 1}
                }).execute()
            else:
                row = existing.data[0]
                timeline = row.get("spread_timeline") or []
                saturation = row.get("saturation_by_region") or {}

                timeline.append({"country": creator_country, "at": scraped_at})
                saturation[creator_country] = saturation.get(creator_country, 0) + 1

                self.supabase.table("trend_lifecycle").update({
                    "spread_timeline": timeline,
                    "saturation_by_region": saturation,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("trend_id", audio_title).execute()
        except Exception as e:
            logging.error(f"Error updating trend lifecycle: {e}", exc_info=True)

    def scrape_trending_reels(self):
        """
        Scrapes trending reels across Indian hashtag groups.
        Uses follower-normalized velocity scoring.
        Saves high-velocity reels to Supabase.
        """
        total_scraped = 0
        saved_count = 0
        high_velocity_reels = []

        # Flatten all hashtags with priority: INDIAN_REGIONAL gets 6 slots, INDIA_TRENDING 4, NICHE 2
        priority_pool = (
            self.hashtag_groups["INDIAN_REGIONAL"][:6] +
            self.hashtag_groups["INDIA_TRENDING"][:4] +
            self.hashtag_groups["NICHE_CONTENT"][:2]
        )
        # Deduplicate while preserving order
        seen = set()
        selected_hashtags = []
        for h in priority_pool:
            if h not in seen:
                seen.add(h)
                selected_hashtags.append(h)

        logging.info(f"Scraping {len(selected_hashtags)} hashtags: {selected_hashtags}")

        for hashtag in selected_hashtags:
            try:
                items = self._call_apify_with_retry(hashtag)
                total_scraped += len(items)

                for item in items:
                    try:
                        reel_id = item.get("shortCode")
                        if not reel_id:
                            continue

                        view_count = int(item.get("videoViewCount") or 0)
                        like_count = int(item.get("likesCount") or 0)
                        comment_count = int(item.get("commentsCount") or 0)
                        follower_count = int(item.get("ownerFollowersCount") or 0)

                        timestamp_str = item.get("timestamp")
                        if not timestamp_str:
                            continue
                        if timestamp_str.endswith("Z"):
                            timestamp_str = timestamp_str[:-1] + "+00:00"
                        posted_at = datetime.fromisoformat(timestamp_str)
                        hours_live = max((datetime.now(timezone.utc) - posted_at).total_seconds() / 3600.0, 0.5)

                        # 2026 Instagram algorithm-weighted velocity:
                        # DM shares ≈ 15× likes | Saves ≈ 10× likes | Rewatches ≈ 5× likes | Comments ≈ 4× likes
                        # Since we don't have DM/save/rewatch data from the scraper,
                        # we proxy: saves ≈ like_count*0.1, rewatches ≈ view_count*0.05
                        proxy_saves   = like_count * 0.1     # ~10% of likes become saves
                        proxy_replays = view_count * 0.05    # ~5% of views are rewatches
                        engagement_2026 = (
                            view_count  * 1.0 +
                            proxy_saves * 10.0 +    # saves = 10× likes
                            comment_count * 4.0 +   # threaded comments are strong signal
                            like_count  * 1.0 +     # likes = weakest signal
                            proxy_replays * 5.0     # rewatches = strong quality signal
                        )
                        subscribers = max(follower_count, 1000)
                        velocity_score = (engagement_2026 / hours_live / subscribers) * 10000

                        # Accept if:
                        # - velocity > 0.3 (normalized), OR
                        # - raw view_count > 5000 in < 6 hrs (catches small creators going viral)
                        passes_velocity = velocity_score > 0.3
                        passes_raw = view_count > 5000 and hours_live < 6
                        if not (passes_velocity or passes_raw):
                            continue

                        # Skip if already in DB
                        check = self.supabase.table("reels").select("reel_id").eq("reel_id", reel_id).execute()
                        if check.data:
                            continue

                        owner_username = item.get("ownerUsername")
                        caption = (item.get("caption") or "")[:500]
                        hashtags_list = re.findall(r"#(\w+)", caption)
                        video_url = item.get("videoUrl")
                        
                        # Parse nested musicInfo
                        music_title = None
                        music_artist = None
                        music_info_dict = item.get("musicInfo")
                        if music_info_dict:
                            minfo = music_info_dict.get("music_info")
                            if minfo:
                                asset = minfo.get("music_asset_info") or {}
                                music_title = asset.get("title")
                                music_artist = asset.get("display_artist")
                            if not music_title or not music_title.strip():
                                orig = music_info_dict.get("original_sound_info")
                                if orig:
                                    music_title = orig.get("original_audio_title")
                                    ig_artist = orig.get("ig_artist") or {}
                                    music_artist = ig_artist.get("username") or ig_artist.get("full_name")
                                    
                        thumbnail_url = item.get("thumbnailUrl") or item.get("displayUrl")

                        reel_data = {
                            "platform": "instagram",
                            "reel_id": reel_id,
                            "view_count": view_count,
                            "like_count": like_count,
                            "comment_count": comment_count,
                            "posted_at": posted_at.isoformat(),
                            "owner_username": owner_username,
                            "owner_follower_count": follower_count,
                            "caption": caption,
                            "hashtags": hashtags_list,
                            "video_url": video_url,
                            "thumbnail_url": thumbnail_url,
                            "audio_title": music_title,
                            "audio_artist": music_artist,
                            "velocity_score": velocity_score,
                        }

                        # Call Groq tagging for the reel metadata
                        metadata = self.detect_reel_metadata(reel_data)
                        reel_data.update({
                            "audio_language": metadata.get("audio_language", "unknown"),
                            "caption_language": metadata.get("caption_language", "unknown"),
                            "trend_origin": metadata.get("trend_origin", "unknown"),
                            "creator_country": metadata.get("creator_country", "unknown"),
                            "is_cross_cultural": metadata.get("is_cross_cultural", False),
                            "language_confidence": metadata.get("confidence", 0.0),
                        })

                        self.supabase.table("reels").insert(reel_data).execute()
                        logging.info(f"Saved reel {reel_id} by @{owner_username} (velocity={velocity_score:.3f})")
                        
                        # Update trend lifecycle
                        scraped_time_str = datetime.now(timezone.utc).isoformat()
                        self._update_trend_lifecycle(
                            audio_title=music_title or "unknown_trend",
                            creator_country=metadata.get("creator_country", "unknown"),
                            scraped_at=scraped_time_str
                        )
                        
                        high_velocity_reels.append(velocity_score)
                        saved_count += 1

                    except Exception as e:
                        logging.error(f"Error processing reel: {e}", exc_info=True)

            except Exception as e:
                logging.error(f"Failed hashtag #{hashtag}: {e}", exc_info=True)

        high_velocity_reels.sort(reverse=True)
        top3 = [round(s, 4) for s in high_velocity_reels[:3]]
        print(f"Total scraped: {total_scraped} | Saved: {saved_count} | Top 3 velocities: {top3}")
        return saved_count


if __name__ == "__main__":
    scraper = InstagramScraper()
    scraper.scrape_trending_reels()
