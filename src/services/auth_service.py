"""
Authentication Service

Handles user registration, login, and token management.

Features:
- User registration with password hashing (bcrypt)
- Login with row-level locking for concurrent safety
- Single-device login enforcement via last_login_at timestamp
- JWT token generation and refresh

Author: Iteration 2 - User Authentication
Created: 2026-03-01
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from mysql.connector import IntegrityError

import config
from lib.client.db import MySQLClient
from api.middleware.error_handler import BadRequestException, UnauthorizedException


class AuthService:
    """
    Authentication service for user management.

    Follows the same initialization pattern as KnowledgeService.
    """

    def __init__(self, db_name: str = None):
        self.db_name = db_name or config.DB_NAME
        self.client = MySQLClient(db=self.db_name)

    def register(self, username: str, password: str, email: str = None) -> dict:
        """
        Register a new user.

        Args:
            username: Unique username
            password: Plain text password (will be hashed)
            email: Optional email address

        Returns:
            User info dict (id, username, email, role)

        Raises:
            BadRequestException: If username or email already exists
        """
        # Hash password with bcrypt
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        try:
            self.client.execute(
                """INSERT INTO users (username, password_hash, email)
                   VALUES (%s, %s, %s)""",
                (username, password_hash, email)
            )

            # Fetch the created user
            user = self.client.fetch_one(
                "SELECT id, username, email, role FROM users WHERE username = %s",
                (username,)
            )
            return dict(user) if user else {}

        except IntegrityError as e:
            # 1062 = Duplicate entry
            if "1062" in str(e) or "Duplicate entry" in str(e):
                if "username" in str(e).lower():
                    raise BadRequestException(
                        message="Username already exists",
                        error="Username already taken"
                    )
                if "email" in str(e).lower():
                    raise BadRequestException(
                        message="Email already exists",
                        error="Email already registered"
                    )
            raise BadRequestException(message="Registration failed", error=str(e))

    def login(self, username: str, password: str) -> dict:
        """
        Authenticate user and generate tokens.

        Uses row-level locking (SELECT ... FOR UPDATE) for concurrent safety.

        Args:
            username: Username
            password: Plain text password

        Returns:
            Dict with tokens and user info (access_token, refresh_token, user)

        Raises:
            UnauthorizedException: If credentials are invalid
        """
        # Use a separate client with autocommit=False for proper transaction
        tx_client = MySQLClient(db=self.db_name, autocommit=False)

        with tx_client as client:  # Transaction context
            # SELECT ... FOR UPDATE acquires row lock to prevent race conditions
            user = client.fetch_one(
                """SELECT id, username, password_hash, role
                   FROM users WHERE username = %s FOR UPDATE""",
                (username,)
            )

            if not user:
                raise UnauthorizedException(error="Invalid credentials")

            # Verify password
            if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
                raise UnauthorizedException(error="Invalid credentials")

            # Update last login time (under row lock) - use UTC for consistency with JWT iat
            client.execute(
                "UPDATE users SET last_login_at = UTC_TIMESTAMP() WHERE id = %s",
                (user['id'],)
            )

        # Generate tokens (outside transaction)
        tokens = self._generate_tokens(user['id'])

        # Add user info to response
        tokens['user'] = {
            'id': user['id'],
            'username': user['username'],
            'role': user['role']
        }

        return tokens

    def refresh_token(self, refresh_token: str) -> dict:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New token dict (access_token only, same refresh_token)

        Raises:
            UnauthorizedException: If refresh token is invalid or expired
        """
        from api.middleware.auth import get_jwt_secret, JWT_ALGORITHM

        secret = get_jwt_secret()
        if not secret:
            raise UnauthorizedException(error="Authentication not configured")

        try:
            payload = jwt.decode(refresh_token, secret, algorithms=[JWT_ALGORITHM])
            user_id = payload.get('user_id')
            iat = payload.get('iat')

            if not user_id or not iat:
                raise UnauthorizedException(error="Invalid refresh token")

            # Single-device check - add 2-second tolerance for timing differences
            last_login_ts = self.get_last_login_time(user_id)
            if last_login_ts and iat < (last_login_ts - 2):
                raise UnauthorizedException(error="Session expired, please login again")

            # Generate new access token only (refresh token stays the same)
            return self._generate_tokens(user_id)

        except jwt.ExpiredSignatureError:
            raise UnauthorizedException(error="Refresh token expired")
        except jwt.PyJWTError as e:
            raise UnauthorizedException(error=f"Invalid refresh token: {str(e)}")

    def get_last_login_time(self, user_id: int) -> Optional[float]:
        """
        Get user's last login timestamp as UNIX timestamp.

        Used for single-device login validation.
        Returns UNIX timestamp (UTC seconds) for direct comparison with JWT iat.

        Args:
            user_id: User ID

        Returns:
            UNIX timestamp (float) or None if never logged in
        """
        row = self.client.fetch_one(
            "SELECT UNIX_TIMESTAMP(last_login_at) as ts FROM users WHERE id = %s",
            (user_id,)
        )
        if row and row['ts']:
            return float(row['ts'])
        return None

    def _generate_tokens(self, user_id: int) -> dict:
        """
        Generate access and refresh tokens.

        Args:
            user_id: User ID to embed in token

        Returns:
            Token dict (access_token, refresh_token, token_type, expires_in)
        """
        # Import JWT config here to avoid circular dependencies
        from api.middleware.auth import (
            get_jwt_secret, JWT_ALGORITHM,
            get_access_token_expire, get_refresh_token_expire
        )

        secret = get_jwt_secret()
        if not secret:
            raise UnauthorizedException(error="JWT_SECRET not configured")

        access_expire = get_access_token_expire()
        refresh_expire = get_refresh_token_expire()

        now = datetime.utcnow()
        iat_timestamp = int(now.timestamp())

        access_payload = {
            'user_id': user_id,
            'exp': now + timedelta(seconds=access_expire),
            'iat': iat_timestamp
        }

        refresh_payload = {
            'user_id': user_id,
            'exp': now + timedelta(seconds=refresh_expire),
            'iat': iat_timestamp
        }

        return {
            'access_token': jwt.encode(access_payload, secret, algorithm=JWT_ALGORITHM),
            'refresh_token': jwt.encode(refresh_payload, secret, algorithm=JWT_ALGORITHM),
            'token_type': 'Bearer',
            'expires_in': access_expire
        }
