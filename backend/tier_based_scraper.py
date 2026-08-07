#!/usr/bin/env python3
"""
Tier-based Scraping Orchestrator - Implements tier-based scraping strategy
"""

import os
import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

logger = logging.getLogger(__name__)

# Scraper configuration tiers
SCRAPER_TIERS = {
    "micro_pool": {
        "frequency_hours": 1,  # Hourly for micro pools
        "reels_per_hashtag": 50,
        "max_creators": 100,
        "priority": "high"
    },
    "main_pool": {
        "frequency_hours": 8,  # Every 8 hours for main pools
        "reels_per_hashtag": 100,
        "max_creators": 500,
        "priority": "normal"
    },
    "monitoring": {
        "frequency_hours": 0.5,  # Every 30 minutes for monitoring
        "reels_per_hashtag": 20,
        "max_creators": 50,
        "priority": "critical"
    }
}

# Hashtag pool assignments
HASHTAG_POOL_ASSIGNMENTS = {
    "micro": ["MICRO_DANCE", "MICRO_FOOD", "MICRO_FASHION", "MICRO_COMEDY"],
    "main": ["INDIA_TRENDING", "INDIA_VERNACULAR", "GLOBAL_NICHES", "GLOBAL_DISCOVERY"],
    "monitoring": ["MICRO_DANCE", "MICRO_FOOD"]  # Top performers for monitoring
}

class TierBasedScraper:
    """
    Implements tier-based scraping strategy for early detection
    """
    
    def __init__(self):
        self.supabase = sb
        self.last_scrape_times = {}
    
    def get_scrape_schedule(self) -> Dict[str, Dict]:
        """
        Get the current scrape schedule based on tiers
        """
        now = datetime.now(timezone.utc)
        schedule = {}
        
        for tier_name, tier_config in SCRAPER_TIERS.items():
            pools = HASHTAG_POOL_ASSIGNMENTS.get(tier_name, [])
            
            for pool_name in pools:
                last_scrape = self.last_scrape_times.get(f"{tier_name}_{pool_name}")
                
                if last_scrape:
                    time_since_scrape = (now - last_scrape).total_seconds() / 3600
                    should_scrape = time_since_scrape >= tier_config["frequency_hours"]
                else:
                    should_scrape = True
                
                schedule[f"{tier_name}_{pool_name}"] = {
                    "should_scrape": should_scrape,
                    "priority": tier_config["priority"],
                    "reels_per_hashtag": tier_config["reels_per_hashtag"],
                    "frequency_hours": tier_config["frequency_hours"],
                    "last_scrape": last_scrape.isoformat() if last_scrape else None,
                    "time_since_scrape_hours": (now - last_scrape).total_seconds() / 3600 if last_scrape else None
                }
        
        return schedule
    
    def execute_tier_scrape(self, tier_name: str, pool_name: str) -> Dict:
        """
        Execute scrape for a specific tier and pool
        """
        try:
            tier_config = SCRAPER_TIERS.get(tier_name)
            if not tier_config:
                return {"success": False, "error": f"Unknown tier: {tier_name}"}
            
            # Get hashtags for this pool
            pool_hashtags = self._get_pool_hashtags(pool_name)
            if not pool_hashtags:
                return {"success": False, "error": f"No hashtags found for pool: {pool_name}"}
            
            # Execute scrape (placeholder - would call actual scraper)
            scraped_count = self._simulate_scrape(pool_hashtags, tier_config["reels_per_hashtag"])
            
            # Update last scrape time
            self.last_scrape_times[f"{tier_name}_{pool_name}"] = datetime.now(timezone.utc)
            
            return {
                "success": True,
                "tier": tier_name,
                "pool": pool_name,
                "hashtags_scraped": len(pool_hashtags),
                "reels_scraped": scraped_count,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Error executing tier scrape for {tier_name}/{pool_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_pool_hashtags(self, pool_name: str) -> List[str]:
        """
        Get hashtags for a specific pool
        """
        try:
            # Get from hashtag_performance table
            result = self.supabase.table('hashtag_performance').select('hashtag').eq('pool_name', pool_name).eq('status', 'active').execute()
            
            if result.data:
                return [row['hashtag'] for row in result.data]
            
            # Fallback to classification rules
            from classification_rules import HASHTAG_POOL_MAP
            return list(HASHTAG_POOL_MAP.get(pool_name, set()))
        except Exception as e:
            logger.error(f"Error getting pool hashtags for {pool_name}: {e}")
            return []
    
    def _simulate_scrape(self, hashtags: List[str], reels_per_hashtag: int) -> int:
        """
        Simulate scraping (placeholder for actual scraper integration)
        """
        # This would be replaced with actual scraper call
        total_reels = len(hashtags) * reels_per_hashtag
        logger.info(f"Simulated scrape: {len(hashtags)} hashtags × {reels_per_hashtag} reels = {total_reels} reels")
        return total_reels
    
    def execute_schedule(self) -> Dict:
        """
        Execute all scheduled scrapes
        """
        schedule = self.get_scrape_schedule()
        results = {
            "total_pools": len(schedule),
            "scraped_pools": 0,
            "skipped_pools": 0,
            "failed_pools": 0,
            "details": []
        }
        
        for pool_key, pool_schedule in schedule.items():
            if pool_schedule["should_scrape"]:
                tier_name, pool_name = pool_key.split("_", 1)
                result = self.execute_tier_scrape(tier_name, pool_name)
                
                if result.get("success"):
                    results["scraped_pools"] += 1
                else:
                    results["failed_pools"] += 1
                
                results["details"].append({
                    "pool": pool_key,
                    "result": result
                })
            else:
                results["skipped_pools"] += 1
                results["details"].append({
                    "pool": pool_key,
                    "skipped": True,
                    "reason": f"Last scrape was {pool_schedule['time_since_scrape_hours']:.1f} hours ago (frequency: {pool_schedule['frequency_hours']}h)"
                })
        
        return results
    
    def get_pool_statistics(self) -> Dict:
        """
        Get statistics for all hashtag pools
        """
        try:
            stats = {}
            
            for pool_name in list(HASHTAG_POOL_ASSIGNMENTS["micro"]) + list(HASHTAG_POOL_ASSIGNMENTS["main"]):
                result = self.supabase.table('hashtag_performance').select('*').eq('pool_name', pool_name).execute()
                
                if result.data:
                    avg_score = sum(h.get('performance_score', 0) for h in result.data) / len(result.data)
                    early_signal_count = sum(h.get('early_signal_count', 0) for h in result.data)
                    
                    stats[pool_name] = {
                        "total_hashtags": len(result.data),
                        "avg_performance_score": avg_score,
                        "total_early_signals": early_signal_count,
                        "high_performing": sum(1 for h in result.data if h.get('performance_score', 0) > 70),
                        "low_performing": sum(1 for h in result.data if h.get('performance_score', 0) < 30)
                    }
            
            return {"success": True, "pool_statistics": stats}
        except Exception as e:
            logger.error(f"Error getting pool statistics: {e}")
            return {"success": False, "error": str(e)}

# Global instance
tier_scraper = TierBasedScraper()