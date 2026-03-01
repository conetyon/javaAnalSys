"""
Authentication Schemas

Pydantic models for user authentication requests and responses.

Author: Iteration 2 - User Authentication
Created: 2026-03-01
"""

import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator, EmailStr


class RegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Username (3-50 chars, alphanumeric and underscore only)"
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (8-128 chars)"
    )
    email: Optional[EmailStr] = Field(
        None,
        description="Email address (optional)"
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username can only contain letters, numbers, and underscores')
        return v


class LoginRequest(BaseModel):
    """User login request"""
    username: str = Field(..., min_length=1, description="Username")
    password: str = Field(..., min_length=1, description="Password")


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str = Field(..., description="Refresh token")


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str = Field(description="Access token")
    refresh_token: str = Field(description="Refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(default=900, description="Expiration time (seconds)")


class UserInfo(BaseModel):
    """User information"""
    id: int
    username: str
    email: Optional[str] = None
    role: str = "user"
