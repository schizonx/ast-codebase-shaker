"""Authentication module."""

from db import query_user
from utils import hash_password


def login(username: str, password: str):
    """Authenticate a user."""
    hashed = hash_password(password)
    user = query_user(username)
    if user and user.password_hash == hashed:
        return user
    return None


def logout(user) -> None:
    """Log out a user."""
    user.session = None
