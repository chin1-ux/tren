"""
Redis-backed Rate Limiter
Replaces in-memory slowapi with distributed rate limiting using Upstash Redis
"""
import os
import time
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

try:
    import redis
except ImportError:
    redis = None

load_dotenv()

UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL")

class RedisRateLimiter:
    """
    Distributed rate limiter using Redis
    """
    
    def __init__(self):
        self.redis_client = None
        if redis and UPSTASH_REDIS_URL:
            try:
                self.redis_client = redis.from_url(
                    UPSTASH_REDIS_URL,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                logger.info("redis_connected")
            except Exception as e:
                logger.warning("redis_connect_failed", extra={"error": str(e)})
                self.redis_client = None
        else:
            logger.warning("redis_not_configured")
    
    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limit
        
        Args:
            key: Unique identifier for rate limit (e.g., "user@example.com:api_call")
            limit: Maximum requests allowed in window
            window_seconds: Time window in seconds
        
        Returns:
            (allowed, info) where info contains:
                - remaining: Remaining requests in window
                - reset_at: Unix timestamp when window resets
                - current: Current request count
        """
        if not self.redis_client:
            # Fallback: allow all requests if Redis unavailable
            return True, {"remaining": limit, "reset_at": int(time.time()) + window_seconds, "current": 0}
        
        try:
            current_time = int(time.time())
            window_start = current_time - window_seconds
            
            # Use Redis sorted set for sliding window
            # Key format: rate_limit:{key}
            redis_key = f"rate_limit:{key}"
            
            # Remove entries outside current window
            self.redis_client.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current requests in window
            current_count = self.redis_client.zcard(redis_key)
            
            # Check if under limit
            if current_count < limit:
                # Add current request
                self.redis_client.zadd(redis_key, {str(current_time): current_time})
                # Set expiry on key
                self.redis_client.expire(redis_key, window_seconds + 1)
                
                remaining = limit - current_count - 1
                return True, {
                    "remaining": remaining,
                    "reset_at": current_time + window_seconds,
                    "current": current_count + 1
                }
            else:
                # Rate limit exceeded
                remaining = 0
                # Get oldest request to calculate reset time
                oldest = self.redis_client.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    reset_at = int(oldest[0][1]) + window_seconds
                else:
                    reset_at = current_time + window_seconds
                
                return False, {
                    "remaining": remaining,
                    "reset_at": reset_at,
                    "current": current_count
                }
        except Exception as e:
            if not hasattr(self, '_redis_error_logged'):
                logger.error("redis_rate_limit_error", extra={"key": key, "error": str(e)})
                self._redis_error_logged = True
            else:
                logger.debug("redis_rate_limit_error_suppressed", extra={"key": key, "error": str(e)})
            # Fallback: allow on error to avoid blocking legitimate users
            return True, {"remaining": limit, "reset_at": int(time.time()) + window_seconds, "current": 0}
    
    def reset(self, key: str):
        """
        Reset rate limit for a specific key
        
        Args:
            key: Unique identifier for rate limit
        """
        if not self.redis_client:
            return
        
        try:
            redis_key = f"rate_limit:{key}"
            self.redis_client.delete(redis_key)
        except Exception as e:
            logger.warning("redis_reset_failed", extra={"key": key, "error": str(e)})


# Global rate limiter instance
_global_limiter = None

def get_rate_limiter() -> RedisRateLimiter:
    """Get or create global rate limiter instance"""
    global _global_limiter
    if _global_limiter is None:
        _global_limiter = RedisRateLimiter()
    return _global_limiter


def check_rate_limit(identifier: str, limit: int, window_seconds: int = 60) -> tuple[bool, dict]:
    """
    Convenience function to check rate limit
    
    Args:
        identifier: Unique identifier (email, IP, etc.)
        limit: Maximum requests allowed
        window_seconds: Time window in seconds
    
    Returns:
        (allowed, info) tuple
    """
    limiter = get_rate_limiter()
    return limiter.is_allowed(identifier, limit, window_seconds)


if __name__ == "__main__":
    # Test the rate limiter
    print("=== Testing Redis Rate Limiter ===")
    
    limiter = get_rate_limiter()
    
    # Test 1: Check if allowed
    print("\nTest 1: Check if allowed")
    allowed, info = limiter.is_allowed("test@example.com", 5, 60)
    print(f"  Allowed: {allowed}")
    print(f"  Info: {info}")
    
    # Test 2: Hit limit
    print("\nTest 2: Hit limit")
    for i in range(6):
        allowed, info = limiter.is_allowed("test@example.com", 5, 60)
        print(f"  Request {i+1}: Allowed={allowed}, Remaining={info['remaining']}")
    
    # Test 3: Reset
    print("\nTest 3: Reset")
    limiter.reset("test@example.com")
    allowed, info = limiter.is_allowed("test@example.com", 5, 60)
    print(f"  After reset: Allowed={allowed}, Remaining={info['remaining']}")
    
    print("\n=== Redis Rate Limiter Test Complete ===")