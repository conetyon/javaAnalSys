"""
Rate Limiter Service - Sliding Window Rate Limiting

Implements in-memory sliding window rate limiting to prevent
abuse of the AI explanation feature.

Author: Iteration 4 - Code Explanation Feature
Created: 2026-03-07
"""

import time
from collections import defaultdict
from typing import Optional, Tuple

from lib.globals import Cfg, core_logger as log


class RateLimiter:
    """
    In-memory sliding window rate limiter.

    Features:
    - Per-user rate limiting
    - Configurable requests per minute
    - Burst allowance for short spikes
    - Thread-safe for single-process deployment
    """

    def __init__(
        self,
        requests_per_minute: int = None,
        burst: int = None
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Max sustained requests per minute
            burst: Additional burst requests allowed
        """
        rate_cfg = Cfg.rate_limit
        if rate_cfg:
            self.requests_per_minute = requests_per_minute or rate_cfg.requests_per_minute
            self.burst = burst if burst is not None else rate_cfg.burst
        else:
            self.requests_per_minute = requests_per_minute or 10
            self.burst = burst if burst is not None else 3

        # Sliding window state: user_id -> list of timestamps
        self._windows: dict = defaultdict(list)

        # Window size in seconds
        self._window_size = 60.0

    def check_rate_limit(self, user_id: int) -> Tuple[bool, Optional[int]]:
        """
        Check if user is within rate limit.

        Args:
            user_id: User ID to check

        Returns:
            Tuple of (allowed: bool, retry_after_seconds: int or None)
            - (True, None) if request is allowed
            - (False, seconds) if rate limited, with retry suggestion
        """
        now = time.time()
        window_start = now - self._window_size

        # Get user's request timestamps
        timestamps = self._windows[user_id]

        # Remove expired timestamps (outside sliding window)
        timestamps = [ts for ts in timestamps if ts > window_start]
        self._windows[user_id] = timestamps

        # Calculate limit (base + burst)
        max_requests = self.requests_per_minute + self.burst

        if len(timestamps) >= max_requests:
            # Rate limited - calculate retry time
            oldest = min(timestamps) if timestamps else now
            retry_after = int(oldest + self._window_size - now) + 1
            retry_after = max(1, retry_after)  # At least 1 second
            return False, retry_after

        return True, None

    def record_request(self, user_id: int) -> None:
        """
        Record a request for rate limiting.

        Call this AFTER successfully processing a request.

        Args:
            user_id: User ID
        """
        now = time.time()
        self._windows[user_id].append(now)

    def get_remaining(self, user_id: int) -> int:
        """
        Get remaining requests in current window.

        Args:
            user_id: User ID

        Returns:
            Number of remaining requests allowed
        """
        now = time.time()
        window_start = now - self._window_size

        timestamps = self._windows.get(user_id, [])
        active_count = sum(1 for ts in timestamps if ts > window_start)

        max_requests = self.requests_per_minute + self.burst
        return max(0, max_requests - active_count)

    def reset(self, user_id: int = None) -> None:
        """
        Reset rate limit state.

        Args:
            user_id: Specific user to reset, or None for all users
        """
        if user_id is not None:
            self._windows.pop(user_id, None)
        else:
            self._windows.clear()

    def cleanup(self) -> int:
        """
        Remove expired entries from all windows.

        Returns:
            Number of entries removed
        """
        now = time.time()
        window_start = now - self._window_size
        removed = 0

        for user_id in list(self._windows.keys()):
            timestamps = self._windows[user_id]
            new_timestamps = [ts for ts in timestamps if ts > window_start]
            removed += len(timestamps) - len(new_timestamps)

            if new_timestamps:
                self._windows[user_id] = new_timestamps
            else:
                del self._windows[user_id]

        return removed


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get singleton RateLimiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
