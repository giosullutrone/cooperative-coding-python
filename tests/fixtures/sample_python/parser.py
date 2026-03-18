from typing import Protocol


class DocumentParser(Protocol):
    """Parse raw documents into structured AST nodes.

    Responsibility:
        Owns the full parsing pipeline from raw text to validated AST.

    Collaborators:
        ParserConfig: Provides tokenizer settings.

    Attributes:
        config: Parser configuration and settings.
        plugins: Ordered list of transform plugins.
    """

    config: "ParserConfig"
    plugins: list["ParserPlugin"]

    def parse(self, source: str) -> "AST":
        """Transform raw source into a validated AST.

        Responsibility:
            Parse raw document text into structured AST nodes.

        Pseudo Code:
            1. Check _cache for source hash
            2. Tokenize source
            3. Build raw AST

        Args:
            source: Raw document text to parse.

        Returns:
            Parsed abstract syntax tree.

        Raises:
            ParseError: If the source is malformed.
        """
        ...

    def validate(self, ast: "AST") -> bool:
        """Validate an AST structure."""
        ...
