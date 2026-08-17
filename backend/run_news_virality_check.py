import sys
import os
import argparse
import logging
from datetime import datetime
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("news_virality_check")

# Configure UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding="utf-8")

def run_news_check():
    from dotenv import load_dotenv
    load_dotenv("backend/.env")
    # 1. Initialize Supabase
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY must be configured in environment.")
        sys.exit(1)
        
    supabase: Client = create_client(supabase_url, supabase_key)
    
    # 2. Fetch news articles
    from news_client import NewsClient, evaluate_news_virality_batch
    client = NewsClient()
    categories = ['sports', 'entertainment', 'meme', 'india']
    articles = []
    for cat in categories:
        try:
            res = client.get_trending_news(cat)
            logger.info(f"Fetched {len(res)} articles for category: {cat}")
            articles.extend(res)
        except Exception as e:
            logger.error(f"Failed to fetch news for category {cat}: {e}")
            
    if not articles:
        logger.error("Fetch returned 0 news articles across all categories.")
        sys.exit(1)
        
    # Deduplicate by URL
    unique_articles = {}
    for a in articles:
        if a.get('url'):
            unique_articles[a['url']] = a
    articles_list = list(unique_articles.values())
    
    logger.info(f"Unique news articles count to process: {len(articles_list)}")
    
    # 3. Evaluate virality in chunks of 8
    try:
        scored = evaluate_news_virality_batch(articles_list, batch_size=8)
        # Check if the evaluation actually populated scores or returned empty default fallbacks
        success_scored = [a for a in scored if a.get("viral_potential_score", 0) > 0]
        if not success_scored:
            logger.error("All articles received fallback 0 score. LLM evaluation call failed or was empty.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"LLM virality scoring failed: {e}")
        sys.exit(1)
        
    logger.info(f"Successfully evaluated and scored {len(scored)} articles.")
    
    # 4. Insert into database
    to_insert = []
    for a in scored:
        to_insert.append({
            "title": a["title"],
            "description": a.get("description", ""),
            "url": a.get("url", ""),
            "source": a.get("source", ""),
            "published_at": a.get("publishedAt") if a.get("publishedAt") else None,
            "viral_potential_score": int(a.get("viral_potential_score", 0)),
            "recommended_angle": a.get("recommended_angle", ""),
            "target_niches": a.get("target_niches", [])
        })
        
    try:
        # Clear existing predictions before upserting fresh predictions
        supabase.table("news_virality_predictions").delete().neq("title", "").execute()
        res = supabase.table("news_virality_predictions").upsert(to_insert).execute()
        logger.info(f"Successfully saved {len(res.data)} predictions to news_virality_predictions table.")
    except Exception as e:
        logger.error(f"Failed to insert predictions into database: {e}")
        sys.exit(1)
        
    # 5. Print high-level summary of top 5 articles by virality score
    print("\n==================================================")
    print("      TOP EMERGING VIRAL NEWS PREDICTIONS         ")
    print("==================================================")
    sorted_scored = sorted(scored, key=lambda x: x.get("viral_potential_score", 0), reverse=True)
    for idx, a in enumerate(sorted_scored[:5], start=1):
        print(f"{idx}. {a['title']}")
        print(f"   Score: {a.get('viral_potential_score', 0)} | Angle: {a.get('recommended_angle', '')} | Niches: {a.get('target_niches', [])}")
        print(f"   Source: {a.get('source', '')} | Link: {a.get('url', '')}")
        print("-" * 50)

if __name__ == "__main__":
    run_news_check()
