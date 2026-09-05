#!/usr/bin/env python3
"""
Early Signal Detector - Detects early viral signals before trends become mainstream
"""

import os
import json
import logging
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

# Signal thresholds
VELOCITY_SIGNAL_THRESHOLDS = {
    "explosive": 10.0,      # 10x baseline = very early viral
    "high": 5.0,            # 5x baseline = early growth
    "moderate": 2.0,        # 2x baseline = normal growth
    "low": 1.0,             # 1x baseline = baseline
    "declining": 0.5        # Below baseline = declining
}

# Detection tiers
DETECTION_TIERS = {
    "very_early": {"threshold": 70, "confidence_min": 0.6},
    "early_growth": {"threshold": 80, "confidence_min": 0.75},
    "crossover": {"threshold": 85, "confidence_min": 0.85}
}

class EarlySignalDetector:
    """
    Detects early viral signals before trends become mainstream
    """
    
    def __init__(self):
        self.supabase = sb
    
    def detect_velocity_spikes(self, reel: dict, creator_baseline: dict) -> dict:
        """
        Detect explosive velocity spikes relative to creator baseline
        """
        try:
            # Calculate current engagement
            current_engagement = reel.get('view_count', 0) + (reel.get('like_count', 0) * 3) + (reel.get('comment_count', 0) * 5)
            
            # Get baseline engagement
            baseline_engagement = creator_baseline.get('avg_engagement', 1000)
            
            # Calculate hours live
            posted_at = reel.get('posted_at')
            if posted_at:
                posted_time = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
                hours_live = max((datetime.now(timezone.utc) - posted_time).total_seconds() / 3600.0, 0.5)
            else:
                hours_live = 0.5
            
            # Calculate hourly rate
            hourly_rate = current_engagement / hours_live
            baseline_hourly_rate = baseline_engagement / 24  # Daily baseline
            
            # Calculate velocity multiplier
            velocity_multiplier = hourly_rate / baseline_hourly_rate if baseline_hourly_rate > 0 else 0
            
            # Classify velocity signal
            if velocity_multiplier >= VELOCITY_SIGNAL_THRESHOLDS["explosive"]:
                signal_type = "explosive"
                strength = 95
            elif velocity_multiplier >= VELOCITY_SIGNAL_THRESHOLDS["high"]:
                signal_type = "high"
                strength = 80
            elif velocity_multiplier >= VELOCITY_SIGNAL_THRESHOLDS["moderate"]:
                signal_type = "moderate"
                strength = 60
            elif velocity_multiplier >= VELOCITY_SIGNAL_THRESHOLDS["low"]:
                signal_type = "low"
                strength = 40
            else:
                signal_type = "declining"
                strength = 20
            
            return {
                "signal_type": signal_type,
                "strength": strength,
                "velocity_multiplier": velocity_multiplier,
                "current_engagement": current_engagement,
                "baseline_engagement": baseline_engagement,
                "hours_live": hours_live
            }
        except Exception as e:
            logger.error(f"Error detecting velocity spikes: {e}")
            return {"signal_type": "error", "strength": 0}
    
    def detect_audio_acceleration(self, audio_id: str) -> dict:
        """
        Detect exponential audio adoption growth
        """
        try:
            # Get audio adoption history from last 24 hours
            # Query audio_adoption_timeline for this audio
            result = self.supabase.table('audio_adoption_timeline').select('*').eq('audio_id', audio_id).order('hour_bucket', desc=True).limit(24).execute()
            
            if not result.data or len(result.data) < 2:
                return {
                    "acceleration_rate": 0,
                    "trend_type": "insufficient_data",
                    "strength": 0
                }
            
            # Extract use counts
            use_counts = [row['use_count'] for row in result.data]
            use_counts.reverse()  # Oldest to newest
            
            # Calculate day-over-day growth rates
            recent_growth = []
            for i in range(1, len(use_counts)):
                current = use_counts[i]
                previous = use_counts[i-1]
                if previous > 0:
                    growth_rate = (current - previous) / previous
                    recent_growth.append(growth_rate)
            
            if not recent_growth:
                return {
                    "acceleration_rate": 0,
                    "trend_type": "stable",
                    "strength": 0
                }
            
            # Calculate average growth rate
            avg_growth_rate = sum(recent_growth) / len(recent_growth)
            
            # Classify trend type
            if avg_growth_rate > 2.0:
                trend_type = "exponential"  # Viral potential
                strength = 90
            elif avg_growth_rate > 1.0:
                trend_type = "linear"  # Normal growth
                strength = 60
            elif avg_growth_rate > 0:
                trend_type = "stable"  # Steady growth
                strength = 40
            else:
                trend_type = "declining"  # Dying trend
                strength = 20
            
            return {
                "acceleration_rate": avg_growth_rate,
                "trend_type": trend_type,
                "strength": strength,
                "recent_growth_rates": recent_growth[-7:] if len(recent_growth) >= 7 else recent_growth,
                "use_count_history": use_counts
            }
        except Exception as e:
            logger.error(f"Error detecting audio acceleration: {e}")
            return {"acceleration_rate": 0, "trend_type": "error", "strength": 0}
    
    def detect_creator_cascade(self, audio_id: str) -> dict:
        """
        Detect micro→mid→macro creator tier adoption pattern
        """
        try:
            # Get reels using this audio with creator tiers
            result = self.supabase.table('reels').select('owner_follower_count', 'created_at').eq('audio_id', audio_id).execute()
            
            if not result.data:
                return {
                    "cascade_detected": False,
                    "strength": 0,
                    "tier_distribution": {}
                }
            
            # Classify creators into tiers
            tier_distribution = {
                "nano": 0,      # < 1K followers
                "micro": 0,     # 1K-10K followers
                "mid_tier": 0,   # 10K-100K followers
                "macro": 0,      # 100K-1M followers
                "mega": 0       # 1M+ followers
            }
            
            for reel in result.data:
                followers = reel.get('owner_follower_count', 0)
                if followers < 1000:
                    tier_distribution["nano"] += 1
                elif followers < 10000:
                    tier_distribution["micro"] += 1
                elif followers < 100000:
                    tier_distribution["mid_tier"] += 1
                elif followers < 1000000:
                    tier_distribution["macro"] += 1
                else:
                    tier_distribution["mega"] += 1
            
            total_creators = sum(tier_distribution.values())
            
            # Detect cascade pattern
            # Cascade pattern: nano → micro → mid_tier → macro
            # Check if we have creators across multiple tiers
            active_tiers = [tier for tier, count in tier_distribution.items() if count > 0]
            
            cascade_detected = len(active_tiers) >= 3
            
            # Calculate cascade strength
            if cascade_detected:
                # Check if cascade is moving up (nano to micro to mid)
                if tier_distribution["nano"] > 0 and tier_distribution["micro"] > 0 and tier_distribution["mid_tier"] > 0:
                    strength = 85
                elif tier_distribution["micro"] > 0 and tier_distribution["mid_tier"] > 0 and tier_distribution["macro"] > 0:
                    strength = 90
                else:
                    strength = 70
            else:
                strength = 30
            
            return {
                "cascade_detected": cascade_detected,
                "strength": strength,
                "tier_distribution": tier_distribution,
                "total_creators": total_creators,
                "active_tiers": active_tiers
            }
        except Exception as e:
            logger.error(f"Error detecting creator cascade: {e}")
            return {"cascade_detected": False, "strength": 0, "tier_distribution": {}}
    
    def detect_hashtag_virality(self, hashtags: List[str]) -> dict:
        """
        Detect new hashtag virality patterns
        """
        try:
            if not hashtags:
                return {
                    "viral_hashtags": [],
                    "strength": 0,
                    "cross_hashtag_spreading": False
                }
            
            # Check hashtag performance
            hashtag_performance = {}
            for tag in hashtags:
                result = self.supabase.table('hashtag_performance').select('*').eq('hashtag', tag.lstrip('#')).execute()
                if result.data:
                    hashtag_performance[tag] = result.data[0]
            
            # Check for viral hashtags (high performance score)
            viral_hashtags = [
                tag for tag, perf in hashtag_performance.items()
                if perf.get('performance_score', 0) > 70
            ]
            
            # Check for cross-hashtag spreading
            # This would require tracking hashtag co-occurrence
            cross_hashtag_spreading = len(viral_hashtags) >= 2
            
            strength = min(90, len(viral_hashtags) * 20 + (50 if cross_hashtag_spreading else 0))
            
            return {
                "viral_hashtags": viral_hashtags,
                "strength": strength,
                "cross_hashtag_spreading": cross_hashtag_spreading,
                "hashtag_performance": hashtag_performance
            }
        except Exception as e:
            logger.error(f"Error detecting hashtag virality: {e}")
            return {"viral_hashtags": [], "strength": 0, "cross_hashtag_spreading": False}
    
    def calculate_early_signal_score(self, signals: List[dict]) -> float:
        """
        Calculate composite early signal score (0-100)
        """
        if not signals:
            return 0
        
        # Weighted average of signal strengths
        signal_weights = {
            "velocity_spike": 0.35,
            "audio_acceleration": 0.30,
            "creator_cascade": 0.25,
            "hashtag_virality": 0.10
        }
        
        total_score = 0
        total_weight = 0
        
        for signal in signals:
            signal_type = signal.get("signal_type", "")
            strength = signal.get("strength", 0)
            
            # Map signal type to weight
            if signal_type == "explosive" or signal_type == "high":
                weight = signal_weights["velocity_spike"]
            elif signal_type == "exponential" or signal_type == "linear":
                weight = signal_weights["audio_acceleration"]
            elif signal_type == "cascade_detected":
                weight = signal_weights["creator_cascade"]
            elif signal_type == "viral_hashtags":
                weight = signal_weights["hashtag_virality"]
            else:
                weight = 0.1  # Default low weight
            
            total_score += strength * weight
            total_weight += weight
        
        if total_weight > 0:
            return min(100, total_score / total_weight)
        return 0
    
    def predict_viral_probability(self, signal_score: float, context: dict) -> float:
        """
        Predict probability of viral success
        """
        try:
            # Base probability from signal score
            base_probability = signal_score / 100
            
            # Adjust based on additional context
            audio_use_count = context.get('audio_use_count', 0)
            engagement_rate = context.get('engagement_rate', 0)
            
            # Adjustments
            if audio_use_count > 1000:
                base_probability *= 0.9  # Saturated
            elif audio_use_count < 10:
                base_probability *= 1.1  # Early stage potential
            
            if engagement_rate > 0.15:
                base_probability *= 1.2  # High engagement
            
            return min(0.95, max(0.05, base_probability))
        except Exception as e:
            logger.error(f"Error predicting viral probability: {e}")
            return signal_score / 100
    
    def store_early_signal(self, signal_data: dict) -> dict:
        """
        Store early signal in database
        """
        try:
            result = self.supabase.table('early_signals').insert(signal_data).execute()
            return {"success": True, "signal_id": result.data[0]['id']}
        except Exception as e:
            logger.error(f"Error storing early signal: {e}")
            return {"success": False, "error": str(e)}

# Global instance
detector = EarlySignalDetector()