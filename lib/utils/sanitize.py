"""
Log Sanitization Utilities

Provides functions to sanitize sensitive data before logging.

Author: Iteration 2 - User Authentication
Created: 2026-03-01
"""

# Sensitive field names that should be masked in logs
SENSITIVE_KEYS = {
    'password',
    'password_hash',
    'access_token',
    'refresh_token',
    'secret',
    'token',
    'api_key',
    'apikey',
    'authorization',
    'credential',
    'credentials',
}


def sanitize_for_log(data: dict) -> dict:
    """
    Remove sensitive fields from a dictionary for safe logging.

    Recursively processes nested dictionaries.

    Args:
        data: Dictionary potentially containing sensitive data

    Returns:
        Dictionary with sensitive values replaced by '***'

    Example:
        >>> sanitize_for_log({'username': 'john', 'password': 'secret123'})
        {'username': 'john', 'password': '***'}
    """
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        key_lower = key.lower()
        if key_lower in SENSITIVE_KEYS:
            result[key] = '***'
        elif isinstance(value, dict):
            result[key] = sanitize_for_log(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_for_log(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value

    return result
