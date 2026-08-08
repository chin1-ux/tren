"""
Creator Success Dashboard Backend
Tracks creator performance, provides analytics, and integrates with trend data.
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
        filename="creator_analytics.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
except Exception:
    pass

logger = logging.getLogger(__name__)

@dataclass
class CreatorMetrics:
    """Represents performance metrics for a creator"""
    creator_email: str
    total_reels_analyzed: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    avg_engagement_rate: float
    avg_velocity_score: float
    top_performing_content: List[Dict]
    content_categories: Dict[str, int]  # {category: count}
    trend_adoption_rate: float
    viral_content_count: int
    growth_trend: str  # "growing", "stable", "declining"
    peak_performance_hours: List[int]  # Hours when content performs best
    optimal_posting_times: List[str]
    is_connected: bool = True

@dataclass
class TrendAdoption:
    """Represents a creator's adoption of specific trends"""
    trend_id: int
    trend_name: str
    adoption_date: datetime
    content_created: int
    avg_performance: float
    success_score: float  # How well the trend worked for this creator
    timing_score: float  # How early they jumped on the trend
    category_fit: str  # How well the trend matches their usual content

@dataclass
class ContentPerformance:
    """Represents performance of individual content pieces"""
    content_id: str
    content_type: str
    category: str
    views: int
    likes: int
    comments: int
    shares: int
    saves: int
    engagement_rate: float
    velocity_score: float
    posted_at: datetime
    trending_hashtags: List[str]
    audio_used: Optional[str]
    performance_score: float

class CreatorAnalyticsEngine:
    """
    Creator Success Dashboard Backend
    Analyzes creator performance and provides actionable insights
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
    
    def get_creator_metrics(self, creator_email: str, days_back: int = 30) -> CreatorMetrics:
        """
        Get comprehensive metrics for a creator
        """
        if not self.supabase:
            logger.warning("Supabase not available for creator analytics")
            return self._empty_metrics(creator_email, is_connected=False)
        
        try:
            # Check if user is connected via instagram_tokens
            tokens_res = self.supabase.table('instagram_tokens').select('id').eq('user_email', creator_email).execute()
            if not tokens_res.data:
                logger.info(f"Creator {creator_email} is not connected to Instagram")
                return self._empty_metrics(creator_email, is_connected=False)
            
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
            
            # Get creator's reels (assuming reels have owner_email or similar field)
            # For now, we'll simulate this with a general query
            reels_res = self.supabase.table('reels') \
                .select('*') \
                .gte('created_at', time_threshold) \
                .limit(1000) \
                .execute()
            
            reels = reels_res.data or []
            
            # Calculate metrics
            total_views = sum(r.get('view_count', 0) for r in reels)
            total_likes = sum(r.get('like_count', 0) for r in reels)
            total_comments = sum(r.get('comment_count', 0) for r in reels)
            total_shares = sum(r.get('share_count', 0) for r in reels)
            
            avg_engagement_rate = 0
            if total_views > 0:
                total_engagement = total_likes + total_comments + total_shares
                avg_engagement_rate = (total_engagement / total_views) * 100
            
            avg_velocity = sum(r.get('velocity_score', 0) for r in reels) / len(reels) if reels else 0
            
            # Top performing content
            sorted_reels = sorted(reels, key=lambda r: r.get('view_count', 0), reverse=True)
            top_performing = sorted_reels[:5]
            
            # Content categories
            categories = defaultdict(int)
            for reel in reels:
                category = reel.get('category', 'general')
                categories[category] += 1
            
            # Viral content (high velocity or views)
            viral_count = sum(1 for r in reels if r.get('velocity_score', 0) > 50 or r.get('view_count', 0) > 100000)
            
            # Growth trend (simplified - compare recent vs older)
            mid_point = len(reels) // 2
            recent_avg = sum(r.get('view_count', 0) for r in reels[:mid_point]) / mid_point if mid_point > 0 else 0
            older_avg = sum(r.get('view_count', 0) for r in reels[mid_point:]) / (len(reels) - mid_point) if len(reels) > mid_point else 0
            
            if recent_avg > older_avg * 1.2:
                growth_trend = "growing"
            elif recent_avg < older_avg * 0.8:
                growth_trend = "declining"
            else:
                growth_trend = "stable"
            
            # Peak performance hours
            hours = defaultdict(int)
            for reel in reels:
                try:
                    created_at = reel.get('created_at', '')
                    if created_at.endswith('Z'):
                        created_at = created_at[:-1] + '+00:00'
                    dt = datetime.fromisoformat(created_at)
                    hours[dt.hour] += reel.get('view_count', 0)
                except Exception:
                    pass
            
            peak_hours = sorted(hours.items(), key=lambda x: x[1], reverse=True)[:3]
            peak_performance_hours = [h for h, _ in peak_hours]
            
            # Optimal posting times
            optimal_times = self._get_optimal_posting_times(peak_performance_hours)
            
            # Trend adoption rate (simplified)
            trend_adoption_rate = 0.7  # Placeholder
            
            return CreatorMetrics(
                creator_email=creator_email,
                total_reels_analyzed=len(reels),
                total_views=total_views,
                total_likes=total_likes,
                total_comments=total_comments,
                total_shares=total_shares,
                avg_engagement_rate=avg_engagement_rate,
                avg_velocity_score=avg_velocity,
                top_performing_content=[{
                    'id': r.get('id'),
                    'views': r.get('view_count'),
                    'likes': r.get('like_count'),
                    'velocity': r.get('velocity_score'),
                    'category': r.get('category')
                } for r in top_performing],
                content_categories=dict(categories),
                trend_adoption_rate=trend_adoption_rate,
                viral_content_count=viral_count,
                growth_trend=growth_trend,
                peak_performance_hours=peak_performance_hours,
                optimal_posting_times=optimal_times,
                is_connected=True
            )
            
        except Exception as e:
            logger.error(f"Error getting creator metrics: {e}")
            return self._empty_metrics(creator_email, is_connected=False)
    
    def get_trend_adoption_history(self, creator_email: str, days_back: int = 90) -> List[TrendAdoption]:
        """
        Get history of trend adoption by the creator
        """
        if not self.supabase:
            return []
        
        try:
            # This would query a creator_trend_adoption table
            # For now, return sample data
            return [
                TrendAdoption(
                    trend_id=1,
                    trend_name="Dance Challenge Trend",
                    adoption_date=datetime.now(timezone.utc) - timedelta(days=15),
                    content_created=3,
                    avg_performance=75.5,
                    success_score=85,
                    timing_score=90,
                    category_fit="excellent"
                ),
                TrendAdoption(
                    trend_id=2,
                    trend_name="Viral Audio Trend",
                    adoption_date=datetime.now(timezone.utc) - timedelta(days=30),
                    content_created=2,
                    avg_performance=60.2,
                    success_score=70,
                    timing_score=75,
                    category_fit="good"
                )
            ]
        except Exception as e:
            logger.error(f"Error getting trend adoption history: {e}")
            return []
    
    def get_content_performance_over_time(self, creator_email: str, days_back: int = 30) -> List[Dict]:
        """
        Get content performance data over time for charts
        """
        if not self.supabase:
            return []
        
        try:
            # Check if user is connected via instagram_tokens
            tokens_res = self.supabase.table('instagram_tokens').select('id').eq('user_email', creator_email).execute()
            if not tokens_res.data:
                logger.info(f"Creator {creator_email} is not connected to Instagram, returning empty performance data")
                return []
            
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
            
            reels_res = self.supabase.table('reels') \
                .select('created_at, view_count, like_count, comment_count, velocity_score') \
                .gte('created_at', time_threshold) \
                .order('created_at') \
                .execute()
            
            reels = reels_res.data or []
            
            # Group by day
            daily_data = defaultdict(lambda: {'views': 0, 'likes': 0, 'comments': 0, 'count': 0})
            
            for reel in reels:
                try:
                    created_at = reel.get('created_at', '')
                    if created_at.endswith('Z'):
                        created_at = created_at[:-1] + '+00:00'
                    dt = datetime.fromisoformat(created_at)
                    day_key = dt.strftime('%Y-%m-%d')
                    
                    daily_data[day_key]['views'] += reel.get('view_count', 0)
                    daily_data[day_key]['likes'] += reel.get('like_count', 0)
                    daily_data[day_key]['comments'] += reel.get('comment_count', 0)
                    daily_data[day_key]['count'] += 1
                except Exception:
                    pass
            
            # Convert to list
            performance_data = []
            for day, data in sorted(daily_data.items()):
                performance_data.append({
                    'date': day,
                    'total_views': data['views'],
                    'total_likes': data['likes'],
                    'total_comments': data['comments'],
                    'content_count': data['count'],
                    'avg_views': data['views'] / data['count'] if data['count'] > 0 else 0
                })
            
            return performance_data
            
        except Exception as e:
            logger.error(f"Error getting content performance over time: {e}")
            return []
    
    def get_success_recommendations(self, creator_email: str) -> List[Dict]:
        """
        Get personalized success recommendations based on creator data
        """
        metrics = self.get_creator_metrics(creator_email)
        recommendations = []
        
        # Growth trend recommendations
        if metrics.growth_trend == "declining":
            recommendations.append({
                'type': 'critical',
                'title': 'Declining Performance Detected',
                'description': 'Your recent content is performing worse than usual. Consider trying new trends or content formats.',
                'action': 'Review top performing content and replicate successful elements'
            })
        elif metrics.growth_trend == "stable":
            recommendations.append({
                'type': 'info',
                'title': 'Stable Performance',
                'description': 'Your performance is consistent. Consider experimenting with viral trends to boost growth.',
                'action': 'Try trending audio or participate in viral challenges'
            })
        
        # Engagement rate recommendations
        if metrics.avg_engagement_rate < 5:
            recommendations.append({
                'type': 'warning',
                'title': 'Low Engagement Rate',
                'description': f'Your engagement rate is {metrics.avg_engagement_rate:.1f}%. Industry average is 5-10%.',
                'action': 'Focus on creating more engaging content with hooks and CTAs'
            })
        
        # Posting time recommendations
        if metrics.peak_performance_hours:
            recommendations.append({
                'type': 'success',
                'title': 'Optimal Posting Times Identified',
                'description': f'Your content performs best at {", ".join(str(h) for h in metrics.peak_performance_hours)}:00 IST.',
                'action': 'Schedule your most important content during these peak hours'
            })
        
        # Category recommendations
        if metrics.content_categories:
            top_category = max(metrics.content_categories.items(), key=lambda x: x[1])
            recommendations.append({
                'type': 'info',
                'title': 'Top Content Category',
                'description': f'You perform best with {top_category[0]} content ({top_category[1]} pieces).',
                'action': 'Focus more on this category while experimenting with others'
            })
        
        # Viral content recommendations
        if metrics.viral_content_count > 0:
            recommendations.append({
                'type': 'success',
                'title': 'Viral Content Success',
                'description': f'You have {metrics.viral_content_count} viral pieces. Analyze what made them successful.',
                'action': 'Replicate successful elements from your viral content'
            })
        
        return recommendations
    
    def _empty_metrics(self, creator_email: str, is_connected: bool = False) -> CreatorMetrics:
        """Return empty metrics when data is unavailable"""
        return CreatorMetrics(
            creator_email=creator_email,
            total_reels_analyzed=0,
            total_views=0,
            total_likes=0,
            total_comments=0,
            total_shares=0,
            avg_engagement_rate=0,
            avg_velocity_score=0,
            top_performing_content=[],
            content_categories={},
            trend_adoption_rate=0,
            viral_content_count=0,
            growth_trend="stable",
            peak_performance_hours=[],
            optimal_posting_times=[],
            is_connected=is_connected
        )
    
    def _get_optimal_posting_times(self, peak_hours: List[int]) -> List[str]:
        """Convert peak hours to readable time strings"""
        times = []
        for hour in peak_hours:
            if hour < 12:
                times.append(f"{hour}:00 AM")
            elif hour == 12:
                times.append("12:00 PM")
            else:
                times.append(f"{hour - 12}:00 PM")
        return times

# Example usage and testing
if __name__ == "__main__":
    analytics = CreatorAnalyticsEngine()
    
    print("=== Creator Success Dashboard Backend ===")
    
    # Get creator metrics
    metrics = analytics.get_creator_metrics("test@example.com")
    print(f"\nCreator Metrics:")
    print(f"  Total Reels: {metrics.total_reels_analyzed}")
    print(f"  Total Views: {metrics.total_views:,}")
    print(f"  Avg Engagement Rate: {metrics.avg_engagement_rate:.2f}%")
    print(f"  Growth Trend: {metrics.growth_trend}")
    print(f"  Viral Content: {metrics.viral_content_count}")
    print(f"  Peak Hours: {metrics.peak_performance_hours}")
    
    # Get trend adoption history
    adoption = analytics.get_trend_adoption_history("test@example.com")
    print(f"\nTrend Adoption History: {len(adoption)}")
    for ad in adoption:
        print(f"  {ad.trend_name}: Success Score {ad.success_score}")
    
    # Get success recommendations
    recommendations = analytics.get_success_recommendations("test@example.com")
    print(f"\nSuccess Recommendations: {len(recommendations)}")
    for rec in recommendations:
        print(f"  [{rec['type'].upper()}] {rec['title']}")
        print(f"    {rec['description']}")
        print(f"    Action: {rec['action']}")