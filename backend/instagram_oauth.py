import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

try:
    logging.basicConfig(
        filename="instagram_oauth.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass
logger = logging.getLogger(__name__)

# Instagram Graph API Configuration
INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID")
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET")
INSTAGRAM_REDIRECT_URI = os.getenv("INSTAGRAM_REDIRECT_URI", "https://your-domain.com/auth/instagram/callback")
INSTAGRAM_API_VERSION = "v18.0"

# Supabase client
supabase: Optional[Client] = None
try:
    _url = os.getenv("SUPABASE_URL")
    _key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
    if _url and _key:
        supabase = create_client(_url, _key)
    else:
        logger.warning("Supabase URL or Key missing for InstagramOAuth")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client in instagram_oauth: {e}")


class InstagramOAuth:
    """Handle Instagram Graph API OAuth flow and token management."""
    
    @staticmethod
    def get_auth_url(state: str = None) -> str:
        """
        Generate Instagram OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL for Instagram OAuth
        """
        if not INSTAGRAM_APP_ID:
            raise ValueError("INSTAGRAM_APP_ID not configured")
        
        scopes = [
            "instagram_basic",
            "instagram_manage_insights",
            "pages_read_engagement"
        ]
        
        params = {
            "client_id": INSTAGRAM_APP_ID,
            "redirect_uri": INSTAGRAM_REDIRECT_URI,
            "scope": ",".join(scopes),
            "response_type": "code",
            "state": state or "default_state"
        }
        
        auth_url = f"https://www.facebook.com/{INSTAGRAM_API_VERSION}/dialog/oauth?{requests.compat.urlencode(params)}"
        logger.info(f"Generated Instagram auth URL for state: {state}")
        return auth_url
    
    @staticmethod
    def exchange_code_for_token(code: str) -> Dict:
        """
        Exchange authorization code for short-lived access token.
        
        Args:
            code: Authorization code from Instagram OAuth callback
            
        Returns:
            Dictionary containing access token and user info
        """
        if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET:
            raise ValueError("Instagram app credentials not configured")
        
        token_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/oauth/access_token"
        
        params = {
            "client_id": INSTAGRAM_APP_ID,
            "client_secret": INSTAGRAM_APP_SECRET,
            "redirect_uri": INSTAGRAM_REDIRECT_URI,
            "code": code
        }
        
        try:
            response = requests.get(token_url, params=params)
            response.raise_for_status()
            token_data = response.json()
            
            logger.info(f"Successfully exchanged code for token")
            return token_data
        except requests.RequestException as e:
            logger.error(f"Failed to exchange code for token: {e}")
            raise
    
    @staticmethod
    def get_long_lived_token(short_lived_token: str) -> Dict:
        """
        Exchange short-lived token for long-lived token (60 days).
        
        Args:
            short_lived_token: Short-lived access token
            
        Returns:
            Dictionary containing long-lived token and expiration
        """
        if not INSTAGRAM_APP_ID or not INSTAGRAM_APP_SECRET:
            raise ValueError("Instagram app credentials not configured")
        
        token_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/oauth/access_token"
        
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": INSTAGRAM_APP_ID,
            "client_secret": INSTAGRAM_APP_SECRET,
            "fb_exchange_token": short_lived_token
        }
        
        try:
            response = requests.get(token_url, params=params)
            response.raise_for_status()
            token_data = response.json()
            
            logger.info("Successfully obtained long-lived token")
            return token_data
        except requests.RequestException as e:
            logger.error(f"Failed to get long-lived token: {e}")
            if response is not None:
                logger.error(f"Response: {response.text}")
            raise
    
    @staticmethod
    def refresh_long_lived_token(access_token: str) -> Dict:
        """
        Refresh a long-lived token before it expires.
        
        Args:
            access_token: Current long-lived access token
            
        Returns:
            Dictionary containing refreshed token and new expiration
        """
        token_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/oauth/access_token"
        
        params = {
            "grant_type": "ig_refresh_token",
            "access_token": access_token
        }
        
        try:
            response = requests.get(token_url, params=params)
            response.raise_for_status()
            token_data = response.json()
            
            logger.info("Successfully refreshed long-lived token")
            return token_data
        except requests.RequestException as e:
            logger.error(f"Failed to refresh token: {e}")
            raise
    
    # Known Page ID for Business Manager-owned pages that don't appear in /me/accounts
    KNOWN_PAGE_IDS = ["1238153086047102"]

    @staticmethod
    def get_instagram_business_account(access_token: str) -> Optional[Dict]:
        """
        Get Instagram Business Account ID from the user's Facebook page.
        
        For Business Manager-owned pages, /me/accounts returns empty.
        Falls back to querying known Page IDs directly.
        
        Args:
            access_token: Valid access token
            
        Returns:
            Dictionary containing Instagram Business Account info
        """
        page_id = None

        # First try /me/accounts (works for personal pages)
        try:
            pages_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/me/accounts"
            response = requests.get(pages_url, params={"access_token": access_token})
            response.raise_for_status()
            pages_data = response.json()

            if pages_data.get("data"):
                page_id = pages_data["data"][0]["id"]
                logger.info(f"Found page via /me/accounts: {page_id}")
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch /me/accounts: {e}")

        # Fallback: query known Page IDs directly (for Business Manager-owned pages)
        if not page_id:
            logger.warning("/me/accounts returned no pages. Trying known Page IDs directly.")
            for known_id in InstagramOAuth.KNOWN_PAGE_IDS:
                try:
                    res = requests.get(
                        f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{known_id}",
                        params={"access_token": access_token, "fields": "id,name,instagram_business_account"}
                    )
                    res.raise_for_status()
                    data = res.json()
                    if "instagram_business_account" in data:
                        page_id = known_id
                        logger.info(f"Found page via direct query: {known_id}")
                        break
                except requests.RequestException:
                    continue

        if not page_id:
            logger.warning("No Facebook page found via any method")
            return None

        try:
            # Get Instagram Business Account linked to the page
            ig_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{page_id}"
            response = requests.get(ig_url, params={"access_token": access_token, "fields": "instagram_business_account"})
            response.raise_for_status()
            ig_data = response.json()

            if "instagram_business_account" not in ig_data:
                logger.warning("No Instagram Business Account found for page")
                return None

            ig_id = ig_data["instagram_business_account"]["id"]
            details_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{ig_id}"
            response = requests.get(details_url, params={
                "access_token": access_token,
                "fields": "id,username,profile_picture_url,followers_count,media_count"
            })
            response.raise_for_status()

            logger.info(f"Successfully retrieved Instagram Business Account: {ig_id}")
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Failed to get Instagram Business Account: {e}")
            raise
    
    @staticmethod
    def store_token(user_email: str, token_data: Dict, ig_account_id: str) -> bool:
        """
        Store Instagram token in Supabase.
        
        Args:
            user_email: User's email for identification
            token_data: Token data from Instagram
            ig_account_id: Instagram Business Account ID
            
        Returns:
            True if successful, False otherwise
        """
        if not supabase:
            logger.error("Supabase client not initialized")
            return False
        
        try:
            # Check if user already has a token
            existing = supabase.table("instagram_tokens").select("*").eq("user_email", user_email).execute()

            from datetime import timezone
            now = datetime.now(timezone.utc)
            token_record = {
                "user_email": user_email,
                "access_token": token_data.get("access_token"),
                "token_type": token_data.get("token_type", "long-lived"),
                "expires_at": (now + timedelta(days=60)).isoformat(),  # Must be ISO string for Supabase
                "ig_account_id": ig_account_id,
                "updated_at": now.isoformat()
            }
            
            if existing.data:
                # Update existing token
                supabase.table("instagram_tokens").update(token_record).eq("user_email", user_email).execute()
                logger.info(f"Updated Instagram token for user: {user_email}")
            else:
                # Insert new token
                supabase.table("instagram_tokens").insert(token_record).execute()
                logger.info(f"Stored new Instagram token for user: {user_email}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to store token in Supabase: {e}")
            return False
    
    @staticmethod
    def get_user_token(user_email: str) -> Optional[Dict]:
        """
        Retrieve Instagram token for a user from Supabase.
        
        Args:
            user_email: User's email
            
        Returns:
            Token record if found and valid, None otherwise
        """
        if not supabase:
            logger.error("Supabase client not initialized")
            return None
        
        try:
            result = supabase.table("instagram_tokens").select("*").eq("user_email", user_email).execute()
            
            if not result.data:
                logger.warning(f"No token found for user: {user_email}")
                return None
            
            token = result.data[0]
            
            # Check if token is expired
            expires_at = datetime.fromisoformat(token["expires_at"])
            if datetime.now() > expires_at:
                logger.warning(f"Token expired for user: {user_email}")
                return None
            
            logger.info(f"Retrieved valid token for user: {user_email}")
            return token
        except Exception as e:
            logger.error(f"Failed to retrieve token from Supabase: {e}")
            return None
    
    @staticmethod
    def get_insights(access_token: str, ig_account_id: str, metrics: list, period: str = "day", days: int = 30) -> Optional[Dict]:
        """
        Fetch Instagram Insights data.
        
        Args:
            access_token: Valid access token
            ig_account_id: Instagram Business Account ID
            metrics: List of metrics to fetch (e.g., ["impressions", "reach", "engagement"])
            period: Period for insights (day, week, days_28)
            days: Number of days of data to fetch
            
        Returns:
            Dictionary containing insights data
        """
        insights_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{ig_account_id}/insights"
        
        params = {
            "metric": ",".join(metrics),
            "period": period,
            "access_token": access_token
        }
        
        try:
            response = requests.get(insights_url, params=params)
            response.raise_for_status()
            insights_data = response.json()
            
            logger.info(f"Successfully fetched insights for account: {ig_account_id}")
            return insights_data
        except requests.RequestException as e:
            logger.error(f"Failed to fetch insights: {e}")
            raise

    @staticmethod
    def fetch_media_insights(access_token: str, media_id: str, media_type: str) -> Dict:
        """Fetch insights for a specific media post (Reel/Video)."""
        metrics = ["reach", "plays", "likes", "comments", "shares", "saves"]
        insights_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{media_id}/insights"
        params = {
            "metric": ",".join(metrics),
            "access_token": access_token
        }
        try:
            res = requests.get(insights_url, params=params)
            res.raise_for_status()
            data = res.json()
            insights = {}
            for item in data.get("data", []):
                name = item.get("name")
                values = item.get("values", [])
                if values:
                    insights[name] = values[0].get("value", 0)
            return insights
        except Exception as e:
            logger.warning(f"Error fetching insights for media {media_id}: {e}")
            return {}

    @staticmethod
    def sync_creator_posts(access_token: str, ig_account_id: str, user_email: str) -> bool:
        """Syncs the last 30 posts of the creator to our creator_posts database."""
        if not supabase:
            logger.error("Supabase not initialized")
            return False
            
        media_url = f"https://graph.facebook.com/{INSTAGRAM_API_VERSION}/{ig_account_id}/media"
        params = {
            "fields": "id,caption,permalink,media_type,media_url,timestamp,username",
            "access_token": access_token,
            "limit": 30
        }
        
        try:
            res = requests.get(media_url, params=params)
            res.raise_for_status()
            media_data = res.json().get("data", [])
            
            for post in media_data:
                media_id = post.get("id")
                media_type = post.get("media_type")
                
                # Fetch insights for this specific media post
                insights = InstagramOAuth.fetch_media_insights(access_token, media_id, media_type)
                
                record = {
                    "user_email": user_email,
                    "instagram_username": post.get("username", "unknown"),
                    "media_id": media_id,
                    "caption": post.get("caption"),
                    "permalink": post.get("permalink"),
                    "media_type": media_type,
                    "media_url": post.get("media_url"),
                    "timestamp": post.get("timestamp"),
                    "like_count": insights.get("likes", 0),
                    "comments_count": insights.get("comments", 0),
                    "shares_count": insights.get("shares", 0),
                    "saves_count": insights.get("saves", 0),
                    "plays_count": insights.get("plays", 0),
                    "reach_count": insights.get("reach", 0),
                }
                
                # Upsert into creator_posts
                supabase.table("creator_posts").upsert(record, on_conflict="media_id").execute()
                
            logger.info(f"Successfully synced posts for creator {user_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to sync posts for creator {user_email}: {e}")
            return False

