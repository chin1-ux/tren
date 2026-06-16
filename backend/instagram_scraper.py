import os
import re
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from apify_client import ApifyClient
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    filename="instagram_scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class InstagramScraper:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Fallback to backend/.env if not loaded (e.g. when run from workspace root)
        if not os.getenv("APIFY_API_TOKEN"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_env = os.path.join(script_dir, ".env")
            if os.path.exists(backend_env):
                load_dotenv(backend_env)
                
        self.apify_token = os.getenv("APIFY_API_TOKEN")
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.apify_token:
            logging.error("APIFY_API_TOKEN is missing from the environment variables.")
            raise ValueError("APIFY_API_TOKEN is missing from .env")
        if not self.supabase_url or not self.supabase_key:
            logging.error("Supabase credentials (SUPABASE_URL / SUPABASE_KEY) are missing.")
            raise ValueError("Supabase credentials are missing from .env")
            
        self.apify_client = ApifyClient(self.apify_token)
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Hashtag groups to scrape
        self.hashtag_groups = {
            "ENGLISH_TRENDING": ["trending", "reels", "viral", "fyp", "explore", "instareels", "reelsviral"],
            "INDIAN_REGIONAL": [
                "kannadareels", "kannada", "karnataka", "hindireels", "bollywood", "hindimusic",
                "tamilreels", "kollywood", "telugureels", "tollywood", "marathireels", "bengalireels", "punjabireel"
            ],
            "NICHE_CONTENT": [
                "glowup", "transformation", "beforeafter", "fashionreels", "foodreels", "travelreels",
                "motivationreels", "devotional", "festivalreels", "comedyreels", "studyreels", "fitnessreels"
            ]
        }

    def _call_apify_with_retry(self, hashtag: str, max_retries: int = 3, delay: int = 10):
        """Calls Apify Instagram Hashtag Scraper actor with retries."""
        actor_id = "apify/instagram-hashtag-scraper"
        run_input = {
            "hashtags": [hashtag],
            "resultsLimit": 30,
            "addParentData": True
        }
        
        for attempt in range(1, max_retries + 1):
            try:
                logging.info(f"Calling Apify for hashtag '{hashtag}' (Attempt {attempt}/{max_retries})...")
                # Call the actor and wait for it to finish
                run = self.apify_client.actor(actor_id).call(run_input=run_input)
                
                # Retrieve default dataset ID robustly
                dataset_id = None
                if run:
                    if hasattr(run, "default_dataset_id"):
                        dataset_id = run.default_dataset_id
                    elif isinstance(run, dict):
                        dataset_id = run.get("defaultDatasetId") or run.get("default_dataset_id")
                    else:
                        dataset_id = getattr(run, "default_dataset_id", None) or getattr(run, "defaultDatasetId", None)
                        
                if not dataset_id:
                    raise ValueError("Could not retrieve defaultDatasetId from Apify run object.")
                    
                # Fetch dataset items
                dataset_items = self.apify_client.dataset(dataset_id).list_items().items
                logging.info(f"Successfully scraped {len(dataset_items)} items for hashtag '{hashtag}'")
                return dataset_items
            except Exception as e:
                logging.error(f"Attempt {attempt} failed for hashtag '{hashtag}': {e}")
                if attempt < max_retries:
                    logging.info(f"Waiting {delay} seconds before retrying...")
                    time.sleep(delay)
                else:
                    logging.error(f"All {max_retries} attempts failed for hashtag '{hashtag}'.")
                    raise e

    def scrape_trending_reels(self):
        """Scrapes trending reels for all hashtag groups, calculates velocity, and saves to Supabase."""
        total_scraped = 0
        high_velocity_reels = []
        
        # Gather all hashtags from all groups
        all_hashtags = []
        for group_name, tags in self.hashtag_groups.items():
            all_hashtags.extend(tags)
            
        # Deduplicate hashtags while preserving order
        unique_hashtags = list(dict.fromkeys(all_hashtags))
        
        # Optimize: Sample 6 hashtags per run to stay well within monthly limits
        import random
        selected_hashtags = random.sample(unique_hashtags, min(6, len(unique_hashtags)))
        
        logging.info(f"Starting scrape for {len(selected_hashtags)} sampled hashtags out of {len(unique_hashtags)} total...")
        
        for hashtag in selected_hashtags:
            try:
                items = self._call_apify_with_retry(hashtag)
                total_scraped += len(items)
                
                for item in items:
                    try:
                        # Extract shortCode as reel_id
                        reel_id = item.get("shortCode")
                        if not reel_id:
                            continue
                            
                        # Extract counts
                        view_count = item.get("videoViewCount")
                        if view_count is None:
                            view_count = 0
                        else:
                            view_count = int(view_count)
                            
                        like_count = int(item.get("likesCount") or 0)
                        comment_count = int(item.get("commentsCount") or 0)
                        
                        # Extract and parse timestamp
                        timestamp_str = item.get("timestamp")
                        if not timestamp_str:
                            continue
                            
                        # Normalize ISO timestamp format for Python datetime parsing
                        if timestamp_str.endswith("Z"):
                            timestamp_str = timestamp_str[:-1] + "+00:00"
                        posted_at = datetime.fromisoformat(timestamp_str)
                        
                        # Calculate velocity score using naive datetimes in local timezone
                        # to match the requested formula:
                        # hours_live = max((datetime.now() - posted_at).seconds / 3600, 0.5)
                        posted_at_naive = posted_at.astimezone().replace(tzinfo=None)
                        time_diff = datetime.now() - posted_at_naive
                        hours_live = max(time_diff.total_seconds() / 3600, 0.5)
                        
                        engagement = view_count + (like_count * 2) + (comment_count * 5)
                        velocity_score = engagement / hours_live / 1000
                        
                        # Filter high-velocity reels
                        if velocity_score <= 0.5:
                            continue
                            
                        # Check if reel already exists in database
                        res = self.supabase.table("reels").select("reel_id").eq("reel_id", reel_id).execute()
                        if res.data:
                            logging.info(f"Reel {reel_id} already exists in database. Skipping.")
                            continue
                            
                        # Extract other details
                        owner_username = item.get("ownerUsername")
                        caption = item.get("caption") or ""
                        truncated_caption = caption[:500]
                        
                        # Extract hashtags list from caption
                        hashtags_list = re.findall(r"#(\w+)", caption)
                        
                        video_url = item.get("videoUrl")
                        music_title = item.get("musicTitle")
                        music_artist = item.get("musicArtist")
                        
                        # Prepare data payload matching 'reels' table schema
                        reel_data = {
                            "platform": "instagram",
                            "reel_id": reel_id,
                            "view_count": view_count,
                            "like_count": like_count,
                            "comment_count": comment_count,
                            "posted_at": posted_at.isoformat(),
                            "owner_username": owner_username,
                            "caption": truncated_caption,
                            "hashtags": hashtags_list,
                            "video_url": video_url,
                            "audio_title": music_title,
                            "audio_artist": music_artist,
                            "velocity_score": velocity_score
                        }
                        
                        # Insert into Supabase
                        self.supabase.table("reels").insert(reel_data).execute()
                        logging.info(f"Successfully saved high-velocity reel {reel_id} (velocity: {velocity_score:.4f})")
                        high_velocity_reels.append(velocity_score)
                        
                    except Exception as e:
                        logging.error(f"Error processing reel item: {e}", exc_info=True)
                        
            except Exception as e:
                logging.error(f"Failed to process hashtag '{hashtag}': {e}", exc_info=True)
                
        # Sort velocity scores to find top 3
        high_velocity_reels.sort(reverse=True)
        top_3_scores = [round(score, 4) for score in high_velocity_reels[:3]]
        
        # Format top 3 scores for printing
        top_3_str = ", ".join(map(str, top_3_str_list := top_3_scores)) if top_3_scores else "None"
        
        # End results printed to stdout
        print(f"Total reels scraped: {total_scraped}")
        print(f"High velocity reels found: {len(high_velocity_reels)}")
        print(f"Top 3 velocity scores: {top_3_str}")

if __name__ == "__main__":
    scraper = InstagramScraper()
    scraper.scrape_trending_reels()
