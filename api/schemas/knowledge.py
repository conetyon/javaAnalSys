# api/schemas/knowledge.py
"""
知识点相关的请求/响应模型
"""
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class KnowledgeNode(BaseModel):
    """知识点节点"""
    id: int = Field(description="知识点 ID")
    name: str = Field(description="知识点名称")
    parent_id: Optional[int] = Field(default=None, description="父节点 ID")
    level: Optional[int] = Field(default=None, description="层级")
    title: Optional[str] = Field(default=None, description="显示标题（前端适配）")
    key: Optional[int] = Field(default=None, description="节点 key（前端适配）")
    children: List["KnowledgeNode"] = Field(default_factory=list, description="子节点")

    class Config:
        from_attributes = True


class KnowledgeDetail(BaseModel):
    """知识点详情"""
    id: int = Field(description="知识点 ID")
    name: str = Field(description="知识点名称")
    parent_id: Optional[int] = Field(default=None, description="父节点 ID")
    level: Optional[int] = Field(default=None, description="层级")
    keywords: Optional[Any] = Field(default=None, description="关键词")
    ast_template: Optional[Any] = Field(default=None, description="AST 模板")

    class Config:
        from_attributes = True


class KnowledgeTreeResponse(BaseModel):
    """知识点树响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: List[KnowledgeNode] = Field(default_factory=list, description="知识点树")


class KnowledgeDetailResponse(BaseModel):
    """知识点详情响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: Optional[KnowledgeDetail] = Field(default=None, description="知识点详情")


class KnowledgeListResponse(BaseModel):
    """知识点列表响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: List[KnowledgeDetail] = Field(default_factory=list, description="知识点列表")


# 允许递归引用
KnowledgeNode.model_rebuild()
