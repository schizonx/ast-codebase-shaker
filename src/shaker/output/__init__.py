"""Output serialization and delivery.

Markdown construction (serializer) and output delivery (clipboard + file).
"""

from shaker.output.clipboard import deliver
from shaker.output.serializer import serialize

__all__ = ["deliver", "serialize"]
