# api/__init__.py
"""
API 模块
Flask 应用工厂模式
"""
from flask import Flask
from flask_cors import CORS

from api.routes import register_routes
from api.middleware import register_error_handlers
from api.middleware.metrics import init_metrics_middleware
from api.middleware.request_logger import init_request_logging
from lib.globals import api_logger as log
from lib.background_jobs import start_worker


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

    # 注册中间件
    init_metrics_middleware(app)
    init_request_logging(app)

    # 注册错误处理器
    register_error_handlers(app)

    # 注册路由
    register_routes(app)

    # 启动后台任务队列工作线程
    start_worker()

    # 根路由 - 健康检查
    @app.route('/')
    def index():
        return {
            "code": 200,
            "message": "Java Knowledge Matching API",
            "version": "1.3.0",
            "endpoints": {
                "health": "GET /api/health",
                "metrics": "GET /api/metrics",
                "knowledge_tree": "GET /api/knowledge/tree",
                "knowledge_list": "GET /api/knowledge/list",
                "knowledge_detail": "GET /api/knowledge/{id}",
                "match": "POST /api/match",
                "batch_match": "POST /api/match/batch",
                "composite_match": "POST /api/match/composite",
                "match_health": "GET /api/match/health",
                "bulk_import": "POST /api/bulk-import",
                "bulk_import_status": "GET /api/bulk-import/{job_id}"
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
