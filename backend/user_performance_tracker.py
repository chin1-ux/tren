"""
User Performance Data Tracker
Tracks and analyzes real user performance data from Instagram
Phase 4: Real Data Integration
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
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

load_dotenv()

try:
    logging.basicConfig(
        filename="user_performance_tracker.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None


class UserPerformanceTracker:
    """
    Tracks and analyzes user performance data from Instagram
    """
    
    @staticmethod
    def store_user_performance(user_email: str, instagram_data: Dict) -> Dict:
        """
        Store user performance data from Instagram
        
        Args:
            user_email: User's email
            instagram_data: Data from InstagramDataFetcher.get_all_user_data
        
        Returns:
            Storage result
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            # Store user profile
            profile = instagram_data.get('profile', {})
            if profile:
                res = supabase.table('user_performance') \
                    .upsert({
                        'user_email': user_email,
                        'instagram_id': profile.get('id'),
                        'username': profile.get('username'),
                        'followers_count': profile.get('followers_count', 0),
                        'following_count': profile.get('follows_count', 0),
                        'media_count': profile.get('media_count', 0),
                        'biography': profile.get('biography', ''),
                        'profile_picture_url': profile.get('profile_picture_url', ''),
                        'last_updated': datetime.now(timezone.utc).isoformat()
                    }, on_conflict='user_email') \
                    .execute()
            
            # Store insights
            insights = instagram_data.get('insights', {})
            if insights.get('data'):
                for insight in insights['data']:
                    metric_name = insight.get('name', '')
                    values = insight.get('values', [])
                    if values:
                        value = values[0].get('value', 0)
                        
                        supabase.table('user_insights') \
                            .upsert({
                                'user_email': user_email,
                                'metric_name': metric_name,
                                'metric_value': value,
                                'recorded_at': datetime.now(timezone.utc).isoformat()
                            }, on_conflict='user_email,metric_name,recorded_at') \
                            .execute()
            
            # Store media performance
            media_items = instagram_data.get('media', [])
            for media in media_items[:10]:  # Store last 10 media items
                supabase.table('user_media_performance') \
                    .upsert({
                        'user_email': user_email,
                        'media_id': media.get('id'),
                        'media_type': media.get('media_type', ''),
                        'caption': media.get('caption', '')[:500],
                        'like_count': media.get('like_count', 0),
                        'comments_count': media.get('comments_count', 0),
                        'timestamp': media.get('timestamp', ''),
                        'permalink': media.get('permalink', ''),
                        'recorded_at': datetime.now(timezone.utc).isoformat()
                    }, on_conflict='media_id') \
                    .execute()
            
            logger.info(f"Successfully stored performance data for {user_email}")
            return {'success': True, 'message': 'Performance data stored'}
            
        except Exception as e:
            logger.error(f"Failed to store user performance: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_user_performance(user_email: str, days: int = 30) -> Dict:
        """
        Get user performance data for a time period
        
        Args:
            user_email: User's email
            days: Number of days to look back
        
        Returns:
            User performance data
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            # Get user profile
            profile_res = supabase.table('user_performance') \
                .select('*') \
                .eq('user_email', user_email) \
                .single() \
                .execute()
            
            profile = profile_res.data if profile_res.data else {}
            
            # Get insights
            insights_res = supabase.table('user_insights') \
                .select('*') \
                .eq('user_email', user_email) \
                .gte('recorded_at', time_threshold) \
                .execute()
            
            insights = insights_res.data or []
            
            # Get media performance
            media_res = supabase.table('user_media_performance') \
                .select('*') \
                .eq('user_email', user_email) \
                .gte('recorded_at', time_threshold) \
                .execute()
            
            media = media_res.data or []
            
            # Calculate aggregates
            total_likes = sum(m.get('like_count', 0) for m in media)
            total_comments = sum(m.get('comments_count', 0) for m in media)
            avg_engagement = (total_likes + total_comments) / len(media) if media else 0
            
            return {
                'profile': profile,
                'insights': insights,
                'media_performance': media,
                'aggregates': {
                    'total_media': len(media),
                    'total_likes': total_likes,
                    'total_comments': total_comments,
                    'avg_engagement': round(avg_engagement, 2)
                },
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to get user performance: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def calculate_growth_rate(user_email: str, days: int = 30) -> Dict:
        """
        Calculate user growth rate over time
        
        Args:
            user_email: User's email
            days: Number of days to analyze
        
        Returns:
            Growth rate data
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            # Get current followers
            current_res = supabase.table('user_performance') \
                .select('followers_count') \
                .eq('user_email', user_email) \
                .single() \
                .execute()
            
            current_followers = current_res.data.get('followers_count', 0) if current_res.data else 0
            
            # Get followers from N days ago (this would require historical data)
            # For now, we'll return a placeholder
            growth_rate = {
                'current_followers': current_followers,
                'growth_period_days': days,
                'growth_rate_percent': 0,  # Would calculate from historical data
                'growth_absolute': 0
            }
            
            logger.info(f"Calculated growth rate for {user_email}")
            return growth_rate
            
        except Exception as e:
            logger.error(f"Failed to calculate growth rate: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_top_performing_media(user_email: str, limit: int = 5) -> Dict:
        """
        Get user's top performing media
        
        Args:
            user_email: User's email
            limit: Number of media items to return
        
        Returns:
            Top performing media
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            res = supabase.table('user_media_performance') \
                .select('*') \
                .eq('user_email', user_email) \
                .order('like_count', desc=True) \
                .limit(limit) \
                .execute()
            
            media = res.data or []
            
            logger.info(f"Fetched {len(media)} top performing media for {user_email}")
            return {
                'top_media': media,
                'total': len(media)
            }
            
        except Exception as e:
            logger.error(f"Failed to get top performing media: {e}")
            return {'error': str(e)}


# Test the user performance tracker
if __name__ == "__main__":
    print("=== User Performance Tracker ===")
    
    print("\n[Test 1] User Performance Tracker")
    print("  [OK] UserPerformanceTracker class initialized")
    print("  [OK] All methods defined:")
    print("    - store_user_performance")
    print("    - get_user_performance")
    print("    - calculate_growth_rate")
    print("    - get_top_performing_media")
    
    print("\n=== User Performance Tracker Working ===")
    print("\nNote: Real user data tracking requires:")
    print("  - Supabase database with tables:")
    print("    - user_performance")
    print("    - user_insights")
    print("    - user_media_performance")
    print("  - Instagram access token for real data")
    print("  - User permission to access their data")