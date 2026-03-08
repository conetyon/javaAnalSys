"""
Explain Routes

Provides AI code explanation endpoints with SSE streaming support.

Endpoints:
- POST /api/explain - Stream AI explanation for a code snippet
- POST /api/explain/chat - Stream AI response for follow-up questions

Author: Iteration 4 - Code Explanation Feature
Created: 2026-03-07
"""

import json
from flask import Blueprint, Response, request, g, stream_with_context, jsonify

from api.schemas.explain import ExplainRequest, ChatRequest
from api.middleware.auth import require_auth
from api.middleware.quota import require_quota
from api.middleware.error_handler import BadRequestException
from lib.globals import api_logger as log
from src.services.quota_service import get_quota_service
from src.services.rate_limiter import get_rate_limiter

# Blueprint with /api/explain prefix
explain_bp = Blueprint('explain', __name__, url_prefix='/api/explain')


# 处理 CORS preflight 请求（在认证之前）
@explain_bp.before_request
def handle_preflight():
    """Handle CORS preflight OPTIONS requests."""
    if request.method == 'OPTIONS':
        # 返回空响应，Flask-CORS 会添加 CORS headers
        return '', 204


# Lazy-load ExplainService singleton
_explain_service = None


def get_explain_service():
    """Get ExplainService singleton (lazy initialization)"""
    global _explain_service
    if _explain_service is None:
        from src.services.explain_service import get_explain_service as _get
        _explain_service = _get()
    return _explain_service


def _make_sse_response(generator):
    """Create SSE Response from generator."""
    return Response(
        stream_with_context(generator),
        content_type='text/event-stream; charset=utf-8',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


def _sse_format(data: dict) -> bytes:
    """Format data as SSE event (returns bytes to ensure UTF-8 encoding)."""
    # 显式编码为 UTF-8 字节，避免 Flask 默认使用 Latin-1
    text = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    return text.encode('utf-8')


@explain_bp.route('', methods=['POST', 'OPTIONS'])
@require_auth
@require_quota
def explain_snippet():
    """
    Stream AI explanation for a code snippet.

    Request body:
        - snippet_id: Code snippet ID
        - kp_id: Knowledge point ID
        - user_level: User expertise level (beginner/intermediate/advanced)

    Returns:
        SSE stream with events:
        - {"type": "content", "content": "..."} - Text chunk
        - {"type": "done", "tokens": {...}} - Completion with token usage
        - {"type": "error", "error": "..."} - Error message
    """
    log.info("[explain_snippet] Request received")

    try:
        data = request.get_json()
        log.info(f"[explain_snippet] Request data: {data}")
        req = ExplainRequest(**data)
    except Exception as e:
        log.error(f"[explain_snippet] Invalid request: {e}")
        raise BadRequestException(message="Invalid request data", error=str(e))

    user_id = g.user_id
    user_role = getattr(g, 'user_role', 'user')

    log.info(f"[POST] /api/explain - user={user_id}, role={user_role}, snippet={req.snippet_id}, kp={req.kp_id}, kp_ids={req.kp_ids}")

    # Record request for rate limiting
    rate_limiter = get_rate_limiter()
    rate_limiter.record_request(user_id)

    # 配额在成功后消耗，不在这里预扣
    quota_service = get_quota_service()

    def generate():
        log.info(f"[explain_snippet] Generator started")
        explain_service = get_explain_service()
        log.info(f"[explain_snippet] ExplainService obtained")
        chunk_count = 0
        success = False  # 追踪是否成功
        # 发送初始连接确认（防止浏览器超时）
        yield _sse_format({"type": "connected"})
        log.info(f"[explain_snippet] Sent connected event")
        try:
            for chunk in explain_service.stream_explain(
                user_id=user_id,
                snippet_id=req.snippet_id,
                kp_id=req.kp_id,
                user_level=req.user_level.value,
                kp_ids=req.kp_ids
            ):
                chunk_count += 1
                log.debug(f"[explain_snippet] Yielding chunk #{chunk_count}: type={chunk.get('type')}")
                yield _sse_format(chunk)
                # 收到 done 事件表示成功
                if chunk.get('type') == 'done':
                    success = True
            log.info(f"[explain_snippet] Completed: total chunks={chunk_count}, success={success}")
        except Exception as e:
            log.error(f"[explain_snippet] Error in generator: {e}", exc_info=True)
            yield _sse_format({"type": "error", "error": str(e)})
        finally:
            # 只有成功时才消耗配额
            if success:
                quota_service.consume_quota(user_id)
                log.info(f"[explain_snippet] Quota consumed for user={user_id}")
            else:
                log.info(f"[explain_snippet] Request failed, quota not consumed for user={user_id}")

    return _make_sse_response(generate())


@explain_bp.route('/chat', methods=['POST', 'OPTIONS'])
@require_auth
@require_quota
def chat_snippet():
    """
    Stream AI response for a follow-up question.

    Request body:
        - snippet_id: Code snippet ID
        - kp_id: Knowledge point ID
        - question: User's question
        - session_id: Optional session ID for continuing conversation

    Returns:
        SSE stream with events:
        - {"type": "session_id", "session_id": "..."} - Session ID (first event)
        - {"type": "content", "content": "..."} - Text chunk
        - {"type": "done", "tokens": {...}} - Completion with token usage
        - {"type": "error", "error": "..."} - Error message
    """
    try:
        data = request.get_json()
        req = ChatRequest(**data)
    except Exception as e:
        raise BadRequestException(message="Invalid request data", error=str(e))

    user_id = g.user_id
    user_role = getattr(g, 'user_role', 'user')

    log.info(f"[POST] /api/explain/chat - user={user_id}, snippet={req.snippet_id}, kp={req.kp_id}")

    # Record request for rate limiting
    rate_limiter = get_rate_limiter()
    rate_limiter.record_request(user_id)

    # 配额在成功后消耗
    quota_service = get_quota_service()

    def generate():
        explain_service = get_explain_service()
        success = False
        try:
            for chunk in explain_service.stream_chat(
                user_id=user_id,
                snippet_id=req.snippet_id,
                kp_id=req.kp_id,
                question=req.question,
                session_id=req.session_id,
                kp_ids=req.kp_ids
            ):
                yield _sse_format(chunk)
                if chunk.get('type') == 'done':
                    success = True
        except Exception as e:
            log.error(f"[chat_snippet] Error: {e}")
            yield _sse_format({"type": "error", "error": str(e)})
        finally:
            if success:
                quota_service.consume_quota(user_id)
                log.info(f"[chat_snippet] Quota consumed for user={user_id}")

    return _make_sse_response(generate())


@explain_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for explain service."""
    # Also check LLM client configuration
    from lib.client.llm import get_llm_client
    llm_client = get_llm_client()

    return jsonify({
        "code": 200,
        "message": "Explain service is healthy",
        "data": {
            "status": "ok",
            "llm_config": {
                "endpoint": llm_client.endpoint[:50] + "..." if llm_client.endpoint and len(llm_client.endpoint) > 50 else llm_client.endpoint,
                "model": llm_client.model,
                "has_api_key": bool(llm_client.api_key),
                "fallback_endpoint": llm_client.fallback_endpoint[:50] + "..." if llm_client.fallback_endpoint and len(llm_client.fallback_endpoint) > 50 else llm_client.fallback_endpoint,
                "fallback_model": llm_client.fallback_model,
                "has_fallback_api_key": bool(llm_client.fallback_api_key),
            }
        }
    })
