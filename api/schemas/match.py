# api/schemas/match.py
"""
匹配相关的请求/响应模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class MatchRequest(BaseModel):
    """匹配请求参数"""
    kp_id: int = Field(description="知识点 ID")
    target_difficulty: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="目标难度 (0-1)"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=50,
        description="返回结果数量"
    )
    ast_min_ratio: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="AST 结构匹配最低阈值"
    )
    keyword_min_score: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="关键词匹配最低得分"
    )
    difficulty_mode: str = Field(
        default="relaxed",
        description="难度匹配模式: strict / relaxed"
    )


class MatchResultItem(BaseModel):
    """单个匹配结果"""
    id: Optional[int] = Field(default=None, description="代码片段 ID")
    content: str = Field(default="", description="代码内容")
    score: float = Field(description="综合得分")
    ast_ratio: float = Field(description="AST 匹配率")
    ast_coverage: float = Field(description="AST 覆盖率")
    keyword_score: float = Field(description="关键词得分")
    keyword_hit: int = Field(default=0, description="命中关键词数")
    keyword_total: int = Field(default=0, description="总关键词数")
    difficulty: float = Field(description="难度得分")
    details: Optional[str] = Field(default=None, description="详情文本")
    details_md: Optional[str] = Field(default=None, description="详情 Markdown")
    file_path: Optional[str] = Field(default=None, description="源文件路径")


class MatchResponse(BaseModel):
    """匹配响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: List[MatchResultItem] = Field(default_factory=list, description="匹配结果列表")
    kp_id: int = Field(description="查询的知识点 ID")
    total: int = Field(default=0, description="结果总数")


class BatchMatchRequest(BaseModel):
    """批量匹配请求"""
    kp_ids: List[int] = Field(description="知识点 ID 列表")
    target_difficulty: float = Field(default=0.5, ge=0.0, le=1.0)
    top_k: int = Field(default=5, ge=1, le=50)
    ast_min_ratio: float = Field(default=0.4, ge=0.0, le=1.0)
    keyword_min_score: float = Field(default=0.4, ge=0.0, le=1.0)
    difficulty_mode: str = Field(default="relaxed")


class BatchMatchResponse(BaseModel):
    """批量匹配响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: dict = Field(default_factory=dict, description="按 kp_id 分组的匹配结果")


class CompositeMatchRequest(BaseModel):
    """综合知识点匹配请求"""
    kp_ids: List[int] = Field(description="知识点 ID 列表（例如：[10011, 10012]）")
    target_difficulty: float = Field(default=0.5, ge=0.0, le=1.0, description="目标难度")
    top_k: int = Field(default=5, ge=1, le=50, description="返回结果数量")
    ast_min_ratio: float = Field(default=0.4, ge=0.0, le=1.0, description="AST 最低阈值（统一默认值）")
    keyword_min_score: float = Field(default=0.4, ge=0.0, le=1.0, description="关键词最低得分（统一默认值）")
    difficulty_mode: str = Field(default="relaxed", description="难度模式")
    score_aggregation: str = Field(
        default="average",
        description="得分聚合方式: average=平均, min=最小值, sum=求和"
    )


class CompositeMatchResultItem(BaseModel):
    """综合匹配单个结果"""
    id: Optional[int] = Field(default=None, description="代码片段 ID")
    content: str = Field(default="", description="代码内容")
    composite_score: float = Field(description="综合得分")
    kp_count: int = Field(description="涉及的知识点数量")
    kp_details: List[dict] = Field(default_factory=list, description="各知识点详细得分")
    score_aggregation: str = Field(description="使用的聚合方式")
    file_path: Optional[str] = Field(default=None, description="源文件路径")


class CompositeMatchResponse(BaseModel):
    """综合匹配响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    kp_ids: List[int] = Field(default_factory=list, description="查询的知识点 ID 列表")
    total: int = Field(default=0, description="结果总数")
    data: List[CompositeMatchResultItem] = Field(default_factory=list, description="匹配结果列表")


# ============================================================================
# 矩阵匹配模式（按难度分级返回）
# ============================================================================

class DifficultyLevel(BaseModel):
    """难度级别定义"""
    name: str = Field(description="级别名称 (如 easy, medium, hard)")
    min_val: float = Field(ge=0.0, le=1.0, description="最小难度值（含）")
    max_val: float = Field(ge=0.0, le=1.0, description="最大难度值（不含，hard 级别除外）")


class MatrixMatchRequest(BaseModel):
    """矩阵匹配请求参数（按难度分级返回）"""
    kp_id: int = Field(description="知识点 ID")
    per_level: int = Field(
        default=5,
        ge=1,
        le=20,
        description="每个难度级别返回的片段数量（矩阵列数 n）"
    )
    ast_min_ratio: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="AST 结构匹配最低阈值"
    )
    keyword_min_score: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="关键词匹配最低得分"
    )


class MatrixMatchResponse(BaseModel):
    """矩阵匹配响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    kp_id: int = Field(description="查询的知识点 ID")
    shape: List[int] = Field(description="矩阵形状 [m, n]，m=难度级别数，n=每级别片段数")
    levels: List[str] = Field(description="难度级别名称列表（矩阵行标签）")
    per_level: int = Field(description="每级别请求的片段数")
    matrix: dict = Field(description="按难度分级的代码片段矩阵 {level_name: [snippets]}")
    total: int = Field(default=0, description="结果总数")


class CompositeMatrixMatchRequest(BaseModel):
    """综合知识点矩阵匹配请求"""
    kp_ids: List[int] = Field(description="知识点 ID 列表")
    per_level: int = Field(
        default=5,
        ge=1,
        le=20,
        description="每个难度级别返回的片段数量"
    )
    ast_min_ratio: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="AST 最低阈值"
    )
    keyword_min_score: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="关键词最低得分"
    )
    score_aggregation: str = Field(
        default="average",
        description="得分聚合方式: average=平均, min=最小值, sum=求和"
    )


class CompositeMatrixMatchResponse(BaseModel):
    """综合知识点矩阵匹配响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    kp_ids: List[int] = Field(description="查询的知识点 ID 列表")
    shape: List[int] = Field(description="矩阵形状 [m, n]")
    levels: List[str] = Field(description="难度级别名称列表")
    per_level: int = Field(description="每级别请求的片段数")
    matrix: dict = Field(description="按难度分级的代码片段矩阵")
    total: int = Field(default=0, description="结果总数")

