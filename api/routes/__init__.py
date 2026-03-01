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

# 导入独立路由蓝图
from api.routes.system import system_bp
from api.routes.auth import auth_bp
from api.routes.user import user_bp


def register_routes(app):
    """
    注册所有路由蓝图到 Flask 应用
    :param app: Flask 应用实例
    """
    app.register_blueprint(api_bp)
    app.register_blueprint(system_bp)  # 系统路由（健康检查、指标）
    app.register_blueprint(auth_bp)    # 认证路由（注册、登录、刷新）
    app.register_blueprint(user_bp)    # 用户路由（历史、收藏）


__all__ = [
    "api_bp",
    "auth_bp",
    "user_bp",
    "register_routes",
]
