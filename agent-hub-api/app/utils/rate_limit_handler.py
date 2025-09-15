"""
🚀 Rate Limit Handler for Azure OpenAI
Implements intelligent retry logic to handle burst usage patterns.
"""
import asyncio
import logging
from typing import Any, Callable, Optional
import time
from functools import wraps

logger = logging.getLogger(__name__)

class RateLimitHandler:
    """Handles Azure OpenAI rate limiting with smart retry logic"""
    
    def __init__(self):
        self.last_request_time = 0
        self.request_count = 0
        self.window_start = time.time()
        
    async def handle_rate_limited_call(
        self, 
        func: Callable, 
        *args, 
        max_retries: int = 3,
        base_delay: float = 1.0,
        **kwargs
    ) -> Any:
        """
        Handle API calls with intelligent rate limiting and retry logic
        
        Args:
            func: Function to call
            max_retries: Maximum number of retries
            base_delay: Base delay in seconds (will use exponential backoff)
        """
        
        for attempt in range(max_retries + 1):
            try:
                # Add slight delay between requests to avoid burst limits
                current_time = time.time()
                time_since_last = current_time - self.last_request_time
                
                if time_since_last < 0.5:  # Minimum 500ms between requests
                    await asyncio.sleep(0.5 - time_since_last)
                
                self.last_request_time = time.time()
                
                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Reset retry count on success
                return result
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Check if it's a rate limit error
                if "rate limit" in error_str or "429" in error_str:
                    if attempt < max_retries:
                        # Extract wait time from error message if available
                        wait_time = self._extract_wait_time(str(e))
                        if wait_time is None:
                            # Use exponential backoff: 1s, 2s, 4s, 8s...
                            wait_time = base_delay * (2 ** attempt)
                        
                        logger.warning(f"⏳ Rate limited (attempt {attempt + 1}/{max_retries + 1}). Waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ Max retries ({max_retries}) exceeded for rate limiting")
                        raise
                else:
                    # Non-rate-limit error, re-raise immediately
                    raise
        
        # Should never reach here
        raise Exception("Unexpected error in rate limit handler")
    
    def _extract_wait_time(self, error_message: str) -> Optional[float]:
        """Extract wait time from Azure OpenAI error message"""
        try:
            # Look for "retry after X seconds" pattern
            import re
            match = re.search(r'retry after (\d+) seconds', error_message)
            if match:
                return float(match.group(1))
        except:
            pass
        return None

# Global instance
rate_limit_handler = RateLimitHandler()

def rate_limited(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for rate-limited functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await rate_limit_handler.handle_rate_limited_call(
                func, *args, max_retries=max_retries, base_delay=base_delay, **kwargs
            )
        return wrapper
    return decorator
