from ccoding.canvas.markdown import (
    parse_class_node, render_class_node,
    parse_method_node, render_method_node,
    parse_field_node, render_field_node,
    ClassContent, MethodContent, FieldContent,
    FieldEntry, MethodEntry, SignatureEntry,
)


class TestClassNode:
    SAMPLE = (
        "«protocol»\n"
        "## DocumentParser\n"
        "\n"
        "> Responsible for parsing raw documents into structured AST nodes\n"
        "\n"
        "### Fields\n"
        "- config: `ParserConfig` ●\n"
        "- _cache: `dict[str, AST]`\n"
        "\n"
        "### Methods\n"
        "- parse(source: `str`) -> `AST` ●\n"
        "- validate(ast: `AST`) -> `bool`\n"
    )

    def test_parse_class(self):
        result = parse_class_node(self.SAMPLE)
        assert result.name == "DocumentParser"
        assert result.stereotype == "protocol"
        assert result.responsibility == "Responsible for parsing raw documents into structured AST nodes"
        assert len(result.fields) == 2
        assert result.fields[0].name == "config"
        assert result.fields[0].type == "ParserConfig"
        assert result.fields[0].has_detail is True
        assert result.fields[1].has_detail is False
        assert len(result.methods) == 2
        assert result.methods[0].name == "parse"
        assert result.methods[0].has_detail is True

    def test_round_trip(self):
        parsed = parse_class_node(self.SAMPLE)
        rendered = render_class_node(parsed)
        reparsed = parse_class_node(rendered)
        assert reparsed.name == parsed.name
        assert reparsed.stereotype == parsed.stereotype
        assert len(reparsed.fields) == len(parsed.fields)
        assert len(reparsed.methods) == len(parsed.methods)


class TestMethodNode:
    SAMPLE = (
        "## DocumentParser.parse\n"
        "\n"
        "### Responsibility\n"
        "Transform raw source into a validated AST.\n"
        "\n"
        "### Signature\n"
        "- **IN:** source: `str` — raw document text\n"
        "- **OUT:** `AST` — parsed syntax tree\n"
        "- **RAISES:** `ParseError` — on malformed input\n"
        "\n"
        "### Pseudo Code\n"
        "1. Check _cache for source hash\n"
        "2. If cached, return cached AST\n"
        "3. Tokenize source\n"
    )

    def test_parse_method(self):
        result = parse_method_node(self.SAMPLE)
        assert result.name == "DocumentParser.parse"
        assert result.responsibility == "Transform raw source into a validated AST."
        assert len(result.signature_in) == 1
        assert result.signature_in[0].name == "source"
        assert result.signature_in[0].type == "str"
        assert result.signature_out.type == "AST"
        assert len(result.raises) == 1
        assert result.pseudo_code.startswith("1.")

    def test_round_trip(self):
        parsed = parse_method_node(self.SAMPLE)
        rendered = render_method_node(parsed)
        reparsed = parse_method_node(rendered)
        assert reparsed.name == parsed.name
        assert len(reparsed.signature_in) == len(parsed.signature_in)


class TestFieldNode:
    SAMPLE = (
        "## DocumentParser.config\n"
        "\n"
        "### Responsibility\n"
        "Holds parser configuration.\n"
        "\n"
        "### Type\n"
        "`ParserConfig`\n"
        "\n"
        "### Constraints\n"
        "- Immutable after initialization\n"
        "\n"
        "### Default\n"
        "ParserConfig.default()\n"
    )

    def test_parse_field(self):
        result = parse_field_node(self.SAMPLE)
        assert result.name == "DocumentParser.config"
        assert result.responsibility == "Holds parser configuration."
        assert result.type == "ParserConfig"
        assert "Immutable" in result.constraints
        assert result.default == "ParserConfig.default()"

    def test_round_trip(self):
        parsed = parse_field_node(self.SAMPLE)
        rendered = render_field_node(parsed)
        reparsed = parse_field_node(rendered)
        assert reparsed.name == parsed.name
        assert reparsed.type == parsed.type
