# api/routes/match.py
"""
匹配相关路由
"""
from flask import jsonify, request
from pydantic import ValidationError
from . import api_bp
from src.services import SearchService
from src.services.search_service import KnowledgePointNotFoundError, NonLeafKnowledgePointError
from api.schemas.match import (
    MatchRequest,
    BatchMatchRequest,
    CompositeMatchRequest,
    MatrixMatchRequest,
    CompositeMatrixMatchRequest
)
from api.middleware.error_handler import BadRequestException, NotFoundException
from lib.globals import api_logger as log
import config


# 初始化服务（懒加载）
_search_service = None


def get_search_service() -> SearchService:
    """获取搜索服务实例（单例）"""
    global _search_service
    if _search_service is None:
        _search_service = SearchService(db_name=config.DB_NAME)
    return _search_service


@api_bp.route('/match', methods=['POST'])
def match_knowledge():
    """
    知识点匹配接口
    ---
    POST /api/match
    
    Request Body:
        {
            "kp_id": 10011,
            "target_difficulty": 0.5,
            "top_k": 5,
            "ast_min_ratio": 0.4,
            "keyword_min_score": 0.4,
            "difficulty_mode": "relaxed"
        }
    
    Response:
        {
            "code": 200,
            "message": "success",
            "kp_id": 10011,
            "total": 3,
            "data": [
                {
                    "id": 1,
                    "content": "...",
                    "score": 0.85,
                    "ast_ratio": 0.9,
                    "ast_coverage": 0.8,
                    "keyword_score": 0.7,
                    "keyword_hit": 3,
                    "keyword_total": 5,
                    "difficulty": 0.6,
                    "details": "...",
                    "file_path": "..."
                }
            ]
        }
    """
    log.info("[POST] /api/match - 开始处理匹配请求")

    try:
        # 解析请求体
        json_data = request.get_json()
        if not json_data:
            raise BadRequestException(
                message="请求体不能为空",
                error="Request body is required"
            )

        # 使用 Pydantic 校验参数
        try:
            req = MatchRequest(**json_data)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                errors.append(f"{field}: {error['msg']}")
            raise BadRequestException(
                message="请求参数校验失败",
                error="; ".join(errors)
            )

        log.info(f"[POST] /api/match - 参数: kp_id={req.kp_id}, "
                 f"difficulty={req.target_difficulty}, top_k={req.top_k}")

        # 调用服务层
        service = get_search_service()
        results = service.search(
            kp_id=req.kp_id,
            target_difficulty=req.target_difficulty,
            top_k=req.top_k,
            ast_min_ratio=req.ast_min_ratio,
            keyword_min_score=req.keyword_min_score,
            difficulty_mode=req.difficulty_mode
        )

        log.info(f"[POST] /api/match - 成功匹配 {len(results)} 条结果")

        return jsonify({
            "code": 200,
            "message": "success",
            "kp_id": req.kp_id,
            "total": len(results),
            "data": results
        })

    except KnowledgePointNotFoundError as e:
        raise NotFoundException(
            message=f"知识点不存在: {e.kp_id}",
            error=f"Knowledge point {e.kp_id} not found"
        )
    except NonLeafKnowledgePointError as e:
        raise BadRequestException(
            message=f"知识点 {e.kp_id} ('{e.name}') 是分类节点，不支持匹配",
            error=f"Knowledge point {e.kp_id} is not a leaf node (level={e.level}). Only leaf nodes (level=3) support matching."
        )
    except BadRequestException:
        raise
    except Exception as e:
        log.error(f"[POST] /api/match - 异常: {str(e)}", exc_info=True)
        raise


@api_bp.route('/match/batch', methods=['POST'])
def batch_match_knowledge():
    """
    批量知识点匹配接口
    ---
    POST /api/match/batch
    
    Request Body:
        {
            "kp_ids": [10011, 10012, 10013],
            "target_difficulty": 0.5,
            "top_k": 5,
            "ast_min_ratio": 0.4,
            "keyword_min_score": 0.4,
            "difficulty_mode": "relaxed"
        }
    
    Response:
        {
            "code": 200,
            "message": "success",
            "data": {
                "10011": [...],
                "10012": [...],
                "10013": [...]
            }
        }
    """
    log.info("[POST] /api/match/batch - 开始处理批量匹配请求")

    try:
        # 解析请求体
        json_data = request.get_json()
        if not json_data:
            raise BadRequestException(
                message="请求体不能为空",
                error="Request body is required"
            )

        # 使用 Pydantic 校验参数
        try:
            req = BatchMatchRequest(**json_data)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                errors.append(f"{field}: {error['msg']}")
            raise BadRequestException(
                message="请求参数校验失败",
                error="; ".join(errors)
            )

        if not req.kp_ids:
            raise BadRequestException(
                message="知识点 ID 列表不能为空",
                error="kp_ids is required and cannot be empty"
            )

        log.info(f"[POST] /api/match/batch - 参数: kp_ids={req.kp_ids}, "
                 f"difficulty={req.target_difficulty}, top_k={req.top_k}")

        # 调用服务层
        service = get_search_service()
        results = {}
        errors = {}  # 记录失败的知识点

        for kp_id in req.kp_ids:
            try:
                kp_results = service.search(
                    kp_id=kp_id,
                    target_difficulty=req.target_difficulty,
                    top_k=req.top_k,
                    ast_min_ratio=req.ast_min_ratio,
                    keyword_min_score=req.keyword_min_score,
                    difficulty_mode=req.difficulty_mode
                )
                results[str(kp_id)] = kp_results
            except KnowledgePointNotFoundError as e:
                log.warning(f"[POST] /api/match/batch - kp_id={kp_id} 不存在")
                results[str(kp_id)] = []
                errors[str(kp_id)] = "Knowledge point not found"
            except NonLeafKnowledgePointError as e:
                log.warning(f"[POST] /api/match/batch - kp_id={kp_id} 是非叶子节点")
                results[str(kp_id)] = []
                errors[str(kp_id)] = f"Non-leaf node (level={e.level}), only leaf nodes support matching"
            except Exception as e:
                log.warning(f"[POST] /api/match/batch - kp_id={kp_id} 匹配失败: {str(e)}")
                results[str(kp_id)] = []
                errors[str(kp_id)] = str(e)

        total_results = sum(len(v) for v in results.values())
        log.info(f"[POST] /api/match/batch - 成功匹配 {len(req.kp_ids)} 个知识点，"
                 f"共 {total_results} 条结果")

        response = {
            "code": 200,
            "message": "success",
            "data": results
        }
        if errors:
            response["errors"] = errors
            response["message"] = f"部分成功 ({len(errors)}/{len(req.kp_ids)} 失败)"

        return jsonify(response)

    except BadRequestException:
        raise
    except Exception as e:
        log.error(f"[POST] /api/match/batch - 异常: {str(e)}", exc_info=True)
        raise


@api_bp.route('/match/health', methods=['GET'])
def match_health():
    """
    匹配服务健康检查
    ---
    GET /api/match/health
    
    Response:
        {
            "code": 200,
            "message": "success",
            "data": {
                "status": "healthy",
                "service": "SearchService"
            }
        }
    """
    try:
        # 尝试初始化服务
        service = get_search_service()
        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "status": "healthy",
                "service": "SearchService"
            }
        })
    except Exception as e:
        log.error(f"[GET] /api/match/health - 服务不健康: {str(e)}")
        return jsonify({
            "code": 503,
            "message": "服务不可用",
            "data": {
                "status": "unhealthy",
                "error": str(e)
            }
        }), 503


@api_bp.route('/match/composite', methods=['POST'])
def composite_match_knowledge():
    """
    综合知识点匹配接口
    计算代码片段与多个知识点的综合匹配度，找到同时涉及多个知识点的代码
    ---
    POST /api/match/composite

    Request Body:
        {
            "kp_ids": [10011, 10012, 10034],
            "target_difficulty": 0.5,
            "top_k": 5,
            "ast_min_ratio": 0.3,
            "keyword_min_score": 0.3,
            "difficulty_mode": "relaxed",
            "score_aggregation": "average"
        }

    Response:
        {
            "code": 200,
            "message": "success",
            "kp_ids": [10011, 10012, 10034],
            "total": 3,
            "data": [
                {
                    "id": 1,
                    "content": "...",
                    "composite_score": 0.75,
                    "kp_count": 3,
                    "kp_details": [
                        {
                            "kp_id": 10011,
                            "kp_name": "循环语句",
                            "score": 0.8,
                            "ast_ratio": 0.9,
                            "keyword_score": 0.7
                        },
                        ...
                    ],
                    "score_aggregation": "average",
                    "file_path": "..."
                }
            ]
        }
    """
    log.info("[POST] /api/match/composite - 开始处理综合匹配请求")

    try:
        # 解析请求体
        json_data = request.get_json()
        if not json_data:
            raise BadRequestException(
                message="请求体不能为空",
                error="Request body is required"
            )

        # 使用 Pydantic 校验参数
        try:
            req = CompositeMatchRequest(**json_data)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                errors.append(f"{field}: {error['msg']}")
            raise BadRequestException(
                message="请求参数校验失败",
                error="; ".join(errors)
            )

        if not req.kp_ids:
            raise BadRequestException(
                message="知识点 ID 列表不能为空",
                error="kp_ids is required and cannot be empty"
            )

        log.info(f"[POST] /api/match/composite - 参数: kp_ids={req.kp_ids}, "
                 f"difficulty={req.target_difficulty}, top_k={req.top_k}, "
                 f"aggregation={req.score_aggregation}")

        # 调用服务层
        service = get_search_service()
        results = service.composite_search(
            kp_ids=req.kp_ids,
            target_difficulty=req.target_difficulty,
            top_k=req.top_k,
            ast_min_ratio=req.ast_min_ratio,
            keyword_min_score=req.keyword_min_score,
            difficulty_mode=req.difficulty_mode,
            score_aggregation=req.score_aggregation
        )

        log.info(f"[POST] /api/match/composite - 成功匹配 {len(results)} 条结果")

        return jsonify({
            "code": 200,
            "message": "success",
            "kp_ids": req.kp_ids,
            "total": len(results),
            "data": results
        })

    except KnowledgePointNotFoundError as e:
        raise NotFoundException(
            message=f"知识点不存在: {e.kp_id}",
            error=f"Knowledge point {e.kp_id} not found"
        )
    except NonLeafKnowledgePointError as e:
        raise BadRequestException(
            message=f"知识点 {e.kp_id} ('{e.name}') 是分类节点，不支持匹配",
            error=f"Knowledge point {e.kp_id} is not a leaf node (level={e.level}). Only leaf nodes (level=3) support matching."
        )
    except BadRequestException:
        raise
    except Exception as e:
        log.error(f"[POST] /api/match/composite - 异常: {str(e)}", exc_info=True)
        raise


@api_bp.route('/match/matrix', methods=['POST'])
def matrix_match_knowledge():
    """
    矩阵匹配接口（按难度分级返回）
    ---
    POST /api/match/matrix

    Request Body:
        {
            "kp_id": 10011,
            "per_level": 5,
            "ast_min_ratio": 0.4,
            "keyword_min_score": 0.4
        }

    Response:
        {
            "code": 200,
            "message": "success",
            "kp_id": 10011,
            "shape": [3, 5],
            "levels": ["easy", "medium", "hard"],
            "per_level": 5,
            "matrix": {
                "easy": [...],
                "medium": [...],
                "hard": [...]
            },
            "total": 12
        }
    """
    log.info("[POST] /api/match/matrix - 开始处理矩阵匹配请求")

    try:
        json_data = request.get_json()
        if not json_data:
            raise BadRequestException(
                message="请求体不能为空",
                error="Request body is required"
            )

        try:
            req = MatrixMatchRequest(**json_data)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                errors.append(f"{field}: {error['msg']}")
            raise BadRequestException(
                message="请求参数校验失败",
                error="; ".join(errors)
            )

        log.info(f"[POST] /api/match/matrix - 参数: kp_id={req.kp_id}, per_level={req.per_level}")

        service = get_search_service()
        result = service.matrix_search(
            kp_id=req.kp_id,
            per_level=req.per_level,
            ast_min_ratio=req.ast_min_ratio,
            keyword_min_score=req.keyword_min_score
        )

        log.info(f"[POST] /api/match/matrix - 成功返回矩阵 shape={result['shape']}, total={result['total']}")

        return jsonify({
            "code": 200,
            "message": "success",
            **result
        })

    except KnowledgePointNotFoundError as e:
        raise NotFoundException(
            message=f"知识点不存在: {e.kp_id}",
            error=f"Knowledge point {e.kp_id} not found"
        )
    except NonLeafKnowledgePointError as e:
        raise BadRequestException(
            message=f"知识点 {e.kp_id} ('{e.name}') 是分类节点，不支持匹配",
            error=f"Knowledge point {e.kp_id} is not a leaf node (level={e.level})"
        )
    except BadRequestException:
        raise
    except Exception as e:
        log.error(f"[POST] /api/match/matrix - 异常: {str(e)}", exc_info=True)
        raise


@api_bp.route('/match/composite/matrix', methods=['POST'])
def composite_matrix_match_knowledge():
    """
    综合知识点矩阵匹配接口（按难度分级返回）
    ---
    POST /api/match/composite/matrix

    Request Body:
        {
            "kp_ids": [10011, 10012],
            "per_level": 5,
            "ast_min_ratio": 0.4,
            "keyword_min_score": 0.4,
            "score_aggregation": "average"
        }

    Response:
        {
            "code": 200,
            "message": "success",
            "kp_ids": [10011, 10012],
            "shape": [3, 5],
            "levels": ["easy", "medium", "hard"],
            "per_level": 5,
            "matrix": {
                "easy": [...],
                "medium": [...],
                "hard": [...]
            },
            "total": 10
        }
    """
    log.info("[POST] /api/match/composite/matrix - 开始处理综合矩阵匹配请求")

    try:
        json_data = request.get_json()
        if not json_data:
            raise BadRequestException(
                message="请求体不能为空",
                error="Request body is required"
            )

        try:
            req = CompositeMatrixMatchRequest(**json_data)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                errors.append(f"{field}: {error['msg']}")
            raise BadRequestException(
                message="请求参数校验失败",
                error="; ".join(errors)
            )

        if not req.kp_ids:
            raise BadRequestException(
                message="知识点列表不能为空",
                error="kp_ids is required and cannot be empty"
            )

        log.info(f"[POST] /api/match/composite/matrix - 参数: kp_ids={req.kp_ids}, per_level={req.per_level}")

        service = get_search_service()
        result = service.composite_matrix_search(
            kp_ids=req.kp_ids,
            per_level=req.per_level,
            ast_min_ratio=req.ast_min_ratio,
            keyword_min_score=req.keyword_min_score,
            score_aggregation=req.score_aggregation
        )

        log.info(f"[POST] /api/match/composite/matrix - 成功返回矩阵 shape={result['shape']}, total={result['total']}")

        return jsonify({
            "code": 200,
            "message": "success",
            **result
        })

    except KnowledgePointNotFoundError as e:
        raise NotFoundException(
            message=f"知识点不存在: {e.kp_id}",
            error=f"Knowledge point {e.kp_id} not found"
        )
    except NonLeafKnowledgePointError as e:
        raise BadRequestException(
            message=f"知识点 {e.kp_id} ('{e.name}') 是分类节点，不支持匹配",
            error=f"Knowledge point {e.kp_id} is not a leaf node (level={e.level})"
        )
    except BadRequestException:
        raise
    except Exception as e:
        log.error(f"[POST] /api/match/composite/matrix - 异常: {str(e)}", exc_info=True)
        raise

