# tests/code/test_generator.py
import ast
from ccoding.code.generator import EdgeInfo, generate_class, generate_method
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


class TestEdgeAwareGeneration:
    """Tests for edge-driven code generation (inherits, implements, composes, depends)."""

    def _minimal_content(self, name: str = "ChildParser", stereotype: str | None = None) -> ClassContent:
        return ClassContent(
            name=name,
            stereotype=stereotype,
            responsibility="A test class",
            fields=[],
            methods=[],
        )

    def test_inherits_edge_adds_base_class(self):
        content = self._minimal_content("ChildParser")
        edge = EdgeInfo(
            relation="inherits",
            target_name="BaseParser",
            target_qname="parsers.base.BaseParser",
            label=None,
        )
        source = generate_class(content, edges=[edge])
        ast.parse(source)
        assert "class ChildParser(BaseParser):" in source
        assert "from parsers.base import BaseParser" in source

    def test_implements_edge_adds_to_bases(self):
        content = self._minimal_content("JsonParser")
        edge = EdgeInfo(
            relation="implements",
            target_name="DocumentParser",
            target_qname="parsers.protocols.DocumentParser",
            label=None,
        )
        source = generate_class(content, edges=[edge])
        ast.parse(source)
        assert "class JsonParser(DocumentParser):" in source
        assert "from parsers.protocols import DocumentParser" in source

    def test_composes_edge_adds_field(self):
        content = self._minimal_content("PipelineRunner")
        edge = EdgeInfo(
            relation="composes",
            target_name="ParserConfig",
            target_qname="parsers.config.ParserConfig",
            label="config",
        )
        source = generate_class(content, edges=[edge])
        ast.parse(source)
        assert "config: ParserConfig" in source
        assert "from parsers.config import ParserConfig" in source

    def test_composes_edge_label_with_description(self):
        """Label 'stages \u2014 Ordered list' should produce field name 'stages'."""
        content = self._minimal_content("Pipeline")
        edge = EdgeInfo(
            relation="composes",
            target_name="Stage",
            target_qname="pipeline.stages.Stage",
            label="stages \u2014 Ordered list of processing stages",
        )
        source = generate_class(content, edges=[edge])
        ast.parse(source)
        assert "stages: Stage" in source
        assert "from pipeline.stages import Stage" in source

    def test_depends_edge_adds_import(self):
        content = self._minimal_content("Runner")
        edge = EdgeInfo(
            relation="depends",
            target_name="Config",
            target_qname="core.config.Config",
            label=None,
        )
        source = generate_class(content, edges=[edge])
        ast.parse(source)
        assert "from core.config import Config" in source
        # depends should NOT add a base or a field (but may appear in Collaborators)
        assert "class Runner(Config)" not in source
        # After the closing docstring quotes, Config must not appear as a field
        body_after_docstring = source.split('"""')[-1]
        assert "Config" not in body_after_docstring

    def test_stereotype_plus_inherits(self):
        """abstract stereotype + inherits edge → both ABC and BaseParser in bases."""
        content = self._minimal_content("ChildParser", stereotype="abstract")
        edge = EdgeInfo(
            relation="inherits",
            target_name="BaseParser",
            target_qname="parsers.base.BaseParser",
            label=None,
        )
        source = generate_class(content, edges=[edge])
        ast.parse(source)
        assert "class ChildParser(ABC, BaseParser):" in source
        assert "from abc import ABC, abstractmethod" in source
        assert "from parsers.base import BaseParser" in source

    def test_multiple_edges(self):
        """inherits + composes + depends all together."""
        content = self._minimal_content("PipelineRunner")
        edges = [
            EdgeInfo(
                relation="inherits",
                target_name="BaseRunner",
                target_qname="runners.base.BaseRunner",
                label=None,
            ),
            EdgeInfo(
                relation="composes",
                target_name="ParserConfig",
                target_qname="parsers.config.ParserConfig",
                label="config",
            ),
            EdgeInfo(
                relation="depends",
                target_name="Logger",
                target_qname="utils.logging.Logger",
                label=None,
            ),
        ]
        source = generate_class(content, edges=edges)
        ast.parse(source)
        assert "class PipelineRunner(BaseRunner):" in source
        assert "from runners.base import BaseRunner" in source
        assert "config: ParserConfig" in source
        assert "from parsers.config import ParserConfig" in source
        assert "from utils.logging import Logger" in source

    def test_no_edges_backward_compatible(self):
        """Calling without edges works exactly as before."""
        content = ClassContent(
            name="DocumentParser",
            stereotype="protocol",
            responsibility="Parse raw documents into structured AST nodes",
            fields=[
                FieldEntry(name="config", type="ParserConfig", has_detail=False),
            ],
            methods=[
                MethodEntry(name="parse", signature="(source: str) -> AST", has_detail=False),
            ],
        )
        source = generate_class(content, language="python")
        ast.parse(source)
        assert "class DocumentParser(Protocol):" in source
        assert "from typing import Protocol" in source


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


class TestSnakeCaseFieldName:
    def test_camel_case_to_snake(self):
        from ccoding.code.generator import _field_name_from_label
        assert _field_name_from_label(None, "ParserConfig") == "parser_config"

    def test_multi_word_camel(self):
        from ccoding.code.generator import _field_name_from_label
        assert _field_name_from_label(None, "HTTPClient") == "http_client"

    def test_label_overrides_derivation(self):
        from ccoding.code.generator import _field_name_from_label
        assert _field_name_from_label("myField", "ParserConfig") == "myField"

    def test_em_dash_separator(self):
        from ccoding.code.generator import _field_name_from_label
        assert _field_name_from_label("config \u2014 parser settings", "ParserConfig") == "config"


class TestCollaboratorsSection:
    def test_collaborators_generated_from_edges(self):
        from ccoding.canvas.markdown import ClassContent, FieldEntry, MethodEntry
        from ccoding.code.generator import generate_class, EdgeInfo
        content = ClassContent(
            name="DocumentParser",
            stereotype="protocol",
            responsibility="Parse documents.",
            fields=[],
            methods=[],
        )
        edges = [
            EdgeInfo(relation="composes", target_name="ParserConfig",
                     target_qname="config.ParserConfig", label="config"),
            EdgeInfo(relation="depends", target_name="TokenStream",
                     target_qname="tokens.TokenStream", label=None),
        ]
        code = generate_class(content, "python", edges=edges)
        assert "Collaborators:" in code
        assert "ParserConfig" in code.split("Collaborators:")[1].split('"""')[0]
        assert "TokenStream" in code.split("Collaborators:")[1].split('"""')[0]

    def test_no_collaborators_without_edges(self):
        from ccoding.canvas.markdown import ClassContent, FieldEntry, MethodEntry
        from ccoding.code.generator import generate_class
        content = ClassContent(
            name="Simple",
            stereotype=None,
            responsibility="A simple class.",
            fields=[],
            methods=[],
        )
        code = generate_class(content, "python")
        assert "Collaborators:" not in code


class TestTypeTranslation:
    def test_field_types_translated_to_python(self):
        from ccoding.canvas.markdown import ClassContent, FieldEntry, MethodEntry
        from ccoding.code.generator import generate_class
        content = ClassContent(
            name="Foo",
            stereotype=None,
            responsibility="Test",
            fields=[FieldEntry(name="items", type="List<String>")],
            methods=[],
        )
        code = generate_class(content, "python")
        assert "list[str]" in code
        assert "List<String>" not in code

    def test_method_param_types_translated(self):
        from ccoding.canvas.markdown import ClassContent, FieldEntry, MethodEntry
        from ccoding.code.generator import generate_class
        content = ClassContent(
            name="Foo",
            stereotype=None,
            responsibility="Test",
            fields=[],
            methods=[MethodEntry(name="run", signature="(x: Integer) -> Boolean")],
        )
        code = generate_class(content, "python")
        assert "x: int" in code
        assert "-> bool" in code
