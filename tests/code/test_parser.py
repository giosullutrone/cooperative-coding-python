# tests/code/test_parser.py
from pathlib import Path
from ccoding.code.parser import PythonAstParser, ClassElement, MethodElement, FieldElement


class TestPythonAstParser:
    def test_parse_protocol(self, fixtures_dir: Path):
        parser = PythonAstParser()
        elements = parser.parse_file(fixtures_dir / "sample_python" / "parser.py")
        classes = [e for e in elements if isinstance(e, ClassElement)]
        assert len(classes) == 1
        cls = classes[0]
        assert cls.name == "DocumentParser"
        assert cls.stereotype == "protocol"
        assert "Owns the full parsing pipeline" in cls.docstring_sections.get("responsibility", "")

    def test_parse_methods(self, fixtures_dir: Path):
        parser = PythonAstParser()
        elements = parser.parse_file(fixtures_dir / "sample_python" / "parser.py")
        classes = [e for e in elements if isinstance(e, ClassElement)]
        cls = classes[0]
        assert len(cls.methods) == 2
        parse_method = cls.methods[0]
        assert parse_method.name == "parse"
        assert len(parse_method.parameters) > 0
        assert parse_method.return_type == "AST"
        assert "Check _cache" in parse_method.docstring_sections.get("pseudo code", "")

    def test_parse_fields(self, fixtures_dir: Path):
        parser = PythonAstParser()
        elements = parser.parse_file(fixtures_dir / "sample_python" / "parser.py")
        classes = [e for e in elements if isinstance(e, ClassElement)]
        cls = classes[0]
        assert len(cls.fields) == 2
        assert cls.fields[0].name == "config"
        assert cls.fields[0].type_annotation == "ParserConfig"

    def test_parse_dataclass(self, fixtures_dir: Path):
        parser = PythonAstParser()
        elements = parser.parse_file(fixtures_dir / "sample_python" / "models.py")
        classes = [e for e in elements if isinstance(e, ClassElement)]
        names = {c.name: c for c in classes}
        assert "ParserConfig" in names
        assert names["ParserConfig"].stereotype == "dataclass"
        assert "OutputFormat" in names
        assert names["OutputFormat"].stereotype == "enum"

    def test_parse_directory(self, fixtures_dir: Path):
        parser = PythonAstParser()
        elements = parser.parse_directory(fixtures_dir / "sample_python")
        classes = [e for e in elements if isinstance(e, ClassElement)]
        names = {c.name for c in classes}
        assert names == {"DocumentParser", "OutputFormat", "ParserConfig"}

    def test_skips_non_architectural_dunders(self, tmp_path: Path):
        src = tmp_path / "example.py"
        src.write_text('''
class Foo:
    def __init__(self, x: int):
        self.x = x

    def __repr__(self) -> str:
        return f"Foo({self.x})"

    def do_stuff(self) -> None:
        pass
''')
        parser = PythonAstParser()
        elements = parser.parse_file(src)
        classes = [e for e in elements if isinstance(e, ClassElement)]
        method_names = [m.name for m in classes[0].methods]
        assert "__init__" in method_names
        assert "__repr__" not in method_names
        assert "do_stuff" in method_names
