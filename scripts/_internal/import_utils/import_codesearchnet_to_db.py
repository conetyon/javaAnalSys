"""
CodeSearchNet Database Import

Imports processed and labeled CodeSearchNet samples into the database
as code_snippets for retrieval experiments.

Usage:
    python experiments/import_codesearchnet_to_db.py
    python experiments/import_codesearchnet_to_db.py --max-samples 1000
    python experiments/import_codesearchnet_to_db.py --clear-existing

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import argparse

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.globals import core_logger as logger
from lib.client.db import MySQLClient
from config import DB_NAME
from src.java_analyzer.analyzer import JavaAnalyzer


def ensure_schema(db_client: MySQLClient):
    """
    Ensure code_files table has required columns.
    Auto-migrate if necessary (idempotent).

    Args:
        db_client: Database client
    """
    # Check existing columns
    columns = db_client.fetch_all("DESCRIBE code_files")
    existing_cols = {col['Field'] for col in columns}

    # Define required columns
    required_cols = {
        'source': "VARCHAR(50) DEFAULT 'manual'",
        'repo_name': "VARCHAR(255) DEFAULT ''",
        'language': "VARCHAR(20) DEFAULT 'java'"
    }

    # Add missing columns silently
    for col_name, col_def in required_cols.items():
        if col_name not in existing_cols:
            try:
                alter_query = f"ALTER TABLE code_files ADD COLUMN {col_name} {col_def}"
                db_client.execute(alter_query)
                logger.info(f"Added missing column: {col_name}")
            except Exception as e:
                logger.warning(f"Could not add column {col_name}: {e}")


def clear_codesearchnet_data(db_client: MySQLClient):
    """
    Clear existing CodeSearchNet data from database.

    Args:
        db_client: Database client
    """
    print("\nClearing existing CodeSearchNet data...")

    # Delete snippets from CodeSearchNet source
    delete_snippets = """
        DELETE FROM code_snippets
        WHERE file_id IN (
            SELECT id FROM code_files WHERE source = 'codesearchnet'
        )
    """

    # Delete files from CodeSearchNet source
    delete_files = "DELETE FROM code_files WHERE source = 'codesearchnet'"

    try:
        rows_deleted = db_client.execute(delete_snippets)
        print(f"  Deleted {rows_deleted} snippets")

        rows_deleted = db_client.execute(delete_files)
        print(f"  Deleted {rows_deleted} files")

        print("[OK] Cleared existing data\n")

    except Exception as e:
        logger.error(f"Failed to clear data: {e}")
        raise


def import_sample(
    sample: dict,
    file_id: int,
    db_client: MySQLClient,
    analyzer: JavaAnalyzer
):
    """
    Import a single sample into database.

    Args:
        sample: Processed sample dict
        file_id: Code file ID
        db_client: Database client
        analyzer: Java analyzer instance

    Returns:
        Snippet ID if successful, None otherwise
    """
    try:
        # Extract features again (we need AST features for storage)
        code = sample['code']
        snippets = analyzer.analyze_file(code)

        if not snippets:
            return None

        snippet_data = snippets[0]

        # Compute content hash for uniqueness (idempotent key)
        import hashlib
        content_hash = hashlib.sha256(code.encode('utf-8')).hexdigest()

        # Prepare insert data (match actual table schema)
        insert_data = {
            'file_id': file_id,
            'content': code,
            'start_line': snippet_data['start_line'],
            'end_line': snippet_data['end_line'],
            'keywords': json.dumps(snippet_data['keywords'], ensure_ascii=False),
            'ast_features': json.dumps(snippet_data['ast_features'], ensure_ascii=False),
            'complexity_score': snippet_data.get('difficulty', 0.0),
            'file_path': sample.get('path', ''),
            'content_hash': content_hash
        }

        # Insert snippet (v1.3.1修复: 使用REPLACE INTO实现幂等性)
        # 幂等性说明: 相同content_hash会替换旧记录，确保重复导入结果一致
        insert_query = """
            REPLACE INTO code_snippets
            (file_id, content, start_line, end_line, keywords, ast_features, complexity_score, file_path, content_hash)
            VALUES (%(file_id)s, %(content)s, %(start_line)s, %(end_line)s, %(keywords)s,
                    %(ast_features)s, %(complexity_score)s, %(file_path)s, %(content_hash)s)
        """

        db_client.execute(insert_query, insert_data)

        # Get inserted snippet ID by content_hash (more reliable than LAST_INSERT_ID with pooling)
        snippet_id = db_client.fetch_one(
            "SELECT id FROM code_snippets WHERE content_hash = %s ORDER BY id DESC LIMIT 1",
            (content_hash,)
        )['id']

        return snippet_id

    except Exception as e:
        logger.error(f"Failed to import sample: {e}")
        import traceback
        traceback.print_exc()
        return None


def import_codesearchnet_to_db(
    processed_file: Path,
    max_samples: int = None,
    clear_existing: bool = False,
    skip_if_exists: bool = True
):
    """
    Import processed CodeSearchNet data to database.

    Args:
        processed_file: Path to processed JSONL file
        max_samples: Maximum samples to import (None = all)
        clear_existing: Whether to clear existing CodeSearchNet data
        skip_if_exists: Skip import if data already exists (idempotent mode)
    """
    print("\n" + "=" * 70)
    print("CODESEARCHNET DATABASE IMPORT")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize
    db_client = MySQLClient(db=DB_NAME)
    analyzer = JavaAnalyzer()

    # Ensure schema (auto-migrate if needed)
    ensure_schema(db_client)

    # Check if data already exists
    check_query = "SELECT COUNT(*) as count FROM code_files WHERE source = 'codesearchnet'"
    existing_count = db_client.fetch_one(check_query)['count']

    if existing_count > 0:
        print(f"Found {existing_count} existing CodeSearchNet files in database")

        if skip_if_exists and not clear_existing:
            print("[SKIP] Data already exists. Use --clear-existing to reimport.")
            print("       Or remove --skip-if-exists to append new data.\n")
            return

        if clear_existing:
            clear_codesearchnet_data(db_client)
        else:
            print("[INFO] Appending to existing data (--skip-if-exists=False)\n")

    # Create a virtual code file for CodeSearchNet samples
    print("Creating code file entry...")

    # Use unique identifier to enable idempotent imports
    file_path = f'/virtual/codesearchnet/train_{datetime.now().strftime("%Y%m%d")}'

    # Check if this specific file already exists
    check_file = "SELECT id FROM code_files WHERE filepath = %s"
    existing_file = db_client.fetch_one(check_file, (file_path,))

    if existing_file:
        file_id = existing_file['id']
        print(f"[OK] Reusing existing file entry with ID: {file_id}\n")
    else:
        file_data = {
            'filename': 'codesearchnet_train.virtual',
            'filepath': file_path,
            'repo_name': 'CodeSearchNet',
            'source': 'codesearchnet',
            'language': 'java'
        }

        insert_file_query = """
            INSERT INTO code_files (filename, filepath, repo_name, source, language)
            VALUES (%(filename)s, %(filepath)s, %(repo_name)s, %(source)s, %(language)s)
        """

        db_client.execute(insert_file_query, file_data)

        # Get inserted file ID (query back instead of LAST_INSERT_ID due to connection pooling)
        file_id = db_client.fetch_one("SELECT id FROM code_files WHERE filepath = %s", (file_path,))['id']

        print(f"[OK] Created file entry with ID: {file_id}\n")

    # Check if snippets already imported for this file
    check_snippets = "SELECT COUNT(*) as count FROM code_snippets WHERE file_id = %s"
    existing_snippets = db_client.fetch_one(check_snippets, (file_id,))['count']

    if existing_snippets > 0 and skip_if_exists:
        print(f"[SKIP] {existing_snippets} snippets already imported for file ID {file_id}")
        print("       Use --clear-existing to reimport.\n")
        return

    # Import samples
    print(f"Importing samples from: {processed_file.name}")
    if max_samples:
        print(f"Max samples: {max_samples:,}")
    print()

    imported = 0
    skipped = 0
    labeled = 0

    with open(processed_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if max_samples and imported >= max_samples:
                break

            try:
                sample = json.loads(line)

                # Import sample
                snippet_id = import_sample(sample, file_id, db_client, analyzer)

                if snippet_id:
                    imported += 1

                    # Track if labeled
                    if sample.get('kp_ids'):
                        labeled += 1

                    if imported % 100 == 0:
                        print(f"  Progress: {imported:,} imported, {labeled:,} labeled, {skipped:,} skipped")

                else:
                    skipped += 1

            except json.JSONDecodeError:
                skipped += 1
                continue
            except Exception as e:
                logger.error(f"Failed to process line {i}: {e}")
                skipped += 1
                continue

    print()
    print("=" * 70)
    print("IMPORT COMPLETE")
    print("=" * 70)
    print(f"Imported: {imported:,} snippets")
    if imported > 0:
        print(f"Labeled: {labeled:,} ({labeled/imported*100:.1f}%)")
    else:
        print(f"Labeled: {labeled:,}")
    print(f"Skipped: {skipped:,}")
    print(f"File ID: {file_id}")
    print("=" * 70 + "\n")

    print("Next steps:")
    print("1. Verify import: SELECT COUNT(*) FROM code_snippets WHERE file_id = {file_id}")
    print("2. Run retrieval experiments with SearchService")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import CodeSearchNet data to database"
    )

    parser.add_argument(
        "--processed-file",
        type=str,
        help="Path to processed JSONL file (default: java_train_processed.jsonl)"
    )

    parser.add_argument(
        "--max-samples",
        type=int,
        help="Maximum samples to import (default: import all)"
    )

    parser.add_argument(
        "--clear-existing",
        action="store_true",
        help="Clear existing CodeSearchNet data before import"
    )

    parser.add_argument(
        "--skip-if-exists",
        action="store_true",
        default=True,
        help="Skip import if data already exists (default: True, idempotent mode)"
    )

    parser.add_argument(
        "--no-skip-if-exists",
        dest="skip_if_exists",
        action="store_false",
        help="Force append even if data exists"
    )

    args = parser.parse_args()

    # Set processed file path
    if args.processed_file:
        processed_file = Path(args.processed_file)
    else:
        processed_file = PROJECT_ROOT / 'experiments' / 'datasets' / 'processed' / 'codesearchnet' / 'java_train_processed.jsonl'

    if not processed_file.exists():
        print(f"[ERROR] Processed file not found: {processed_file}")
        print("\nRun preprocessing first:")
        print("  python experiments/datasets/preprocess_codesearchnet.py")
        return

    # Import data
    import_codesearchnet_to_db(
        processed_file=processed_file,
        max_samples=args.max_samples,
        clear_existing=args.clear_existing,
        skip_if_exists=args.skip_if_exists
    )


if __name__ == "__main__":
    main()
