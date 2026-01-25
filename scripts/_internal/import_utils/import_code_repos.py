"""
Bulk Code Repository Import Script

Imports Java projects from code_repos/ directory into database.
Supports both single repository and batch import modes.

Features:
- Idempotent: Same files = same database state (uses REPLACE INTO)
- Progress tracking: Shows real-time progress
- Error handling: Continues on parse errors, logs failures
- CLI and API modes: Can be called from command line or API

Usage:
    # Import single repository
    python scripts/batch_import/import_code_repos.py --repo code_repos/spring-boot

    # Import all repositories
    python scripts/batch_import/import_code_repos.py --all

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import sys
import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.client.db import MySQLClient
from lib.globals import Cfg, core_logger as logger
from src.java_analyzer.analyzer import JavaAnalyzer
from scripts._internal.import_utils.file_discovery import discover_java_files, discover_java_projects
from scripts._internal.import_utils.hash_utils import compute_snippet_hash
from config import DB_NAME


class ImportProgress:
    """Track import progress and statistics."""

    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.total_snippets = 0
        self.inserted_snippets = 0
        self.replaced_snippets = 0
        self.failed_files = 0
        self.errors = []

    def add_error(self, file_path: str, error: str):
        """Record an error."""
        self.errors.append({"file": file_path, "error": str(error)})
        self.failed_files += 1

    def print_summary(self):
        """Print import summary."""
        logger.info("=" * 60)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total files: {self.total_files}")
        logger.info(f"Processed files: {self.processed_files}")
        logger.info(f"Failed files: {self.failed_files}")
        logger.info(f"Total snippets extracted: {self.total_snippets}")
        logger.info(f"Snippets imported: {self.inserted_snippets + self.replaced_snippets}")
        logger.info(f"  - New insertions: {self.inserted_snippets}")
        logger.info(f"  - Replacements (same hash): {self.replaced_snippets}")

        if self.errors:
            logger.warning(f"\nErrors ({len(self.errors)}):")
            for err in self.errors[:10]:  # Show first 10 errors
                logger.warning(f"  - {err['file']}: {err['error']}")
            if len(self.errors) > 10:
                logger.warning(f"  ... and {len(self.errors) - 10} more errors")

        logger.info("=" * 60)


def analyze_java_file(file_path: str, analyzer: JavaAnalyzer) -> List[Dict]:
    """
    Analyze a Java file and extract code snippets.

    Args:
        file_path: Path to Java file
        analyzer: JavaAnalyzer instance

    Returns:
        List of snippet dictionaries

    Raises:
        Exception if file cannot be parsed
    """
    snippets = analyzer.analyze_file(file_path)

    # Add file_path and content_hash to each snippet
    for snippet in snippets:
        snippet['file_path'] = file_path
        snippet['content_hash'] = compute_snippet_hash(
            file_path,
            snippet.get('content', '')
        )

    return snippets


def import_snippet_to_db(client: MySQLClient, snippet: Dict, file_id: int) -> bool:
    """
    Import a single snippet to database using REPLACE INTO.

    Args:
        client: MySQL client
        snippet: Snippet dictionary
        file_id: Foreign key to code_files table

    Returns:
        True if inserted (new), False if replaced (existing)
    """
    # Check if snippet already exists
    existing = client.fetch_one(
        "SELECT id FROM code_snippets WHERE content_hash = %s",
        (snippet['content_hash'],)
    )

    # Use REPLACE INTO for idempotency
    sql = """
        REPLACE INTO code_snippets (
            file_id, content, content_hash, file_path,
            ast_features, keywords, complexity_score, start_line, end_line
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        file_id,
        snippet.get('content', ''),
        snippet['content_hash'],
        snippet.get('file_path', ''),
        json.dumps(snippet.get('ast_features', {})),
        json.dumps(snippet.get('keywords', [])),
        snippet.get('difficulty', 0.0),
        snippet.get('start_line', 0),
        snippet.get('end_line', 0)
    )

    client.execute(sql, values)

    return existing is None  # True if new insert, False if replacement


def get_or_create_file_record(client: MySQLClient, file_path: str) -> int:
    """
    Get or create a record in code_files table.

    Args:
        client: MySQL client
        file_path: Path to source file

    Returns:
        File ID from code_files table
    """
    # Check if file record exists (code_files table uses 'filepath')
    result = client.fetch_one(
        "SELECT id FROM code_files WHERE filepath = %s",
        (file_path,)
    )

    if result:
        return result['id']

    # Create new file record (code_files table uses 'filepath')
    client.execute(
        "INSERT INTO code_files (filepath) VALUES (%s)",
        (file_path,)
    )

    # Get the inserted ID
    result = client.fetch_one(
        "SELECT LAST_INSERT_ID() as id"
    )
    return result['id'] if result else 0


def import_java_file(
    file_path: str,
    analyzer: JavaAnalyzer,
    client: MySQLClient,
    progress: ImportProgress,
    show_progress: bool = True
) -> None:
    """
    Import a single Java file.

    Args:
        file_path: Path to Java file
        analyzer: JavaAnalyzer instance
        client: MySQL client
        progress: Progress tracker
        show_progress: Whether to print progress
    """
    if show_progress:
        logger.info(f"[{progress.processed_files + 1}/{progress.total_files}] Analyzing {file_path}")

    try:
        # Analyze file
        snippets = analyze_java_file(file_path, analyzer)

        if not snippets:
            logger.debug(f"No snippets extracted from {file_path}")
            progress.processed_files += 1
            return

        # Get or create file record
        file_id = get_or_create_file_record(client, file_path)

        # Import each snippet
        for snippet in snippets:
            is_new = import_snippet_to_db(client, snippet, file_id)

            if is_new:
                progress.inserted_snippets += 1
            else:
                progress.replaced_snippets += 1

            progress.total_snippets += 1

        progress.processed_files += 1

    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        progress.add_error(file_path, str(e))
        progress.processed_files += 1


def import_repository(repo_path: str, show_progress: bool = True) -> ImportProgress:
    """
    Import a single Java repository.

    Args:
        repo_path: Path to repository root
        show_progress: Whether to print progress

    Returns:
        ImportProgress object with statistics
    """
    logger.info("=" * 60)
    logger.info(f"IMPORTING REPOSITORY: {repo_path}")
    logger.info("=" * 60)

    # Initialize components
    analyzer = JavaAnalyzer()
    client = MySQLClient(db=DB_NAME)
    progress = ImportProgress()

    # Discover Java files
    logger.info("Discovering Java files...")
    try:
        java_files = discover_java_files(repo_path)
    except Exception as e:
        logger.error(f"Failed to discover files: {e}")
        return progress

    progress.total_files = len(java_files)
    logger.info(f"Found {progress.total_files} Java file(s)")

    if progress.total_files == 0:
        logger.warning("No Java files found")
        return progress

    # Import each file
    for file_path in java_files:
        import_java_file(file_path, analyzer, client, progress, show_progress)

    # Print summary
    progress.print_summary()

    return progress


def import_all_repositories(root_path: str = "code_repos") -> ImportProgress:
    """
    Import all Java repositories in a root directory.

    Args:
        root_path: Root directory containing repositories

    Returns:
        Combined ImportProgress
    """
    logger.info("=" * 60)
    logger.info(f"BULK IMPORT FROM: {root_path}")
    logger.info("=" * 60)

    # Discover projects
    try:
        projects = discover_java_projects(root_path)
    except Exception as e:
        logger.error(f"Failed to discover projects: {e}")
        return ImportProgress()

    if not projects:
        logger.warning(f"No Java projects found in {root_path}")
        return ImportProgress()

    logger.info(f"Found {len(projects)} project(s):")
    for project in projects:
        logger.info(f"  - {project}")

    # Import each project
    combined_progress = ImportProgress()

    for i, project in enumerate(projects, 1):
        logger.info(f"\n--- Project {i}/{len(projects)}: {project} ---")

        progress = import_repository(project, show_progress=True)

        # Combine statistics
        combined_progress.total_files += progress.total_files
        combined_progress.processed_files += progress.processed_files
        combined_progress.total_snippets += progress.total_snippets
        combined_progress.inserted_snippets += progress.inserted_snippets
        combined_progress.replaced_snippets += progress.replaced_snippets
        combined_progress.failed_files += progress.failed_files
        combined_progress.errors.extend(progress.errors)

    # Print combined summary
    logger.info("\n" + "=" * 60)
    logger.info("OVERALL SUMMARY (ALL PROJECTS)")
    combined_progress.print_summary()

    return combined_progress


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Import Java code repositories into database"
    )
    parser.add_argument(
        "--repo",
        help="Path to a single repository to import"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Import all repositories from code_repos/ directory"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output"
    )

    args = parser.parse_args()

    if not args.repo and not args.all:
        parser.error("Must specify either --repo or --all")

    show_progress = not args.quiet

    if args.all:
        progress = import_all_repositories()
    else:
        progress = import_repository(args.repo, show_progress)

    # Exit with appropriate code
    if progress.failed_files > 0:
        logger.warning(f"Import completed with {progress.failed_files} error(s)")
        sys.exit(1)
    else:
        logger.info("Import completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
