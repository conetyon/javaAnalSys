"""
Database Status Checker

Checks if database is properly initialized and ready for use.
Prints colored output and exits with appropriate status code.

Usage:
    python scripts/init_data/check_status.py

Exit codes:
    0: Database ready
    1: Database incomplete or errors

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.client.db import MySQLClient
from lib.globals import Cfg, core_logger as logger
from config import DB_NAME


# ANSI color codes (disabled on Windows to avoid encoding issues)
GREEN = ''
RED = ''
YELLOW = ''
RESET = ''
BOLD = ''


def print_status(label: str, passed: bool, details: str = ""):
    """Print status line with simple markers."""
    symbol = "[OK]" if passed else "[FAIL]"
    status = "PASS" if passed else "FAIL"
    details_str = f" ({details})" if details else ""
    print(f"  {symbol} {label}: {status}{details_str}")


def check_status():
    """
    Check database initialization status.

    Returns:
        bool: True if ready, False if incomplete
    """
    print(f"\n{'=' * 60}")
    print(f"DATABASE STATUS CHECK")
    print(f"{'=' * 60}\n")

    db_config = Cfg.db[DB_NAME]
    print(f"Database: {db_config.db} @ {db_config.host}:{db_config.port}\n")

    all_passed = True

    try:
        client = MySQLClient(db=DB_NAME)

        # Check 1: Database connection
        try:
            test_result = client.fetch_one("SELECT 1 as test")
            db_connected = test_result is not None
            print_status("Database connection", db_connected)
            all_passed = all_passed and db_connected

            if not db_connected:
                raise Exception("Cannot connect to database")

        except Exception as e:
            print_status("Database connection", False, str(e))
            all_passed = False
            print(f"\n{'=' * 60}")
            print(f"[FAIL] Cannot connect to database")
            print(f"{'=' * 60}\n")
            return False

        # Check 2: Tables exist
        required_tables = ['knowledge_points', 'code_files', 'code_snippets',
                          'experiment_runs']

        with client as conn:
            cursor = conn._conn.cursor()

            cursor.execute("SHOW TABLES")
            existing_tables = [row[0] for row in cursor.fetchall()]

            tables_ok = all(table in existing_tables for table in required_tables)
            print_status(
                "Tables exist",
                tables_ok,
                f"{len(existing_tables)} tables" if tables_ok else f"Missing: {set(required_tables) - set(existing_tables)}"
            )
            all_passed = all_passed and tables_ok

            # Check 2: Knowledge points loaded
            if 'knowledge_points' in existing_tables:
                cursor.execute("SELECT COUNT(*) FROM knowledge_points")
                kp_count = cursor.fetchone()[0]
                kp_ok = kp_count > 0
                print_status("Knowledge points", kp_ok, f"{kp_count} records")
                all_passed = all_passed and kp_ok
            else:
                print_status("Knowledge points", False, "Table missing")
                all_passed = False

            # Check 3: Code snippets analyzed
            if 'code_snippets' in existing_tables:
                cursor.execute("SELECT COUNT(*) FROM code_snippets")
                snippet_count = cursor.fetchone()[0]

                # Also check content_hash column exists
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s
                    AND TABLE_NAME = 'code_snippets'
                    AND COLUMN_NAME = 'content_hash'
                """, (db_config.db,))
                hash_column_exists = cursor.fetchone()[0] > 0

                snippets_ok = snippet_count > 0 and hash_column_exists
                details = f"{snippet_count} snippets"
                if not hash_column_exists:
                    details += ", missing content_hash column"

                print_status("Code snippets", snippets_ok, details)
                all_passed = all_passed and snippets_ok
            else:
                print_status("Code snippets", False, "Table missing")
                all_passed = False

            # Check 4: Code files exist
            if 'code_files' in existing_tables:
                cursor.execute("SELECT COUNT(*) FROM code_files")
                file_count = cursor.fetchone()[0]
                files_ok = file_count > 0
                print_status("Code files", files_ok, f"{file_count} files")
                all_passed = all_passed and files_ok
            else:
                print_status("Code files", False, "Table missing")
                all_passed = False

        print(f"\n{'=' * 60}")
        if all_passed:
            print(f"[OK] Database is ready")
        else:
            print(f"[FAIL] Database initialization incomplete")
            print(f"\nRun: python scripts/init_data/run_all.py")
        print(f"{'=' * 60}\n")

        return all_passed

    except Exception as e:
        print_status("Database connection", False, str(e))
        print(f"\n{'=' * 60}")
        print(f"[FAIL] Cannot connect to database")
        print(f"{'=' * 60}\n")
        return False


if __name__ == "__main__":
    try:
        ready = check_status()
        sys.exit(0 if ready else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
