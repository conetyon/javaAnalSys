"""
Sample Code Analysis Script

Analyzes sample_code.java and stores snippets in database.
Uses REPLACE INTO based on content_hash for strong idempotency.

Usage:
    python scripts/init_data/analyze_sample_code.py

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import os
import sys
import json
import hashlib
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.client.db import MySQLClient
from lib.globals import Cfg, core_logger as logger
from src.java_analyzer.analyzer import JavaAnalyzer
from config import DB_NAME


def compute_content_hash(content: str) -> str:
    """
    Compute SHA256 hash for a code snippet based on content only.

    Args:
        content: Snippet content

    Returns:
        64-character hex hash string
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def analyze_sample_code():
    """
    Analyze sample_code.java and store results in database.
    Uses REPLACE INTO with content_hash for strong idempotency.
    """
    print("=" * 60)
    print("SAMPLE CODE ANALYSIS")
    print("=" * 60)

    logger.info("=" * 60)
    logger.info("SAMPLE CODE ANALYSIS")
    logger.info("=" * 60)

    # Locate sample_code.java
    sample_file = PROJECT_ROOT / 'sample_code.java'
    print(f"Looking for sample code file: {sample_file}")

    if not sample_file.exists():
        print(f"[ERROR] Sample code file not found: {sample_file}")
        logger.error(f"Sample code file not found: {sample_file}")
        return False

    print(f"Found file: {sample_file.name}")
    logger.info(f"Analyzing file: {sample_file.name}")

    # Read and analyze
    print("Reading and analyzing Java code...")
    try:
        with open(sample_file, 'r', encoding='utf-8') as f:
            java_code = f.read()

        print("Initializing Java analyzer...")
        analyzer = JavaAnalyzer()

        print("Extracting code snippets...")
        snippets = analyzer.analyze_file(java_code)

        if not snippets:
            print("[WARNING] No snippets extracted from sample_code.java")
            logger.warning("No snippets extracted from sample_code.java")
            return True

        print(f"Extracted {len(snippets)} snippet(s)")
        logger.info(f"Extracted {len(snippets)} snippet(s)")

    except Exception as e:
        print(f"[ERROR] Failed to analyze {sample_file.name}: {e}")
        logger.error(f"Failed to analyze {sample_file.name}: {e}")
        return False

    # Store in database with idempotency
    print("Storing snippets in database...")
    db_config = Cfg.db[DB_NAME]
    # Use autocommit=False to ensure explicit commit via context manager
    client = MySQLClient(db=DB_NAME, autocommit=False)

    try:
        with client as conn:
            # Get actual cursor from connection
            cursor = conn._conn.cursor()

            # 1. Ensure file record exists (idempotent via filename)
            filename = sample_file.name
            print(f"Checking if file '{filename}' exists in database...")
            cursor.execute(
                "SELECT id FROM code_files WHERE filename = %s",
                (filename,)
            )
            row = cursor.fetchone()

            if row:
                file_id = row[0]
                print(f"File '{filename}' already exists (ID: {file_id})")
                logger.info(f"File '{filename}' already exists (ID: {file_id})")
                # File already exists, no need to update (content field removed)
            else:
                print(f"Inserting new file: {filename}")
                logger.info(f"Inserting new file: {filename}")
                cursor.execute(
                    "INSERT INTO code_files (filename, filepath) VALUES (%s, %s)",
                    (filename, str(sample_file))
                )
                file_id = cursor.lastrowid

                if not file_id:
                    raise ValueError(f"Failed to get file_id for {filename}")

            # 2. Insert/replace snippets using content_hash
            replaced_count = 0

            print(f"Storing {len(snippets)} snippets...")
            for i, snippet in enumerate(snippets, 1):
                content = snippet['content']
                content_hash = compute_content_hash(content)

                # REPLACE INTO: If hash exists, replace; otherwise insert
                cursor.execute("""
                    REPLACE INTO code_snippets
                    (file_id, file_path, start_line, end_line, content, content_hash,
                     complexity_score, ast_features, keywords)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    file_id,
                    str(sample_file),
                    snippet['start_line'],
                    snippet['end_line'],
                    content,
                    content_hash,
                    snippet['difficulty'],
                    json.dumps(snippet['ast_features'], ensure_ascii=False),
                    json.dumps(snippet['keywords'], ensure_ascii=False)
                ))

                replaced_count += 1

                if i % 10 == 0:
                    print(f"  Processed {i}/{len(snippets)} snippets...")

            # Commit handled by context manager

            print("=" * 60)
            print(f"[OK] Replaced/inserted {replaced_count} snippet(s)")
            print(f"[OK] File ID: {file_id}")
            print("=" * 60)

            logger.info("=" * 60)
            logger.info(f"[OK] Replaced/inserted {replaced_count} snippet(s)")
            logger.info(f"[OK] File ID: {file_id}")
            logger.info("=" * 60)

            return True

    except Exception as e:
        print(f"[ERROR] Database operation failed: {e}")
        logger.error(f"Database operation failed: {e}")
        return False


if __name__ == "__main__":
    try:
        success = analyze_sample_code()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
