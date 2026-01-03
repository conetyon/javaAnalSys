# api/schemas/__init__.py
"""
API Schema 模块
使用 Pydantic 定义请求/响应数据模型
"""
from .knowledge import KnowledgeTreeResponse, KnowledgeDetailResponse
from .match import MatchRequest, MatchResponse, MatchResultItem

__all__ = [
    "KnowledgeTreeResponse",
    "KnowledgeDetailResponse",
    "MatchRequest",
    "MatchResponse",
    "MatchResultItem",
]
