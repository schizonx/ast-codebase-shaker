"""Module B with circular import to A."""

from a import func_a


def func_b():
    """Call func_a from module A."""
    return func_a()
