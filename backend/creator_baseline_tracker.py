#!/usr/bin/env python3
"""
Creator Baseline Tracker - Tracks creator performance baselines for velocity comparison
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Initialize Supabase client
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

logger = logging.getLogger(__name__)

# Creator tier thresholds
CREATOR_TIER_THRESHOLDS = {
    "nano": (0, 1000),
    "micro": (1000, 10000),
    "mid_tier": (10000, 100000),
    "macro": (100000, 1000000),
    "mega": (1000000, float('inf'))
}

class CreatorBaselineTracker:
    """
    Tracks creator performance baselines for velocity comparison
    """
    
    def __init__(self):
        self.supabase = sb
    
    def calculate_creator_tier(self, follower_count: int) -> str:
        """
        Classify creator into performance tier
        """
        for tier, (min_followers, max_followers) in CREATOR_TIER_THRESHOLDS.items():
            if min_followers <= follower_count < max_followers:
                return tier
        return "mega"
    
    def update_creator_baseline(self, username: str, reel_data: dict) -> dict:
        """
        Update creator's performance baseline
        """
        try:
            # Check if creator baseline exists
            result = self.supabase.table('creator_baselines').select('*').eq('username', username).execute()
            
            if result.data:
                # Update existing baseline
                baseline = result.data[0]
                self._update_existing_baseline(baseline, reel_data)
                
                # Update in database
                self.supabase.table('creator_baselines').update({
                    'avg_engagement': baseline['avg_engagement'],
                    'avg_velocity': baseline['avg_velocity'],
                    'content_frequency': baseline['content_frequency'],
                    'follower_count': reel_data.get('follower_count', baseline['follower_count']),
                    'creator_tier': baseline['creator_tier'],
                    'last_updated': datetime.now(timezone.utc).isoformat()
                }).eq('username', username).execute()
                
                return {"success": True, "action": "updated", "baseline": baseline}
            else:
                # Create new baseline
                new_baseline = self._create_new_baseline(username, reel_data)
                
                # Insert into database
                self.supabase.table('creator_baselines').insert(new_baseline).execute()
                
                return {"success": True, "action": "created", "baseline": new_baseline}
        except Exception as e:
            logger.error(f"Error updating creator baseline for {username}: {e}")
            return {"success": False, "error": str(e)}
    
    def _update_existing_baseline(self, baseline: dict, reel_data: dict) -> dict:
        """
        Update existing baseline with new reel data
        """
        # Calculate new engagement
        engagement = reel_data.get('view_count', 0) + (reel_data.get('like_count', 0) * 3) + (reel_data.get('comment_count', 0) * 5)
        
        # Calculate velocity
        hours_live = reel_data.get('hours_live', 1.0)
        velocity = engagement / hours_live if hours_live > 0 else engagement
        
        # Calculate moving averages (simplified)
        old_avg_engagement = baseline.get('avg_engagement', 1000)
        old_avg_velocity = baseline.get('avg_velocity', 100)
        
        # Weighted average (20% new, 80% old)
        new_avg_engagement = (engagement * 0.2) + (old_avg_engagement * 0.8)
        new_avg_velocity = (velocity * 0.2) + (old_avg_velocity * 0.8)
        
        # Update content frequency (posts per week - simplified)
        old_frequency = baseline.get('content_frequency', 1.0)
        new_frequency = (old_frequency * 0.9) + (1.0 * 0.1)  # Add 1 post
        
        baseline['avg_engagement'] = new_avg_engagement
        baseline['avg_velocity'] = new_avg_velocity
        baseline['content_frequency'] = new_frequency
        baseline['follower_count'] = reel_data.get('follower_count', baseline['follower_count'])
        baseline['creator_tier'] = self.calculate_creator_tier(reel_data.get('follower_count', baseline['follower_count']))
        baseline['last_updated'] = datetime.now(timezone.utc).isoformat()
        
        return baseline
    
    def _create_new_baseline(self, username: str, reel_data: dict) -> dict:
        """
        Create new baseline for creator
        """
        # Calculate initial metrics
        engagement = reel_data.get('view_count', 0) + (reel_data.get('like_count', 0) * 3) + (reel_data.get('comment_count', 0) * 5)
        
        hours_live = reel_data.get('hours_live', 1.0)
        velocity = engagement / hours_live if hours_live > 0 else engagement
        
        return {
            'username': username,
            'follower_count': reel_data.get('follower_count', 0),
            'avg_engagement': engagement,
            'avg_velocity': velocity,
            'content_frequency': 1.0,  # Assume 1 post per week initially
            'niche_tendencies': self._analyze_niche_tendencies(reel_data),
            'creator_tier': self.calculate_creator_tier(reel_data.get('follower_count', 0)),
            'baseline_period_start': datetime.now(timezone.utc).isoformat(),
            'baseline_period_end': (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
    
    def _analyze_niche_tendencies(self, reel_data: dict) -> dict:
        """
        Analyze creator's niche tendencies from their content
        """
        # This would analyze multiple reels to determine niche preferences
        # For now, return empty dict as placeholder
        return {}
    
    def get_creator_baseline(self, username: str) -> Optional[dict]:
        """
        Get creator's current baseline metrics
        """
        try:
            result = self.supabase.table('creator_baselines').select('*').eq('username', username).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting creator baseline for {username}: {e}")
            return None
    
    def calculate_creator_tier_velocity_weight(self, creator_tier: str) -> float:
        """
        Calculate weight for early signal detection based on creator tier
        Micro creators have higher weight for early detection
        """
        tier_weights = {
            "nano": 1.5,      # Highest early signal weight
            "micro": 1.3,     # Strong early signal
            "mid_tier": 0.8,  # Validation signal
            "macro": 0.5,     # Late signal
            "mega": 0.3       # Saturation signal
        }
        return tier_weights.get(creator_tier, 1.0)
    
    def batch_update_baselines(self, recent_reels: list[dict]) -> dict:
        """
        Batch update baselines for multiple creators
        """
        updated_count = 0
        failed_count = 0
        
        for reel in recent_reels:
            username = reel.get('owner_username')
            if username:
                result = self.update_creator_baseline(username, reel)
                if result.get('success'):
                    updated_count += 1
                else:
                    failed_count += 1
        
        return {
            "success": True,
            "updated_count": updated_count,
            "failed_count": failed_count,
            "total_processed": len(recent_reels)
        }

# Global instance
baseline_tracker = CreatorBaselineTracker()