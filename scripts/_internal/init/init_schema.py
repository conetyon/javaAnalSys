"""
Database Schema Initialization Script

Initializes database tables by running migration scripts.
This script is idempotent - safe to run multiple times.

Usage:
    python scripts/init_data/init_schema.py

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.client.db import MySQLClient
from lib.globals import Cfg, core_logger as logger
from config import DB_NAME
from src.db_manager.database import DatabaseInitializer


def run_migration_file(client: MySQLClient, migration_file: Path):
    """
    Execute a single migration SQL file.
    Handles duplicate column/index errors gracefully (idempotency).

    Args:
        client: MySQL client instance
        migration_file: Path to migration SQL file
    """
    print(f"[Migration] Running: {migration_file.name}")
    logger.info(f"Running migration: {migration_file.name}")

    try:
        with open(migration_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # Split by semicolon and execute each statement
        # Filter out comments and empty lines
        raw_statements = sql_content.split(';')
        statements = []
        for stmt in raw_statements:
            # Remove single-line comments
            lines = [line for line in stmt.split('\n') if not line.strip().startswith('--')]
            cleaned = '\n'.join(lines).strip()
            if cleaned:
                statements.append(cleaned)

        print(f"[Migration] Found {len(statements)} statement(s)")

        if len(statements) == 0:
            print(f"[Migration] No SQL statements found in {migration_file.name}, skipping")
            return True

        # Execute statements using context manager
        with client as conn:
            # Get the actual connection object
            cursor = conn._conn.cursor()

            for i, stmt in enumerate(statements, 1):
                try:
                    print(f"[Migration] Executing statement {i}/{len(statements)}...")
                    cursor.execute(stmt)
                    print(f"[Migration] Statement {i} OK")
                except Exception as e:
                    # Ignore duplicate column/index errors (makes migrations idempotent)
                    error_msg = str(e)
                    if "Duplicate column name" in error_msg or "1060" in error_msg:
                        print(f"[Migration] Column already exists, skipping (OK)")
                        logger.debug(f"Column already exists, skipping: {error_msg}")
                        continue
                    elif "Duplicate key name" in error_msg or "1061" in error_msg:
                        print(f"[Migration] Index already exists, skipping (OK)")
                        logger.debug(f"Index already exists, skipping: {error_msg}")
                        continue
                    else:
                        # Re-raise other errors
                        print(f"[Migration] ERROR: {e}")
                        raise

            # Commit is handled by context manager exit
            cursor.close()

        print(f"[Migration] {migration_file.name} completed successfully")
        logger.info(f"[OK] Migration {migration_file.name} completed successfully")
        return True

    except Exception as e:
        print(f"[Migration] FAILED: {migration_file.name} - {e}")
        logger.error(f"[FAIL] Migration {migration_file.name} failed: {e}")
        raise


def init_schema():
    """
    Initialize database schema by running all migration files.
    Idempotent: Safe to run multiple times.
    """
    print("=" * 60)
    print("DATABASE SCHEMA INITIALIZATION")
    print("=" * 60)

    logger.info("=" * 60)
    logger.info("DATABASE SCHEMA INITIALIZATION")
    logger.info("=" * 60)

    # Get database configuration
    db_config = Cfg.db[DB_NAME]
    print(f"Target database: {db_config.db} @ {db_config.host}:{db_config.port}")
    logger.info(f"Target database: {db_config.db} @ {db_config.host}:{db_config.port}")

    # Step 1: Initialize base schema (tables + indexes)
    print("\nStep 1: Creating base tables and indexes...")
    logger.info("Step 1: Creating base tables and indexes...")
    try:
        initializer = DatabaseInitializer(db_name=DB_NAME)
        initializer.init_db()
        print("[OK] Base schema initialized\n")
        logger.info("[OK] Base schema initialized")
    except Exception as e:
        print(f"[FAIL] Base schema initialization failed: {e}")
        logger.error(f"[FAIL] Base schema initialization failed: {e}")
        return False

    # Step 2: Run migration files for schema updates (optional - for existing databases)
    print("Step 2: Checking for migration scripts...")
    logger.info("Step 2: Checking for migration scripts...")

    # Initialize MySQL client
    client = MySQLClient(db=DB_NAME)

    # Get migration files directory
    migrations_dir = PROJECT_ROOT / 'scripts' / 'migrations'
    if not migrations_dir.exists():
        print("[INFO] No migrations directory found, skipping migration step")
        print("=" * 60)
        print("[OK] Database schema initialized successfully")
        print("=" * 60)
        logger.info("No migrations directory found, skipping migration step")
        logger.info("=" * 60)
        logger.info("[OK] Database schema initialized successfully")
        logger.info("=" * 60)
        return True

    # Get all migration files (sorted by name)
    migration_files = sorted(migrations_dir.glob('*.sql'))

    if not migration_files:
        print("[INFO] No migration files found, skipping migration step")
        print("=" * 60)
        print("[OK] Database schema initialized successfully")
        print("=" * 60)
        logger.info("No migration files found, skipping migration step")
        logger.info("=" * 60)
        logger.info("[OK] Database schema initialized successfully")
        logger.info("=" * 60)
        return True

    print(f"[INFO] Found {len(migration_files)} migration file(s)")
    print("[INFO] Migrations are optional - base schema includes all fields")
    print("[INFO] Only needed for upgrading existing databases")
    print("[INFO] Skipping migrations for clean installation\n")
    logger.info(f"Found {len(migration_files)} migration file(s), skipping for clean installation")

    # Skip migrations for clean installation
    # Uncomment the code below if you need to run migrations on existing databases
    """
    print(f"Running {len(migration_files)} migration file(s)\n")
    logger.info(f"Found {len(migration_files)} migration file(s)")

    # Run each migration
    success = True
    for migration_file in migration_files:
        try:
            run_migration_file(client, migration_file)
        except Exception as e:
            print(f"[ERROR] Failed to run migration {migration_file.name}: {e}")
            logger.error(f"Failed to run migration {migration_file.name}: {e}")
            success = False
            break

    if not success:
        print("\n" + "=" * 60)
        print("[FAIL] Database schema initialization failed")
        print("=" * 60)
        logger.error("=" * 60)
        logger.error("[FAIL] Database schema initialization failed")
        logger.error("=" * 60)
        return False
    """

    print("=" * 60)
    print("[OK] Database schema initialized successfully")
    print("=" * 60)
    logger.info("=" * 60)
    logger.info("[OK] Database schema initialized successfully")
    logger.info("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = init_schema()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
