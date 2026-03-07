"""
User Routes

Provides user-related endpoints: match history and favorites.

Endpoints:
- GET /api/user/history - Get match history (paginated)
- GET /api/user/favorites - Get favorites (paginated)
- GET /api/user/favorites/ids - Get all favorited snippet IDs
- POST /api/user/favorites - Add favorite
- DELETE /api/user/favorites - Remove favorite

Author: Iteration 3 - Advanced Features
Created: 2026-03-01
"""

from flask import Blueprint, jsonify, request, g

from api.schemas.user import (
    HistoryListRequest,
    FavoritesListRequest,
    AddFavoriteRequest,
    RemoveFavoriteRequest
)
from api.middleware.auth import require_auth
from api.middleware.error_handler import BadRequestException
from lib.globals import api_logger as log

# Blueprint with /api/user prefix
user_bp = Blueprint('user', __name__, url_prefix='/api/user')

# Lazy-load UserService singleton
_user_service = None


def get_user_service():
    """Get UserService singleton (lazy initialization)"""
    global _user_service
    if _user_service is None:
        from src.services.user_service import UserService
        _user_service = UserService()
    return _user_service


# ============== History ==============

@user_bp.route('/history', methods=['GET'])
@require_auth
def get_history():
    """
    Get match history for current user (paginated).

    Query params:
        - page: Page number (default 1)
        - page_size: Items per page (default 10, max 50)

    Returns:
        200: Paginated history list
    """
    try:
        req = HistoryListRequest(
            page=int(request.args.get('page', 1)),
            page_size=int(request.args.get('page_size', 10))
        )
    except Exception as e:
        raise BadRequestException(message="Invalid request parameters", error=str(e))

    user_service = get_user_service()
    items, total = user_service.get_history(
        user_id=g.user_id,
        page=req.page,
        page_size=req.page_size
    )

    log.debug(f"[GET] /api/user/history - user={g.user_id}, page={req.page}, total={total}")

    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": req.page,
            "page_size": req.page_size
        }
    })


# ============== Favorites ==============

@user_bp.route('/favorites', methods=['GET'])
@require_auth
def get_favorites():
    """
    Get favorites for current user (paginated).

    Query params:
        - page: Page number (default 1)
        - page_size: Items per page (default 10, max 50)

    Returns:
        200: Paginated favorites list with snippet details
    """
    try:
        req = FavoritesListRequest(
            page=int(request.args.get('page', 1)),
            page_size=int(request.args.get('page_size', 10))
        )
    except Exception as e:
        raise BadRequestException(message="Invalid request parameters", error=str(e))

    user_service = get_user_service()
    items, total = user_service.get_favorites(
        user_id=g.user_id,
        page=req.page,
        page_size=req.page_size
    )

    log.debug(f"[GET] /api/user/favorites - user={g.user_id}, page={req.page}, total={total}")

    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": req.page,
            "page_size": req.page_size
        }
    })


@user_bp.route('/favorites/ids', methods=['GET'])
@require_auth
def get_favorite_ids():
    """
    Get all favorited snippet IDs for current user.

    Lightweight endpoint for frontend to check favorite status.

    Returns:
        200: Array of snippet IDs
    """
    user_service = get_user_service()
    ids = user_service.get_favorite_ids(g.user_id)

    log.debug(f"[GET] /api/user/favorites/ids - user={g.user_id}, count={len(ids)}")

    return jsonify({
        "code": 200,
        "message": "success",
        "data": ids
    })


@user_bp.route('/favorites', methods=['POST'])
@require_auth
def add_favorite():
    """
    Add a code snippet to favorites.

    Request body:
        - snippet_id: Code snippet ID

    Returns:
        200: Added successfully
        200: Already favorited (idempotent)
    """
    try:
        data = request.get_json()
        req = AddFavoriteRequest(**data)
    except Exception as e:
        raise BadRequestException(message="Invalid request data", error=str(e))

    user_service = get_user_service()
    added = user_service.add_favorite(g.user_id, req.snippet_id)

    log.info(f"[POST] /api/user/favorites - user={g.user_id}, snippet={req.snippet_id}, added={added}")

    return jsonify({
        "code": 200,
        "message": "Added to favorites" if added else "Already in favorites",
        "data": {"added": added}
    })


@user_bp.route('/favorites', methods=['DELETE'])
@require_auth
def remove_favorite():
    """
    Remove a code snippet from favorites.

    Request body:
        - snippet_id: Code snippet ID

    Returns:
        200: Removed successfully
        200: Not in favorites (idempotent)
    """
    try:
        data = request.get_json()
        req = RemoveFavoriteRequest(**data)
    except Exception as e:
        raise BadRequestException(message="Invalid request data", error=str(e))

    user_service = get_user_service()
    removed = user_service.remove_favorite(g.user_id, req.snippet_id)

    log.info(f"[DELETE] /api/user/favorites - user={g.user_id}, snippet={req.snippet_id}, removed={removed}")

    return jsonify({
        "code": 200,
        "message": "Removed from favorites" if removed else "Not in favorites",
        "data": {"removed": removed}
    })


# ============== Quota ==============

# Lazy-load QuotaService singleton
_quota_service = None


def get_quota_service():
    """Get QuotaService singleton (lazy initialization)"""
    global _quota_service
    if _quota_service is None:
        from src.services.quota_service import QuotaService
        _quota_service = QuotaService()
    return _quota_service


@user_bp.route('/quota', methods=['GET'])
@require_auth
def get_quota():
    """
    Get AI explanation quota for current user.

    Returns:
        200: Quota information
            - daily_limit: Daily request limit (-1 for unlimited)
            - used_today: Requests used today
            - remaining: Remaining requests (-1 for unlimited)
            - reset_at: Next reset time (ISO format with timezone)
            - unlimited: Whether user has unlimited quota (admin)
    """
    user_role = getattr(g, 'user_role', 'user')
    quota_service = get_quota_service()
    quota_info = quota_service.get_quota_info(g.user_id, user_role)

    log.debug(f"[GET] /api/user/quota - user={g.user_id}, remaining={quota_info.get('remaining')}")

    return jsonify({
        "code": 200,
        "message": "success",
        "data": quota_info
    })
