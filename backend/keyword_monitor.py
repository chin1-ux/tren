#!/usr/bin/env python3
"""
Keyword Monitor (Orbit Search) System
Pulls active keywords from keyword_monitors table, scrapes reels, filters using outlier system, and saves discoveries.
"""

import os
import sys
import time
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("keyword_monitor.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("keyword_monitor")

# Load environment variables
load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
if not url or not key:
    raise RuntimeError("Supabase credentials not set in environment.")
sb = create_client(url, key)

# Import scraper
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from instagram_scraper_browser import InstagramScraper

def clean_tag(keyword: str) -> str:
    """Normalize keyword to a clean tag for Instagram scraping (no spaces, no hash symbol)."""
    clean = keyword.replace("#", "").replace(" ", "").lower().strip()
    return clean

async def run_keyword_monitor():
    logger.info("Starting Keyword Monitor (Orbit Search) batch...")
    
    # 1. Fetch active keywords
    try:
        res = sb.table('keyword_monitors').select('*').eq('is_active', True).execute()
        monitors = res.data or []
        logger.info(f"Retrieved {len(monitors)} active keywords from DB.")
    except Exception as e:
        logger.warning(f"Could not query keyword_monitors table (it may not be created yet): {e}")
        # Fallback to system default keywords for bootstrapping
        monitors = [
            {"id": "sys-gym", "keyword": "gym motivation", "niche_category": "gym"},
            {"id": "sys-food", "keyword": "food recipes", "niche_category": "food"},
            {"id": "sys-travel", "keyword": "travel diary", "niche_category": "travel"},
            {"id": "sys-fashion", "keyword": "outfit inspo", "niche_category": "fashion"}
        ]
        logger.info(f"Using {len(monitors)} fallback keywords.")

    if not monitors:
        logger.info("No active keywords to monitor. Exiting.")
        return

    # 2. Initialize Scraper
    scraper = InstagramScraper()
    if not await scraper._init_browser_async():
        logger.error("Failed to initialize scraper browser. Aborting keyword monitor run.")
        return

    scraped_at = datetime.now(timezone.utc).isoformat()
    scrape_stats = {
        "missing_reel_id": 0,
        "missing_timestamp": 0,
        "low_engagement": 0,
        "velocity_failed": 0,
        "duplicate": 0,
        "insert_attempts": 0,
        "insert_saved": 0,
        "item_errors": 0,
        "stored_videos": 0,
        "failed_video_stores": 0,
    }
    baseline_fetches_this_cycle = 0

    try:
        for idx, monitor in enumerate(monitors):
            keyword = monitor["keyword"]
            niche = monitor.get("niche_category", "general")
            tag = clean_tag(keyword)
            
            logger.info(f"Processing keyword '{keyword}' as tag #{tag} ({idx + 1}/{len(monitors)})...")
            
            # Rate limiting delay
            if idx > 0:
                time.sleep(3)
                
            try:
                # Scrape hashtag page matching the clean tag
                items = await scraper._scrape_hashtag_page_async(tag)
                
                if items:
                    logger.info(f"Scraped {len(items)} items for tag #{tag}. Processing batch...")
                    # Process and save the batch
                    inserted_reels, audio_groups_entries = scraper._process_hashtag_batch(
                        items=items,
                        tag=tag,
                        scraped_at=scraped_at,
                        scrape_stats=scrape_stats,
                        baseline_fetches_this_cycle=baseline_fetches_this_cycle,
                    )
                    
                    saved_for_tag = len(inserted_reels)
                    logger.info(f"Successfully processed tag #{tag}: saved {saved_for_tag} reels/trends.")
                    
                    # Calculate average velocity baseline for this keyword from the inserted reels
                    if inserted_reels:
                        velocities = [r.get("velocity_score", 0) for r in inserted_reels if r.get("velocity_score")]
                        avg_velocity = sum(velocities) / len(velocities) if velocities else 0
                    else:
                        avg_velocity = 0
                        
                    # Update monitor check metadata in DB
                    monitor_id = monitor.get("id")
                    if monitor_id and not str(monitor_id).startswith("sys-"):
                        try:
                            sb.table("keyword_monitors").update({
                                "last_checked_at": scraped_at,
                                "velocity_baseline": avg_velocity
                            }).eq("id", monitor_id).execute()
                            logger.info(f"Updated keyword_monitors row for id={monitor_id}")
                        except Exception as db_err:
                            logger.warning(f"Could not update keyword_monitors metadata for id={monitor_id}: {db_err}")
                else:
                    logger.warning(f"No items scraped for tag #{tag}.")
                    
            except Exception as tag_err:
                logger.error(f"Failed to process keyword '{keyword}': {tag_err}", exc_info=True)
                
    finally:
        logger.info("Closing scraper browser...")
        await scraper._close_browser_async()
        
    logger.info(
        "Keyword monitor run completed. "
        f"stats: attempts={scrape_stats['insert_attempts']}, saved={scrape_stats['insert_saved']}, "
        f"duplicates={scrape_stats['duplicate']}, low_engagement={scrape_stats['low_engagement']}"
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_keyword_monitor())
