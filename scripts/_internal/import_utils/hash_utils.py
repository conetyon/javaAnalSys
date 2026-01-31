"""
Content Hash Utilities

Provides functions to compute deterministic hashes for code snippets.
Used for idempotent imports and deduplication.

Author: System Refactoring v1.3.0
Created: 2026-01-24
"""

import hashlib


def compute_snippet_hash(content: str) -> str:
    """
    Compute SHA256 hash for a code snippet based on content only.

    Same content always produces the same hash, regardless of file path.
    This enables deduplication of identical code across different files.

    Args:
        content: Code snippet content

    Returns:
        64-character hexadecimal hash string

    Example:
        >>> hash1 = compute_snippet_hash("public void main() {}")
        >>> hash2 = compute_snippet_hash("public void main() {}")
        >>> hash1 == hash2
        True
    """
    # Compute SHA256 hash of content only
    hash_bytes = hashlib.sha256(content.encode('utf-8')).digest()

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
    content = "public class Example { public static void main() {} }"

    # Compute hash multiple times
    hash1 = compute_snippet_hash(content)
    hash2 = compute_snippet_hash(content)
    hash3 = compute_snippet_hash(content)

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
    Test function to verify different content produces different hashes.
    Same content from different files should produce the SAME hash.

    Returns:
        True if hashes behave correctly
    """
    # Same content should produce same hash (deduplication)
    hash1 = compute_snippet_hash("int x = 5;")
    hash2 = compute_snippet_hash("int x = 5;")

    # Different content should produce different hash
    hash3 = compute_snippet_hash("int x = 5;")
    hash4 = compute_snippet_hash("int y = 10;")

    same_content_same_hash = (hash1 == hash2)
    diff_content_diff_hash = (hash3 != hash4)

    if same_content_same_hash and diff_content_diff_hash:
        print(f"✓ Hash behavior verified")
        print(f"  Same content: {hash1[:16]}... == {hash2[:16]}...")
        print(f"  Different content: {hash3[:16]}... != {hash4[:16]}...")
    else:
        print(f"✗ Hash behavior failed!")

    return same_content_same_hash and diff_content_diff_hash


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
