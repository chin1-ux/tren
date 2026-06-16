import os
import re
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from apify_client import ApifyClient
from supabase import create_client, Client

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

        self.apify_client = ApifyClient(self.apify_token)
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
        """Calls Apify Instagram Hashtag Scraper with retry logic."""
        actor_id = "apify/instagram-hashtag-scraper"
        run_input = {
            "hashtags": [hashtag],
            "resultsLimit": 30,
            "addParentData": True
        }
        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"Apify call for #{hashtag} (attempt {attempt})")
                run = self.apify_client.actor(actor_id).call(run_input=run_input)
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
                items = self.apify_client.dataset(dataset_id).list_items().items
                logging.info(f"Scraped {len(items)} items for #{hashtag}")
                return items
            except Exception as e:
                logging.error(f"Apify attempt {attempt} failed for #{hashtag}: {e}")
                if attempt < max_retries:
                    time.sleep(delay)
                else:
                    logging.error(f"All {max_retries} attempts failed for #{hashtag}")
                    raise

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

                        # Follower-normalized velocity:
                        # velocity = engagement / hours_live / max(followers, 1000) * 10000
                        posted_naive = posted_at.astimezone().replace(tzinfo=None)
                        time_diff = datetime.now() - posted_naive
                        hours_live = max(time_diff.total_seconds() / 3600, 0.5)

                        engagement = view_count + (like_count * 2) + (comment_count * 5)
                        subscribers = max(follower_count, 1000)
                        velocity_score = (engagement / hours_live / subscribers) * 10000

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
                        music_title = item.get("musicTitle")
                        music_artist = item.get("musicArtist")
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

                        self.supabase.table("reels").insert(reel_data).execute()
                        logging.info(f"Saved reel {reel_id} by @{owner_username} (velocity={velocity_score:.3f})")
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
