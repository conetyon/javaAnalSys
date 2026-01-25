"""
Knowledge Points Data Loader

Loads knowledge point data from kp_dml.sql into database.
Uses REPLACE INTO for strong idempotency - same data every run.

Usage:
    python scripts/init_data/load_knowledge_points.py

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import os
import sys
import re
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.client.db import MySQLClient
from lib.globals import Cfg, core_logger as logger
from config import DB_NAME


def parse_kp_dml_file(dml_file: Path):
    """
    Parse kp_dml.sql and extract INSERT statements.

    Args:
        dml_file: Path to kp_dml.sql file

    Returns:
        List of INSERT statements
    """
    print(f"Parsing {dml_file.name}...")
    logger.info(f"Parsing {dml_file.name}")

    with open(dml_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract INSERT statements (supports ON DUPLICATE KEY UPDATE syntax)
    # Pattern: INSERT INTO knowledge_points (...) VALUES (...) [ON DUPLICATE KEY UPDATE ...];
    insert_pattern = re.compile(
        r'INSERT\s+INTO\s+knowledge_points\s*\([^)]+\)\s*VALUES\s+.+?;',
        re.IGNORECASE | re.DOTALL
    )

    statements = insert_pattern.findall(content)

    print(f"Found {len(statements)} INSERT statement(s)")
    logger.info(f"Found {len(statements)} INSERT statement(s)")
    return statements


def convert_insert_to_replace(insert_stmt: str) -> str:
    """
    Convert INSERT INTO to REPLACE INTO for idempotency.

    If the statement already uses ON DUPLICATE KEY UPDATE,
    leave it as-is (it's already idempotent).

    Args:
        insert_stmt: Original INSERT statement

    Returns:
        REPLACE statement or original statement if using ON DUPLICATE KEY UPDATE
    """
    # If statement already uses ON DUPLICATE KEY UPDATE, it's idempotent
    if re.search(r'ON\s+DUPLICATE\s+KEY\s+UPDATE', insert_stmt, re.IGNORECASE):
        return insert_stmt

    # Otherwise, convert to REPLACE
    return re.sub(r'^\s*INSERT\s+INTO', 'REPLACE INTO', insert_stmt, flags=re.IGNORECASE)


def load_knowledge_points():
    """
    Load knowledge points from kp_dml.sql.
    Uses REPLACE INTO for strong idempotency.
    """
    print("=" * 60)
    print("KNOWLEDGE POINTS DATA LOADING")
    print("=" * 60)

    logger.info("=" * 60)
    logger.info("KNOWLEDGE POINTS DATA LOADING")
    logger.info("=" * 60)

    # Get database configuration
    db_config = Cfg.db[DB_NAME]
    print(f"Target database: {db_config.db}")

    # Use autocommit=False to ensure explicit commit
    client = MySQLClient(db=DB_NAME, autocommit=False)

    # Find kp_dml.sql file
    dml_file = PROJECT_ROOT / 'kp_dml.sql'
    print(f"Looking for knowledge points file: {dml_file}")

    if not dml_file.exists():
        print(f"[ERROR] Knowledge points data file not found: {dml_file}")
        logger.error(f"Knowledge points data file not found: {dml_file}")
        return False

    print(f"Found file: {dml_file.name}")

    # Parse DML file
    print("Parsing DML file...")
    try:
        insert_statements = parse_kp_dml_file(dml_file)
    except Exception as e:
        print(f"[ERROR] Failed to parse {dml_file.name}: {e}")
        logger.error(f"Failed to parse {dml_file.name}: {e}")
        return False

    if not insert_statements:
        print("[WARNING] No INSERT statements found in kp_dml.sql")
        logger.warning("No INSERT statements found in kp_dml.sql")
        return True

    print(f"Found {len(insert_statements)} knowledge point(s)")

    # Convert to REPLACE statements and execute
    print("Loading knowledge points to database...")
    logger.info("Loading knowledge points to database...")

    success_count = 0
    failed_count = 0

    with client as conn:
        cursor = conn._conn.cursor()

        for i, insert_stmt in enumerate(insert_statements, 1):
            try:
                # Convert INSERT to REPLACE for idempotency
                replace_stmt = convert_insert_to_replace(insert_stmt)

                cursor.execute(replace_stmt)

                success_count += 1

                if i % 10 == 0:
                    print(f"  Processed {i}/{len(insert_statements)} knowledge points...")
                    logger.info(f"Progress: {i}/{len(insert_statements)} knowledge points")

            except Exception as e:
                print(f"[ERROR] Failed to execute statement {i}: {e}")
                logger.error(f"Failed to execute statement {i}: {e}")
                failed_count += 1

        # Commit handled by context manager

    print("=" * 60)
    print(f"[OK] Replaced {success_count} knowledge points")
    if failed_count > 0:
        print(f"[WARN] Failed {failed_count} knowledge points")
    print("=" * 60)

    logger.info("=" * 60)
    logger.info(f"[OK] Replaced {success_count} knowledge points")
    if failed_count > 0:
        logger.warning(f"[WARN] Failed {failed_count} knowledge points")
    logger.info("=" * 60)

    return failed_count == 0


if __name__ == "__main__":
    try:
        success = load_knowledge_points()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
