import os
import sys
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

# Configure logging
logger = logging.getLogger("news_client")

load_dotenv("backend/.env")

class NewsClient:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        self.gnews_api_key = os.getenv("GNEWS_API_KEY")
        
        # We need the service_role key to write to/read from news_api_cache due to RLS policies
        if self.supabase_url and self.supabase_key:
            try:
                self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                logger.error(f"Failed to create Supabase client in NewsClient: {e}")
                self.supabase = None
        else:
            self.supabase = None

    def _get_cached_query(self, query: str) -> list | None:
        if not self.supabase:
            return None
        try:
            res = self.supabase.table("news_api_cache").select("*").eq("query", query).execute()
            if res.data:
                cached = res.data[0]
                created_at_str = cached.get("created_at")
                if created_at_str:
                    # Parse timestamp (e.g. 2026-07-24T17:12:00+00:00)
                    if created_at_str.endswith("Z"):
                        created_at_str = created_at_str[:-1] + "+00:00"
                    created_at = datetime.fromisoformat(created_at_str)
                    
                    # 1 hour expiration
                    now_utc = datetime.now(timezone.utc)
                    if now_utc - created_at < timedelta(hours=1):
                        logger.info(f"Cache hit for query: '{query}'")
                        return cached.get("response")
                    else:
                        logger.info(f"Cache expired for query: '{query}'")
            return None
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return None

    def _set_cached_query(self, query: str, response: list):
        if not self.supabase:
            return
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            self.supabase.table("news_api_cache").upsert({
                "query": query,
                "response": response,
                "created_at": now_iso
            }).execute()
            logger.info(f"Cached query results for: '{query}'")
        except Exception as e:
            logger.error(f"Error writing to cache: {e}")

    def fetch_gnews(self, query: str) -> list:
        if not self.gnews_api_key:
            raise ValueError("GNEWS_API_KEY not configured")
        
        logger.info(f"Querying GNews API for: '{query}'")
        url = "https://gnews.io/api/v4/search"
        params = {
            "q": query,
            "lang": "en",
            "country": "in",
            "max": 5,
            "apikey": self.gnews_api_key
        }
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        
        data = res.json()
        articles = data.get("articles", [])
        
        results = []
        for a in articles:
            results.append({
                "title": a.get("title", ""),
                "description": a.get("description", ""),
                "url": a.get("url", ""),
                "publishedAt": a.get("publishedAt", ""),
                "source": a.get("source", {}).get("name", "GNews")
            })
        return results

    def fetch_google_news_rss(self, query: str) -> list:
        logger.info(f"Querying Google News RSS fallback for: '{query}'")
        url = "https://news.google.com/rss/search"
        params = {
            "q": query,
            "hl": "en-IN",
            "gl": "IN",
            "ceid": "IN:en"
        }
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(res.content)
        items = root.findall(".//item")
        
        results = []
        # Return at most 5 articles
        for item in items[:5]:
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
            description = item.find("description").text if item.find("description") is not None else ""
            source = item.find("source").text if item.find("source") is not None else "Google News RSS"
            
            # Parse pub_date to ISO-8601 if possible
            try:
                # format: Fri, 24 Jul 2026 12:00:00 GMT
                dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                published_at = dt.replace(tzinfo=timezone.utc).isoformat()
            except Exception as _date_err:
                logger.debug(f"fetch_google_news_rss: could not parse pubDate '{pub_date}': {_date_err}; using raw string")
                published_at = pub_date
                
            results.append({
                "title": title,
                "description": description,
                "url": link,
                "publishedAt": published_at,
                "source": source
            })
        return results

    def get_trending_news(self, query: str) -> list:
        # 1. Clean query
        query_clean = query.strip().lower()
        if not query_clean:
            return []
            
        # 2. Check cache
        cached = self._get_cached_query(query_clean)
        if cached is not None:
            return cached
            
        # 3. Fetch from GNews
        articles = []
        try:
            if self.gnews_api_key:
                articles = self.fetch_gnews(query_clean)
            else:
                logger.info("No GNEWS_API_KEY, falling back to Google News RSS")
                articles = self.fetch_google_news_rss(query_clean)
        except Exception as e:
            logger.warning(f"GNews API failed: {e}. Falling back to Google News RSS...")
            try:
                articles = self.fetch_google_news_rss(query_clean)
            except Exception as rss_err:
                logger.error(f"Google News RSS fallback also failed: {rss_err}")
                articles = []
                
        # 4. Save cache
        self._set_cached_query(query_clean, articles)
        return articles

def check_keyword_overlap(trend_keywords: list[str], article: dict) -> float:
    """
    Returns a similarity score between 0.0 and 1.0 based on overlap between trend keywords 
    and the news article's title/description.
    """
    text = f"{article.get('title', '')} {article.get('description', '')}".lower()
    if not text or not trend_keywords:
        return 0.0
        
    matches = 0
    total_len = len(trend_keywords)
    for kw in trend_keywords:
        # Check simple substring match or word boundaries
        if kw.lower() in text:
            matches += 1
            
    return matches / total_len if total_len > 0 else 0.0


def evaluate_news_virality_batch(articles: list[dict], batch_size: int = 8) -> list[dict]:
    """
    Evaluate news items for virality in chunks of up to batch_size to prevent token overflow.
    Uses unified call_llm from llm.py.
    """
    from llm import call_llm

    scored_articles = []
    
    # Process articles in chunks of batch_size (default 20)
    for chunk_start in range(0, len(articles), batch_size):
        chunk = articles[chunk_start:chunk_start + batch_size]
        blocks = []
        for i, a in enumerate(chunk):
            blocks.append(f"{i+1}. Title: {a['title']}\n   Summary: {a.get('description', '')[:200]}")

        system_prompt = "You are a social media trend forecaster predicting Instagram Reels virality."
        user_prompt = f"""Rate each news item below for its potential to go viral on Instagram Reels in India, over the next 24-48 hours.

For each item return: viral_potential_score (0-100), recommended_angle (e.g. POV, greenscreen, commentary, reaction), target_niches (array of strings).

Respond ONLY in JSON matching this exact structure:
{{
  "items": [
    {{"index": 1, "viral_potential_score": 85, "recommended_angle": "greenscreen", "target_niches": ["sports", "comedy"]}}
  ]
}}

Items to evaluate:
{chr(10).join(blocks)}
"""
        try:
            res = call_llm(system_prompt=system_prompt, user_prompt=user_prompt, response_mime_type="application/json")
            items = res.get("items", [])
            for item in items:
                idx = item.get("index", 1) - 1
                if 0 <= idx < len(chunk):
                    art = chunk[idx].copy()
                    art["viral_potential_score"] = item.get("viral_potential_score", 0)
                    art["recommended_angle"] = item.get("recommended_angle", "")
                    art["target_niches"] = item.get("target_niches", [])
                    scored_articles.append(art)
        except Exception as e:
            logger.error(f"Error scoring news batch starting at {chunk_start}: {e}")
            # Fallback for failed batch: default scores
            for a in chunk:
                art = a.copy()
                art["viral_potential_score"] = 0
                art["recommended_angle"] = "commentary"
                art["target_niches"] = []
                scored_articles.append(art)

    return scored_articles

