"""Utility functions."""


def hash_password(password: str) -> str:
    """Hash a password."""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()
