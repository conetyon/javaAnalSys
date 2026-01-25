"""
Content Hash Utilities

Provides functions to compute deterministic hashes for code snippets.
Used for idempotent imports (same file = same hash = same database state).

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import hashlib


def compute_snippet_hash(file_path: str, content: str) -> str:
    """
    Compute SHA256 hash for a code snippet.

    The hash includes both file path and content to ensure uniqueness:
    - Different files with same content get different hashes
    - Same file with same content always gets same hash

    Args:
        file_path: Path to the source file
        content: Code snippet content

    Returns:
        64-character hexadecimal hash string

    Example:
        >>> hash1 = compute_snippet_hash("App.java", "public void main() {}")
        >>> hash2 = compute_snippet_hash("App.java", "public void main() {}")
        >>> hash1 == hash2
        True
        >>> hash3 = compute_snippet_hash("Other.java", "public void main() {}")
        >>> hash1 == hash3
        False
    """
    # Combine file path and content with delimiter
    combined = f"{file_path}::{content}"

    # Compute SHA256 hash
    hash_bytes = hashlib.sha256(combined.encode('utf-8')).digest()

    # Convert to hexadecimal string
    return hash_bytes.hex()


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA256 hash for an entire file.

    Args:
        file_path: Path to the file

    Returns:
        64-character hexadecimal hash string

    Example:
        >>> hash = compute_file_hash("sample_code.java")
        >>> len(hash)
        64
    """
    hasher = hashlib.sha256()

    with open(file_path, 'rb') as f:
        # Read file in chunks to handle large files
        while chunk := f.read(8192):
            hasher.update(chunk)

    return hasher.hexdigest()


def verify_hash_determinism():
    """
    Test function to verify hash computation is deterministic.

    Returns:
        True if hashes are deterministic
    """
    # Test data
    file_path = "test/Example.java"
    content = "public class Example { public static void main() {} }"

    # Compute hash multiple times
    hash1 = compute_snippet_hash(file_path, content)
    hash2 = compute_snippet_hash(file_path, content)
    hash3 = compute_snippet_hash(file_path, content)

    # All hashes should be identical
    deterministic = (hash1 == hash2 == hash3)

    if deterministic:
        print(f"✓ Hash determinism verified: {hash1}")
    else:
        print(f"✗ Hash determinism failed!")
        print(f"  hash1: {hash1}")
        print(f"  hash2: {hash2}")
        print(f"  hash3: {hash3}")

    return deterministic


def verify_hash_uniqueness():
    """
    Test function to verify different inputs produce different hashes.

    Returns:
        True if hashes are unique
    """
    # Different file paths, same content
    hash1 = compute_snippet_hash("FileA.java", "int x = 5;")
    hash2 = compute_snippet_hash("FileB.java", "int x = 5;")

    # Same file path, different content
    hash3 = compute_snippet_hash("FileA.java", "int x = 5;")
    hash4 = compute_snippet_hash("FileA.java", "int y = 10;")

    unique_paths = (hash1 != hash2)
    unique_content = (hash3 != hash4)

    if unique_paths and unique_content:
        print(f"✓ Hash uniqueness verified")
        print(f"  Different paths: {hash1[:16]}... != {hash2[:16]}...")
        print(f"  Different content: {hash3[:16]}... != {hash4[:16]}...")
    else:
        print(f"✗ Hash uniqueness failed!")

    return unique_paths and unique_content


if __name__ == "__main__":
    print("Testing hash utilities...")
    print()

    print("Test 1: Determinism")
    deterministic = verify_hash_determinism()
    print()

    print("Test 2: Uniqueness")
    unique = verify_hash_uniqueness()
    print()

    if deterministic and unique:
        print("✓ All tests passed")
        exit(0)
    else:
        print("✗ Some tests failed")
        exit(1)
