#!/usr/bin/env python3
"""
Dynamic Hashtag Discovery - Discovers and manages trending hashtags for early detection
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

logger = logging.getLogger(__name__)

# Initial micro-creator hashtag pools
MICRO_CREATOR_POOLS = {
    "MICRO_DANCE": [
        "#microdance", "#trendingdance", "#viralchallenge", "#dancehacks",
        "#indiandance", "#southdance", "#bangaloredance", "#punjabidance"
    ],
    "MICRO_FOOD": [
        "#foodcreators", "#microfood", "#tastyfood", "#indianfood",
        "#streetfood", "#foodrecipe", "#kitchenhacks", "#homecooking"
    ],
    "MICRO_FASHION": [
        "#fashionhacks", "#styletips", "#outfitideas", "#microfashion",
        "#indianfashion", "#sareestyle", "#fashiondiy", "#budgetfashion"
    ],
    "MICRO_COMEDY": [
        "#funnyreels", "#comedyhacks", "#relatable", "#microcomedy",
        "#indiancomedy", "#viralcomedy", "#humor", "#troll"
    ]
}

# Hashtag evaluation criteria
HASHTAG_EVALUATION_THRESHOLDS = {
    "early_signal_rate": 0.15,  # 15% of reels with this hashtag are early signals
    "micro_creator_ratio": 0.6,  # 60% of creators are micro/nano
    "geographic_diversity": 50,  # At least 50/100 diversity score
    "min_use_count": 50  # At least 50 reels using the hashtag
}

class DynamicHashtagDiscovery:
    """
    Discovers and manages trending hashtags for early detection
    """
    
    def __init__(self):
        self.supabase = sb
    
    def initialize_hashtag_pools(self) -> dict:
        """
        Initialize hashtag pools in database
        """
        try:
            added_count = 0
            skipped_count = 0
            
            for pool_name, hashtags in MICRO_CREATOR_POOLS.items():
                for hashtag in hashtags:
                    # Check if hashtag already exists
                    result = self.supabase.table('hashtag_performance').select('*').eq('hashtag', hashtag.lstrip('#')).execute()
                    
                    if not result.data:
                        # Add new hashtag
                        self.supabase.table('hashtag_performance').insert({
                            'hashtag': hashtag.lstrip('#'),
                            'pool_name': pool_name,
                            'avg_velocity': 0,
                            'early_signal_count': 0,
                            'viral_conversion_rate': 0,
                            'micro_creator_ratio': 0,
                            'geographic_diversity_score': 0,
                            'performance_score': 0,
                            'added_to_pool_at': datetime.now(timezone.utc).isoformat(),
                            'status': 'active'
                        }).execute()
                        added_count += 1
                    else:
                        skipped_count += 1
            
            return {
                "success": True,
                "added_count": added_count,
                "skipped_count": skipped_count,
                "total_hashtags": len([h for pool in MICRO_CREATOR_POOLS.values() for h in pool])
            }
        except Exception as e:
            logger.error(f"Error initializing hashtag pools: {e}")
            return {"success": False, "error": str(e)}
    
    def evaluate_hashtag_performance(self, hashtag: str) -> dict:
        """
        Evaluate hashtag performance for early detection potential
        """
        try:
            # Get reels using this hashtag (paginated — Supabase default limit is 1000)
            reels = []
            offset = 0
            PAGE = 1000
            while True:
                page = self.supabase.table('reels').select('*').contains('hashtags', [hashtag]).range(offset, offset + PAGE - 1).execute()
                reels.extend(page.data or [])
                if not page.data or len(page.data) < PAGE:
                    break
                offset += PAGE

            if not reels:
                return {
                    "hashtag": hashtag,
                    "early_signal_rate": 0,
                    "micro_creator_ratio": 0,
                    "geographic_diversity": 0,
                    "performance_score": 0,
                    "evaluation": "insufficient_data"
                }
            
            total_reels = len(reels)
            
            # Count early signals (from early_signals table)
            early_signal_result = self.supabase.table('early_signals').select('*').execute()
            early_signal_reel_ids = [signal['reel_id'] for signal in early_signal_result.data]
            
            early_signal_count = sum(1 for reel in reels if reel.get('id') in early_signal_reel_ids)
            early_signal_rate = early_signal_count / total_reels if total_reels > 0 else 0
            
            # Calculate micro creator ratio
            micro_creators = sum(1 for reel in reels if reel.get('owner_follower_count', 0) < 10000)
            micro_creator_ratio = micro_creators / total_reels if total_reels > 0 else 0
            
            # Get geographic diversity (simplified)
            geographic_diversity = self._calculate_hashtag_geographic_diversity(reels)
            
            # Calculate performance score
            performance_score = self._calculate_performance_score(
                early_signal_rate,
                micro_creator_ratio,
                geographic_diversity,
                total_reels
            )
            
            # Determine evaluation
            if performance_score > 70:
                evaluation = "high_potential"
            elif performance_score > 50:
                evaluation = "moderate_potential"
            elif performance_score > 30:
                evaluation = "low_potential"
            else:
                evaluation = "poor"
            
            return {
                "hashtag": hashtag,
                "early_signal_rate": early_signal_rate,
                "micro_creator_ratio": micro_creator_ratio,
                "geographic_diversity": geographic_diversity,
                "performance_score": performance_score,
                "evaluation": evaluation,
                "total_reels": total_reels,
                "early_signal_count": early_signal_count
            }
        except Exception as e:
            logger.error(f"Error evaluating hashtag performance for {hashtag}: {e}")
            return {"hashtag": hashtag, "performance_score": 0, "evaluation": "error"}
    
    def _calculate_hashtag_geographic_diversity(self, reels: list) -> float:
        """
        Calculate geographic diversity for hashtag (simplified)
        """
        # This would use the geographic spread analyzer
        # For now, return a simplified score
        unique_captions = len(set(reel.get('caption', '') for reel in reels))
        return min(100, unique_captions * 2)
    
    def _calculate_performance_score(self, early_signal_rate: float, micro_creator_ratio: float, 
                                     geographic_diversity: float, use_count: int) -> float:
        """
        Calculate overall performance score
        """
        # Weighted components
        early_signal_score = (early_signal_rate / HASHTAG_EVALUATION_THRESHOLDS["early_signal_rate"]) * 100
        micro_creator_score = (micro_creator_ratio / HASHTAG_EVALUATION_THRESHOLDS["micro_creator_ratio"]) * 100
        geographic_score = geographic_diversity
        use_count_score = min(100, (use_count / HASHTAG_EVALUATION_THRESHOLDS["min_use_count"]) * 100)
        
        # Weighted average
        performance_score = (
            (early_signal_score * 0.4) +
            (micro_creator_score * 0.3) +
            (geographic_score * 0.2) +
            (use_count_score * 0.1)
        )
        
        return min(100, performance_score)
    
    def discover_new_hashtags(self, pool_name: str, limit: int = 5) -> List[str]:
        """
        Discover new trending hashtags from recent reels
        """
        try:
            # Get recent reels from the pool's existing hashtags
            existing_hashtags = MICRO_CREATOR_POOLS.get(pool_name, [])
            
            # Get reels with similar hashtags
            recent_reels = []
            for hashtag in existing_hashtags:
                result = self.supabase.table('reels').select('hashtags').contains('hashtags', [hashtag]).order('created_at', desc=True).limit(100).execute()
                recent_reels.extend(result.data)
            
            # Extract all hashtags from these reels
            all_hashtags = defaultdict(int)
            for reel in recent_reels:
                hashtags = reel.get('hashtags', [])
                for tag in hashtags:
                    all_hashtags[tag] += 1
            
            # Filter out existing hashtags
            new_hashtags = {tag: count for tag, count in all_hashtags.items() 
                           if tag not in [h.lstrip('#') for h in existing_hashtags]}
            
            # Sort by frequency
            sorted_hashtags = sorted(new_hashtags.items(), key=lambda x: x[1], reverse=True)
            
            # Return top candidates
            return [tag for tag, count in sorted_hashtags[:limit]]
        except Exception as e:
            logger.error(f"Error discovering new hashtags for {pool_name}: {e}")
            return []
    
    def add_hashtag_to_pool(self, hashtag: str, pool_name: str) -> dict:
        """
        Add a new hashtag to a pool
        """
        try:
            # Check if hashtag already exists
            result = self.supabase.table('hashtag_performance').select('*').eq('hashtag', hashtag.lstrip('#')).execute()
            
            if result.data:
                # Update existing hashtag
                self.supabase.table('hashtag_performance').update({
                    'pool_name': pool_name,
                    'status': 'active'
                }).eq('hashtag', hashtag.lstrip('#')).execute()
                
                return {"success": True, "action": "updated"}
            else:
                # Add new hashtag
                self.supabase.table('hashtag_performance').insert({
                    'hashtag': hashtag.lstrip('#'),
                    'pool_name': pool_name,
                    'avg_velocity': 0,
                    'early_signal_count': 0,
                    'viral_conversion_rate': 0,
                    'micro_creator_ratio': 0,
                    'geographic_diversity_score': 0,
                    'performance_score': 0,
                    'added_to_pool_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'active'
                }).execute()
                
                return {"success": True, "action": "created"}
        except Exception as e:
            logger.error(f"Error adding hashtag {hashtag} to pool {pool_name}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_pool_hashtags(self, pool_name: str) -> List[str]:
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

    def remove_poor_performing_hashtags(self, threshold: float = 30) -> dict:
        """
        Remove hashtags with poor performance scores
        """
        try:
            # Get hashtags below threshold
            result = self.supabase.table('hashtag_performance').select('*').lt('performance_score', threshold).execute()
            
            removed_count = 0
            for hashtag in result.data:
                self.supabase.table('hashtag_performance').update({
                    'status': 'inactive'
                }).eq('id', hashtag['id']).execute()
                removed_count += 1
            
            return {
                "success": True,
                "removed_count": removed_count
            }
        except Exception as e:
            logger.error(f"Error removing poor performing hashtags: {e}")
            return {"success": False, "error": str(e)}
    
    def get_pool_performance_summary(self) -> dict:
        """
        Get performance summary for all hashtag pools
        """
        try:
            summary = {}
            
            for pool_name in MICRO_CREATOR_POOLS.keys():
                result = self.supabase.table('hashtag_performance').select('*').eq('pool_name', pool_name).eq('status', 'active').execute()
                
                if result.data:
                    avg_score = sum(h.get('performance_score', 0) for h in result.data) / len(result.data)
                    total_hashtags = len(result.data)
                    
                    summary[pool_name] = {
                        "total_hashtags": total_hashtags,
                        "avg_performance_score": avg_score,
                        "high_performing": sum(1 for h in result.data if h.get('performance_score', 0) > 70),
                        "low_performing": sum(1 for h in result.data if h.get('performance_score', 0) < 30)
                    }
            
            return {
                "success": True,
                "pool_summary": summary
            }
        except Exception as e:
            logger.error(f"Error getting pool performance summary: {e}")
            return {"success": False, "error": str(e)}

# Global instance
hashtag_discovery = DynamicHashtagDiscovery()