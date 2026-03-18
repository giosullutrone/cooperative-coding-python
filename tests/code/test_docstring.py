# tests/code/test_docstring.py
from ccoding.code.docstring import parse_docstring, render_docstring


class TestParseDocstring:
    def test_class_docstring(self):
        doc = '''Parse raw documents into structured AST nodes.

    Responsibility:
        Owns the full parsing pipeline from raw text to validated AST.

    Collaborators:
        ParserConfig: Provides tokenizer settings.
        ParserPlugin: Transforms AST during parsing.

    Attributes:
        config: Parser configuration and settings.
        plugins: Ordered list of transform plugins.
    '''
        sections = parse_docstring(doc)
        assert sections["summary"] == "Parse raw documents into structured AST nodes."
        assert "Owns the full parsing pipeline" in sections["responsibility"]
        assert "ParserConfig" in sections["collaborators"]
        assert "config" in sections["attributes"]

    def test_method_docstring(self):
        doc = '''Transform raw source into a validated AST.

    Responsibility:
        Parse raw document text into structured AST nodes.

    Pseudo Code:
        1. Check _cache for source hash
        2. If cached, return cached AST
        3. Tokenize source

    Args:
        source: Raw document text to parse.

    Returns:
        Parsed and validated abstract syntax tree.

    Raises:
        ParseError: If the source is malformed.
    '''
        sections = parse_docstring(doc)
        assert sections["summary"] == "Transform raw source into a validated AST."
        assert "Check _cache" in sections["pseudo code"]
        assert "source" in sections["args"]
        assert "ParseError" in sections["raises"]

    def test_empty_docstring(self):
        sections = parse_docstring("")
        assert sections["summary"] == ""

    def test_summary_only(self):
        sections = parse_docstring("Just a summary.")
        assert sections["summary"] == "Just a summary."


class TestRenderDocstring:
    def test_round_trip(self):
        original = {
            "summary": "Parse documents.",
            "responsibility": "Owns parsing pipeline.",
            "args": "source: Raw text.",
            "returns": "Parsed AST.",
        }
        rendered = render_docstring(original)
        reparsed = parse_docstring(rendered)
        assert reparsed["summary"] == original["summary"]
        assert reparsed["responsibility"] == original["responsibility"]
