import os
import time
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import requests
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    filename="youtube_scraper.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class YouTubeScraper:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Fallback to backend/.env if not loaded (e.g. when run from workspace root)
        if not os.getenv("YOUTUBE_API_KEY"):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            backend_env = os.path.join(script_dir, ".env")
            if os.path.exists(backend_env):
                load_dotenv(backend_env)
        
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.api_key:
            logging.error("YOUTUBE_API_KEY is missing from environment variables.")
            raise ValueError("YOUTUBE_API_KEY is missing from .env")
        if not self.supabase_url or not self.supabase_key:
            logging.error("Supabase credentials (SUPABASE_URL / SUPABASE_KEY) are missing.")
            raise ValueError("Supabase credentials are missing from .env")
            
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)

    def scrape_trending_shorts(self):
        """
        Scrapes trending YouTube Shorts in India, calculates velocity scores,
        and stores new Shorts into the Supabase database.
        """
        logging.info("Starting scrape_trending_shorts process...")
        
        # 1. Search for trending Shorts in India across different relevance languages
        languages = ["en", "hi", "kn", "ta"]
        collected_video_ids = {}  # maps video_id -> language (keeps the first occurrence language)
        
        # Calculate publishedAfter (48 hours ago in RFC3339 format)
        published_after = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat().replace("+00:00", "Z")
        logging.info(f"Searching for videos published after: {published_after}")
        
        for lang in languages:
            try:
                logging.info(f"Searching YouTube Shorts for relevanceLanguage '{lang}'...")
                search_url = "https://www.googleapis.com/youtube/v3/search"
                params = {
                    "part": "snippet",
                    "type": "video",
                    "videoDuration": "short",
                    "regionCode": "IN",
                    "order": "viewCount",
                    "publishedAfter": published_after,
                    "maxResults": 50,
                    "relevanceLanguage": lang,
                    "q": "shorts",
                    "key": self.api_key
                }
                
                response = requests.get(search_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                items = data.get("items", [])
                logging.info(f"Found {len(items)} search items for language '{lang}'")
                
                for item in items:
                    video_id = item.get("id", {}).get("videoId")
                    if video_id and video_id not in collected_video_ids:
                        collected_video_ids[video_id] = lang
            except Exception as e:
                logging.error(f"Error searching for language '{lang}': {e}", exc_info=True)
                
        total_found = len(collected_video_ids)
        logging.info(f"Total unique video IDs collected: {total_found}")
        
        if not collected_video_ids:
            print("No videos found to scrape.")
            return
            
        # 2. Get video statistics and snippets in batches of 50
        video_details = {}
        video_ids_list = list(collected_video_ids.keys())
        
        for i in range(0, len(video_ids_list), 50):
            batch_ids = video_ids_list[i:i+50]
            try:
                logging.info(f"Fetching details for batch of {len(batch_ids)} videos...")
                videos_url = "https://www.googleapis.com/youtube/v3/videos"
                params = {
                    "part": "statistics,snippet",
                    "id": ",".join(batch_ids),
                    "key": self.api_key
                }
                response = requests.get(videos_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("items", []):
                    v_id = item.get("id")
                    video_details[v_id] = item
            except Exception as e:
                logging.error(f"Error fetching details for batch {batch_ids}: {e}", exc_info=True)
                
        # 3. Get channel subscriber count for each unique channel ID in batches of 50
        channel_ids = set()
        for v_id, item in video_details.items():
            chan_id = item.get("snippet", {}).get("channelId")
            if chan_id:
                channel_ids.add(chan_id)
                
        channel_subs = {}
        channel_ids_list = list(channel_ids)
        for i in range(0, len(channel_ids_list), 50):
            batch_chans = channel_ids_list[i:i+50]
            try:
                logging.info(f"Fetching subscriber counts for batch of {len(batch_chans)} channels...")
                channels_url = "https://www.googleapis.com/youtube/v3/channels"
                params = {
                    "part": "statistics",
                    "id": ",".join(batch_chans),
                    "key": self.api_key
                }
                response = requests.get(channels_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                for item in data.get("items", []):
                    c_id = item.get("id")
                    sub_count = 0
                    stats = item.get("statistics", {})
                    if "subscriberCount" in stats:
                        try:
                            sub_count = int(stats["subscriberCount"])
                        except ValueError:
                            sub_count = 0
                    channel_subs[c_id] = sub_count
            except Exception as e:
                logging.error(f"Error fetching channel details for batch {batch_chans}: {e}", exc_info=True)
                
        # 4. Calculate metrics and save to Supabase
        saved_count = 0
        skipped_count = 0
        error_count = 0
        saved_velocities = []
        
        for v_id, item in video_details.items():
            try:
                # Check if video_id already exists in Supabase
                res = self.supabase.table("youtube_shorts").select("video_id").eq("video_id", v_id).execute()
                if res.data:
                    logging.info(f"Video {v_id} already exists in database. Skipping.")
                    skipped_count += 1
                    continue
                
                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})
                
                title = snippet.get("title")
                channel_title = snippet.get("channelTitle")
                channel_id = snippet.get("channelId")
                published_at_str = snippet.get("publishedAt")
                tags = snippet.get("tags") or []
                
                # Fetch statistics counts safely
                view_count = int(statistics.get("viewCount") or 0)
                like_count = int(statistics.get("likeCount") or 0)
                comment_count = int(statistics.get("commentCount") or 0)
                
                # Parse published_at string to UTC datetime
                if published_at_str.endswith("Z"):
                    published_at_clean = published_at_str[:-1] + "+00:00"
                else:
                    published_at_clean = published_at_str
                
                published_at = datetime.fromisoformat(published_at_clean)
                time_diff = datetime.now(timezone.utc) - published_at
                
                # hours_live = max(hours since publishedAt, 0.5)
                hours_live = max(time_diff.total_seconds() / 3600.0, 0.5)
                
                # subscribers = max(subscriberCount, 1000)
                sub_count = channel_subs.get(channel_id, 0)
                subscribers = max(sub_count, 1000)
                
                # velocity_score = viewCount / hours_live / subscribers * 10000
                velocity_score = (view_count / hours_live / subscribers) * 10000
                
                # Get correct language code from search discovery
                lang = collected_video_ids.get(v_id, "en")
                
                short_data = {
                    "video_id": v_id,
                    "title": title,
                    "channel_title": channel_title,
                    "channel_id": channel_id,
                    "view_count": view_count,
                    "like_count": like_count,
                    "comment_count": comment_count,
                    "published_at": published_at.isoformat(),
                    "tags": tags,
                    "velocity_score": velocity_score,
                    "region_code": "IN",
                    "language": lang
                }
                
                # Save to database
                self.supabase.table("youtube_shorts").insert(short_data).execute()
                logging.info(f"Successfully saved video {v_id} (velocity_score: {velocity_score:.4f})")
                
                saved_count += 1
                saved_velocities.append(velocity_score)
                
            except Exception as e:
                logging.error(f"Error processing video {v_id}: {e}", exc_info=True)
                error_count += 1
                
        # Sort velocity scores to find top 3
        saved_velocities.sort(reverse=True)
        top_3_scores = [round(score, 4) for score in saved_velocities[:3]]
        top_3_str = ", ".join(map(str, top_3_scores)) if top_3_scores else "None"
        
        # Output summary at the end
        print("\n=== YouTube Shorts Scraper Summary ===")
        print(f"Total Unique Videos Found: {total_found}")
        print(f"Saved to Supabase: {saved_count}")
        print(f"Skipped (Already Exists): {skipped_count}")
        print(f"Errors Encountered: {error_count}")
        print(f"Top 3 Velocity Scores: {top_3_str}")
        print("======================================\n")

if __name__ == "__main__":
    scraper = YouTubeScraper()
    scraper.scrape_trending_shorts()
