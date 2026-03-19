# tests/code/test_types.py
import pytest
from ccoding.code.types import canvas_to_python, python_to_canvas


class TestCanvasToPython:
    def test_primitive_types(self):
        assert canvas_to_python("String") == "str"
        assert canvas_to_python("Integer") == "int"
        assert canvas_to_python("Boolean") == "bool"
        assert canvas_to_python("Float") == "float"
        assert canvas_to_python("Void") == "None"

    def test_generic_list(self):
        assert canvas_to_python("List<String>") == "list[str]"

    def test_generic_map(self):
        assert canvas_to_python("Map<String, Integer>") == "dict[str, int]"

    def test_generic_optional(self):
        assert canvas_to_python("Optional<String>") == "str | None"

    def test_generic_set(self):
        assert canvas_to_python("Set<Integer>") == "set[int]"

    def test_generic_tuple(self):
        assert canvas_to_python("Tuple<String, Integer>") == "tuple[str, int]"

    def test_generic_union(self):
        assert canvas_to_python("Union<String, Integer>") == "str | int"

    def test_nested_generics(self):
        assert canvas_to_python("List<Map<String, Integer>>") == "list[dict[str, int]]"
        assert canvas_to_python("Optional<List<String>>") == "list[str] | None"

    def test_custom_type_passthrough(self):
        assert canvas_to_python("ParserConfig") == "ParserConfig"
        assert canvas_to_python("AST") == "AST"

    def test_callable(self):
        assert canvas_to_python("Callable<[String, Integer], Boolean>") == "Callable[[str, int], bool]"

    def test_already_python_type(self):
        assert canvas_to_python("str") == "str"
        assert canvas_to_python("int") == "int"
        assert canvas_to_python("list[str]") == "list[str]"


class TestPythonToCanvas:
    def test_primitive_types(self):
        assert python_to_canvas("str") == "String"
        assert python_to_canvas("int") == "Integer"
        assert python_to_canvas("bool") == "Boolean"
        assert python_to_canvas("float") == "Float"
        assert python_to_canvas("None") == "Void"

    def test_generic_list(self):
        assert python_to_canvas("list[str]") == "List<String>"

    def test_generic_dict(self):
        assert python_to_canvas("dict[str, int]") == "Map<String, Integer>"

    def test_union_syntax(self):
        assert python_to_canvas("str | None") == "Optional<String>"
        assert python_to_canvas("str | int") == "Union<String, Integer>"

    def test_set(self):
        assert python_to_canvas("set[int]") == "Set<Integer>"

    def test_tuple(self):
        assert python_to_canvas("tuple[str, int]") == "Tuple<String, Integer>"

    def test_callable(self):
        assert python_to_canvas("Callable[[str, int], bool]") == "Callable<[String, Integer], Boolean>"

    def test_nested_generics(self):
        assert python_to_canvas("list[dict[str, int]]") == "List<Map<String, Integer>>"

    def test_custom_type_passthrough(self):
        assert python_to_canvas("ParserConfig") == "ParserConfig"
        assert python_to_canvas("AST") == "AST"

    def test_already_canvas_type(self):
        assert python_to_canvas("String") == "String"
