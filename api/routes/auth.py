"""
Authentication Routes

Provides user registration, login, and token refresh endpoints.

Endpoints:
- POST /api/auth/register - Register new user
- POST /api/auth/login - Login and get tokens
- POST /api/auth/refresh - Refresh access token

Author: Iteration 2 - User Authentication
Created: 2026-03-01
"""

from flask import Blueprint, jsonify, request

from api.schemas.auth import RegisterRequest, LoginRequest, RefreshRequest
from api.middleware.error_handler import BadRequestException
from lib.globals import api_logger as log

# Blueprint with /api/auth prefix
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Lazy-load AuthService singleton
_auth_service = None


def get_auth_service():
    """Get AuthService singleton (lazy initialization)"""
    global _auth_service
    if _auth_service is None:
        from src.services.auth_service import AuthService
        _auth_service = AuthService()
    return _auth_service


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.

    Request body:
        - username: str (3-50 chars, alphanumeric and underscore)
        - password: str (8-128 chars)
        - email: str (optional, valid email format)

    Returns:
        201: Registration successful
        400: Validation error or username already exists
    """
    try:
        data = request.get_json()
        req = RegisterRequest(**data)
    except Exception as e:
        raise BadRequestException(message="Invalid request data", error=str(e))

    auth_service = get_auth_service()

    try:
        user = auth_service.register(
            username=req.username,
            password=req.password,
            email=req.email
        )
        log.info(f"[POST] /api/auth/register - User registered: {req.username}")

        return jsonify({
            "code": 201,
            "message": "Registration successful",
            "data": {
                "id": user['id'],
                "username": user['username'],
                "email": user.get('email'),
                "role": user.get('role', 'user')
            }
        }), 201

    except BadRequestException:
        raise
    except Exception as e:
        log.error(f"[POST] /api/auth/register - Registration failed: {e}")
        raise BadRequestException(message="Registration failed", error=str(e))


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login and get access/refresh tokens.

    Request body:
        - username: str
        - password: str

    Returns:
        200: Login successful with tokens
        401: Invalid credentials
    """
    try:
        data = request.get_json()
        req = LoginRequest(**data)
    except Exception as e:
        raise BadRequestException(message="Invalid request data", error=str(e))

    auth_service = get_auth_service()
    tokens = auth_service.login(req.username, req.password)

    log.info(f"[POST] /api/auth/login - User logged in: {req.username}")

    return jsonify({
        "code": 200,
        "message": "Login successful",
        "data": tokens
    })


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Refresh access token using refresh token.

    Request body:
        - refresh_token: str

    Returns:
        200: New access token
        401: Invalid or expired refresh token
    """
    try:
        data = request.get_json()
        req = RefreshRequest(**data)
    except Exception as e:
        raise BadRequestException(message="Invalid request data", error=str(e))

    auth_service = get_auth_service()
    tokens = auth_service.refresh_token(req.refresh_token)

    log.debug("[POST] /api/auth/refresh - Token refreshed")

    return jsonify({
        "code": 200,
        "message": "Token refreshed",
        "data": tokens
    })
