"""
Request Logging Middleware

Logs all incoming requests and their responses for observability.

Log format:
- Before request: [timestamp] [IP] METHOD /path
- After request: [timestamp] [IP] METHOD /path -> STATUS (response_time ms)

Author: System Refactoring v1.3.0
Created: 2026-01-24
Updated: 2026-03-01 (Added request/response body logging with sanitization)
"""

import time
from flask import request, g

from lib.globals import api_logger as logger
from lib.utils.sanitize import sanitize_for_log


def init_request_logging(app):
    """
    Initialize request logging middleware.

    Args:
        app: Flask application instance
    """
    @app.before_request
    def log_request_start():
        """Log incoming request."""
        g.start_time = time.time()

        # Get client IP (handle proxy headers)
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()

        method = request.method
        path = request.path

        logger.info(f"[{client_ip}] {method} {path}")

        # Log request body at DEBUG level (sanitized)
        if request.is_json and logger.isEnabledFor(10):  # DEBUG level
            try:
                body = request.get_json(silent=True)
                if body:
                    safe_body = sanitize_for_log(body)
                    logger.debug(f"[{client_ip}] {method} {path} - body: {safe_body}")
            except Exception:
                pass  # Ignore JSON parsing errors

    @app.after_request
    def log_request_end(response):
        """Log response."""
        try:
            if hasattr(g, 'start_time'):
                response_time_ms = round((time.time() - g.start_time) * 1000, 2)

                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                if client_ip and ',' in client_ip:
                    client_ip = client_ip.split(',')[0].strip()

                method = request.method
                path = request.path
                status = response.status_code

                # Skip detailed logging for SSE streams (avoid memory issues)
                is_sse = response.content_type and 'text/event-stream' in response.content_type
                if is_sse:
                    logger.info(f"[{client_ip}] {method} {path} -> {status} (SSE stream)")
                    return response

                # Use different log levels based on status code
                if status >= 500:
                    logger.error(f"[{client_ip}] {method} {path} -> {status} ({response_time_ms}ms)")
                elif status >= 400:
                    logger.warning(f"[{client_ip}] {method} {path} -> {status} ({response_time_ms}ms)")
                else:
                    logger.info(f"[{client_ip}] {method} {path} -> {status} ({response_time_ms}ms)")

                # Log response body at DEBUG level in debug mode (sanitized)
                if app.debug and response.is_json and logger.isEnabledFor(10):
                    try:
                        body = response.get_json(silent=True)
                        if body:
                            safe_body = sanitize_for_log(body)
                            logger.debug(f"[{client_ip}] {method} {path} - response: {safe_body}")
                    except Exception:
                        pass  # Ignore JSON parsing errors

        except Exception as e:
            logger.error(f"Failed to log request: {e}")

        return response
