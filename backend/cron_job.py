import os
import sys
import time
import logging
from datetime import datetime
import schedule

# Allow running from other directories and importing backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging to log to both pipeline.log and stdout
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pipeline.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

try:
    from instagram_scraper import InstagramScraper
    from youtube_scraper import YouTubeScraper
    from trend_engine import TrendEngine
    from alert_system import AlertSystem
except Exception as import_err:
    logging.critical(f"Failed to import scraper/engine/alert modules: {import_err}", exc_info=True)
    raise

def run_full_pipeline():
    start_msg = f"=== TRENDROP PIPELINE STARTING {datetime.now()} ==="
    print(start_msg)
    logging.info(start_msg)
    
    # 1. Run InstagramScraper().scrape_trending_reels()
    try:
        logging.info("Step 1: Scraping trending reels from Instagram...")
        insta_scraper = InstagramScraper()
        insta_scraper.scrape_trending_reels()
        logging.info("Instagram reels scraping complete.")
    except Exception as e:
        logging.error(f"Error scraping Instagram reels: {e}", exc_info=True)
        
    # 2. Run YouTubeScraper().scrape_trending_shorts()
    try:
        logging.info("Step 2: Scraping trending shorts from YouTube...")
        yt_scraper = YouTubeScraper()
        yt_scraper.scrape_trending_shorts()
        logging.info("YouTube shorts scraping complete.")
    except Exception as e:
        logging.error(f"Error scraping YouTube shorts: {e}", exc_info=True)
        
    # 3. Run TrendEngine().detect_trends() — save returned trend_ids
    trend_ids = []
    try:
        logging.info("Step 3: Detecting trends using TrendEngine...")
        trend_engine = TrendEngine()
        trend_ids = trend_engine.detect_trends()
        logging.info(f"Trend detection complete. Trend IDs returned: {trend_ids}")
    except Exception as e:
        logging.error(f"Error detecting trends: {e}", exc_info=True)
        
    # 4. If new trend_ids found: Run AlertSystem().send_trend_alerts(trend_ids)
    if trend_ids:
        try:
            logging.info(f"Step 4: New trend IDs found {trend_ids}. Sending trend alerts...")
            alert_system = AlertSystem()
            alert_system.send_trend_alerts(trend_ids)
            logging.info("Trend alerts sent successfully.")
        except Exception as e:
            logging.error(f"Error sending trend alerts for IDs {trend_ids}: {e}", exc_info=True)
    else:
        logging.info("Step 4: No new trend IDs detected. Skipping alerts.")
        
    count = len(trend_ids)
    end_msg = f"=== PIPELINE COMPLETE. New trends: {count} ==="
    print(end_msg)
    logging.info(end_msg)

if __name__ == "__main__":
    logging.info("Cron job script initialized. Starting first run immediately...")
    # Run once immediately on startup
    try:
        run_full_pipeline()
    except Exception as startup_err:
        logging.error(f"Error in initial pipeline run: {startup_err}", exc_info=True)
        
    # Schedule: schedule.every(2).hours.do(run_full_pipeline)
    logging.info("Scheduling pipeline to run every 2 hours...")
    schedule.every(2).hours.do(run_full_pipeline)
    
    # Main loop
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logging.info("Cron job script stopped by user.")
