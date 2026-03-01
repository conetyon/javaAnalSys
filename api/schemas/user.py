"""
User-related Schemas

Pydantic models for history and favorites endpoints.

Author: Iteration 3 - Advanced Features
Created: 2026-03-01
"""

from __future__ import annotations

from typing import Optional, List
from pydantic import BaseModel, Field


# ============== History ==============

class HistoryItem(BaseModel):
    """Single history record"""
    id: int
    kp_ids: List[int]
    kp_names: List[str]
    params: dict
    mode: str = "list"
    created_at: str  # ISO format datetime string


class HistoryResponse(BaseModel):
    """Paginated history response"""
    items: List[HistoryItem]
    total: int
    page: int
    page_size: int


class HistoryListRequest(BaseModel):
    """History list request parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50)


# ============== Favorites ==============

class FavoriteItem(BaseModel):
    """Single favorite record with snippet details"""
    id: int  # favorite record id
    snippet_id: int
    content: str
    file_path: Optional[str] = None
    created_at: str  # ISO format datetime string


class FavoritesResponse(BaseModel):
    """Paginated favorites response"""
    items: List[FavoriteItem]
    total: int
    page: int
    page_size: int


class FavoritesListRequest(BaseModel):
    """Favorites list request parameters"""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=50)


class AddFavoriteRequest(BaseModel):
    """Add favorite request"""
    snippet_id: int = Field(..., gt=0)


class RemoveFavoriteRequest(BaseModel):
    """Remove favorite request"""
    snippet_id: int = Field(..., gt=0)
