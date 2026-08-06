"""
Global Event Monitoring System
Detects major events (sports, cultural festivals, news) that flood social media feeds.
Creators can leverage these events for content creation and trend participation.
"""
import os
import sys
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
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
        filename="event_monitor.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
except Exception:
    pass

logger = logging.getLogger(__name__)

class EventType(Enum):
    SPORTS = "sports"
    ENTERTAINMENT = "entertainment"
    CULTURAL = "cultural"
    NEWS = "news"
    POLITICAL = "political"
    TECHNOLOGY = "technology"

class EventImpact(Enum):
    HIGH = "high"      # Major event, widespread participation
    MEDIUM = "medium"  # Significant event, niche but notable
    LOW = "low"        # Minor event, limited impact

@dataclass
class SocialMediaEvent:
    """Represents a major event that affects social media content"""
    id: str
    name: str
    event_type: EventType
    impact: EventImpact
    start_date: datetime
    end_date: datetime
    hashtags: List[str]
    content_themes: List[str]
    creator_opportunities: List[str]
    target_audiences: List[str]
    platform_relevance: Dict[str, float]  # {platform: relevance_score}
    viral_potential: float  # 0-100
    trending_now: bool = False
    estimated_creator_participation: int = 0  # estimated number of creators participating

class EventMonitor:
    """
    Global Event Monitoring System
    Tracks events that cause social media feeds to flood with specific content
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
        
        # Predefined Indian cultural events (static database)
        self.indian_cultural_events = self._get_indian_cultural_events()
        
        # Sports events database
        self.sports_events = self._get_sports_events()
    
    def _get_indian_cultural_events(self) -> List[Dict]:
        """Static database of major Indian cultural events"""
        current_year = datetime.now().year
        return [
            {
                "id": f"diwali_{current_year}",
                "name": "Diwali",
                "event_type": EventType.CULTURAL,
                "impact": EventImpact.HIGH,
                "month": 10,  # October/November
                "hashtags": ["#diwali", "#diwali2026", "#festivaloflights", "#deepavali", "#diwalicelebrations"],
                "content_themes": ["home decoration", "rangoli", "diyas", "sweets", "family gatherings", "traditional outfits"],
                "creator_opportunities": ["home decor tutorials", "recipe videos", "outfit showcases", "family vlogs", "rangoli art"],
                "target_audiences": ["family-oriented", "home decor enthusiasts", "food lovers", "fashion enthusiasts"],
                "platform_relevance": {"instagram": 0.9, "youtube_shorts": 0.85, "tiktok": 0.7},
                "viral_potential": 85
            },
            {
                "id": f"eid_{current_year}",
                "name": "Eid al-Fitr",
                "event_type": EventType.CULTURAL,
                "impact": EventImpact.HIGH,
                "month": 3,  # Varies (March/April)
                "hashtags": ["#eid", "#eid2026", "#eidmubarak", "#celebration", "#festivals"],
                "content_themes": ["festive food", "traditional outfits", "family gatherings", "prayer videos", "charity"],
                "creator_opportunities": ["recipe videos", "outfit showcases", "family vlogs", "charity content"],
                "target_audiences": ["family-oriented", "food lovers", "fashion enthusiasts", "community-focused"],
                "platform_relevance": {"instagram": 0.85, "youtube_shorts": 0.8, "tiktok": 0.75},
                "viral_potential": 80
            },
            {
                "id": f"holi_{current_year}",
                "name": "Holi",
                "event_type": EventType.CULTURAL,
                "impact": EventImpact.HIGH,
                "month": 2,  # March
                "hashtags": ["#holi", "#holi2026", "#festivalofcolors", "#rang", "#holicelebrations"],
                "content_themes": ["color play", "holi parties", "traditional sweets", "music", "dance"],
                "creator_opportunities": ["music videos", "dance tutorials", "party content", "recipe videos", "fashion"],
                "target_audiences": ["youth", "music lovers", "dance enthusiasts", "party-goers"],
                "platform_relevance": {"instagram": 0.95, "youtube_shorts": 0.9, "tiktok": 0.85},
                "viral_potential": 90
            },
            {
                "id": f"navratri_{current_year}",
                "name": "Navratri",
                "event_type": EventType.CULTURAL,
                "impact": EventImpact.HIGH,
                "month": 9,  # October
                "hashtags": ["#navratri", "#navratri2026", "#garba", "#dandiya", "#festivals"],
                "content_themes": ["garba dance", "traditional music", "fashion", "prayer", "fasting"],
                "creator_opportunities": ["dance tutorials", "music videos", "outfit showcases", "religious content"],
                "target_audiences": ["dance enthusiasts", "music lovers", "fashion enthusiasts", "religious communities"],
                "platform_relevance": {"instagram": 0.8, "youtube_shorts": 0.75, "tiktok": 0.6},
                "viral_potential": 75
            },
            {
                "id": f"christmas_{current_year}",
                "name": "Christmas",
                "event_type": EventType.CULTURAL,
                "impact": EventImpact.HIGH,
                "month": 12,  # December
                "hashtags": ["#christmas", "#christmas2026", "#xmas", "#festivals", "#celebration"],
                "content_themes": ["decorations", "gifts", "family gatherings", "food", "music"],
                "creator_opportunities": ["decor tutorials", "gift guides", "recipe videos", "family vlogs"],
                "target_audiences": ["family-oriented", "home decor enthusiasts", "food lovers"],
                "platform_relevance": {"instagram": 0.8, "youtube_shorts": 0.75, "tiktok": 0.7},
                "viral_potential": 75
            },
            {
                "id": f"pongal_{current_year}",
                "name": "Pongal",
                "event_type": EventType.CULTURAL,
                "impact": EventImpact.MEDIUM,
                "month": 1,  # January
                "hashtags": ["#pongal", "#pongal2026", "#harvestfestival", "#tamil", "#festivals"],
                "content_themes": ["harvest", "traditional food", "sugar cane", "decorations", "family"],
                "creator_opportunities": ["recipe videos", "fashion", "family vlogs", "cultural education"],
                "target_audiences": ["tamil community", "food lovers", "cultural enthusiasts"],
                "platform_relevance": {"instagram": 0.7, "youtube_shorts": 0.65, "tiktok": 0.5},
                "viral_potential": 65
            },
            {
                "id": f"onam_{current_year}",
                "name": "Onam",
                "event_type": EventType.CULTURAL,
                "impact": EventImpact.MEDIUM,
                "month": 8,  # August/September
                "hashtags": ["#onam", "#onam2026", "#kerala", "#harvestfestival", "#festivals"],
                "content_themes": ["boat races", "traditional food", "flower arrangements", "dance", "music"],
                "creator_opportunities": ["cultural education", "recipe videos", "travel content", "dance"],
                "target_audiences": ["kerala community", "travel enthusiasts", "cultural enthusiasts"],
                "platform_relevance": {"instagram": 0.7, "youtube_shorts": 0.65, "tiktok": 0.5},
                "viral_potential": 65
            }
        ]
    
    def _get_sports_events(self) -> List[Dict]:
        """Sports events that typically drive social media activity"""
        current_year = datetime.now().year
        events = []
        
        # IPL (Indian Premier League) - runs March-May
        events.append({
            "id": f"ipl_{current_year}",
            "name": "IPL Indian Premier League",
            "event_type": EventType.SPORTS,
            "impact": EventImpact.HIGH,
            "month": 4,  # Peak in April
            "hashtags": ["#ipl", f"#ipl{current_year}", "#cricket", "#t20", "#indiancricket"],
            "content_themes": ["match highlights", "player celebrations", "team support", "cricket analysis", "stadium vibes"],
            "creator_opportunities": ["match reaction videos", "cricket analysis", "team support content", "stadium experiences"],
            "target_audiences": ["cricket fans", "sports enthusiasts", "team supporters"],
            "platform_relevance": {"instagram": 0.95, "youtube_shorts": 0.9, "twitter": 0.85},
            "viral_potential": 95
        })
        
        # FIFA World Cup (if happening)
        events.append({
            "id": f"fifa_world_cup_{current_year}",
            "name": "FIFA World Cup",
            "event_type": EventType.SPORTS,
            "impact": EventImpact.HIGH,
            "month": 6,  # June/July (varies)
            "hashtags": ["#fifaworldcup", "#worldcup", "#football", "#soccer", "#fifa"],
            "content_themes": ["match highlights", "player celebrations", "national pride", "watch parties", "football analysis"],
            "creator_opportunities": ["match reactions", "football analysis", "watch party content", "national pride"],
            "target_audiences": ["football fans", "sports enthusiasts", "national pride"],
            "platform_relevance": {"instagram": 0.9, "youtube_shorts": 0.85, "twitter": 0.95, "tiktok": 0.8},
            "viral_potential": 98
        })
        
        # Olympics (if happening)
        events.append({
            "id": f"olympics_{current_year}",
            "name": "Olympic Games",
            "event_type": EventType.SPORTS,
            "impact": EventImpact.HIGH,
            "month": 7,  # July/August (varies)
            "hashtags": ["#olympics", f"#olympics{current_year}", "#olympicgames", "#sports", "#athletes"],
            "content_themes": ["athlete stories", "competition highlights", "national pride", "opening ceremony", "sports analysis"],
            "creator_opportunities": ["athlete features", "sports analysis", "national pride content", "behind-the-scenes"],
            "target_audiences": ["sports enthusiasts", "national pride", "athlete fans"],
            "platform_relevance": {"instagram": 0.85, "youtube_shorts": 0.8, "twitter": 0.9, "tiktok": 0.75},
            "viral_potential": 90
        })
        
        return events
    
    def get_active_events(self, days_ahead: int = 30, days_behind: int = 7) -> List[SocialMediaEvent]:
        """
        Get events that are currently active or coming up soon
        """
        now = datetime.now(timezone.utc)
        active_events = []
        
        # Check cultural events
        for event_data in self.indian_cultural_events:
            event = self._create_event_from_data(event_data, now)
            if self._is_event_active(event, now, days_ahead, days_behind):
                active_events.append(event)
        
        # Check sports events
        for event_data in self.sports_events:
            event = self._create_event_from_data(event_data, now)
            if self._is_event_active(event, now, days_ahead, days_behind):
                active_events.append(event)
        
        # Sort by proximity and viral potential
        active_events.sort(key=lambda e: (
            abs((e.start_date - now).days),
            -e.viral_potential
        ))
        
        return active_events
    
    def _create_event_from_data(self, event_data: Dict, now: datetime) -> SocialMediaEvent:
        """Create SocialMediaEvent from dictionary data"""
        current_year = now.year
        month = event_data.get('month', 1)
        
        # Estimate dates (this is simplified - in production, use actual event calendars)
        year = current_year if month >= now.month else current_year + 1
        start_date = datetime(year, month, 1, tzinfo=timezone.utc)
        end_date = datetime(year, month, 15, tzinfo=timezone.utc)  # Assume ~2 weeks duration
        
        return SocialMediaEvent(
            id=event_data['id'],
            name=event_data['name'],
            event_type=event_data['event_type'],
            impact=event_data['impact'],
            start_date=start_date,
            end_date=end_date,
            hashtags=event_data['hashtags'],
            content_themes=event_data['content_themes'],
            creator_opportunities=event_data['creator_opportunities'],
            target_audiences=event_data['target_audiences'],
            platform_relevance=event_data['platform_relevance'],
            viral_potential=event_data['viral_potential'],
            trending_now=self._is_event_trending_now(event_data['hashtags']),
            estimated_creator_participation=self._estimate_participation(event_data['impact'])
        )
    
    def _is_event_active(self, event: SocialMediaEvent, now: datetime, days_ahead: int, days_behind: int) -> bool:
        """Check if event is within the active window"""
        time_until_start = (event.start_date - now).days
        time_since_end = (now - event.end_date).days
        
        return -days_behind <= time_until_start <= days_ahead or time_since_end <= days_behind
    
    def _is_event_trending_now(self, hashtags: List[str]) -> bool:
        """Check if event hashtags are currently trending (simplified)"""
        # In production, this would check actual hashtag velocity from your reels data
        # For now, we'll simulate this based on time proximity
        current_month = datetime.now().month
        trending_months = [2, 3, 10, 12]  # Months with major events
        return current_month in trending_months
    
    def _estimate_participation(self, impact: EventImpact) -> int:
        """Estimate number of creators participating"""
        if impact == EventImpact.HIGH:
            return 100000  # 100K+ creators
        elif impact == EventImpact.MEDIUM:
            return 50000   # 50K+ creators
        else:
            return 10000   # 10K+ creators
    
    def detect_event_hashtag_spikes(self, hours_window: int = 24) -> List[Dict]:
        """
        Detect sudden spikes in hashtag usage that might indicate trending events
        This would analyze your reels data for unusual hashtag velocity patterns
        """
        if not self.supabase:
            logger.warning("Supabase not available for hashtag spike detection")
            return []
        
        try:
            # Look for hashtags with unusual velocity in recent reels
            time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours_window)).isoformat()
            
            # This is a simplified version - in production, you'd aggregate hashtag counts
            # and compare against baselines to detect anomalies
            query = f"""
            SELECT 
                unnest(hashtags) as hashtag,
                COUNT(*) as usage_count,
                AVG(velocity_score) as avg_velocity
            FROM reels
            WHERE created_at >= '{time_threshold}'
            GROUP BY hashtag
            HAVING COUNT(*) > 10
            ORDER BY avg_velocity DESC
            LIMIT 20
            """
            
            # For now, return sample data based on current events
            current_events = self.get_active_events(days_ahead=7, days_behind=7)
            spike_data = []
            
            for event in current_events:
                for hashtag in event.hashtags[:3]:  # Top 3 hashtags per event
                    spike_data.append({
                        'hashtag': hashtag,
                        'event_name': event.name,
                        'usage_count': event.estimated_creator_participation,
                        'velocity_score': event.viral_potential,
                        'spike_detected': True,
                        'trend_direction': 'increasing'
                    })
            
            return spike_data
            
        except Exception as e:
            logger.error(f"Error detecting hashtag spikes: {e}")
            return []
    
    def get_creator_opportunities_for_event(self, event_id: str) -> Dict:
        """
        Get detailed creator opportunities for a specific event
        """
        active_events = self.get_active_events()
        event = next((e for e in active_events if e.id == event_id), None)
        
        if not event:
            return {'error': 'Event not found'}
        
        return {
            'event': {
                'name': event.name,
                'type': event.event_type.value,
                'impact': event.impact.value,
                'viral_potential': event.viral_potential,
                'days_until_start': (event.start_date - datetime.now(timezone.utc)).days,
                'trending_now': event.trending_now
            },
            'opportunities': {
                'content_themes': event.content_themes,
                'creator_ideas': event.creator_opportunities,
                'target_audiences': event.target_audiences,
                'recommended_hashtags': event.hashtags,
                'platform_strategy': event.platform_relevance
            },
            'timing': {
                'best_content_windows': [
                    f"{(event.start_date - timedelta(days=7)).strftime('%Y-%m-%d')} to {event.start_date.strftime('%Y-%m-%d')} (pre-event)",
                    f"{event.start_date.strftime('%Y-%m-%d')} to {event.end_date.strftime('%Y-%m-%d')} (during event)",
                    f"{(event.end_date).strftime('%Y-%m-%d')} to {(event.end_date + timedelta(days=3)).strftime('%Y-%m-%d')} (post-event)"
                ],
                'peak_engagement_times': [
                    "9:00 AM IST - Morning browsing",
                    "7:00 PM IST - Evening prime time",
                    "10:00 PM IST - Late night social"
                ]
            },
            'estimated_metrics': {
                'creator_participation': event.estimated_creator_participation,
                'total_content_volume': event.estimated_creator_participation * 5,  # Assuming 5 posts per creator
                'competition_level': 'high' if event.impact == EventImpact.HIGH else 'medium'
            }
        }

# Example usage and testing
if __name__ == "__main__":
    monitor = EventMonitor()
    
    print("=== Global Event Monitoring System ===")
    
    # Get active events
    active_events = monitor.get_active_events(days_ahead=30, days_behind=7)
    print(f"\nActive Events (Next 30 days): {len(active_events)}")
    
    for event in active_events:
        print(f"\n📅 {event.name}")
        print(f"   Type: {event.event_type.value}")
        print(f"   Impact: {event.impact.value}")
        print(f"   Viral Potential: {event.viral_potential}/100")
        print(f"   Days until start: {(event.start_date - datetime.now(timezone.utc)).days}")
        print(f"   Hashtags: {', '.join(event.hashtags[:3])}")
        print(f"   Creator Opportunities: {', '.join(event.creator_opportunities[:3])}")
    
    # Detect hashtag spikes
    print("\n=== Hashtag Spike Detection ===")
    spikes = monitor.detect_event_hashtag_spikes()
    print(f"Detected {len(spikes)} hashtag spikes")
    
    for spike in spikes[:5]:
        print(f"\n📈 #{spike['hashtag']}")
        print(f"   Event: {spike['event_name']}")
        print(f"   Usage Count: {spike['usage_count']:,}")
        print(f"   Velocity Score: {spike['velocity_score']}")