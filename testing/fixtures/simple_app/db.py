"""Database module."""


def query_user(username: str):
    """Look up a user by username."""
    return _db_get("users", username)


def _db_get(table: str, key: str):
    """Simulated database lookup."""
    return None
