from dataclasses import dataclass
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats."""
    JSON = "json"
    XML = "xml"


@dataclass
class ParserConfig:
    """Configuration for the document parser.

    Responsibility:
        Holds all parser settings.

    Attributes:
        format: Output format selection.
        max_depth: Maximum nesting depth.
    """

    format: OutputFormat = OutputFormat.JSON
    max_depth: int = 10
