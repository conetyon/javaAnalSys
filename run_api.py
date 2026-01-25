#!/usr/bin/env python
"""
API Service Startup Entry Point

Starts the Flask API server with comprehensive validation.

Features:
- Pre-flight validation (config, database connection)
- Fail-fast on critical errors
- Clear error messages with troubleshooting hints
- CLI argument parsing

Usage:
    python run_api.py                      # Default: http://0.0.0.0:5000
    python run_api.py --port 8080          # Custom port
    python run_api.py --host 127.0.0.1     # Custom host
    python run_api.py --debug              # Enable debug mode

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import sys
import argparse
from pathlib import Path

from lib.globals import api_logger as logger


def validate_environment():
    """
    Validate environment before starting API server.

    Checks:
    1. Configuration file exists
    2. Database connection works
    3. Required tables exist

    Raises:
        SystemExit: If validation fails (exit code 1)
    """
    print("\n" + "=" * 70)
    print("API STARTUP VALIDATION")
    print("=" * 70)

    # Step 1: Check configuration file
    print("\n[1/3] Checking configuration...")

    config_file = Path("config/db.yaml")
    if not config_file.exists():
        print(f"[FAIL] Configuration file not found: {config_file}")
        print("\nTroubleshooting:")
        print("  1. Ensure config/db.yaml exists")
        print("  2. Copy from config/db.yaml.example if needed")
        print("  3. Configure database credentials")
        sys.exit(1)

    print(f"[OK] Configuration file found: {config_file}")

    # Step 2: Test database connection
    print("\n[2/3] Testing database connection...")

    try:
        from lib.client.db import MySQLClient
        from config import DB_NAME

        client = MySQLClient(db=DB_NAME)

        # Use fetch_one method instead of direct cursor access
        result = client.fetch_one("SELECT VERSION() as version")
        version = result['version'] if result else "Unknown"

        print(f"[OK] Database connected: MySQL {version}")

    except Exception as e:
        print(f"[FAIL] Database connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check database credentials in config/db.yaml")
        print("  2. Ensure MySQL server is running")
        print("  3. Verify database exists: CREATE DATABASE IF NOT EXISTS javalearningsys")
        print("  4. Test connection: mysql -u <user> -p -h <host>")
        sys.exit(1)

    # Step 3: Check required tables
    print("\n[3/3] Validating database schema...")

    required_tables = [
        "knowledge_points",
        "code_files",
        "code_snippets",
        "experiment_runs",
        "bulk_import_jobs"
    ]

    try:
        # Use fetch_all method to get tables
        with client as conn:
            cursor = conn._conn.cursor()
            cursor.execute("SHOW TABLES")
            existing_tables = [row[0] for row in cursor.fetchall()]

        missing_tables = [t for t in required_tables if t not in existing_tables]

        if missing_tables:
            print(f"[FAIL] Missing tables: {', '.join(missing_tables)}")
            print("\nTroubleshooting:")
            print("  1. Run database initialization:")
            print("     python scripts/init_data/run_all.py")
            print("  2. Or manually run migrations:")
            print("     python scripts/init_data/init_schema.py")
            sys.exit(1)

        print(f"[OK] All required tables exist ({len(required_tables)} tables)")

    except Exception as e:
        print(f"[FAIL] Schema validation failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("[OK] ALL VALIDATION PASSED")
    print("=" * 70 + "\n")


def parse_args():
    """
    Parse command-line arguments.

    Returns:
        Namespace with parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Java Knowledge Matching API Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_api.py                      # Start with defaults (0.0.0.0:5000)
  python run_api.py --port 8080          # Use custom port
  python run_api.py --host 127.0.0.1     # Bind to localhost only
  python run_api.py --debug              # Enable debug mode (hot reload)
  python run_api.py --skip-validation    # Skip startup validation (not recommended)
        """
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Server host address (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Server port (default: 5000)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (hot reload, verbose errors)"
    )

    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip startup validation (not recommended)"
    )

    return parser.parse_args()


def print_api_info(host: str, port: int, debug: bool):
    """
    Print API server information.

    Args:
        host: Server host address
        port: Server port
        debug: Debug mode enabled
    """
    print("\n" + "=" * 70)
    print("JAVA KNOWLEDGE MATCHING API SERVER")
    print("=" * 70)
    print(f"\nServer: http://{host}:{port}")
    print(f"Debug mode: {'ENABLED' if debug else 'DISABLED'}")
    print("\nAvailable Endpoints:")
    print("  GET  /                              - Service information")
    print("  GET  /health                        - Health check")
    print("  GET  /api/health                    - Detailed health check")
    print("  GET  /api/metrics                   - Runtime metrics")
    print("  GET  /api/knowledge/tree            - Knowledge point tree")
    print("  GET  /api/knowledge/list            - Knowledge point list")
    print("  GET  /api/knowledge/{id}            - Knowledge point details")
    print("  GET  /api/knowledge/{id}/children   - Child knowledge points")
    print("  POST /api/match                     - Single KP matching")
    print("  POST /api/match/batch               - Batch KP matching")
    print("  POST /api/match/composite           - Composite KP matching")
    print("  GET  /api/match/health              - Matching service health")
    print("  POST /api/bulk-import               - Start bulk import job")
    print("  GET  /api/bulk-import/{job_id}      - Query import job status")
    print("\n" + "-" * 70 + "\n")


def main():
    """
    Main entry point.
    """
    args = parse_args()

    # Run validation (unless explicitly skipped)
    if not args.skip_validation:
        try:
            validate_environment()
        except KeyboardInterrupt:
            print("\n\n[INFO] Validation interrupted by user")
            sys.exit(0)

    # Print server information
    print_api_info(args.host, args.port, args.debug)

    # Create Flask app
    try:
        from api import create_app
        app = create_app()
    except Exception as e:
        logger.error(f"Failed to create Flask app: {e}", exc_info=True)
        print(f"\n[ERROR] Failed to create Flask app: {e}")
        print("\nTroubleshooting:")
        print("  1. Check logs in api/logs/ for detailed error")
        print("  2. Verify all dependencies installed: pip install -r requirements.txt")
        print("  3. Ensure database is properly initialized")
        sys.exit(1)

    # Start server
    logger.info(f"Starting API server on {args.host}:{args.port} (debug={args.debug})")

    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
    except KeyboardInterrupt:
        print("\n\n[INFO] Server stopped by user")
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        print(f"\n[ERROR] Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
