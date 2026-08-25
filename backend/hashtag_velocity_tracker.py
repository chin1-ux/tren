"""
Hashtag Velocity Tracking System
Monitors hashtag usage patterns to detect trending, growing, and declining hashtags.
This helps creators identify what topics and conversations are gaining traction.
"""
import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client, Client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

try:
    logging.basicConfig(
        filename="hashtag_velocity.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
except Exception:
    pass

logger = logging.getLogger(__name__)

@dataclass
class HashtagVelocity:
    """Represents velocity data for a single hashtag"""
    hashtag: str
    current_count: int
    previous_count: int
    velocity_score: float  # Growth rate
    trend_direction: str  # "rising", "stable", "declining"
    acceleration: float  # Rate of change of velocity
    usage_frequency: float  # Posts per hour
    niche_relevance: str  # "general", "fitness", "food", etc.
    estimated_total_creators: int
    peak_24h_usage: int
    discovered_at: datetime

@dataclass
class HashtagTrend:
    """Represents a trending hashtag with context"""
    hashtag: str
    velocity_score: float
    trend_direction: str
    related_hashtags: List[str]
    content_themes: List[str]
    target_audiences: List[str]
    optimal_content_types: List[str]
    estimated_lifespan_hours: int
    competition_level: str  # "low", "medium", "high"
    platform_performance: Dict[str, float]  # {platform: engagement_score}

class HashtagVelocityTracker:
    """
    Hashtag Velocity Tracking System
    Monitors hashtag usage patterns to identify trending topics and conversations
    """
    
    def __init__(self):
        load_dotenv()
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        self.supabase: Optional[Client] = None
        
        if self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase client: {e}")
        
        # Niche keyword mapping for hashtag categorization
        self.niche_keywords = {
            'fitness': ['gym', 'workout', 'fitness', 'exercise', 'muscle', 'cardio', 'yoga', 'bodybuilding', 'health'],
            'food': ['food', 'recipe', 'cooking', 'chef', 'kitchen', 'baking', 'restaurant', 'foodie', 'tasty'],
            'comedy': ['funny', 'comedy', 'humor', 'laugh', 'joke', 'memes', 'viral', 'hilarious', 'comedian'],
            'fashion': ['fashion', 'style', 'outfit', 'dress', 'clothing', 'designer', 'brand', 'trend', 'ootd'],
            'travel': ['travel', 'vacation', 'trip', 'destination', 'beach', 'mountain', 'hotel', 'adventure', 'explore'],
            'beauty': ['beauty', 'makeup', 'skincare', 'hair', 'cosmetics', 'glow', 'tutorial', 'routine', 'product'],
            'motivation': ['motivation', 'inspire', 'success', 'mindset', 'goals', 'hustle', 'grind', 'positive', 'growth'],
            'dance': ['dance', 'choreography', 'trending', 'moves', 'tutorial', 'viral', 'challenge', 'step', 'party'],
            'music': ['music', 'song', 'album', 'artist', 'cover', 'remix', 'audio', 'sound', 'track']
        }
    
    def track_hashtag_velocity(self, hours_window: int = 24) -> List[HashtagVelocity]:
        """
        Track velocity for all hashtags found in recent reels
        """
        if not self.supabase:
            logger.warning("Supabase not available for hashtag tracking")
            return []
        
        try:
            # Get hashtags from recent reels
            time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours_window)).isoformat()
            
            # Get all reels with hashtags in the time window
            reels_res = self.supabase.table('reels') \
                .select('hashtags, created_at, velocity_score') \
                .gte('created_at', time_threshold) \
                .not_.is_('hashtags', 'null') \
                .execute()
            
            reels = reels_res.data or []
            
            # Aggregate hashtag usage
            hashtag_usage = defaultdict(lambda: {'count': 0, 'velocities': [], 'timestamps': []})
            
            for reel in reels:
                hashtags = reel.get('hashtags', [])
                velocity = reel.get('velocity_score', 0)
                created_at = reel.get('created_at')
                
                for tag in hashtags:
                    if tag and isinstance(tag, str) and tag.startswith('#'):
                        hashtag_usage[tag]['count'] += 1
                        hashtag_usage[tag]['velocities'].append(velocity)
                        if created_at:
                            try:
                                if created_at.endswith('Z'):
                                    created_at = created_at[:-1] + '+00:00'
                                hashtag_usage[tag]['timestamps'].append(datetime.fromisoformat(created_at))
                            except Exception:
                                pass
            
            # Calculate velocity for each hashtag
            hashtag_velocities = []
            
            for hashtag, data in hashtag_usage.items():
                if data['count'] < 5:  # Skip very low usage hashtags
                    continue
                
                current_count = data['count']
                avg_velocity = sum(data['velocities']) / len(data['velocities']) if data['velocities'] else 0
                
                # Calculate velocity score (growth rate)
                # Simplified: compare recent vs older usage
                if len(data['timestamps']) >= 2:
                    timestamps = sorted(data['timestamps'])
                    mid_point = len(timestamps) // 2
                    recent_count = len([t for t in timestamps if t > timestamps[mid_point]])
                    older_count = len([t for t in timestamps if t <= timestamps[mid_point]])
                    
                    if older_count > 0:
                        velocity_score = ((recent_count - older_count) / older_count) * 100
                    else:
                        velocity_score = 100
                else:
                    velocity_score = 0
                
                # Determine trend direction
                if velocity_score > 20:
                    trend_direction = "rising"
                elif velocity_score < -20:
                    trend_direction = "declining"
                else:
                    trend_direction = "stable"
                
                # Calculate acceleration (rate of change)
                acceleration = velocity_score * 0.1  # Simplified
                
                # Calculate usage frequency (posts per hour)
                time_span_hours = hours_window
                usage_frequency = current_count / time_span_hours if time_span_hours > 0 else 0
                
                # Determine niche relevance
                niche_relevance = self._determine_niche_relevance(hashtag)
                
                # Estimate total creators (simplified: assume 1 post per creator on average)
                estimated_creators = int(current_count * 0.8)
                
                # Peak 24h usage
                peak_24h = current_count  # Simplified
                
                hashtag_velocities.append(HashtagVelocity(
                    hashtag=hashtag,
                    current_count=current_count,
                    previous_count=int(current_count * 0.8),  # Simplified
                    velocity_score=velocity_score,
                    trend_direction=trend_direction,
                    acceleration=acceleration,
                    usage_frequency=usage_frequency,
                    niche_relevance=niche_relevance,
                    estimated_total_creators=estimated_creators,
                    peak_24h_usage=peak_24h,
                    discovered_at=datetime.now(timezone.utc)
                ))
            
            # Sort by velocity score
            hashtag_velocities.sort(key=lambda h: h.velocity_score, reverse=True)
            
            return hashtag_velocities[:50]  # Return top 50
            
        except Exception as e:
            logger.error(f"Error tracking hashtag velocity: {e}")
            return []
    
    def get_trending_hashtags(self, hours_window: int = 24, min_velocity: float = 20.0) -> List[HashtagTrend]:
        """
        Get trending hashtags with detailed trend analysis
        """
        hashtag_velocities = self.track_hashtag_velocity(hours_window)
        
        # Filter for trending hashtags
        trending = [h for h in hashtag_velocities if h.velocity_score >= min_velocity]
        
        hashtag_trends = []
        
        for hv in trending:
            # Get related hashtags (hashtags that often appear together)
            related_hashtags = self._find_related_hashtags(hv.hashtag)
            
            # Determine content themes based on hashtag
            content_themes = self._determine_content_themes(hv.hashtag, hv.niche_relevance)
            
            # Determine target audiences
            target_audiences = self._determine_target_audiences(hv.niche_relevance)
            
            # Determine optimal content types
            optimal_content_types = self._determine_optimal_content_types(hv.niche_relevance)
            
            # Estimate lifespan (based on trend direction and velocity)
            estimated_lifespan = self._estimate_hashtag_lifespan(hv)
            
            # Determine competition level
            competition_level = self._determine_competition_level(hv.estimated_total_creators)
            
            # Platform performance (simplified)
            platform_performance = {
                'instagram': min(1.0, hv.velocity_score / 100),
                'youtube_shorts': min(1.0, hv.velocity_score / 120),
                'tiktok': min(1.0, hv.velocity_score / 150)
            }
            
            hashtag_trends.append(HashtagTrend(
                hashtag=hv.hashtag,
                velocity_score=hv.velocity_score,
                trend_direction=hv.trend_direction,
                related_hashtags=related_hashtags,
                content_themes=content_themes,
                target_audiences=target_audiences,
                optimal_content_types=optimal_content_types,
                estimated_lifespan_hours=estimated_lifespan,
                competition_level=competition_level,
                platform_performance=platform_performance
            ))
        
        return hashtag_trends
    
    def _determine_niche_relevance(self, hashtag: str) -> str:
        """Determine which niche a hashtag belongs to"""
        hashtag_lower = hashtag.lower()
        
        for niche, keywords in self.niche_keywords.items():
            if any(keyword in hashtag_lower for keyword in keywords):
                return niche
        
        return 'general'
    
    def _find_related_hashtags(self, hashtag: str, limit: int = 5) -> List[str]:
        """
        Find hashtags that often appear together with the given hashtag
        """
        if not self.supabase:
            return []
        
        try:
            # Find reels containing this hashtag
            time_threshold = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
            
            reels_res = self.supabase.table('reels') \
                .select('hashtags') \
                .contains('hashtags', hashtag) \
                .gte('created_at', time_threshold) \
                .limit(100) \
                .execute()
            
            reels = reels_res.data or []
            
            # Count co-occurring hashtags
            co_occurrence = defaultdict(int)
            
            for reel in reels:
                hashtags = reel.get('hashtags', [])
                for tag in hashtags:
                    if tag and tag != hashtag and isinstance(tag, str) and tag.startswith('#'):
                        co_occurrence[tag] += 1
            
            # Return top related hashtags
            related = sorted(co_occurrence.items(), key=lambda x: x[1], reverse=True)
            return [tag for tag, count in related[:limit]]
            
        except Exception as e:
            logger.error(f"Error finding related hashtags: {e}")
            return []
    
    def _determine_content_themes(self, hashtag: str, niche: str) -> List[str]:
        """Determine content themes associated with a hashtag"""
        themes = {
            'fitness': ['workout routines', 'exercise tutorials', 'fitness challenges', 'nutrition tips', 'transformation'],
            'food': ['recipe tutorials', 'cooking tips', 'food reviews', 'restaurant showcases', 'meal prep'],
            'comedy': ['skits', 'relatable humor', 'viral trends', 'memes', 'standup'],
            'fashion': ['outfit showcases', 'styling tips', 'brand reviews', 'trend analysis', 'lookbooks'],
            'travel': ['destination guides', 'travel tips', 'vlog content', 'adventure', 'local experiences'],
            'beauty': ['makeup tutorials', 'skincare routines', 'product reviews', 'transformations', 'hairstyles'],
            'motivation': ['success stories', 'mindset advice', 'goal setting', 'morning routines', 'productivity tips'],
            'dance': ['choreography tutorials', 'dance challenges', 'viral dance trends', 'step-by-step guides', 'dance covers'],
            'music': ['music covers', 'audio recommendations', 'artist features', 'music challenges', 'song reactions'],
            'general': ['viral content', 'trend participation', 'behind-the-scenes', 'day in the life', 'storytelling']
        }
        
        return themes.get(niche, themes['general'])
    
    def _determine_target_audiences(self, niche: str) -> List[str]:
        """Determine target audiences for a niche"""
        audiences = {
            'fitness': ['fitness enthusiasts', 'gym-goers', 'health-conscious individuals', 'beginners', 'advanced athletes'],
            'food': ['home cooks', 'foodies', 'restaurant-goers', 'cooking enthusiasts', 'health-conscious eaters'],
            'comedy': ['entertainment seekers', 'gen z', 'millennials', 'viral content consumers', 'meme lovers'],
            'fashion': ['fashion enthusiasts', 'style-conscious individuals', 'brand followers', 'trend adopters', 'shoppers'],
            'travel': ['travel enthusiasts', 'adventure seekers', 'vacation planners', 'digital nomads', 'local explorers'],
            'beauty': ['beauty enthusiasts', 'skincare conscious', 'makeup lovers', 'transformation seekers', 'product researchers'],
            'motivation': ['self-improvement seekers', 'entrepreneurs', 'students', 'career-focused individuals', 'personal growth enthusiasts'],
            'dance': ['dancers', 'dance enthusiasts', 'music lovers', 'party-goers', 'viral trend participants'],
            'music': ['music lovers', 'artists', 'music enthusiasts', 'cover artists', 'genre fans'],
            'general': ['viral content consumers', 'entertainment seekers', 'social media users', 'general audience', 'content creators']
        }
        
        return audiences.get(niche, audiences['general'])
    
    def _determine_optimal_content_types(self, niche: str) -> List[str]:
        """Determine optimal content types for a niche"""
        content_types = {
            'fitness': ['tutorial videos', 'workout routines', 'transformation content', 'challenge participation', 'nutrition tips'],
            'food': ['recipe tutorials', 'cooking tips', 'food reviews', 'restaurant showcases', 'meal prep content'],
            'comedy': ['skits', 'relatable humor', 'viral trend participation', 'memes', 'standup clips'],
            'fashion': ['outfit showcases', 'styling tips', 'try-on hauls', 'brand reviews', 'lookbook creation'],
            'travel': ['destination guides', 'travel tips', 'vlog content', 'adventure content', 'local exploration'],
            'beauty': ['makeup tutorials', 'skincare routines', 'product reviews', 'transformations', 'hairstyle tutorials'],
            'motivation': ['motivational speeches', 'success stories', 'mindset advice', 'goal setting', 'daily routines'],
            'dance': ['choreography tutorials', 'dance challenges', 'viral dance trends', 'step-by-step guides', 'dance covers'],
            'music': ['music covers', 'audio recommendations', 'artist features', 'music challenges', 'song reactions'],
            'general': ['viral trend participation', 'storytelling', 'behind-the-scenes', 'day in the life', 'entertainment']
        }
        
        return content_types.get(niche, content_types['general'])
    
    def _estimate_hashtag_lifespan(self, hashtag_velocity: HashtagVelocity) -> int:
        """Estimate how long a hashtag will remain trending"""
        if hashtag_velocity.trend_direction == "declining":
            return 24  # 1 day left
        elif hashtag_velocity.trend_direction == "stable":
            return 72  # 3 days
        elif hashtag_velocity.velocity_score > 100:
            return 168  # 7 days for super viral
        else:
            return 120  # 5 days for regular viral
    
    def _determine_competition_level(self, estimated_creators: int) -> str:
        """Determine competition level based on creator participation"""
        if estimated_creators > 100000:
            return "high"
        elif estimated_creators > 50000:
            return "medium"
        else:
            return "low"

# Example usage and testing
if __name__ == "__main__":
    tracker = HashtagVelocityTracker()
    
    print("=== Hashtag Velocity Tracking System ===")
    
    # Track hashtag velocity
    velocities = tracker.track_hashtag_velocity(hours_window=24)
    print(f"\nTracked {len(velocities)} hashtags")
    
    print("\nTop 10 Hashtags by Velocity:")
    for hv in velocities[:10]:
        print(f"\n#{hv.hashtag}")
        print(f"   Velocity Score: {hv.velocity_score:.1f}")
        print(f"   Direction: {hv.trend_direction}")
        print(f"   Usage Count: {hv.current_count}")
        print(f"   Niche: {hv.niche_relevance}")
    
    # Get trending hashtags
    trending = tracker.get_trending_hashtags(min_velocity=10)
    print(f"\n\nTrending Hashtags: {len(trending)}")
    
    for trend in trending[:5]:
        print(f"\n#{trend.hashtag}")
        print(f"   Velocity: {trend.velocity_score:.1f}")
        print(f"   Direction: {trend.trend_direction}")
        print(f"   Themes: {', '.join(trend.content_themes[:3])}")
        print(f"   Competition: {trend.competition_level}")
        print(f"   Lifespan: {trend.estimated_lifespan_hours}h")