"""
System Health and Metrics API Routes

Provides operational endpoints for monitoring service health and performance.

Endpoints:
    GET /api/health - Health check with database connectivity
    GET /api/metrics - Runtime metrics and statistics

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

from flask import Blueprint, jsonify
from datetime import datetime

from lib.client.db import MySQLClient
from lib.globals import api_logger as logger
from config import DB_NAME


system_bp = Blueprint('system', __name__)


@system_bp.route('/api/health', methods=['GET'])
def health_check():
    """
    Service health check endpoint.

    Checks:
    - API service is running
    - Database connection is working

    Returns:
        {
            "status": "healthy" | "unhealthy",
            "database": "connected" | "disconnected",
            "timestamp": "2026-01-24T10:30:00.000Z"
        }

    Status Codes:
        200: Service is healthy
        503: Service is unhealthy (database connection failed)
    """
    try:
        # Test database connection
        client = MySQLClient(db=DB_NAME)

        # Use fetch_one to test connection
        result = client.fetch_one("SELECT 1 as test")

        if result:
            # Database connection successful
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }), 200
        else:
            raise Exception("Query returned None")

    except Exception as e:
        logger.error(f"Health check failed: {e}")

        # Database connection failed
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 503


@system_bp.route('/api/metrics', methods=['GET'])
def get_metrics():
    """
    Runtime metrics endpoint.

    Returns:
        {
            "uptime_seconds": 3600,
            "requests": {
                "total": 1234,
                "endpoints": {
                    "/api/match": 500,
                    "/api/knowledge/tree": 300
                }
            },
            "performance": {
                "avg_response_time_ms": 45.2,
                "p95_response_time_ms": 120.0
            },
            "database": {
                "pool_size": 10,
                "active_connections": 3
            }
        }

    Status Codes:
        200: Metrics retrieved successfully
        500: Failed to retrieve metrics
    """
    try:
        from api.middleware.metrics import get_metrics_data

        metrics = get_metrics_data()

        return jsonify(metrics), 200

    except Exception as e:
        logger.error(f"Failed to retrieve metrics: {e}")

        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500
