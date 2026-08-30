import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client

# Importing individual signal detectors
from format_trend_detector import FormatTrendDetector
from news_client import NewsClient, evaluate_news_virality_batch
# from comment_clustering import detect_meme_patterns
from niche_relevance_engine import compute_niche_relevance, generate_adaptation_brief
from alert_system import AlertSystem

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("unified_signal_processor")

load_dotenv("backend/.env")

class UnifiedSignalProcessor:
    """
    Collects signals from all sources (Format, News, Cultural Events, Memes)
    and fuses them into the `content_trends` table with niche enrichment.
    """
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be configured")
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.alert_system = AlertSystem()
        self.news_client = NewsClient()

    def _enrich_with_niche(self, signal: dict) -> dict:
        """Adds niche_relevance and adaptation_briefs to a signal."""
        # Score the signal across all niches
        niche_scores = compute_niche_relevance(signal)
        
        # Keep only niches with score > 0.3
        relevant_niches = {n: s for n, s in niche_scores.items() if s > 0.3}
        signal["niche_relevance"] = relevant_niches
        
        # Generate adaptation briefs for relevant niches
        briefs = {}
        for niche, score in relevant_niches.items():
            brief_data = generate_adaptation_brief(signal, niche, score)
            if brief_data:
                briefs[niche] = brief_data.get("brief", "")
                
        signal["adaptation_briefs"] = briefs
        return signal

    def process_format_trends(self, hours: int = 24) -> List[Dict]:
        logger.info(f"Processing format trends for last {hours} hours...")
        try:
            detector = FormatTrendDetector()
            # Assuming FormatTrendDetector has a method to get active patterns
            patterns = detector.detect_trending_patterns(hours_lookback=hours)
            
            signals = []
            for p in patterns:
                signal = {
                    "trend_type": "format",
                    "trend_name": p.get("trend_name", "Format Trend"),
                    "template_pattern": p.get("template_pattern"),
                    "reel_count": p.get("reel_count", 0),
                    "velocity_avg": p.get("velocity", 0.0),
                    "confidence": p.get("confidence", 50.0),
                    "status": "emerging"
                }
                signals.append(self._enrich_with_niche(signal))
            return signals
        except Exception as e:
            logger.error(f"Failed to process format trends: {e}")
            return []

    def process_news_events(self) -> List[Dict]:
        logger.info("Processing breaking news events...")
        try:
            categories = ['india', 'sports', 'entertainment', 'geopolitics', 'current_affairs', 'disaster']
            articles = []
            for cat in categories:
                res = self.news_client.get_trending_news(cat)
                articles.extend(res)

            # Deduplicate by URL
            unique_articles = {a.get('url'): a for a in articles if a.get('url')}
            articles_list = list(unique_articles.values())
            
            # Evaluate virality
            scored_news = evaluate_news_virality_batch(articles_list, batch_size=8)
            
            signals = []
            for n in scored_news:
                if n.get("viral_potential_score", 0) > 60:
                    signal = {
                        "trend_type": "news",
                        "trend_name": n["title"],
                        "template_pattern": f"news_{n.get('url', '')[-20:]}",
                        "topic_keywords": n.get("target_niches", []),
                        "velocity_avg": float(n.get("viral_potential_score", 0)),
                        "confidence": float(n.get("viral_potential_score", 0)),
                        "status": "rising"
                    }
                    signals.append(self._enrich_with_niche(signal))
            return signals
        except Exception as e:
            logger.error(f"Failed to process news events: {e}")
            return []

    def process_cultural_events(self, days_ahead: int = 7) -> List[Dict]:
        logger.info(f"Processing cultural events for next {days_ahead} days from DB...")
        try:
            # Query cultural_events from DB instead of hardcoded Python dict
            now_date = datetime.now(timezone.utc).date()
            future_date = now_date + timedelta(days=days_ahead)
            
            res = self.supabase.table("cultural_events") \
                .select("*") \
                .gte("start_date", now_date.isoformat()) \
                .lte("start_date", future_date.isoformat()) \
                .execute()
                
            events = res.data or []
            signals = []
            
            for e in events:
                start = datetime.fromisoformat(e["start_date"]).date()
                days_until = (start - now_date).days
                
                # Confidence higher if it's closer
                confidence = max(50, 100 - (days_until * 10))
                
                signal = {
                    "trend_type": "event",
                    "trend_name": e["name"],
                    "template_pattern": e["slug"],
                    "topic_keywords": e.get("primary_regions", []),
                    "velocity_avg": float(e.get("feed_flood_intensity", 0) * 100),
                    "confidence": confidence,
                    "status": "emerging",
                    # Pre-load DB niche opportunities if present
                    "niche_relevance": e.get("niche_opportunities", {}),
                }
                # Enrich with any additional niches
                signal = self._enrich_with_niche(signal)
                
                # Override adaptation briefs with specific content ideas if provided by the event DB
                if e.get("content_ideas"):
                    signal["adaptation_briefs"] = e["content_ideas"]
                    
                signals.append(signal)
            return signals
        except Exception as e:
            logger.error(f"Failed to process cultural events: {e}")
            return []

    def process_meme_patterns(self, hours: int = 12) -> List[Dict]:
        logger.info(f"Processing meme patterns for last {hours} hours...")
        try:
            meme_signals = [] # detect_meme_patterns(hours=hours)
            signals = []
            for m in meme_signals:
                signal = {
                    "trend_type": "meme",
                    "trend_name": m.get("cluster_name", "Meme Trend"),
                    "template_pattern": f"meme_{m.get('cluster_id', '')}",
                    "reel_count": m.get("reel_count", 0),
                    "velocity_avg": m.get("velocity", 0.0),
                    "confidence": m.get("confidence", 50.0),
                    "status": "emerging"
                }
                signals.append(self._enrich_with_niche(signal))
            return signals
        except Exception as e:
            logger.error(f"Failed to process meme patterns: {e}")
            return []

    def process_global_events(self) -> List[Dict]:
        logger.info("Processing global events from event_monitor...")
        try:
            from event_monitor import EventMonitor
            em = EventMonitor()
            active_events = em.get_active_events(days_ahead=14, days_behind=3)
            
            signals = []
            for ev in active_events:
                signal = {
                    "trend_type": "event",
                    "trend_name": ev.name,
                    "template_pattern": f"event_{ev.id}",
                    "topic_keywords": ev.hashtags[:5],
                    "velocity_avg": float(ev.viral_potential or 50.0),
                    "confidence": 80.0,
                    "status": "rising",
                }
                signals.append(self._enrich_with_niche(signal))
            return signals
        except Exception as e:
            logger.error(f"Failed to process global events: {e}")
            return []

    def save_signals_to_db(self, signals: List[Dict]):
        if not signals:
            logger.info("No signals to save.")
            return

        logger.info(f"Saving {len(signals)} unified signals to content_trends table...")
        to_upsert = []
        for s in signals:
            if not s.get("template_pattern") or not s.get("trend_type"):
                continue
                
            to_upsert.append({
                "trend_type": s["trend_type"],
                "trend_name": s["trend_name"],
                "template_pattern": s["template_pattern"],
                "topic_keywords": s.get("topic_keywords", []),
                "reel_count": s.get("reel_count", 0),
                "velocity_avg": s.get("velocity_avg", 0.0),
                "confidence": s.get("confidence", 0.0),
                "status": s.get("status", "emerging"),
                "niche_relevance": s.get("niche_relevance", {}),
                "adaptation_briefs": s.get("adaptation_briefs", {}),
                "last_updated_at": datetime.now(timezone.utc).isoformat()
            })
            
        try:
            res = self.supabase.table("content_trends").upsert(
                to_upsert, 
                on_conflict="trend_type,template_pattern"
            ).execute()
            logger.info(f"Successfully saved {len(res.data)} content trends.")
            return [t['id'] for t in res.data] if res.data else []
        except Exception as e:
            logger.error(f"Failed to save signals to content_trends: {e}")
            return []

    def run_full_cycle(self):
        """Runs all detectors, enriches, saves to DB, and fires alerts."""
        logger.info("=== Starting Unified Signal Processor Cycle ===")
        all_signals = []
        
        # 1. Collect signals
        all_signals.extend(self.process_format_trends())
        all_signals.extend(self.process_news_events())
        all_signals.extend(self.process_cultural_events())
        all_signals.extend(self.process_global_events())
        
        # 2. Write to content_trends table
        saved_ids = self.save_signals_to_db(all_signals)
        
        # 3. Trigger alerts for high urgency signals
        if saved_ids:
            self.alert_system.send_trend_alerts(saved_ids)
        logger.info("=== Completed Unified Signal Processor Cycle ===")
        
if __name__ == "__main__":
    processor = UnifiedSignalProcessor()
    processor.run_full_cycle()
