# api/routes/__init__.py
"""
API 路由模块
使用 Flask Blueprint 组织路由
"""
from flask import Blueprint

# 创建主路由蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')

# 导入子路由模块（会自动注册到 api_bp）
from . import knowledge, match

# 导入批量导入蓝图（独立注册，不使用 api_bp 前缀）
from api.routes.bulk_import import bulk_import_bp

# 导入系统路由蓝图
from api.routes.system import system_bp


def register_routes(app):
    """
    注册所有路由蓝图到 Flask 应用
    :param app: Flask 应用实例
    """
    app.register_blueprint(api_bp)
    app.register_blueprint(bulk_import_bp)  # 注册批量导入路由
    app.register_blueprint(system_bp)  # 注册系统路由（健康检查、指标）


__all__ = [
    "api_bp",
    "register_routes",
]
