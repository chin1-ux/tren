"""
Plan Enforcement Middleware
Shared dependency for checking user plan access and enforcing feature limits
"""
import os
import logging
from typing import Optional, Dict, List
from fastapi import HTTPException, Header, Depends, status
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class PlanEnforcement:
    """
    Shared plan enforcement logic for all endpoints
    """
    
    # Feature to plan mapping based on plan_features table
    PAID_FEATURES = {
        'early_detection': ['pro', 'business'],
        'unlimited_trends': ['pro', 'business'],
        'ai_generation': ['pro', 'business'],
        'advanced_analytics': ['pro', 'business'],
        'india_features': ['pro', 'business'],
        'video_analysis': ['pro', 'business'],
        'team_features': ['business'],
        'api_access': ['business'],
        'priority_support': ['business']
    }
    
    # Quota-based features
    QUOTA_FEATURES = {
        'api_call': 'api_limit_per_day',
        'trend_view': 'trend_views_per_day'
    }
    
    @staticmethod
    def get_user_plan(user_email: str) -> str:
        """
        Get the user's effective plan, considering plan_overrides first.
        
        Priority: plan_override (if active and not expired) → Razorpay-derived plan → free
        
        Also checks subscription grace period: if subscription was cancelled/failed
        but grace period hasn't ended, user retains paid plan. After grace period,
        automatically downgrades to free.
        
        Args:
            user_email: User's email
        
        Returns:
            Plan name (free, pro, business) or 'free' for guests/errors
        """
        from datetime import datetime, timezone, timedelta
        
        if not user_email or user_email == "guest@trendrop.app":
            return 'free'
        
        try:
            # Get user ID first
            user_res = supabase.table('users').select('id', 'plan', 'subscription_status', 'grace_period_ends_at').eq('email', user_email).single().execute()
            if not user_res.data:
                return 'free'
            
            user_id = user_res.data.get('id')
            razorpay_plan = user_res.data.get('plan', 'free')
            subscription_status = user_res.data.get('subscription_status')
            grace_period_ends_at = user_res.data.get('grace_period_ends_at')
            
            # Check for active plan override
            now = datetime.now(timezone.utc).isoformat()
            
            override_res = supabase.table('plan_overrides') \
                .select('tier', 'expires_at') \
                .eq('user_id', user_id) \
                .execute()
            
            if override_res.data:
                for override in override_res.data:
                    expires_at = override.get('expires_at')
                    # If no expiration or not expired yet, use override
                    if not expires_at or expires_at > now:
                        return override.get('tier', razorpay_plan)
            
            # Check subscription grace period
            if subscription_status in ['subscription.cancelled', 'subscription.halted', 'payment.failed']:
                if grace_period_ends_at:
                    try:
                        # Handle both Z suffix and +00:00 formats, and timezone-naive strings
                        grace_end_str = grace_period_ends_at.replace('Z', '+00:00')
                        grace_end = datetime.fromisoformat(grace_end_str)
                        
                        # If the parsed datetime is naive, assume UTC
                        if grace_end.tzinfo is None:
                            grace_end = grace_end.replace(tzinfo=timezone.utc)
                        
                        current_time = datetime.now(timezone.utc)
                        
                        if current_time < grace_end:
                            # Still within grace period, keep paid plan
                            logger.info(f"User {user_email} within grace period until {grace_end}")
                            return razorpay_plan
                        else:
                            # Grace period ended, downgrade to free
                            logger.info(f"Grace period ended for {user_email}, downgrading to free")
                            try:
                                supabase.table('users').update({'plan': 'free'}).eq('email', user_email).execute()
                            except Exception as update_error:
                                logger.error(f"Failed to downgrade plan for {user_email}: {update_error}")
                            return 'free'
                    except (ValueError, TypeError) as e:
                        logger.error(f"Invalid grace_period_ends_at format for {user_email}: {e}")
                        # On error, keep current plan to avoid breaking legitimate users
                        return razorpay_plan
                else:
                    # No grace period set - default to 30 days from now for safety
                    logger.warning(f"No grace period set for {user_email} with {subscription_status}, setting default 30-day grace")
                    default_grace_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
                    try:
                        supabase.table('users').update({'grace_period_ends_at': default_grace_end}).eq('email', user_email).execute()
                    except Exception as update_error:
                        logger.error(f"Failed to set default grace period for {user_email}: {update_error}")
                    return razorpay_plan
            
            # Fall back to Razorpay plan
            return razorpay_plan
            
        except Exception as e:
            print(f"Error getting user plan: {e}")
            return 'free'
    
    @staticmethod
    def get_plan_features(plan_name: str) -> Dict:
        """
        Get feature configuration for a plan from plan_features table
        
        Args:
            plan_name: Plan name (free, pro, business)
        
        Returns:
            Dict with plan configuration
        """
        try:
            res = supabase.table('plan_features') \
                .select('*') \
                .eq('plan_name', plan_name) \
                .single() \
                .execute()
            
            if res.data:
                return {
                    'api_limit_per_day': res.data.get('api_limit_per_day', 5),
                    'trend_views_per_day': res.data.get('trend_views_per_day', 10),
                    'features': res.data.get('features', [])
                }
            
            # Default fallback if plan not found
            return {
                'api_limit_per_day': 5,
                'trend_views_per_day': 10,
                'features': ['basic_trends']
            }
            
        except Exception as e:
            print(f"Error getting plan features: {e}")
            return {
                'api_limit_per_day': 5,
                'trend_views_per_day': 10,
                'features': ['basic_trends']
            }
    
    @staticmethod
    def check_feature_access(user_email: str, required_feature: str) -> None:
        """
        Check if user has access to a feature, raise 403 if not
        
        Args:
            user_email: User's email
            required_feature: Feature required (e.g., 'early_detection', 'ai_generation')
        
        Raises:
            HTTPException 403 if user doesn't have access
        """
        # Skip check for demo accounts (pro/agency demo accounts)
        if user_email in ['agency-demo@trendrop.app', 'creator-demo@trendrop.app']:
            return
        
        user_plan = PlanEnforcement.get_user_plan(user_email)
        
        # Free tier has limited features
        if user_plan == 'free':
            allowed_features = ['basic_trends', 'algorithm_insights', 'limited_analytics']
            if required_feature not in allowed_features:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "plan_upgrade_required",
                        "feature": required_feature,
                        "message": f"The '{required_feature}' feature requires a Pro or Business plan",
                        "upgrade_url": "/pricing",
                        "current_plan": user_plan
                    }
                )
        
        # Check plan-specific feature access
        if required_feature in PlanEnforcement.PAID_FEATURES:
            allowed_plans = PlanEnforcement.PAID_FEATURES[required_feature]
            if user_plan not in allowed_plans:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "plan_upgrade_required",
                        "feature": required_feature,
                        "message": f"The '{required_feature}' feature requires a {allowed_plans[-1].upper()} plan",
                        "upgrade_url": "/pricing",
                        "current_plan": user_plan
                    }
                )
    
    @staticmethod
    def check_quota_limit(user_email: str, quota_type: str) -> None:
        """
        Check if user has exceeded their quota limit
        
        Args:
            user_email: User's email
            quota_type: Type of quota ('api_call', 'trend_view')
        
        Raises:
            HTTPException 429 if quota exceeded
        """
        # Skip quota check for demo accounts
        if user_email in ['agency-demo@trendrop.app', 'creator-demo@trendrop.app']:
            return
        
        from datetime import datetime, timezone, timedelta
        
        user_plan = PlanEnforcement.get_user_plan(user_email)
        plan_config = PlanEnforcement.get_plan_features(user_plan)
        
        # Get the limit for this quota type
        if quota_type == 'api_call':
            limit = plan_config['api_limit_per_day']
        elif quota_type == 'trend_view':
            limit = plan_config['trend_views_per_day']
        else:
            return  # Unknown quota type, skip check
        
        # -1 means unlimited
        if limit == -1:
            return
        
        # Check today's usage
        from datetime import datetime, timezone, timedelta
        time_threshold = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        
        try:
            res = supabase.table('usage_logs') \
                .select('*') \
                .eq('user_email', user_email) \
                .gte('timestamp', time_threshold) \
                .execute()
            
            usage_logs = res.data or []
            
            # Count quota usage
            quota_count = sum(1 for log in usage_logs if log['feature_used'] == quota_type)
            
            if quota_count >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "quota_exceeded",
                        "quota_type": quota_type,
                        "limit": limit,
                        "current_usage": quota_count,
                        "message": f"Daily {quota_type} limit reached: {limit} per day",
                        "reset_time": "24 hours"
                    }
                )
                
        except Exception as e:
            print(f"Error checking quota: {e}")
            # Allow on error to avoid blocking legitimate users
    
    @staticmethod
    def log_usage(user_email: str, feature: str, metadata: Optional[Dict] = None):
        """
        Log feature usage for analytics and quota tracking
        
        Args:
            user_email: User's email
            feature: Feature being used
            metadata: Additional metadata about the usage
        """
        from datetime import datetime, timezone
        
        try:
            plan = PlanEnforcement.get_user_plan(user_email)
            
            supabase.table('usage_logs') \
                .insert({
                    'user_email': user_email,
                    'feature_used': feature,
                    'plan_at_time': plan,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'metadata': metadata or {}
                }) \
                .execute()
            
            # Update user's usage count
            user_res = supabase.table('users') \
                .select('usage_count') \
                .eq('email', user_email) \
                .single() \
                .execute()
            
            current_count = user_res.data.get('usage_count', 0) if user_res.data else 0
            
            supabase.table('users') \
                .update({
                    'usage_count': current_count + 1,
                    'last_active': datetime.now(timezone.utc).isoformat()
                }) \
                .eq('email', user_email) \
                .execute()
            
        except Exception as e:
            print(f"Error logging usage: {e}")


def require_feature(feature: str):
    """
    FastAPI dependency factory for checking feature access
    
    Args:
        feature: Feature required for this endpoint
        
    Returns:
        Dependency function that can be used in FastAPI endpoints
    """
    def check_feature_dependency(current_user: str = Depends(lambda: "guest@trendrop.app")):
        PlanEnforcement.check_feature_access(current_user, feature)
        return current_user
    
    return check_feature_dependency


def require_quota(quota_type: str):
    """
    FastAPI dependency factory for checking quota limits
    
    Args:
        quota_type: Type of quota to check ('api_call', 'trend_view')
        
    Returns:
        Dependency function that can be used in FastAPI endpoints
    """
    def check_quota_dependency(current_user: str = Depends(lambda: "guest@trendrop.app")):
        PlanEnforcement.check_quota_limit(current_user, quota_type)
        return current_user
    
    return check_quota_dependency


def log_endpoint_usage(feature: str):
    """
    FastAPI dependency factory for logging endpoint usage
    
    Args:
        feature: Feature to log usage for
        
    Returns:
        Dependency function that logs usage after endpoint completes
    """
    def log_usage_dependency(current_user: str = Depends(lambda: "guest@trendrop.app")):
        PlanEnforcement.log_usage(current_user, feature)
        return current_user
    
    return log_usage_dependency
