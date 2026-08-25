#!/usr/bin/env python3
"""
Geographic Spread Analyzer - Tracks geographic spread of trends
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

# Geographic regions
INDIAN_REGIONS = {
    "north": ["delhi", "mumbai", "punjab", "haryana", "uttar_pradesh", "rajasthan"],
    "south": ["bangalore", "chennai", "hyderabad", "kerala", "karnataka", "tamil_nadu", "telangana"],
    "east": ["kolkata", "odisha", "west_bengal", "bihar", "jharkhand"],
    "west": ["gujarat", "maharashtra", "goa"],
    "northeast": ["assam", "manipur", "meghalaya", "nagaland", "tripura", "sikkim"]
}

# Geographic spread stages
GEOGRAPHIC_STAGES = {
    "local": {"threshold": 1, "radius": 50},  # Single city/area
    "regional": {"threshold": 3, "radius": 500},  # Multiple cities in region
    "national": {"threshold": 10, "radius": 2000},  # Multiple regions
    "global": {"threshold": 5, "countries": 3}  # Multiple countries
}

class GeographicSpreadAnalyzer:
    """
    Tracks geographic spread of trends
    """
    
    def __init__(self):
        self.supabase = sb
    
    def extract_location_from_caption(self, caption: str) -> Optional[str]:
        """
        Extract location from caption (placeholder - would need NLP)
        """
        # This is a simplified version
        # In production, this would use NLP/geocoding
        if not caption:
            return None
        
        # Simple keyword matching
        caption_lower = caption.lower()
        for region, cities in INDIAN_REGIONS.items():
            for city in cities:
                if city in caption_lower:
                    return city
        
        return None
    
    def analyze_geographic_spread(self, audio_id: str) -> dict:
        """
        Analyze geographic spread of a trend
        """
        try:
            # Get reels using this audio
            result = self.supabase.table('reels').select('caption', 'owner_location').eq('audio_id', audio_id).execute()
            
            if not result.data:
                return {
                    "spread_stage": "unknown",
                    "diversity_score": 0,
                    "regional_distribution": {}
                }
            
            # Extract locations
            locations = []
            for reel in result.data:
                # Try to get location from various fields
                location = reel.get('owner_location') or self.extract_location_from_caption(reel.get('caption', ''))
                if location:
                    locations.append(location.lower())
            
            if not locations:
                return {
                    "spread_stage": "unknown",
                    "diversity_score": 0,
                    "regional_distribution": {}
                }
            
            # Classify locations into regions
            regional_distribution = defaultdict(int)
            for location in locations:
                for region, cities in INDIAN_REGIONS.items():
                    if any(city in location for city in cities):
                        regional_distribution[region] += 1
                        break
            
            # Calculate diversity score
            total_locations = len(locations)
            unique_regions = len(regional_distribution)
            diversity_score = (unique_regions / 5) * 100  # 5 regions max
            
            # Determine spread stage
            if unique_regions == 1:
                spread_stage = "local"
            elif unique_regions >= 2 and unique_regions < 4:
                spread_stage = "regional"
            elif unique_regions >= 4:
                spread_stage = "national"
            else:
                spread_stage = "unknown"
            
            return {
                "spread_stage": spread_stage,
                "diversity_score": diversity_score,
                "regional_distribution": dict(regional_distribution),
                "total_locations": total_locations,
                "unique_regions": unique_regions
            }
        except Exception as e:
            logger.error(f"Error analyzing geographic spread: {e}")
            return {"spread_stage": "error", "diversity_score": 0, "regional_distribution": {}}
    
    def track_spread_velocity(self, audio_id: str, time_window_hours: int = 24) -> dict:
        """
        Track how quickly a trend is spreading geographically
        """
        try:
            # Get reels within time window
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
            
            result = self.supabase.table('reels').select('caption', 'owner_location', 'created_at').eq('audio_id', audio_id).gte('created_at', cutoff_time.isoformat()).execute()
            
            if not result.data:
                return {
                    "spread_velocity": 0,
                    "new_regions": 0,
                    "stage_transition": None
                }
            
            # Extract locations and timestamps
            location_timeline = []
            for reel in result.data:
                location = reel.get('owner_location') or self.extract_location_from_caption(reel.get('caption', ''))
                if location:
                    location_timeline.append({
                        'location': location.lower(),
                        'timestamp': reel.get('created_at')
                    })
            
            # Sort by timestamp
            location_timeline.sort(key=lambda x: x['timestamp'])
            
            # Track region progression
            regions_seen = set()
            new_regions = 0
            previous_stage = "local"
            
            for item in location_timeline:
                location = item['location']
                for region, cities in INDIAN_REGIONS.items():
                    if any(city in location for city in cities):
                        if region not in regions_seen:
                            regions_seen.add(region)
                            new_regions += 1
                        break
            
            # Determine current stage
            current_stage = self._determine_stage(len(regions_seen))
            
            # Calculate spread velocity (regions per hour)
            spread_velocity = new_regions / time_window_hours if time_window_hours > 0 else 0
            
            return {
                "spread_velocity": spread_velocity,
                "new_regions": new_regions,
                "current_stage": current_stage,
                "regions_seen": list(regions_seen),
                "stage_transition": previous_stage != current_stage
            }
        except Exception as e:
            logger.error(f"Error tracking spread velocity: {e}")
            return {"spread_velocity": 0, "new_regions": 0, "stage_transition": None}
    
    def _determine_stage(self, region_count: int) -> str:
        """
        Determine geographic spread stage based on region count
        """
        if region_count == 1:
            return "local"
        elif region_count >= 2 and region_count < 4:
            return "regional"
        elif region_count >= 4:
            return "national"
        else:
            return "unknown"
    
    def calculate_geographic_score(self, spread_data: dict) -> float:
        """
        Calculate geographic spread score (0-100)
        """
        try:
            spread_stage = spread_data.get('spread_stage', 'unknown')
            diversity_score = spread_data.get('diversity_score', 0)
            spread_velocity = spread_data.get('spread_velocity', 0)
            
            # Base score from stage
            stage_scores = {
                "local": 20,
                "regional": 50,
                "national": 80,
                "global": 100,
                "unknown": 0
            }
            
            base_score = stage_scores.get(spread_stage, 0)
            
            # Add diversity bonus
            diversity_bonus = diversity_score * 0.2
            
            # Add velocity bonus
            velocity_bonus = min(20, spread_velocity * 10)
            
            total_score = base_score + diversity_bonus + velocity_bonus
            
            return min(100, total_score)
        except Exception as e:
            logger.error(f"Error calculating geographic score: {e}")
            return 0
    
    def store_geographic_data(self, signal_id: int, geographic_data: dict) -> dict:
        """
        Store geographic data with early signal
        """
        try:
            result = self.supabase.table('early_signals').update({
                'geographic_spread': geographic_data
            }).eq('id', signal_id).execute()
            
            return {"success": True}
        except Exception as e:
            logger.error(f"Error storing geographic data: {e}")
            return {"success": False, "error": str(e)}

# Global instance
geo_analyzer = GeographicSpreadAnalyzer()