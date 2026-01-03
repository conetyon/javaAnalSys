# api/__init__.py
"""
API 模块
Flask 应用工厂模式
"""
from flask import Flask
from flask_cors import CORS

from api.routes import register_routes
from api.middleware import register_error_handlers
from lib.globals import api_logger as log


def create_app(config_object=None) -> Flask:
    """
    Flask 应用工厂函数
    
    :param config_object: 配置对象（可选）
    :return: Flask 应用实例
    """
    app = Flask(__name__)

    # 加载配置
    if config_object:
        app.config.from_object(config_object)

    # 默认配置
    app.config.setdefault('JSON_AS_ASCII', False)  # 支持中文
    app.config.setdefault('JSON_SORT_KEYS', False)  # 保持 JSON 键顺序

    # 启用 CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # 注册错误处理器
    register_error_handlers(app)

    # 注册路由
    register_routes(app)

    # 根路由 - 健康检查
    @app.route('/')
    def index():
        return {
            "code": 200,
            "message": "Java Knowledge Matching API",
            "version": "1.0.0",
            "endpoints": {
                "knowledge_tree": "GET /api/knowledge/tree",
                "knowledge_list": "GET /api/knowledge/list",
                "knowledge_detail": "GET /api/knowledge/{id}",
                "match": "POST /api/match",
                "batch_match": "POST /api/match/batch",
                "health": "GET /api/match/health"
            }
        }

    @app.route('/health')
    def health():
        return {"status": "healthy", "service": "java-knowledge-api"}

    log.info("Flask application created successfully")
    return app


# 为了向后兼容，保留直接导入 app 的方式
# 但推荐使用 create_app() 工厂函数
def get_app() -> Flask:
    """获取 Flask 应用实例（单例）"""
    return create_app()


__all__ = [
    "create_app",
    "get_app",
]
