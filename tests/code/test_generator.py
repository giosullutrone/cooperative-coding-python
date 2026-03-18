# tests/code/test_generator.py
import ast
from ccoding.code.generator import generate_class, generate_method
from ccoding.canvas.markdown import ClassContent, MethodContent, FieldEntry, MethodEntry, SignatureEntry


class TestGenerateClass:
    def test_generate_protocol(self):
        content = ClassContent(
            name="DocumentParser",
            stereotype="protocol",
            responsibility="Parse raw documents into structured AST nodes",
            fields=[
                FieldEntry(name="config", type="ParserConfig", has_detail=False),
                FieldEntry(name="plugins", type="list[ParserPlugin]", has_detail=False),
            ],
            methods=[
                MethodEntry(name="parse", signature="(source: str) -> AST", has_detail=False),
            ],
        )
        source = generate_class(content, language="python")
        ast.parse(source)  # Must be valid Python
        assert "class DocumentParser(Protocol):" in source
        assert "from typing import Protocol" in source
        assert "config: ParserConfig" in source
        assert "def parse(self, source: str) -> AST:" in source

    def test_generate_dataclass(self):
        content = ClassContent(
            name="Config",
            stereotype="dataclass",
            responsibility="Holds settings",
            fields=[
                FieldEntry(name="max_depth", type="int", has_detail=False),
            ],
            methods=[],
        )
        source = generate_class(content, language="python")
        ast.parse(source)
        assert "@dataclass" in source
        assert "from dataclasses import dataclass" in source

    def test_generate_abstract(self):
        content = ClassContent(
            name="BaseParser",
            stereotype="abstract",
            responsibility="Abstract base for parsers",
            fields=[],
            methods=[
                MethodEntry(name="parse", signature="(source: str) -> AST", has_detail=False),
            ],
        )
        source = generate_class(content, language="python")
        ast.parse(source)
        assert "class BaseParser(ABC):" in source
        assert "@abstractmethod" in source


class TestGenerateMethod:
    def test_generate_method_with_pseudo_code(self):
        content = MethodContent(
            name="DocumentParser.parse",
            responsibility="Transform raw source into validated AST.",
            signature_in=[SignatureEntry(name="source", type="str", description="raw text")],
            signature_out=SignatureEntry(name="", type="AST", description="parsed tree"),
            raises=[SignatureEntry(name="", type="ParseError", description="on bad input")],
            pseudo_code="1. Tokenize source\n2. Build AST\n3. Validate",
        )
        source = generate_method(content)
        assert "def parse(self, source: str) -> AST:" in source
        assert "Pseudo Code:" in source
        assert "Tokenize source" in source
