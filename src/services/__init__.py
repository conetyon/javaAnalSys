# src/services/__init__.py
"""
服务层模块
封装业务逻辑，供 API 和离线任务共用
"""
from .search_service import SearchService
from .knowledge_service import KnowledgeService

__all__ = [
    "SearchService",
    "KnowledgeService",
]
