"""Output serialization and delivery.

Markdown, XML, JSON, and plain text serializers plus output delivery.
"""

from shaker.output.clipboard import deliver
from shaker.output.json_serializer import serialize as serialize_json
from shaker.output.plain_serializer import serialize as serialize_plain
from shaker.output.serializer import serialize as serialize_markdown
from shaker.output.xml_serializer import serialize as serialize_xml

__all__ = [
    "deliver",
    "serialize_json",
    "serialize_markdown",
    "serialize_plain",
    "serialize_xml",
]
