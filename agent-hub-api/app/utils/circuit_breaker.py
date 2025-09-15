"""
Circuit Breaker pattern implementation for agent execution resilience.
"""
import asyncio
import time
from enum import Enum
from typing import Dict, Callable, Any, Optional
from dataclasses import dataclass, field
from app.utils.logging import setup_logging

logger = setup_logging(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit breaker is open, rejecting calls
    HALF_OPEN = "half_open"  # Testing if the service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: float = 30.0      # Seconds before trying half-open
    success_threshold: int = 2          # Successes needed to close from half-open
    timeout: float = 60.0               # Maximum execution timeout
    

@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    state: CircuitState = CircuitState.CLOSED
    consecutive_successes: int = 0


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.stats.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"🔄 Circuit breaker '{self.name}' attempting half-open")
                    self.stats.state = CircuitState.HALF_OPEN
                else:
                    logger.warning(f"⚡ Circuit breaker '{self.name}' is OPEN - rejecting call")
                    raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs), 
                timeout=self.config.timeout
            )
            
            await self._record_success()
            return result
            
        except asyncio.TimeoutError:
            await self._record_failure()
            logger.error(f"⏰ Circuit breaker '{self.name}' - execution timeout")
            raise CircuitBreakerTimeoutError(f"Execution timeout in '{self.name}'")
            
        except Exception as e:
            # Check for rate limiting errors (don't count as failures)
            error_msg = str(e).lower()
            if "429" in error_msg or "rate limit" in error_msg or "quota" in error_msg:
                logger.warning(f"⚠️ Circuit breaker '{self.name}' - rate limited (not counted as failure): {e}")
                raise RateLimitError(f"Rate limited in '{self.name}': {e}")
            else:
                await self._record_failure()
                logger.error(f"❌ Circuit breaker '{self.name}' - execution failed: {e}")
                raise
    
    async def _record_success(self):
        """Record a successful execution."""
        async with self._lock:
            self.stats.success_count += 1
            
            if self.stats.state == CircuitState.HALF_OPEN:
                self.stats.consecutive_successes += 1
                if self.stats.consecutive_successes >= self.config.success_threshold:
                    logger.info(f"✅ Circuit breaker '{self.name}' closing - service recovered")
                    self.stats.state = CircuitState.CLOSED
                    self.stats.failure_count = 0
                    self.stats.consecutive_successes = 0
            elif self.stats.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.stats.failure_count = max(0, self.stats.failure_count - 1)
    
    async def _record_failure(self):
        """Record a failed execution."""
        async with self._lock:
            self.stats.failure_count += 1
            self.stats.last_failure_time = time.time()
            self.stats.consecutive_successes = 0
            
            if (self.stats.state == CircuitState.CLOSED and 
                self.stats.failure_count >= self.config.failure_threshold):
                logger.warning(f"⚡ Circuit breaker '{self.name}' opening - too many failures")
                self.stats.state = CircuitState.OPEN
            elif self.stats.state == CircuitState.HALF_OPEN:
                logger.warning(f"⚡ Circuit breaker '{self.name}' re-opening - half-open test failed")
                self.stats.state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        if self.stats.last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self.stats.last_failure_time
        return time_since_failure >= self.config.recovery_timeout
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.stats.state.value,
            "failure_count": self.stats.failure_count,
            "success_count": self.stats.success_count,
            "consecutive_successes": self.stats.consecutive_successes,
            "last_failure_time": self.stats.last_failure_time,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerTimeoutError(Exception):
    """Raised when execution times out."""
    pass


class RateLimitError(Exception):
    """Raised when rate limiting occurs."""
    pass


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
    
    def get_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()
