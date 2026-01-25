"""
Request Metrics Tracking Middleware

Tracks API request statistics including:
- Request counts per endpoint
- Response times (average, p95, p99)
- Error rates
- Uptime

Thread-safe implementation using threading.Lock.

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import time
import threading
from datetime import datetime
from typing import Dict, List
from flask import request, g


# Global metrics storage
_metrics_lock = threading.Lock()
_metrics = {
    "start_time": datetime.utcnow(),
    "requests_total": 0,
    "requests_by_endpoint": {},  # {endpoint: count}
    "response_times": [],  # List of response times in ms
    "errors_total": 0,
    "errors_by_status": {}  # {status_code: count}
}


def init_metrics_middleware(app):
    """
    Initialize metrics tracking middleware.

    Args:
        app: Flask application instance
    """
    @app.before_request
    def before_request():
        """Record request start time."""
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        """Track request metrics after response."""
        try:
            # Calculate response time
            if hasattr(g, 'start_time'):
                response_time_ms = (time.time() - g.start_time) * 1000

                with _metrics_lock:
                    # Increment total request count
                    _metrics["requests_total"] += 1

                    # Track endpoint request count
                    endpoint = request.endpoint or "unknown"
                    _metrics["requests_by_endpoint"][endpoint] = (
                        _metrics["requests_by_endpoint"].get(endpoint, 0) + 1
                    )

                    # Track response time (keep last 1000 entries)
                    _metrics["response_times"].append(response_time_ms)
                    if len(_metrics["response_times"]) > 1000:
                        _metrics["response_times"].pop(0)

                    # Track errors
                    status_code = response.status_code
                    if status_code >= 400:
                        _metrics["errors_total"] += 1
                        _metrics["errors_by_status"][status_code] = (
                            _metrics["errors_by_status"].get(status_code, 0) + 1
                        )

        except Exception:
            # Silently ignore metrics tracking errors
            pass

        return response


def get_metrics_data() -> Dict:
    """
    Get current metrics snapshot.

    Returns:
        Dictionary containing all metrics data
    """
    with _metrics_lock:
        # Calculate uptime
        uptime_seconds = (datetime.utcnow() - _metrics["start_time"]).total_seconds()

        # Calculate response time statistics
        response_times = _metrics["response_times"]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # Calculate percentiles
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)

        p95_response_time = sorted_times[p95_index] if sorted_times else 0
        p99_response_time = sorted_times[p99_index] if sorted_times else 0

        # Build response
        metrics = {
            "uptime_seconds": round(uptime_seconds, 2),
            "requests": {
                "total": _metrics["requests_total"],
                "endpoints": dict(_metrics["requests_by_endpoint"])
            },
            "performance": {
                "avg_response_time_ms": round(avg_response_time, 2),
                "p95_response_time_ms": round(p95_response_time, 2),
                "p99_response_time_ms": round(p99_response_time, 2),
                "samples": len(response_times)
            },
            "errors": {
                "total": _metrics["errors_total"],
                "by_status_code": dict(_metrics["errors_by_status"])
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        return metrics


def reset_metrics():
    """
    Reset all metrics (useful for testing).
    """
    with _metrics_lock:
        _metrics["start_time"] = datetime.utcnow()
        _metrics["requests_total"] = 0
        _metrics["requests_by_endpoint"].clear()
        _metrics["response_times"].clear()
        _metrics["errors_total"] = 0
        _metrics["errors_by_status"].clear()
