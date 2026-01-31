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
        self.total_files = 0           # 发现的文件总数
        self.files_with_methods = 0    # 有方法的文件数（已导入）
        self.files_no_methods = 0      # 无方法的文件数（跳过）
        self.files_all_duplicates = 0  # 全部重复的文件数（不创建文件记录）
        self.failed_files = 0          # 失败的文件数
        self.total_snippets = 0        # 提取的片段总数
        self.unique_snippets = 0       # 唯一片段数（新增）
        self.duplicate_snippets = 0    # 重复片段数（去重）
        self.errors = []

    def add_error(self, file_path: str, error: str):
        """Record an error."""
        self.errors.append({"file": file_path, "error": str(error)})
        self.failed_files += 1

    def print_summary(self):
        """Print import summary."""
        logger.info("=" * 60)
        logger.info("导入统计")
        logger.info("=" * 60)

        # 文件统计
        logger.info(f"发现文件: {self.total_files}")
        logger.info(f"  ├─ 有新片段: {self.files_with_methods} (已导入)")
        logger.info(f"  ├─ 无方法: {self.files_no_methods} (跳过)")
        logger.info(f"  ├─ 全重复: {self.files_all_duplicates} (不创建文件记录)")
        logger.info(f"  └─ 失败: {self.failed_files}")

        # 片段统计
        logger.info(f"提取片段: {self.total_snippets}")
        logger.info(f"  ├─ 新增: {self.unique_snippets}")
        logger.info(f"  └─ 已存在: {self.duplicate_snippets} (去重/更新)")

        if self.errors:
            logger.warning(f"\n错误详情 ({len(self.errors)}):")
            for err in self.errors[:10]:  # Show first 10 errors
                logger.warning(f"  - {err['file']}: {err['error']}")
            if len(self.errors) > 10:
                logger.warning(f"  ... 还有 {len(self.errors) - 10} 个错误")

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
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        java_code = f.read()

    # 传入代码内容（而非文件路径）
    snippets = analyzer.analyze_file(java_code)

    # Add file_path and content_hash to each snippet
    for snippet in snippets:
        snippet['file_path'] = file_path
        snippet['content_hash'] = compute_snippet_hash(
            snippet.get('content', '')
        )

    return snippets


def import_snippet_to_db(client: MySQLClient, snippet: Dict, file_id: int, skip_check: bool = False) -> bool:
    """
    Import a single snippet to database using INSERT ... ON DUPLICATE KEY UPDATE.

    Args:
        client: MySQL client
        snippet: Snippet dictionary
        file_id: Foreign key to code_files table
        skip_check: If True, skip the existence check (caller already verified it's new)

    Returns:
        True if inserted (new), False if updated (existing)
    """
    # Check if snippet already exists (unless caller says skip)
    if not skip_check:
        existing = client.fetch_one(
            "SELECT id FROM code_snippets WHERE content_hash = %s",
            (snippet['content_hash'],)
        )
        if existing:
            return False

    # Use INSERT ... ON DUPLICATE KEY UPDATE for idempotency
    # This is better than REPLACE INTO because it doesn't delete+insert (which changes IDs)
    sql = """
        INSERT INTO code_snippets (
            file_id, content, content_hash, file_path,
            ast_features, keywords, complexity_score, start_line, end_line
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            file_id = VALUES(file_id),
            content = VALUES(content),
            file_path = VALUES(file_path),
            ast_features = VALUES(ast_features),
            keywords = VALUES(keywords),
            complexity_score = VALUES(complexity_score),
            start_line = VALUES(start_line),
            end_line = VALUES(end_line)
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

    return True


def extract_file_metadata(file_path: str) -> tuple:
    """
    Extract filename and repo_name from file path.

    Args:
        file_path: Full path to the file

    Returns:
        Tuple of (filename, repo_name)
    """
    from pathlib import Path
    path = Path(file_path)
    filename = path.name

    # Try to extract repo_name from path
    # Look for 'code_repos' in path and get the next directory
    repo_name = ''
    parts = path.parts
    for i, part in enumerate(parts):
        if part == 'code_repos' and i + 1 < len(parts):
            repo_name = parts[i + 1]
            break

    return filename, repo_name


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

    # Extract metadata from path
    filename, repo_name = extract_file_metadata(file_path)

    # Create new file record using INSERT IGNORE (safe for concurrent access)
    # Note: We use INSERT IGNORE instead of INSERT + LAST_INSERT_ID() because
    # connection pooling may give different connections for execute() and fetch_one(),
    # making LAST_INSERT_ID() return 0 (wrong session).
    client.execute(
        "INSERT IGNORE INTO code_files (filepath, filename, repo_name) VALUES (%s, %s, %s)",
        (file_path, filename, repo_name)
    )

    # Re-fetch the ID (either just inserted or existed from concurrent insert)
    result = client.fetch_one(
        "SELECT id FROM code_files WHERE filepath = %s",
        (file_path,)
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
    current = progress.files_with_methods + progress.files_no_methods + progress.files_all_duplicates + progress.failed_files + 1
    if show_progress:
        logger.info(f"[{current}/{progress.total_files}] Analyzing {file_path}")

    try:
        # Analyze file
        snippets = analyze_java_file(file_path, analyzer)

        if not snippets:
            logger.debug(f"No snippets extracted from {file_path}")
            progress.files_no_methods += 1
            return

        # First pass: check which snippets are new (without creating file record)
        new_snippets = []
        duplicate_count = 0

        for snippet in snippets:
            existing = client.fetch_one(
                "SELECT id FROM code_snippets WHERE content_hash = %s",
                (snippet['content_hash'],)
            )
            if existing is None:
                new_snippets.append(snippet)
            else:
                duplicate_count += 1

        # Update statistics
        progress.total_snippets += len(snippets)
        progress.duplicate_snippets += duplicate_count

        # If all snippets are duplicates, don't create file record
        if not new_snippets:
            logger.debug(f"All {len(snippets)} snippets from {file_path} already exist, skipping file record")
            progress.files_all_duplicates += 1
            return

        # Only create file record when we have new snippets
        file_id = get_or_create_file_record(client, file_path)

        # Import only new snippets (skip_check=True since we already verified)
        for snippet in new_snippets:
            import_snippet_to_db(client, snippet, file_id, skip_check=True)
            progress.unique_snippets += 1

        progress.files_with_methods += 1

    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        progress.add_error(file_path, str(e))


def import_repository(repo_path: str, show_progress: bool = True, flat_mode: bool = False) -> ImportProgress:
    """
    Import a single Java repository.

    Args:
        repo_path: Path to repository root
        show_progress: Whether to print progress
        flat_mode: If True, only scan direct files (non-recursive)

    Returns:
        ImportProgress object with statistics
    """
    logger.info("=" * 60)
    logger.info(f"IMPORTING REPOSITORY: {repo_path}" + (" (flat)" if flat_mode else ""))
    logger.info("=" * 60)

    # Initialize components
    analyzer = JavaAnalyzer()
    client = MySQLClient(db=DB_NAME)
    progress = ImportProgress()

    # Discover Java files
    logger.info("Discovering Java files...")
    try:
        if flat_mode:
            from scripts._internal.import_utils.file_discovery import discover_java_files_flat
            java_files = discover_java_files_flat(repo_path)
        else:
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
        # Check for flat mode marker
        flat_mode = project.endswith("::FLAT")
        if flat_mode:
            project = project[:-6]  # Remove "::FLAT" suffix

        logger.info(f"\n--- Project {i}/{len(projects)}: {project}" + (" (flat)" if flat_mode else "") + " ---")

        progress = import_repository(project, show_progress=True, flat_mode=flat_mode)

        # Combine statistics
        combined_progress.total_files += progress.total_files
        combined_progress.files_with_methods += progress.files_with_methods
        combined_progress.files_no_methods += progress.files_no_methods
        combined_progress.files_all_duplicates += progress.files_all_duplicates
        combined_progress.total_snippets += progress.total_snippets
        combined_progress.unique_snippets += progress.unique_snippets
        combined_progress.duplicate_snippets += progress.duplicate_snippets
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
