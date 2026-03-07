"""
Quota Middleware

Provides decorators for checking user quota and rate limits.

Author: Iteration 4 - Code Explanation Feature
Created: 2026-03-07
"""

from functools import wraps
from flask import g

from api.middleware.error_handler import TooManyRequestsException
from src.services.quota_service import get_quota_service
from src.services.rate_limiter import get_rate_limiter
from lib.globals import api_logger as log


def require_quota(f):
    """
    Decorator that checks quota and rate limit before processing request.

    Must be used AFTER @require_auth decorator.

    Checks:
    1. Rate limit (requests per minute)
    2. Daily quota

    Raises:
        TooManyRequestsException: If rate limited or quota exhausted
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = g.user_id
        user_role = getattr(g, 'user_role', 'user')

        log.debug(f"[quota] Checking quota for user={user_id}, role={user_role}")

        # Check rate limit first
        rate_limiter = get_rate_limiter()
        allowed, retry_after = rate_limiter.check_rate_limit(user_id)

        if not allowed:
            log.warning(f"[quota] Rate limited: user={user_id}, retry_after={retry_after}")
            raise TooManyRequestsException(
                message="请求过于频繁，请稍后再试",
                error="rate_limited",
                retry_after=retry_after
            )

        # Check daily quota
        quota_service = get_quota_service()
        has_quota = quota_service.check_quota(user_id, user_role)

        if not has_quota:
            quota_info = quota_service.get_quota_info(user_id, user_role)
            log.warning(f"[quota] Quota exhausted: user={user_id}, info={quota_info}")
            raise TooManyRequestsException(
                message="今日配额已用完",
                error="quota_exhausted",
                reset_at=quota_info.get("reset_at")
            )

        log.debug(f"[quota] Quota check passed for user={user_id}")
        return f(*args, **kwargs)

    return decorated


def consume_quota_after(f):
    """
    Decorator that consumes quota AFTER successful request.

    Use this decorator on the actual route handler (after require_quota).
    Records the request for rate limiting and consumes one quota unit.

    Must be used AFTER @require_auth and @require_quota decorators.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        result = f(*args, **kwargs)

        # Only consume quota if request succeeded
        user_id = g.user_id
        user_role = getattr(g, 'user_role', 'user')

        # Record for rate limiting
        rate_limiter = get_rate_limiter()
        rate_limiter.record_request(user_id)

        # Consume quota (unless admin with unlimited)
        quota_service = get_quota_service()
        quota_service.consume_quota(user_id)

        return result

    return decorated
