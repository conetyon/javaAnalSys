"""
Bulk Import API Routes

Provides API endpoints for asynchronous bulk code import.

Endpoints:
    POST /api/bulk-import - Start import job
    GET /api/bulk-import/<job_id> - Query job status

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

from flask import Blueprint, request, jsonify
from pathlib import Path

from lib.background_jobs import submit_import_job, get_job_status
from lib.globals import api_logger as logger


bulk_import_bp = Blueprint('bulk_import', __name__)


@bulk_import_bp.route('/api/bulk-import', methods=['POST'])
def start_bulk_import():
    """
    Start a bulk import job.

    Request JSON:
        {
            "repo_path": "code_repos/spring-boot"
        }

    Returns:
        {
            "job_id": "import-20260124-120000",
            "status": "queued",
            "message": "Import job started"
        }

    Status Codes:
        200: Job started successfully
        400: Invalid request (missing or invalid repo_path)
        500: Server error
    """
    try:
        # Validate request
        if not request.json:
            return jsonify({
                "error": "Request body must be JSON"
            }), 400

        repo_path = request.json.get('repo_path')

        if not repo_path:
            return jsonify({
                "error": "Missing required field: repo_path"
            }), 400

        # Check if path exists
        path = Path(repo_path)
        if not path.exists():
            return jsonify({
                "error": f"Repository path not found: {repo_path}"
            }), 400

        if not path.is_dir():
            return jsonify({
                "error": f"Repository path is not a directory: {repo_path}"
            }), 400

        # Submit job to queue
        job_id = submit_import_job(repo_path)

        logger.info(f"Bulk import job started: {job_id} for {repo_path}")

        return jsonify({
            "job_id": job_id,
            "status": "queued",
            "message": "Import job started successfully"
        }), 200

    except Exception as e:
        logger.error(f"Failed to start bulk import: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@bulk_import_bp.route('/api/bulk-import/<job_id>', methods=['GET'])
def get_bulk_import_status(job_id):
    """
    Get status of a bulk import job.

    Path Parameters:
        job_id: Job identifier

    Returns:
        {
            "job_id": "import-20260124-120000",
            "status": "running",
            "progress": 450,
            "total_files": 1000,
            "snippets_imported": 2340,
            "errors": []
        }

    Status Codes:
        200: Status retrieved successfully
        404: Job not found
        500: Server error
    """
    try:
        # Query job status from database
        job_status = get_job_status(job_id)

        if not job_status:
            return jsonify({
                "error": "Job not found",
                "job_id": job_id
            }), 404

        # Format response
        response = {
            "job_id": job_status['job_id'],
            "repo_path": job_status['repo_path'],
            "status": job_status['status'],
            "progress": job_status.get('progress', 0),
            "total_files": job_status.get('total_files', 0),
            "snippets_imported": job_status.get('snippets_imported', 0),
            "created_at": job_status['created_at'].isoformat() if job_status.get('created_at') else None,
            "updated_at": job_status['updated_at'].isoformat() if job_status.get('updated_at') else None,
            "errors": job_status.get('errors', [])
        }

        return jsonify(response), 200

    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500
