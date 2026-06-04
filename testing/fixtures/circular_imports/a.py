"""Module A with circular import to B."""

from b import func_b


def func_a():
    """Call func_b from module B."""
    return func_b()
