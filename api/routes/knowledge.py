# api/routes/knowledge.py
"""
知识点相关路由
"""
from flask import jsonify, request
from . import api_bp
from src.services import KnowledgeService
from api.middleware.error_handler import NotFoundException, BadRequestException
from lib.globals import api_logger as log
import config


# 初始化服务（懒加载）
_knowledge_service = None


def get_knowledge_service() -> KnowledgeService:
    """获取知识点服务实例（单例）"""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService(db_name=config.DB_NAME)
    return _knowledge_service


@api_bp.route('/knowledge/tree', methods=['GET'])
def get_knowledge_tree():
    """
    获取知识点树状结构
    ---
    GET /api/knowledge/tree
    
    Response:
        {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": 1,
                    "name": "Java基础",
                    "parent_id": null,
                    "level": 1,
                    "title": "Java基础",
                    "key": 1,
                    "children": [...]
                }
            ]
        }
    """
    log.info("[GET] /api/knowledge/tree - 开始获取知识点树结构")

    try:
        service = get_knowledge_service()
        tree_data = service.get_tree()

        count = _count_nodes(tree_data)
        log.info(f"[GET] /api/knowledge/tree - 成功获取 {count} 个知识点节点")

        return jsonify({
            "code": 200,
            "message": "success",
            "data": tree_data
        })
    except Exception as e:
        log.error(f"[GET] /api/knowledge/tree - 异常: {str(e)}", exc_info=True)
        raise


@api_bp.route('/knowledge/list', methods=['GET'])
def get_knowledge_list():
    """
    获取知识点扁平列表
    ---
    GET /api/knowledge/list
    
    Response:
        {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": 1,
                    "name": "Java基础",
                    "parent_id": null,
                    "level": 1,
                    "keywords": [...],
                    "ast_template": {...}
                }
            ]
        }
    """
    log.info("[GET] /api/knowledge/list - 开始获取知识点列表")

    try:
        service = get_knowledge_service()
        list_data = service.get_flat_list()

        log.info(f"[GET] /api/knowledge/list - 成功获取 {len(list_data)} 个知识点")

        return jsonify({
            "code": 200,
            "message": "success",
            "data": list_data
        })
    except Exception as e:
        log.error(f"[GET] /api/knowledge/list - 异常: {str(e)}", exc_info=True)
        raise


@api_bp.route('/knowledge/<int:kp_id>', methods=['GET'])
def get_knowledge_detail(kp_id: int):
    """
    获取单个知识点详情
    ---
    GET /api/knowledge/{kp_id}
    
    Path Parameters:
        kp_id: 知识点 ID
    
    Response:
        {
            "code": 200,
            "message": "success",
            "data": {
                "id": 1,
                "name": "Java基础",
                "parent_id": null,
                "level": 1,
                "keywords": [...],
                "ast_template": {...}
            }
        }
    """
    log.info(f"[GET] /api/knowledge/{kp_id} - 开始获取知识点详情")

    try:
        service = get_knowledge_service()
        kp_data = service.get_by_id(kp_id)

        if not kp_data:
            log.warning(f"[GET] /api/knowledge/{kp_id} - 知识点不存在")
            raise NotFoundException(
                message=f"知识点 {kp_id} 不存在",
                error=f"Knowledge point with id {kp_id} not found"
            )

        log.info(f"[GET] /api/knowledge/{kp_id} - 成功获取知识点: {kp_data.get('name')}")

        return jsonify({
            "code": 200,
            "message": "success",
            "data": kp_data
        })
    except NotFoundException:
        raise
    except Exception as e:
        log.error(f"[GET] /api/knowledge/{kp_id} - 异常: {str(e)}", exc_info=True)
        raise


@api_bp.route('/knowledge/<int:parent_id>/children', methods=['GET'])
def get_knowledge_children(parent_id: int):
    """
    获取指定知识点的子节点
    ---
    GET /api/knowledge/{parent_id}/children
    
    Path Parameters:
        parent_id: 父节点 ID
    
    Response:
        {
            "code": 200,
            "message": "success",
            "data": [
                {
                    "id": 2,
                    "name": "变量与数据类型",
                    "parent_id": 1,
                    "level": 2,
                    "keywords": [...]
                }
            ]
        }
    """
    log.info(f"[GET] /api/knowledge/{parent_id}/children - 开始获取子节点")

    try:
        service = get_knowledge_service()
        children = service.get_children(parent_id)

        log.info(f"[GET] /api/knowledge/{parent_id}/children - 成功获取 {len(children)} 个子节点")

        return jsonify({
            "code": 200,
            "message": "success",
            "data": children
        })
    except Exception as e:
        log.error(f"[GET] /api/knowledge/{parent_id}/children - 异常: {str(e)}", exc_info=True)
        raise


def _count_nodes(tree: list) -> int:
    """递归统计树节点数量"""
    count = 0
    for node in tree:
        count += 1
        if node.get('children'):
            count += _count_nodes(node['children'])
    return count
