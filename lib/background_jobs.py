"""
Background Job Queue for Async Operations

Provides lightweight async job processing using Python's queue and threading.
No external dependencies (Redis/Celery) required.

Features:
- Single worker thread (sequential processing)
- Job status tracking in database
- Progress updates during execution
- Error handling and recovery

Usage:
    from lib.background_jobs import start_worker, submit_import_job

    # Start worker thread (call once on app startup)
    start_worker()

    # Submit import job
    job_id = submit_import_job("code_repos/spring-boot")

    # Query job status from bulk_import_jobs table

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import queue
import threading
import time
import json
from datetime import datetime
from typing import Optional
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.client.db import MySQLClient
from lib.globals import core_logger as logger
from config import DB_NAME


# Global job queue
job_queue = queue.Queue()

# Worker thread reference
worker_thread: Optional[threading.Thread] = None


class ImportJob:
    """
    Represents a bulk import job.
    """

    def __init__(self, job_id: str, repo_path: str):
        """
        Initialize import job.

        Args:
            job_id: Unique job identifier
            repo_path: Path to repository to import
        """
        self.job_id = job_id
        self.repo_path = repo_path
        self.client = MySQLClient(db=DB_NAME)

    def update_status(self, status: str, **kwargs):
        """
        Update job status in database.

        Args:
            status: Job status (queued, running, completed, failed)
            **kwargs: Additional fields to update (progress, total_files, etc.)
        """
        try:
            # Build UPDATE statement dynamically
            fields = {"status": status, "updated_at": datetime.now()}
            fields.update(kwargs)

            set_clause = ", ".join([f"{k} = %s" for k in fields.keys()])
            values = list(fields.values())
            values.append(self.job_id)

            sql = f"UPDATE bulk_import_jobs SET {set_clause} WHERE job_id = %s"

            # Use MySQLClient.execute() which auto-commits
            self.client.execute(sql, tuple(values))

        except Exception as e:
            logger.error(f"Failed to update job status: {e}")

    def execute(self):
        """
        Execute the import job.
        Updates progress in database during execution.
        """
        logger.info(f"[Job {self.job_id}] Starting import from {self.repo_path}")

        # Update status to running
        self.update_status("running")

        try:
            # Import the import_code_repos module here to avoid circular imports
            from scripts._internal.import_utils.import_code_repos import import_repository

            # Custom progress callback
            def progress_callback(processed, total, snippets_imported):
                self.update_status(
                    "running",
                    progress=processed,
                    total_files=total,
                    snippets_imported=snippets_imported
                )

            # Execute import
            # Note: We'll need to modify import_repository to accept progress callback
            # For now, just call it directly
            progress = import_repository(self.repo_path, show_progress=False)

            # Mark as completed
            self.update_status(
                "completed",
                progress=progress.processed_files,
                total_files=progress.total_files,
                snippets_imported=progress.inserted_snippets + progress.replaced_snippets,
                errors=json.dumps(progress.errors) if progress.errors else None
            )

            logger.info(f"[Job {self.job_id}] Completed successfully")

        except Exception as e:
            logger.error(f"[Job {self.job_id}] Failed: {e}")

            # Mark as failed
            self.update_status(
                "failed",
                errors=json.dumps([{"error": str(e)}])
            )

    def mark_completed(self):
        """Mark job as completed (called after successful execution)."""
        self.update_status("completed")

    def mark_failed(self, error: str):
        """
        Mark job as failed.

        Args:
            error: Error message
        """
        self.update_status(
            "failed",
            errors=json.dumps([{"error": error}])
        )


def worker():
    """
    Background worker thread.
    Continuously processes jobs from the queue.
    """
    logger.info("[Worker] Background worker thread started")

    while True:
        try:
            # Wait for job (blocking)
            job = job_queue.get()

            logger.info(f"[Worker] Processing job: {job.job_id}")

            # Execute job
            try:
                job.execute()
            except Exception as e:
                logger.error(f"[Worker] Job execution failed: {e}")
                try:
                    job.mark_failed(str(e))
                except Exception:
                    pass  # Ignore errors in error handling

            # Mark job as done
            job_queue.task_done()

        except Exception as e:
            logger.error(f"[Worker] Worker thread error: {e}")
            time.sleep(1)  # Prevent tight loop on errors


def start_worker():
    """
    Start the background worker thread.
    Call this once on application startup.
    """
    global worker_thread

    if worker_thread is not None and worker_thread.is_alive():
        logger.warning("[Worker] Worker thread already running")
        return

    worker_thread = threading.Thread(target=worker, daemon=True, name="ImportWorker")
    worker_thread.start()

    logger.info("[Worker] Background worker thread initialized")


def submit_import_job(repo_path: str) -> str:
    """
    Submit a bulk import job to the queue.

    Args:
        repo_path: Path to repository to import

    Returns:
        Job ID
    """
    # Generate job ID
    job_id = f"import-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:20]}"

    # Create job record in database
    client = MySQLClient(db=DB_NAME)

    client.execute(
        """
        INSERT INTO bulk_import_jobs (job_id, repo_path, status)
        VALUES (%s, %s, 'queued')
        """,
        (job_id, repo_path)
    )

    # Create job object
    job = ImportJob(job_id, repo_path)

    # Add to queue
    job_queue.put(job)

    logger.info(f"[Queue] Job {job_id} submitted")

    return job_id


def get_job_status(job_id: str) -> Optional[dict]:
    """
    Get job status from database.

    Args:
        job_id: Job ID

    Returns:
        Job status dictionary or None if not found
    """
    client = MySQLClient(db=DB_NAME)

    result = client.fetch_one(
        "SELECT * FROM bulk_import_jobs WHERE job_id = %s",
        (job_id,)
    )

    if result and result.get('errors'):
        try:
            result['errors'] = json.loads(result['errors'])
        except Exception:
            pass

    return result


# Auto-start worker if imported as module
# Comment this out if you want manual control
# start_worker()
