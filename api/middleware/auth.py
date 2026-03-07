"""
Authentication Middleware

Provides decorators for JWT token validation and user authentication.

Decorators:
- @require_auth: Requires valid JWT token, returns 401 if not authenticated
- @optional_auth: Parses JWT if present, sets g.user_id (None if not authenticated)

Author: Iteration 2 - User Authentication
Created: 2026-03-01
"""

from __future__ import annotations

import os
from functools import wraps
from typing import Optional, Tuple
from flask import request, g
import jwt

from api.middleware.error_handler import UnauthorizedException
from lib.globals import api_logger as log

# JWT configuration - use functions to get values at runtime (after dotenv loads)
JWT_ALGORITHM = 'HS256'


def get_jwt_secret() -> Optional[str]:
    """Get JWT_SECRET at runtime to ensure dotenv has loaded."""
    return os.environ.get('JWT_SECRET')


def get_access_token_expire() -> int:
    """Get ACCESS_TOKEN_EXPIRE at runtime."""
    return int(os.environ.get('ACCESS_TOKEN_EXPIRE', 900))


def get_refresh_token_expire() -> int:
    """Get REFRESH_TOKEN_EXPIRE at runtime."""
    return int(os.environ.get('REFRESH_TOKEN_EXPIRE', 604800))


# Token expiration times (accessed via functions now)
ACCESS_TOKEN_EXPIRE = 900  # Default, use get_access_token_expire() for runtime value
REFRESH_TOKEN_EXPIRE = 604800  # Default, use get_refresh_token_expire() for runtime value

# Lazy-load AuthService singleton to avoid circular imports
_auth_service = None


def _get_auth_service():
    """Get AuthService singleton (lazy initialization)"""
    global _auth_service
    if _auth_service is None:
        from src.services.auth_service import AuthService
        _auth_service = AuthService()
    return _auth_service


def _validate_token(token: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Validate JWT token and return user_id and role.

    Args:
        token: JWT token string

    Returns:
        Tuple of (user_id, role) if valid, (None, None) if invalid or expired
    """
    secret = get_jwt_secret()
    if not secret:
        log.error("[auth] JWT_SECRET not configured!")
        return None, None

    try:
        # Security: Always specify algorithms to prevent JWT header manipulation attacks
        payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        iat = payload.get('iat')
        role = payload.get('role', 'user')  # Default to 'user' for backward compatibility

        if not user_id or not iat:
            log.warning(f"[auth] Token missing user_id or iat: {payload}")
            return None, None

        # Single-device validation: check if token was issued before last login
        # Add 2-second tolerance for timing differences between JWT iat and DB update
        last_login_ts = _get_auth_service().get_last_login_time(user_id)
        if last_login_ts and iat < (last_login_ts - 2):
            log.warning(f"[auth] Token issued before last login: iat={iat}, last_login={last_login_ts}")
            return None, None

        return user_id, role

    except jwt.ExpiredSignatureError:
        log.warning("[auth] Token expired")
        return None, None
    except jwt.PyJWTError as e:
        log.warning(f"[auth] JWT error: {e}")
        return None, None


def require_auth(f):
    """
    Decorator that requires authentication.

    Use for user-specific endpoints (history, favorites, etc.)
    Returns 401 if not authenticated.

    Sets:
        g.user_id: Authenticated user's ID
        g.user_role: Authenticated user's role ('user' or 'admin')
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        log.debug(f"[auth] require_auth called for {f.__name__}")

        secret = get_jwt_secret()
        if not secret:
            log.error("[auth] JWT_SECRET not set on server")
            raise UnauthorizedException(
                message="Authentication not configured",
                error="JWT_SECRET not set on server"
            )

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            log.warning(f"[auth] Missing or invalid Authorization header for {f.__name__}")
            raise UnauthorizedException(error="Missing or invalid Authorization header")

        token = auth_header.split(' ')[1]
        user_id, role = _validate_token(token)

        if user_id is None:
            log.warning(f"[auth] Invalid or expired token for {f.__name__}")
            raise UnauthorizedException(error="Invalid or expired token")

        log.debug(f"[auth] Authenticated user={user_id}, role={role}")
        g.user_id = user_id
        g.user_role = role
        return f(*args, **kwargs)

    return decorated


def optional_auth(f):
    """
    Decorator that optionally authenticates.

    Use for endpoints that work for both anonymous and authenticated users.
    (e.g., match endpoints that record history for logged-in users)

    Sets:
        g.user_id: Authenticated user's ID, or None if not authenticated
        g.user_role: Authenticated user's role, or None if not authenticated
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        g.user_id = None  # Default: anonymous
        g.user_role = None

        secret = get_jwt_secret()
        if not secret:
            return f(*args, **kwargs)

        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            user_id, role = _validate_token(token)
            g.user_id = user_id  # None if invalid
            g.user_role = role if user_id else None

        return f(*args, **kwargs)

    return decorated
