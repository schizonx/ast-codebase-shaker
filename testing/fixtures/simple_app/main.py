"""Main entry point for the simple app fixture."""

from auth import login, logout
from db import query_user


def main():
    """Run the application."""
    user = login("admin", "secret")
    if user:
        data = query_user(user.id)
        print(data)
        logout(user)
    return 0


if __name__ == "__main__":
    exit(main())
