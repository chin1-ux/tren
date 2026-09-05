#!/usr/bin/env python3
"""
Real-time Velocity Tracker - Tracks real-time velocity changes for early detection
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

# Velocity thresholds for real-time alerts
VELOCITY_ALERT_THRESHOLDS = {
    "explosive": {"multiplier": 10.0, "window_minutes": 15},
    "high": {"multiplier": 5.0, "window_minutes": 30},
    "moderate": {"multiplier": 2.0, "window_minutes": 60},
    "baseline": {"multiplier": 1.0, "window_minutes": 120}
}

class RealTimeVelocityTracker:
    """
    Tracks real-time velocity changes for early detection
    """
    
    def __init__(self):
        self.supabase = sb
        self.velocity_history = defaultdict(list)
    
    def track_reel_velocity(self, reel_id: str, engagement_data: dict) -> dict:
        """
        Track velocity for a specific reel in real-time
        """
        try:
            # Calculate current engagement
            current_engagement = (
                engagement_data.get('view_count', 0) + 
                (engagement_data.get('like_count', 0) * 3) + 
                (engagement_data.get('comment_count', 0) * 5)
            )
            
            # Get posted time
            posted_at = engagement_data.get('posted_at')
            if posted_at:
                posted_time = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
                hours_live = max((datetime.now(timezone.utc) - posted_time).total_seconds() / 3600.0, 0.1)
            else:
                hours_live = 0.1
            
            # Calculate current velocity
            current_velocity = current_engagement / hours_live
            
            # Get historical velocity data
            history = self.velocity_history[reel_id]
            history.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'velocity': current_velocity,
                'engagement': current_engagement,
                'hours_live': hours_live
            })
            
            # Keep only last 24 hours of data
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            self.velocity_history[reel_id] = [
                h for h in history 
                if datetime.fromisoformat(h['timestamp']) > cutoff_time
            ]
            
            # Calculate velocity acceleration
            acceleration = self._calculate_velocity_acceleration(reel_id)
            
            # Detect velocity spikes
            alert = self._detect_velocity_spike(reel_id, current_velocity)
            
            return {
                "success": True,
                "reel_id": reel_id,
                "current_velocity": current_velocity,
                "velocity_acceleration": acceleration,
                "alert": alert,
                "history_length": len(self.velocity_history[reel_id])
            }
        except Exception as e:
            logger.error(f"Error tracking velocity for reel {reel_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_velocity_acceleration(self, reel_id: str) -> float:
        """
        Calculate velocity acceleration (rate of change)
        """
        history = self.velocity_history[reel_id]
        
        if len(history) < 2:
            return 0.0
        
        # Calculate rate of change between consecutive points
        rates = []
        for i in range(1, len(history)):
            prev_velocity = history[i-1]['velocity']
            curr_velocity = history[i]['velocity']
            
            if prev_velocity > 0:
                rate = (curr_velocity - prev_velocity) / prev_velocity
                rates.append(rate)
        
        if not rates:
            return 0.0
        
        # Return average acceleration
        return sum(rates) / len(rates)
    
    def _detect_velocity_spike(self, reel_id: str, current_velocity: float) -> Optional[dict]:
        """
        Detect velocity spikes that indicate early viral potential
        """
        history = self.velocity_history[reel_id]
        
        if len(history) < 5:
            return None
        
        # Calculate baseline velocity (median of recent history)
        recent_velocities = [h['velocity'] for h in history[-10:]]
        baseline_velocity = sorted(recent_velocities)[len(recent_velocities) // 2]
        
        if baseline_velocity == 0:
            return None
        
        # Calculate multiplier
        velocity_multiplier = current_velocity / baseline_velocity
        
        # Check against thresholds
        for alert_type, threshold_config in VELOCITY_ALERT_THRESHOLDS.items():
            if velocity_multiplier >= threshold_config["multiplier"]:
                return {
                    "alert_type": alert_type,
                    "velocity_multiplier": velocity_multiplier,
                    "baseline_velocity": baseline_velocity,
                    "current_velocity": current_velocity,
                    "threshold": threshold_config["multiplier"],
                    "window_minutes": threshold_config["window_minutes"]
                }
        
        return None
    
    def track_audio_velocity(self, audio_id: str) -> dict:
        """
        Track velocity for a specific audio across all reels
        """
        try:
            # Get all reels using this audio
            result = self.supabase.table('reels').select('*').eq('audio_id', audio_id).execute()
            
            if not result.data:
                return {"success": False, "error": "No reels found for this audio"}
            
            # Calculate total velocity
            total_velocity = 0
            reel_count = 0
            
            for reel in result.data:
                velocity_result = self.track_reel_velocity(
                    reel['id'],
                    {
                        'view_count': reel.get('view_count', 0),
                        'like_count': reel.get('like_count', 0),
                        'comment_count': reel.get('comment_count', 0),
                        'posted_at': reel.get('created_at')
                    }
                )
                
                if velocity_result.get('success'):
                    total_velocity += velocity_result['current_velocity']
                    reel_count += 1
            
            if reel_count == 0:
                return {"success": False, "error": "No valid velocity data"}
            
            avg_velocity = total_velocity / reel_count
            
            return {
                "success": True,
                "audio_id": audio_id,
                "avg_velocity": avg_velocity,
                "total_reels": reel_count,
                "total_velocity": total_velocity
            }
        except Exception as e:
            logger.error(f"Error tracking audio velocity for {audio_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def get_velocity_analytics(self, reel_id: str) -> dict:
        """
        Get detailed velocity analytics for a reel
        """
        try:
            history = self.velocity_history[reel_id]
            
            if not history:
                return {"success": False, "error": "No velocity history found"}
            
            # Calculate analytics
            velocities = [h['velocity'] for h in history]
            accelerations = []
            
            for i in range(1, len(history)):
                prev_vel = history[i-1]['velocity']
                curr_vel = history[i]['velocity']
                if prev_vel > 0:
                    acc = (curr_vel - prev_vel) / prev_vel
                    accelerations.append(acc)
            
            return {
                "success": True,
                "reel_id": reel_id,
                "data_points": len(history),
                "current_velocity": velocities[-1] if velocities else 0,
                "avg_velocity": sum(velocities) / len(velocities) if velocities else 0,
                "max_velocity": max(velocities) if velocities else 0,
                "min_velocity": min(velocities) if velocities else 0,
                "avg_acceleration": sum(accelerations) / len(accelerations) if accelerations else 0,
                "max_acceleration": max(accelerations) if accelerations else 0,
                "time_span_hours": self._calculate_time_span(history)
            }
        except Exception as e:
            logger.error(f"Error getting velocity analytics for reel {reel_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _calculate_time_span(self, history: List[dict]) -> float:
        """
        Calculate time span in hours for velocity history
        """
        if len(history) < 2:
            return 0.0
        
        first_time = datetime.fromisoformat(history[0]['timestamp'])
        last_time = datetime.fromisoformat(history[-1]['timestamp'])
        
        return (last_time - first_time).total_seconds() / 3600.0
    
    def cleanup_old_data(self, days_to_keep: int = 7) -> dict:
        """
        Clean up old velocity data
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            cleaned_count = 0
            
            for reel_id in list(self.velocity_history.keys()):
                self.velocity_history[reel_id] = [
                    h for h in self.velocity_history[reel_id]
                    if datetime.fromisoformat(h['timestamp']) > cutoff_time
                ]
                
                if not self.velocity_history[reel_id]:
                    del self.velocity_history[reel_id]
                    cleaned_count += 1
            
            return {
                "success": True,
                "cleaned_count": cleaned_count,
                "remaining_reels": len(self.velocity_history)
            }
        except Exception as e:
            logger.error(f"Error cleaning up old velocity data: {e}")
            return {"success": False, "error": str(e)}

# Global instance
velocity_tracker = RealTimeVelocityTracker()