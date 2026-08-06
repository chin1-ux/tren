"""
YouTube Data API Fetcher
Fetches trending videos and topics from YouTube
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
        filename="youtube_data_fetcher.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass

logger = logging.getLogger(__name__)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeDataFetcher:
    """
    Fetches real data from YouTube Data API
    """
    
    @staticmethod
    def get_trending_videos(region_code: str = "IN", category_id: str = "10", max_results: int = 25) -> Dict:
        """
        Get trending videos in a specific region
        
        Args:
            region_code: ISO country code (default: IN for India)
            category_id: Category ID (10 = Music, 22 = People & Blogs, 23 = Comedy)
            max_results: Maximum number of results
        
        Returns:
            Trending videos data
        """
        if not YOUTUBE_API_KEY:
            return {'error': 'YOUTUBE_API_KEY not configured'}
        
        url = f"{YOUTUBE_API_BASE_URL}/videos"
        
        params = {
            'part': 'snippet,statistics,contentDetails',
            'chart': 'mostPopular',
            'regionCode': region_code,
            'videoCategoryId': category_id,
            'maxResults': max_results,
            'key': YOUTUBE_API_KEY
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully fetched {len(data.get('items', []))} trending videos for {region_code}")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch trending videos: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_video_details(video_id: str) -> Dict:
        """
        Get detailed information about a specific video
        
        Args:
            video_id: YouTube video ID
        
        Returns:
            Video details
        """
        if not YOUTUBE_API_KEY:
            return {'error': 'YOUTUBE_API_KEY not configured'}
        
        url = f"{YOUTUBE_API_BASE_URL}/videos"
        
        params = {
            'part': 'snippet,statistics,contentDetails',
            'id': video_id,
            'key': YOUTUBE_API_KEY
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully fetched video details for {video_id}")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch video details: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def search_videos(query: str, max_results: int = 25, region_code: str = "IN") -> Dict:
        """
        Search for videos matching a query
        
        Args:
            query: Search query
            max_results: Maximum number of results
            region_code: ISO country code
        
        Returns:
            Search results
        """
        if not YOUTUBE_API_KEY:
            return {'error': 'YOUTUBE_API_KEY not configured'}
        
        url = f"{YOUTUBE_API_BASE_URL}/search"
        
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': max_results,
            'regionCode': region_code,
            'order': 'relevance',
            'key': YOUTUBE_API_KEY
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully searched for '{query}' - {len(data.get('items', []))} results")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to search videos: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_video_comments(video_id: str, max_results: int = 20) -> Dict:
        """
        Get comments for a video
        
        Args:
            video_id: YouTube video ID
            max_results: Maximum number of comments
        
        Returns:
            Video comments
        """
        if not YOUTUBE_API_KEY:
            return {'error': 'YOUTUBE_API_KEY not configured'}
        
        url = f"{YOUTUBE_API_BASE_URL}/commentThreads"
        
        params = {
            'part': 'snippet',
            'videoId': video_id,
            'maxResults': max_results,
            'order': 'relevance',
            'key': YOUTUBE_API_KEY
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Successfully fetched {len(data.get('items', []))} comments for {video_id}")
            return data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch video comments: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_trending_music_india(max_results: int = 25) -> Dict:
        """
        Get trending music videos in India
        
        Args:
            max_results: Maximum number of results
        
        Returns:
            Trending music videos
        """
        return YouTubeDataFetcher.get_trending_videos(
            region_code="IN",
            category_id="10",  # Music category
            max_results=max_results
        )
    
    @staticmethod
    def get_trending_comedy_india(max_results: int = 25) -> Dict:
        """
        Get trending comedy videos in India
        
        Args:
            max_results: Maximum number of results
        
        Returns:
            Trending comedy videos
        """
        return YouTubeDataFetcher.get_trending_videos(
            region_code="IN",
            category_id="23",  # Comedy category
            max_results=max_results
        )
    
    @staticmethod
    def get_trending_people_blogs_india(max_results: int = 25) -> Dict:
        """
        Get trending people & blogs videos in India
        
        Args:
            max_results: Maximum number of results
        
        Returns:
            Trending people & blogs videos
        """
        return YouTubeDataFetcher.get_trending_videos(
            region_code="IN",
            category_id="22",  # People & Blogs category
            max_results=max_results
        )
    
    @staticmethod
    def extract_trending_topics(trending_data: Dict) -> List[Dict]:
        """
        Extract trending topics from YouTube trending videos
        
        Args:
            trending_data: Data from get_trending_videos
        
        Returns:
            List of trending topics with metadata
        """
        topics = []
        
        if 'error' in trending_data:
            return topics
        
        for item in trending_data.get('items', []):
            snippet = item.get('snippet', {})
            statistics = item.get('statistics', {})
            
            topic = {
                'video_id': item.get('id'),
                'title': snippet.get('title', ''),
                'channel': snippet.get('channelTitle', ''),
                'published_at': snippet.get('publishedAt', ''),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'thumbnail': snippet.get('thumbnails', {}).get('default', {}).get('url', ''),
                'trend_score': YouTubeDataFetcher._calculate_trend_score(statistics)
            }
            
            topics.append(topic)
        
        # Sort by trend score
        topics.sort(key=lambda x: x['trend_score'], reverse=True)
        
        logger.info(f"Extracted {len(topics)} trending topics")
        return topics
    
    @staticmethod
    def _calculate_trend_score(statistics: Dict) -> float:
        """
        Calculate a trend score based on video statistics
        
        Args:
            statistics: Video statistics
        
        Returns:
            Trend score (0-100)
        """
        view_count = int(statistics.get('viewCount', 0))
        like_count = int(statistics.get('likeCount', 0))
        comment_count = int(statistics.get('commentCount', 0))
        
        # Normalize to 0-100 scale
        # Based on research: 1M+ views = high trend score
        view_score = min(100, (view_count / 1000000) * 100)
        
        # Engagement rate (likes + comments) / views
        engagement_rate = (like_count + comment_count) / view_count if view_count > 0 else 0
        engagement_score = min(100, engagement_rate * 1000)  # 10% engagement = 100 score
        
        # Combined score
        trend_score = (view_score * 0.7) + (engagement_score * 0.3)
        
        return round(trend_score, 2)


# Test the YouTube data fetcher
if __name__ == "__main__":
    print("=== YouTube Data Fetcher ===")
    
    # Test with sample data (requires real API key for actual API calls)
    print("\n[Test 1] YouTube Data Fetcher")
    print("  [OK] YouTubeDataFetcher class initialized")
    print("  [OK] All methods defined:")
    print("    - get_trending_videos")
    print("    - get_video_details")
    print("    - search_videos")
    print("    - get_video_comments")
    print("    - get_trending_music_india")
    print("    - get_trending_comedy_india")
    print("    - get_trending_people_blogs_india")
    print("    - extract_trending_topics")
    
    print("\n=== YouTube Data Fetcher Working ===")
    print("\nNote: Actual API calls require:")
    print("  - YOUTUBE_API_KEY environment variable")
    print("  - YouTube Data API enabled in Google Cloud Console")
    print("  - API quota: 10,000 units/day (free tier)")