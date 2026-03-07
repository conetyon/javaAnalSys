# api/middleware/error_handler.py
"""
统一异常处理中间件
"""
from flask import Flask, jsonify, request
from pydantic import ValidationError
from lib.globals import api_logger as log


class ApiException(Exception):
    """自定义 API 异常"""

    def __init__(self, message: str, code: int = 400, error: str = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.error = error


class NotFoundException(ApiException):
    """资源未找到异常"""

    def __init__(self, message: str = "资源未找到", error: str = None):
        super().__init__(message, code=404, error=error)


class BadRequestException(ApiException):
    """请求参数错误异常"""

    def __init__(self, message: str = "请求参数错误", error: str = None):
        super().__init__(message, code=400, error=error)


class InternalServerException(ApiException):
    """服务器内部错误异常"""

    def __init__(self, message: str = "服务器内部错误", error: str = None):
        super().__init__(message, code=500, error=error)


class UnauthorizedException(ApiException):
    """未授权访问异常"""

    def __init__(self, message: str = "未授权访问", error: str = None):
        super().__init__(message, code=401, error=error)


class TooManyRequestsException(ApiException):
    """配额耗尽或请求过于频繁异常"""

    def __init__(
        self,
        message: str = "请求过于频繁",
        error: str = None,
        reset_at: str = None,
        retry_after: int = None
    ):
        super().__init__(message, code=429, error=error)
        self.reset_at = reset_at
        self.retry_after = retry_after


def register_error_handlers(app: Flask):
    """
    注册全局异常处理器
    :param app: Flask 应用实例
    """

    @app.errorhandler(ApiException)
    def handle_api_exception(e: ApiException):
        """处理自定义 API 异常"""
        log.warning(f"[{request.method}] {request.path} - ApiException: {e.message}")
        response = {
            "code": e.code,
            "message": e.message,
        }
        if e.error:
            response["error"] = e.error
        return jsonify(response), e.code

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        """处理 Pydantic 校验异常"""
        log.warning(f"[{request.method}] {request.path} - ValidationError: {str(e)}")
        errors = []
        for error in e.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(f"{field}: {error['msg']}")
        return jsonify({
            "code": 422,
            "message": "请求参数校验失败",
            "error": "; ".join(errors)
        }), 422

    @app.errorhandler(400)
    def handle_bad_request(e):
        """处理 400 错误"""
        log.warning(f"[{request.method}] {request.path} - Bad Request: {str(e)}")
        return jsonify({
            "code": 400,
            "message": "请求格式错误",
            "error": str(e)
        }), 400

    @app.errorhandler(401)
    def handle_unauthorized(e):
        """处理原生 401 错误（如 abort(401)）"""
        log.warning(f"[{request.method}] {request.path} - Unauthorized: {str(e)}")
        return jsonify({
            "code": 401,
            "message": "未授权访问",
            "error": str(e.description) if hasattr(e, 'description') else str(e)
        }), 401

    @app.errorhandler(TooManyRequestsException)
    def handle_too_many_requests(e: TooManyRequestsException):
        """处理 429 配额/限流异常"""
        log.warning(f"[{request.method}] {request.path} - TooManyRequests: {e.message}")
        response = {
            "code": 429,
            "message": e.message,
        }
        if e.error:
            response["error"] = e.error
        if e.reset_at:
            response["reset_at"] = e.reset_at
        if e.retry_after:
            response["retry_after"] = e.retry_after
        return jsonify(response), 429

    @app.errorhandler(404)
    def handle_not_found(e):
        """处理 404 错误"""
        log.info(f"[{request.method}] {request.path} - Not Found")
        return jsonify({
            "code": 404,
            "message": "接口不存在",
            "error": f"路径 {request.path} 未找到"
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        """处理 405 错误"""
        log.warning(f"[{request.method}] {request.path} - Method Not Allowed")
        return jsonify({
            "code": 405,
            "message": "请求方法不允许",
            "error": f"路径 {request.path} 不支持 {request.method} 方法"
        }), 405

    @app.errorhandler(500)
    def handle_internal_error(e):
        """处理 500 错误"""
        log.error(f"[{request.method}] {request.path} - Internal Error: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": "服务器内部错误",
            "error": str(e)
        }), 500

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """处理未捕获的异常"""
        log.error(f"[{request.method}] {request.path} - Unhandled Exception: {str(e)}", exc_info=True)
        return jsonify({
            "code": 500,
            "message": "服务器内部错误",
            "error": str(e)
        }), 500
