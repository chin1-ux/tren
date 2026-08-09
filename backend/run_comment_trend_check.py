import sys
import os
import argparse
import logging
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("comment_trend_check")

# Configure UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding="utf-8")

def run_comment_check():
    parser = argparse.ArgumentParser(description="Run on-demand Instagram comment clustering for trend detection.")
    parser.add_argument("--hashtag", type=str, help="Scrape latest reels from hashtag and check comment trends.")
    parser.add_argument("--reels", type=str, help="Comma-separated list of alphanumeric reel shortcodes to scrape directly.")
    args = parser.parse_args()
    
    # 1. Initialize Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be configured in environment.")
        sys.exit(1)
        
    supabase: Client = create_client(supabase_url, supabase_key)
    
    reels_to_query = []
    
    # 2. Scrape on-demand if CLI arguments provided
    if args.reels:
        codes = [c.strip() for c in args.reels.split(",") if c.strip()]
        logger.info(f"Direct shortcodes passed: {codes}")
        # Resolve or backfill pk by querying tags matching or querying explore
        # For direct verification, we fetch comments using the backfilled pk in our reels table
        res = supabase.table("reels").select("reel_id, pk").in_("reel_id", codes).execute()
        reels_to_query = res.data or []
        
    elif args.hashtag:
        tag = args.hashtag.strip().replace("#", "")
        logger.info(f"Target hashtag passed: #{tag}")
        
        # Load credentials for manual scraper call
        import requests
        import json
        cookies_path = "backend/cookies.json"
        if not os.path.exists(cookies_path):
            cookies_path = "cookies.json"
        if not os.path.exists(cookies_path):
            logger.error("cookies.json not found. Run scraper verification/auth setup first.")
            sys.exit(1)
            
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-IG-App-ID": "936619743392459",
            "X-Requested-With": "XMLHttpRequest",
        }
        cookies = {}
        with open(cookies_path, "r", encoding="utf-8") as f:
            raw_cookies = json.load(f)
        for cookie in raw_cookies:
            cookies[cookie["name"]] = cookie["value"]
            
        # Get live explore section
        logger.info(f"Querying live Instagram Explore API for #{tag} to map pk...")
        url = f"https://www.instagram.com/api/v1/tags/web_info/?tag_name={tag}"
        try:
            r = requests.get(url, headers=headers, cookies=cookies, timeout=15)
            r.raise_for_status()
            sections = r.json().get("data", {}).get("top", {}).get("sections", [])
            matched_count = 0
            
            # Map code -> pk and update database on the fly
            conn_url = os.getenv("SUPABASE_DB_URL")
            if conn_url:
                import psycopg2
                conn = psycopg2.connect(conn_url)
                conn.autocommit = True
                cur = conn.cursor()
                for s in sections:
                    layout_content = s.get("layout_content", {})
                    for m_wrapper in layout_content.get("medias", []):
                        media = m_wrapper.get("media")
                        if media:
                            pk = str(media.get("pk"))
                            code = media.get("code")
                            cur.execute("UPDATE reels SET pk=%s WHERE reel_id=%s", (pk, code))
                            if cur.rowcount > 0:
                                matched_count += 1
                                reels_to_query.append({"reel_id": code, "pk": pk})
                cur.close()
                conn.close()
            logger.info(f"Mapped and backfilled {matched_count} matching reels in database.")
        except Exception as e:
            logger.error(f"Failed to query live hashtag exploration: {e}")
            
    # Fallback to general top reels if no params passed
    if not reels_to_query:
        logger.info("No query args passed or no on-the-fly matches. Fetching top reels from database with pk values...")
        res = supabase.table("reels").select("reel_id, pk").not_.is_("pk", "null").order("view_count", desc=True).limit(20).execute()
        reels_to_query = res.data or []
        
    if not reels_to_query:
        logger.error("No target reels with valid pk values found. Verify scraper has run and populated pk column.")
        sys.exit(1)
        
    logger.info(f"Targeting {len(reels_to_query)} reels for comment checking.")
    
    # 3. Fetch Comments
    from comment_scraper_pilot import fetch_comments_for_reel, load_cookies
    c_headers, c_cookies = load_cookies()
    
    total_comments_inserted = 0
    import time
    import random
    
    for idx, r in enumerate(reels_to_query, start=1):
        reel_id = r["reel_id"]
        pk = r.get("pk")
        comments = fetch_comments_for_reel(reel_id, pk, c_headers, c_cookies)
        
        to_insert = []
        for c in comments:
            to_insert.append({
                "comment_id": str(c.get("pk")),
                "reel_id": reel_id,
                "text": c.get("text", ""),
                "commenter_username": c.get("user", {}).get("username", "unknown"),
                "created_at": c.get("created_at")
            })
            
        if to_insert:
            try:
                supabase.table("comments").upsert(to_insert).execute()
                total_comments_inserted += len(to_insert)
            except Exception as e:
                logger.error(f"Failed to insert comments for reel {reel_id}: {e}")
                
        if idx < len(reels_to_query) and pk:
            time.sleep(random.uniform(2.0, 4.0))
            
    logger.info(f"Finished scraping comments. Added {total_comments_inserted} comments to database.")
    
    # 4. Clustering Pipeline execution
    import comment_clustering
    engine = comment_clustering.CommentClusteringEngine()
    
    # Read back all comments
    c_res = supabase.table("comments").select("reel_id, text, commenter_username").execute()
    comments_with_meta = []
    for row in c_res.data:
        txt = row.get("text") or ""
        cleaned_txt = comment_clustering.clean_comments([txt])
        if not cleaned_txt:
             continue
        phrases = comment_clustering.extract_phrases_regex(cleaned_txt[0])
        if phrases:
            comments_with_meta.append({
                "text": cleaned_txt[0],
                "post_id": row["reel_id"],
                "creator_id": row["commenter_username"] or "unknown",
                "extracted_phrases": phrases
            })
            
    logger.info(f"Processing {len(comments_with_meta)} comments for trend clustering.")
    clusters = engine.build_clusters(comments_with_meta)
    
    # Run CPDI with standard thresholds
    flagged = engine.calculate_cpdi_and_flag(clusters, min_unique_posts=5, cpdi_threshold=0.15)
    
    print("\n==================================================")
    print("        EMERGING COMMENT-DRIVEN TRENDS            ")
    print("==================================================")
    print(f"Total flagged trends found: {len(flagged)}")
    for idx, f in enumerate(flagged, start=1):
        print(f"{idx}. Canonical Key: {f['canonical_key']}")
        print(f"   CPDI: {f['cpdi']:.2f} | Unique Posts: {f['unique_posts_count']} | Total Comments: {f['total_comments_count']}")
        print(f"   Sample phrases: {f['sample_phrases'][:4]}")
        print("-" * 50)

if __name__ == "__main__":
    run_comment_check()
