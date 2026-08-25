"""
Plan Enforcement Middleware

Subscription-based pricing with 4 creator tiers + 3 brand tiers:
  Creator:  free | early_bird (₹999) | pro (₹2,999)
  Brand:    brand_starter (₹4,999) | brand_growth (₹14,999) | brand_enterprise (₹49,999)

Marketplace commission: 10% on brand-creator deals (separate from subscriptions).
Credits are deprecated — subscriptions + hard rate limits are the model.
"""
import os
import logging
from typing import Optional, Dict
from fastapi import HTTPException, Header, Depends, status, BackgroundTasks
from dotenv import load_dotenv

_PLAN_CACHE = {}
_PLAN_CACHE_TTL = 300

def invalidate_plan_cache(email: str):
    if email in _PLAN_CACHE:
        del _PLAN_CACHE[email]

from supabase import create_client, Client

try:
    from auth import get_current_user
except ImportError:
    def get_current_user():
        return "guest@trendrop.app"

logger = logging.getLogger(__name__)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Tier definitions (creator plans) ───────────────────────────────────────────
# These are the valid plan values stored in users.plan column.
# Current DB supports 'free' | 'pro'. Early bird and brand tiers
# will be added when the DB schema is migrated to 4-tier subscriptions.
CREATOR_TIERS = ('free', 'early_bird', 'pro')
BRAND_TIERS = ('brand_starter', 'brand_growth', 'brand_enterprise')
ALL_TIERS = CREATOR_TIERS + BRAND_TIERS

# ── Daily rate limits per tier (trends per day) ────────────────────────────────
TIER_DAILY_LIMITS = {
    'free': 5,
    'early_bird': 50,
    'pro': 999999,  # unlimited
    'brand_starter': 100,
    'brand_growth': 500,
    'brand_enterprise': 999999,
}

# ── Credit costs per operation (legacy — kept for backward compatibility) ──────
CREDIT_COSTS = {
    'ai_generation': 5,
    'video_analysis': 10,
    'export': 2,
}
# Trend browsing and search cost 0 credits — they are the core product.

FREE_TIER_FEATURES = ['basic_trends', 'algorithm_insights', 'limited_analytics']


class PlanEnforcement:
    """
    Subscription-based plan enforcement.

    Creator plans: free | early_bird | pro
    Brand plans: brand_starter | brand_growth | brand_enterprise

    The DB currently stores 'free' or 'pro' in users.plan.
    Early bird and brand tiers are defined here for when the DB migrates.
    """

    PAID_FEATURES = {
        'early_detection': ['early_bird', 'pro'],
        'unlimited_trends': ['pro'],
        'ai_generation': ['early_bird', 'pro'],
        'advanced_analytics': ['early_bird', 'pro'],
        'india_features': ['early_bird', 'pro'],
        'video_analysis': ['pro'],
        'team_features': ['pro'],
        'api_access': ['pro'],
        'priority_support': ['pro'],
        'marketplace_access': ['free', 'early_bird', 'pro'],  # free for all creators
        'brand_matching': ['early_bird', 'pro'],
        'campaign_analytics': ['pro'],
    }

    BRAND_DEALS_CONFIG = {
        'free': {'delay_hours': 48, 'max_deals': 5},
        'early_bird': {'delay_hours': 24, 'max_deals': 20},
        'pro':  {'delay_hours': 0,  'max_deals': None},
        'brand_starter': {'delay_hours': 0, 'max_deals': 10},
        'brand_growth': {'delay_hours': 0, 'max_deals': 50},
        'brand_enterprise': {'delay_hours': 0, 'max_deals': None},
    }

    # ── Plan resolution ────────────────────────────────────────────────────────

    @staticmethod
    def get_user_plan(user_email: str) -> str:
        if not user_email or user_email == "guest@trendrop.app":
            return 'free'
        import time
        now_ts = time.time()
        if user_email in _PLAN_CACHE:
            entry = _PLAN_CACHE[user_email]
            if now_ts - entry['time'] < _PLAN_CACHE_TTL:
                return entry['plan']
        plan = PlanEnforcement._get_user_plan_db(user_email)
        _PLAN_CACHE[user_email] = {'time': now_ts, 'plan': plan}
        return plan

    @staticmethod
    def _get_user_plan_db(user_email: str) -> str:
        from datetime import datetime, timezone
        try:
            user_res = supabase.table('users') \
                .select('id', 'plan', 'subscription_status', 'grace_period_ends_at') \
                .eq('email', user_email).single().execute()
            if not user_res.data:
                return 'free'

            plan = user_res.data.get('plan', 'free')
            if plan not in ALL_TIERS:
                plan = 'free'
            subscription_status = user_res.data.get('subscription_status')
            grace_period_ends_at = user_res.data.get('grace_period_ends_at')

            override_res = supabase.table('plan_overrides') \
                .select('tier', 'expires_at') \
                .eq('user_id', user_res.data.get('id')).execute()
            if override_res.data:
                now = datetime.now(timezone.utc).isoformat()
                for override in override_res.data:
                    expires_at = override.get('expires_at')
                    if not expires_at or expires_at > now:
                        t = override.get('tier', plan)
                        return t if t in ALL_TIERS else 'free'

            if subscription_status in ['cancelled', 'halted', 'past_due']:
                if grace_period_ends_at:
                    try:
                        grace_end_str = grace_period_ends_at.replace('Z', '+00:00')
                        grace_end = datetime.fromisoformat(grace_end_str)
                        if grace_end.tzinfo is None:
                            grace_end = grace_end.replace(tzinfo=timezone.utc)
                        if datetime.now(timezone.utc) < grace_end:
                            return plan
                        else:
                            supabase.table('users').update({'plan': 'free'}).eq('email', user_email).execute()
                            return 'free'
                    except (ValueError, TypeError):
                        return plan
                else:
                    supabase.table('users').update({'plan': 'free'}).eq('email', user_email).execute()
                    return 'free'

            return plan
        except Exception as e:
            logger.error(f"Error getting user plan: {e}")
            return 'free'

    # ── Feature access ─────────────────────────────────────────────────────────

    @staticmethod
    def check_feature_access(user_email: str, required_feature: str) -> None:
        if PlanEnforcement.is_demo_allowlisted(user_email):
            return
        user_plan = PlanEnforcement.get_user_plan(user_email)
        if user_plan == 'free':
            if required_feature not in FREE_TIER_FEATURES:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "plan_upgrade_required",
                        "feature": required_feature,
                        "message": f"The '{required_feature}' feature requires a Pro plan",
                        "upgrade_url": "/pricing",
                        "current_plan": user_plan,
                    },
                )
        elif required_feature in PlanEnforcement.PAID_FEATURES:
            if user_plan not in PlanEnforcement.PAID_FEATURES[required_feature]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error": "plan_upgrade_required",
                        "feature": required_feature,
                        "message": f"The '{required_feature}' feature requires a Pro plan",
                        "upgrade_url": "/pricing",
                        "current_plan": user_plan,
                    },
                )

    # ── Credit deduction ───────────────────────────────────────────────────────

    @staticmethod
    def deduct_credits(user_email: str, cost: int, reason: str, endpoint: Optional[str] = None) -> int:
        """
        Atomically deduct credits. Returns remaining balance.
        Uses UPDATE ... WHERE credits_remaining >= cost as the guard.
        Raises 429 if insufficient credits.

        NOTE: supabase-py does not support UPDATE RETURNING, so we do a
        two-step read+write. For full atomicity under high concurrency,
        call the raw SQL CTE via psql/RPC. At Trendrop's current scale
        (pre-launch, single-region), the sub-ms race window is acceptable.
        """
        if cost <= 0:
            return 0

        if PlanEnforcement.is_demo_allowlisted(user_email):
            return 999_999

        user_res = supabase.table('users') \
            .select('id, credits_remaining') \
            .eq('email', user_email).single().execute()
        if not user_res.data:
            raise HTTPException(status_code=429, detail={
                "error": "credits_exhausted",
                "credits_remaining": 0,
                "cost": cost,
                "upgrade_url": "/pricing",
            })

        user_id = user_res.data['id']
        old_balance = user_res.data.get('credits_remaining', 0) or 0

        if old_balance < cost:
            raise HTTPException(status_code=429, detail={
                "error": "credits_exhausted",
                "credits_remaining": old_balance,
                "cost": cost,
                "message": f"Insufficient credits: need {cost}, have {old_balance}",
                "upgrade_url": "/pricing",
            })

        new_balance = old_balance - cost
        supabase.table('users').update({
            'credits_remaining': new_balance,
            'credits_used_this_month': cost,
        }).eq('id', user_id).execute()

        supabase.table('credit_transactions').insert({
            'user_id': user_id,
            'amount': -cost,
            'reason': reason,
            'endpoint': endpoint,
            'balance_after': new_balance,
        }).execute()

        return new_balance

    @staticmethod
    def check_credit_balance(user_email: str, cost: int) -> int:
        """Read-only check. Returns current balance without deducting."""
        if cost <= 0:
            return 999_999
        if PlanEnforcement.is_demo_allowlisted(user_email):
            return 999_999
        user_res = supabase.table('users') \
            .select('credits_remaining') \
            .eq('email', user_email).single().execute()
        if not user_res.data:
            return 0
        return user_res.data.get('credits_remaining', 0) or 0

    # ── Usage logging ──────────────────────────────────────────────────────────

    @staticmethod
    def log_usage(user_email: str, feature: str, metadata: Optional[Dict] = None):
        from datetime import datetime, timezone
        try:
            plan = PlanEnforcement.get_user_plan(user_email)
            supabase.table('usage_logs').insert({
                'user_email': user_email,
                'feature_used': feature,
                'plan_at_time': plan,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata or {},
            }).execute()
            user_res = supabase.table('users') \
                .select('usage_count') \
                .eq('email', user_email).single().execute()
            current_count = user_res.data.get('usage_count', 0) if user_res.data else 0
            supabase.table('users').update({
                'usage_count': current_count + 1,
                'last_active': datetime.now(timezone.utc).isoformat(),
            }).eq('email', user_email).execute()
        except Exception as e:
            logger.error(f"Error logging usage: {e}")

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def is_phone_verified(user_email: str) -> bool:
        try:
            res = supabase.table("users").select("phone_verified").eq("email", user_email).limit(1).execute()
            if res.data:
                return res.data[0].get("phone_verified", False)
            return False
        except Exception as e:
            logger.error(f"Error checking phone verification: {e}")
            return False

    @staticmethod
    def is_demo_allowlisted(user_email: str) -> bool:
        demo_allowlist = os.getenv("DEMO_ALLOWLIST", "")
        if not demo_allowlist:
            return False
        allowed = [e.strip().lower() for e in demo_allowlist.split(",")]
        return user_email.lower() in allowed


# ── Dependency factories ──────────────────────────────────────────────────────

def require_phone_verified(current_user: str = Depends(get_current_user)) -> str:
    if current_user == "guest@trendrop.app":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if not PlanEnforcement.is_phone_verified(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Phone verification required.")
    return current_user


def require_feature(feature: str):
    def check(current_user: str = Depends(get_current_user)):
        if current_user == "guest@trendrop.app":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        PlanEnforcement.check_feature_access(current_user, feature)
        return current_user
    return check


def require_credits(cost: int):
    """Dependency factory: checks credit balance now, schedules deduction
    to run ONLY after the endpoint completes successfully.

    Why: FastAPI solves sub-dependencies before validating route params,
    so an inline deduction fires even when the request later 422s —
    charging users for malformed requests (P-PAY-9). BackgroundTasks are
    attached to the response object and discarded whenever validation
    fails (422) or the handler raises, so failed requests cost nothing.
    """
    def check(
        background_tasks: BackgroundTasks,
        current_user: str = Depends(get_current_user),
    ):
        if current_user == "guest@trendrop.app":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        balance = PlanEnforcement.check_credit_balance(current_user, cost)
        if balance < cost:
            raise HTTPException(status_code=429, detail={
                "error": "credits_exhausted",
                "credits_remaining": balance,
                "cost": cost,
                "message": f"Insufficient credits: need {cost}, have {balance}",
                "upgrade_url": "/pricing",
            })
        background_tasks.add_task(
            PlanEnforcement.deduct_credits,
            current_user, cost, reason='api_usage', endpoint=None,
        )
        return current_user
    return check


def log_endpoint_usage(feature: str):
    def log(current_user: str = Depends(get_current_user)):
        if current_user == "guest@trendrop.app":
            return current_user
        PlanEnforcement.log_usage(current_user, feature)
        return current_user
    return log
