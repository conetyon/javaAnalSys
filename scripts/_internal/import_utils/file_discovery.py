"""
Java File Discovery Module

Recursively discovers Java files in a directory while excluding build/test directories.

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import os
from pathlib import Path
from typing import List


# Directories to exclude from scanning
EXCLUDED_DIRS = {
    'target',      # Maven build output
    'build',       # Gradle build output
    '.git',        # Version control
    'node_modules', # Node.js dependencies (if mixed project)
    '.idea',       # IDE files
    '.vscode',     # IDE files
    '__pycache__', # Python cache
    'dist',        # Distribution files
    'out',         # Output directories
}

# Optional: Exclude test directories (configurable)
EXCLUDE_TESTS = True
if EXCLUDE_TESTS:
    EXCLUDED_DIRS.add('test')
    EXCLUDED_DIRS.add('tests')


def should_exclude_dir(dir_name: str) -> bool:
    """
    Check if a directory should be excluded from scanning.

    Args:
        dir_name: Name of the directory

    Returns:
        True if directory should be excluded
    """
    return dir_name in EXCLUDED_DIRS


def discover_java_files(root_path: str) -> List[str]:
    """
    Recursively discover all Java files in a directory.

    Args:
        root_path: Root directory to search

    Returns:
        List of absolute paths to Java files

    Example:
        >>> files = discover_java_files('code_repos/spring-boot')
        >>> len(files)
        1234
    """
    root = Path(root_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    java_files = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Remove excluded directories from dirnames (in-place modification)
        # This prevents os.walk from descending into those directories
        dirnames[:] = [d for d in dirnames if not should_exclude_dir(d)]

        # Find Java files in current directory
        for filename in filenames:
            if filename.endswith('.java'):
                file_path = Path(dirpath) / filename
                java_files.append(str(file_path))

    return sorted(java_files)  # Sort for consistent ordering


def discover_java_projects(root_path: str) -> List[str]:
    """
    Discover Java projects (subdirectories) in a root directory.
    Also includes the root directory itself if it contains Java files directly (not in subdirs).

    Args:
        root_path: Root directory containing multiple Java projects

    Returns:
        List of project directory paths

    Example:
        >>> projects = discover_java_projects('code_repos')
        >>> projects
        ['code_repos', 'code_repos/spring-boot', 'code_repos/my-project']
    """
    root = Path(root_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root}")

    projects = []

    # First check if root directory itself has Java files directly (not in subdirs)
    root_java_files = [f for f in root.iterdir() if f.is_file() and f.suffix == '.java']
    if root_java_files:
        # Mark root as a "flat" project (only direct files, no recursion)
        projects.append(str(root) + "::FLAT")

    # Look for subdirectories that contain Java files
    for item in root.iterdir():
        if item.is_dir() and not should_exclude_dir(item.name):
            # Check if this directory contains any Java files
            try:
                java_files = discover_java_files(str(item))
                if java_files:
                    projects.append(str(item))
            except Exception:
                # Skip directories that can't be scanned
                continue

    return sorted(projects)


def discover_java_files_flat(root_path: str) -> List[str]:
    """
    Discover Java files directly in a directory (non-recursive).

    Args:
        root_path: Directory to search

    Returns:
        List of absolute paths to Java files in this directory only
    """
    root = Path(root_path).resolve()

    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root}")

    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root}")

    java_files = []
    for item in root.iterdir():
        if item.is_file() and item.suffix == '.java':
            java_files.append(str(item))

    return sorted(java_files)


if __name__ == "__main__":
    # Test discovery
    import sys

    if len(sys.argv) < 2:
        print("Usage: python file_discovery.py <directory>")
        sys.exit(1)

    path = sys.argv[1]

    try:
        files = discover_java_files(path)
        print(f"Found {len(files)} Java file(s) in {path}")

        if len(files) <= 10:
            for f in files:
                print(f"  - {f}")
        else:
            for f in files[:5]:
                print(f"  - {f}")
            print(f"  ... and {len(files) - 5} more")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
