"""
Explain Schemas

Pydantic models for AI code explanation requests and responses.

Author: Iteration 4 - Code Explanation Feature
Created: 2026-03-07
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class UserLevel(str, Enum):
    """User expertise level for explanation customization"""
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class ExplainRequest(BaseModel):
    """Request for AI code explanation"""
    snippet_id: int = Field(..., description="Code snippet ID")
    kp_id: int = Field(..., description="Primary knowledge point ID")
    kp_ids: Optional[List[int]] = Field(
        None,
        description="Multiple knowledge point IDs (for composite matching). If provided, kp_id is ignored."
    )
    user_level: UserLevel = Field(
        default=UserLevel.beginner,
        description="User expertise level"
    )


class ChatRequest(BaseModel):
    """Request for multi-turn conversation"""
    snippet_id: int = Field(..., description="Code snippet ID")
    kp_id: int = Field(..., description="Primary knowledge point ID")
    kp_ids: Optional[List[int]] = Field(
        None,
        description="Multiple knowledge point IDs (for composite matching)"
    )
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User's question"
    )
    session_id: Optional[str] = Field(
        None,
        description="Session ID for continuing conversation"
    )


class QuotaResponse(BaseModel):
    """User quota information"""
    daily_limit: int = Field(description="Daily request limit (-1 for unlimited)")
    used_today: int = Field(description="Requests used today")
    remaining: int = Field(description="Remaining requests (-1 for unlimited)")
    reset_at: Optional[str] = Field(
        None,
        description="Next reset time (ISO format with timezone)"
    )
    unlimited: bool = Field(
        default=False,
        description="Whether user has unlimited quota (admin)"
    )


class HighlightRange(BaseModel):
    """A highlighted range in the code"""
    start_line: int = Field(description="Start line (1-indexed)")
    end_line: int = Field(description="End line (1-indexed)")
    type: str = Field(description="AST node type or 'keyword_match'")
    label: str = Field(description="Human-readable label")


class TokenUsage(BaseModel):
    """Token usage statistics"""
    prompt_tokens: int = Field(default=0, description="Prompt tokens used")
    completion_tokens: int = Field(default=0, description="Completion tokens used")
