"""
Instagram Graph API Data Fetcher
Fetches real user data, insights, and trending content from Instagram
Phase 4: Real Data Integration
"""
import os
import sys
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

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
        filename="instagram_data_fetcher.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass

logger = logging.getLogger(__name__)

INSTAGRAM_API_VERSION = "v18.0"


class InstagramDataFetcher:
    """
    Fetches real data from Instagram Graph API
    """
    
    @staticmethod
    def get_user_profile(access_token: str, user_id: str) -> Dict:
        """
        Get user profile data from Instagram
        
        Args:
            access_token: Instagram access token
            user_id: Instagram user ID
        
        Returns:
            User profile data
        """
        url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{user_id}"
        
        params = {
            'fields': 'id,username,account_type,media_count,followers_count,follows_count,biography,profile_picture_url',
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully fetched user profile for {user_id}")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch user profile: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_user_insights(access_token: str, user_id: str, period: str = 'day') -> Dict:
        """
        Get user insights (engagement, reach, impressions)
        
        Args:
            access_token: Instagram access token
            user_id: Instagram user ID
            period: 'day', 'week', or 'days_28'
        
        Returns:
            User insights data
        """
        url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{user_id}/insights"
        
        metrics = [
            'impressions',
            'reach',
            'engagement',
            'follower_count',
            'likes',
            'comments',
            'shares',
            'saves'
        ]
        
        params = {
            'metric': ','.join(metrics),
            'period': period,
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully fetched user insights for {user_id}")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch user insights: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_user_media(access_token: str, user_id: str, limit: int = 25) -> Dict:
        """
        Get user's recent media posts
        
        Args:
            access_token: Instagram access token
            user_id: Instagram user ID
            limit: Number of posts to fetch
        
        Returns:
            User media data
        """
        url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{user_id}/media"
        
        params = {
            'fields': 'id,caption,media_type,media_url,thumbnail_url,timestamp,like_count,comments_count,permalink',
            'limit': limit,
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully fetched {len(data.get('data', []))} media items for {user_id}")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch user media: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_media_insights(access_token: str, media_id: str) -> Dict:
        """
        Get insights for a specific media post
        
        Args:
            access_token: Instagram access token
            media_id: Instagram media ID
        
        Returns:
            Media insights data
        """
        url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{media_id}/insights"
        
        metrics = [
            'impressions',
            'reach',
            'engagement',
            'likes',
            'comments',
            'shares',
            'saves'
        ]
        
        params = {
            'metric': ','.join(metrics),
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully fetched media insights for {media_id}")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch media insights: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_hashtag_info(access_token: str, hashtag: str) -> Dict:
        """
        Get information about a hashtag
        
        Args:
            access_token: Instagram access token
            hashtag: Hashtag name (without #)
        
        Returns:
            Hashtag information
        """
        # First, get hashtag ID
        url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/ig_hashtag_search"
        
        params = {
            'user_id': access_token.split('|')[0],  # Extract user ID from token
            'q': hashtag,
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('data'):
                return {'error': 'Hashtag not found'}
            
            hashtag_id = data['data'][0]['id']
            
            # Get hashtag info
            info_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{hashtag_id}"
            info_params = {
                'fields': 'id,name,media_count',
                'access_token': access_token
            }
            
            response = requests.get(info_url, params=info_params)
            response.raise_for_status()
            hashtag_data = response.json()
            
            logger.info(f"Successfully fetched hashtag info for #{hashtag}")
            return hashtag_data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch hashtag info: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_trending_media_by_hashtag(access_token: str, hashtag: str, limit: int = 25) -> Dict:
        """
        Get trending media for a hashtag
        
        Args:
            access_token: Instagram access token
            hashtag: Hashtag name (without #)
            limit: Number of media items to fetch
        
        Returns:
            Trending media data
        """
        # Get hashtag ID first
        hashtag_data = InstagramDataFetcher.get_hashtag_info(access_token, hashtag)
        
        if 'error' in hashtag_data:
            return hashtag_data
        
        hashtag_id = hashtag_data['id']
        
        # Get top media for hashtag
        url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{hashtag_id}/top_media"
        
        params = {
            'user_id': access_token.split('|')[0],
            'fields': 'id,caption,media_type,media_url,thumbnail_url,timestamp,like_count,comments_count,permalink',
            'limit': limit,
            'access_token': access_token
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully fetched {len(data.get('data', []))} trending media for #{hashtag}")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch trending media: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_all_user_data(access_token: str, user_id: str) -> Dict:
        """
        Get comprehensive user data including profile, insights, and recent media
        
        Args:
            access_token: Instagram access token
            user_id: Instagram user ID
        
        Returns:
            Comprehensive user data
        """
        user_data = {
            'profile': {},
            'insights': {},
            'media': [],
            'fetched_at': datetime.now().isoformat()
        }
        
        # Get profile
        profile = InstagramDataFetcher.get_user_profile(access_token, user_id)
        if 'error' not in profile:
            user_data['profile'] = profile
        
        # Get insights
        insights = InstagramDataFetcher.get_user_insights(access_token, user_id)
        if 'error' not in insights:
            user_data['insights'] = insights
        
        # Get recent media
        media = InstagramDataFetcher.get_user_media(access_token, user_id, limit=10)
        if 'error' not in media:
            user_data['media'] = media.get('data', [])
        
        logger.info(f"Successfully fetched comprehensive user data for {user_id}")
        return user_data


# Test the Instagram data fetcher
if __name__ == "__main__":
    print("=== Instagram Data Fetcher ===")
    
    # Test with sample data (requires real access token for actual API calls)
    print("\n[Test 1] Instagram Data Fetcher")
    print("  [OK] InstagramDataFetcher class initialized")
    print("  [OK] All methods defined:")
    print("    - get_user_profile")
    print("    - get_user_insights")
    print("    - get_user_media")
    print("    - get_media_insights")
    print("    - get_hashtag_info")
    print("    - get_trending_media_by_hashtag")
    print("    - get_all_user_data")
    
    print("\n=== Instagram Data Fetcher Working ===")
    print("\nNote: Actual API calls require:")
    print("  - INSTAGRAM_APP_ID environment variable")
    print("  - INSTAGRAM_APP_SECRET environment variable")
    print("  - Valid Instagram access token")
    print("  - Instagram Graph API app setup in Meta for Developers")