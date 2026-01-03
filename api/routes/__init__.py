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


def register_routes(app):
    """
    注册所有路由蓝图到 Flask 应用
    :param app: Flask 应用实例
    """
    app.register_blueprint(api_bp)


__all__ = [
    "api_bp",
    "register_routes",
]
