# tests/sync/test_engine.py
import json
from pathlib import Path
from ccoding.sync.engine import sync, import_codebase, SyncResult
from ccoding.sync.state import load_sync_state
from ccoding.canvas.reader import read_canvas
from ccoding.canvas.writer import write_canvas


class TestImportCodebase:
    def test_import_creates_canvas(self, tmp_project: Path, fixtures_dir: Path):
        canvas_path = tmp_project / "design.canvas"
        result = import_codebase(
            source_dir=fixtures_dir / "sample_python",
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )
        canvas = read_canvas(canvas_path)
        class_names = {
            n.ccoding.qualified_name
            for n in canvas.nodes
            if n.ccoding and n.ccoding.kind == "class"
        }
        assert len(class_names) >= 3
        for n in canvas.nodes:
            if n.ccoding:
                assert n.ccoding.status == "accepted"
                assert n.ccoding.layout_pending is True
        state = load_sync_state(tmp_project)
        assert len(state.elements) > 0


class TestSync:
    def test_sync_no_changes(self, tmp_project: Path, fixtures_dir: Path):
        import shutil
        canvas_path = tmp_project / "design.canvas"
        src_dir = tmp_project / "src"
        for f in (fixtures_dir / "sample_python").glob("*.py"):
            shutil.copy(f, src_dir / f.name)
        import_codebase(
            source_dir=src_dir,
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )
        result = sync(canvas_path=canvas_path, project_root=tmp_project)
        assert result.conflicts == []
        assert result.canvas_to_code == []
        assert result.code_to_canvas == []

    def test_sync_detects_code_addition(self, tmp_project: Path):
        canvas_path = tmp_project / "design.canvas"
        src_dir = tmp_project / "src"
        (src_dir / "new_module.py").write_text(
            'class NewClass:\n    """A new class.\n\n    Responsibility:\n        Does new things.\n    """\n    pass\n'
        )
        result = sync(canvas_path=canvas_path, project_root=tmp_project)
        assert len(result.code_to_canvas) > 0
        canvas = read_canvas(canvas_path)
        names = {
            n.ccoding.qualified_name
            for n in canvas.nodes
            if n.ccoding and n.ccoding.kind == "class"
        }
        assert any("NewClass" in name for name in names)


class TestSyncSkipsRejected:
    def test_rejected_nodes_excluded_from_sync(self, tmp_project: Path, fixtures_dir: Path):
        """Rejected nodes must not participate in sync hashing or code generation."""
        canvas_path = tmp_project / "design.canvas"
        import_codebase(
            source_dir=fixtures_dir / "sample_python",
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )
        # Manually set a node to rejected status
        canvas = read_canvas(canvas_path)
        target_node = None
        for node in canvas.nodes:
            if node.ccoding and node.ccoding.qualified_name:
                target_node = node
                break
        assert target_node is not None
        target_node.ccoding.status = "rejected"
        write_canvas(canvas, canvas_path)

        # Sync should not try to process the rejected node
        result = sync(canvas_path=canvas_path, project_root=tmp_project)
        qname = target_node.ccoding.qualified_name
        assert qname not in result.canvas_to_code
        assert qname not in result.code_to_canvas


class TestSyncSkipsStale:
    def test_stale_nodes_excluded_from_sync(self, tmp_project: Path, fixtures_dir: Path):
        """Stale nodes must not participate in sync."""
        import shutil
        canvas_path = tmp_project / "design.canvas"
        src_dir = tmp_project / "src"
        shutil.copytree(fixtures_dir / "sample_python", src_dir, dirs_exist_ok=True)

        import_codebase(
            source_dir=src_dir,
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )
        canvas = read_canvas(canvas_path)
        state = load_sync_state(tmp_project)
        qname = next(iter(state.elements))
        node = canvas.find_by_qualified_name(qname)
        node.ccoding.status = "stale"
        from ccoding.canvas.writer import write_canvas
        write_canvas(canvas, canvas_path)

        result = sync(canvas_path=canvas_path, project_root=tmp_project)
        assert qname not in result.canvas_to_code


class TestSyncStaleHandling:
    def test_canvas_deleted_deprecates_code(self, tmp_project: Path, fixtures_dir: Path):
        """When a canvas node is deleted, the corresponding code should be deprecated."""
        import shutil
        canvas_path = tmp_project / "design.canvas"
        src_dir = tmp_project / "src"

        # Copy fixtures to temp project
        shutil.copytree(fixtures_dir / "sample_python", src_dir, dirs_exist_ok=True)

        import_codebase(
            source_dir=src_dir,
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )

        # Pick a node and remember its source file
        state = load_sync_state(tmp_project)
        qname = next(iter(state.elements))
        elem_state = state.elements[qname]
        source_file = tmp_project / elem_state.source_path
        assert source_file.exists()

        # Delete the node from the canvas
        canvas = read_canvas(canvas_path)
        canvas.nodes = [n for n in canvas.nodes
                        if not (n.ccoding and n.ccoding.qualified_name == qname)]
        write_canvas(canvas, canvas_path)

        # Sync should deprecate the code
        result = sync(canvas_path=canvas_path, project_root=tmp_project)

        # Check that the code file has a deprecation marker
        if source_file.exists():
            code = source_file.read_text()
            class_name = qname.rsplit(".", 1)[-1]
            assert "DEPRECATED" in code or "deprecated" in code

    def test_code_deleted_marks_canvas_stale(self, tmp_project: Path, fixtures_dir: Path):
        """When code is deleted, the sync engine must mark the canvas node as stale."""
        import shutil
        canvas_path = tmp_project / "design.canvas"
        src_dir = tmp_project / "src"
        for f in (fixtures_dir / "sample_python").glob("*.py"):
            shutil.copy(f, src_dir / f.name)
        import_codebase(
            source_dir=src_dir,
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )
        # Find a source file and delete it
        state = load_sync_state(tmp_project)
        qname = next(iter(state.elements))
        elem_state = state.elements[qname]
        source_file = tmp_project / elem_state.source_path
        source_file.unlink()

        # Sync should detect deletion and mark the canvas node stale
        result = sync(canvas_path=canvas_path, project_root=tmp_project)
        canvas = read_canvas(canvas_path)
        node = canvas.find_by_qualified_name(qname)
        assert node is not None
        assert node.ccoding.status == "stale"


class TestSyncEdgeAwareCodeGeneration:
    """Verify that canvas edges are read and passed to the code generator."""

    def _make_canvas_json(
        self,
        nodes: list[dict],
        edges: list[dict],
    ) -> str:
        return json.dumps({"nodes": nodes, "edges": edges})

    def test_canvas_inherits_edge_generates_base_class(self, tmp_project: Path):
        """An 'inherits' edge should cause the child class to extend the base class."""
        canvas_path = tmp_project / "design.canvas"
        src_dir = tmp_project / "src"

        canvas_data = self._make_canvas_json(
            nodes=[
                {
                    "id": "node-base",
                    "type": "text",
                    "x": 0, "y": 0, "width": 320, "height": 280,
                    "text": "## BaseParser\n\n**Responsibility:** Base parser class.\n",
                    "ccoding": {
                        "kind": "class",
                        "qualifiedName": "parsers.base.BaseParser",
                        "status": "accepted",
                        "language": "python",
                        "source": "src/parsers/base.py",
                    },
                },
                {
                    "id": "node-child",
                    "type": "text",
                    "x": 400, "y": 0, "width": 320, "height": 280,
                    "text": "## CsvParser\n\n**Responsibility:** Parses CSV files.\n",
                    "ccoding": {
                        "kind": "class",
                        "qualifiedName": "parsers.csv_parser.CsvParser",
                        "status": "accepted",
                        "language": "python",
                        "source": "src/parsers/csv_parser.py",
                    },
                },
            ],
            edges=[
                {
                    "id": "edge-001",
                    "fromNode": "node-child",
                    "toNode": "node-base",
                    "label": "inherits",
                    "ccoding": {
                        "relation": "inherits",
                        "status": "accepted",
                    },
                },
            ],
        )
        canvas_path.write_text(canvas_data)

        result = sync(canvas_path=canvas_path, project_root=tmp_project)

        # CsvParser should have been generated
        assert any("CsvParser" in qname for qname in result.canvas_to_code)

        child_file = src_dir / "parsers" / "csv_parser.py"
        assert child_file.exists(), f"Expected generated file at {child_file}"
        code = child_file.read_text()

        # The child class declaration should extend BaseParser
        assert "BaseParser" in code, (
            f"Expected 'BaseParser' in generated code:\n{code}"
        )
        assert "class CsvParser(BaseParser)" in code or "class CsvParser(BaseParser," in code, (
            f"Expected class declaration with BaseParser base in:\n{code}"
        )

    def test_canvas_composes_edge_generates_field(self, tmp_project: Path):
        """A 'composes' edge with a label should produce a typed field in the child class."""
        canvas_path = tmp_project / "design.canvas"
        src_dir = tmp_project / "src"

        canvas_data = self._make_canvas_json(
            nodes=[
                {
                    "id": "node-config",
                    "type": "text",
                    "x": 0, "y": 0, "width": 320, "height": 280,
                    "text": "## ParserConfig\n\n**Responsibility:** Parser configuration holder.\n",
                    "ccoding": {
                        "kind": "class",
                        "qualifiedName": "parsers.config.ParserConfig",
                        "status": "accepted",
                        "language": "python",
                        "source": "src/parsers/config.py",
                    },
                },
                {
                    "id": "node-parser",
                    "type": "text",
                    "x": 400, "y": 0, "width": 320, "height": 280,
                    "text": "## SmartParser\n\n**Responsibility:** Smart parser that uses config.\n",
                    "ccoding": {
                        "kind": "class",
                        "qualifiedName": "parsers.smart.SmartParser",
                        "status": "accepted",
                        "language": "python",
                        "source": "src/parsers/smart.py",
                    },
                },
            ],
            edges=[
                {
                    "id": "edge-002",
                    "fromNode": "node-parser",
                    "toNode": "node-config",
                    "label": "config \u2014 Parser settings",
                    "ccoding": {
                        "relation": "composes",
                        "status": "accepted",
                    },
                },
            ],
        )
        canvas_path.write_text(canvas_data)

        result = sync(canvas_path=canvas_path, project_root=tmp_project)

        # SmartParser should have been generated
        assert any("SmartParser" in qname for qname in result.canvas_to_code), (
            f"Expected SmartParser in canvas_to_code, got: {result.canvas_to_code}"
        )

        parser_file = src_dir / "parsers" / "smart.py"
        assert parser_file.exists(), f"Expected generated file at {parser_file}"
        code = parser_file.read_text()

        # The composed field should appear as "config: ParserConfig"
        assert "config: ParserConfig" in code, (
            f"Expected 'config: ParserConfig' field in generated code:\n{code}"
        )


class TestEdgeCreationFromCode:
    """Verify that composes and depends edges are created when importing or syncing code."""

    def test_import_creates_composes_edges(self, tmp_project: Path):
        """Typed field references to tracked classes produce composes edges on import."""
        src_dir = tmp_project / "src"
        canvas_path = tmp_project / "design.canvas"

        # Write Config class
        (src_dir / "config.py").write_text(
            'class Config:\n'
            '    """Configuration holder.\n\n'
            '    Responsibility:\n'
            '        Holds configuration values.\n'
            '    """\n'
            '    value: str\n'
        )
        # Write Parser class with a field typed as Config
        (src_dir / "parser.py").write_text(
            'class Parser:\n'
            '    """Parses input.\n\n'
            '    Responsibility:\n'
            '        Parses things.\n'
            '    """\n'
            '    config: Config\n'
        )

        import_codebase(
            source_dir=src_dir,
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )

        canvas = read_canvas(canvas_path)

        composes_edges = [
            e for e in canvas.edges
            if e.ccoding and e.ccoding.relation == "composes"
        ]
        assert len(composes_edges) >= 1, (
            f"Expected at least one composes edge, got: {canvas.edges}"
        )
        assert any("config" in (e.label or "") for e in composes_edges), (
            f"Expected a composes edge with label containing 'config', got: {composes_edges}"
        )

    def test_import_creates_depends_edges(self, tmp_project: Path):
        """Import statements referencing tracked classes produce depends edges on import."""
        src_dir = tmp_project / "src"
        canvas_path = tmp_project / "design.canvas"

        # Write Config class
        (src_dir / "config.py").write_text(
            'class Config:\n'
            '    """Configuration holder.\n\n'
            '    Responsibility:\n'
            '        Holds configuration values.\n'
            '    """\n'
            '    value: str\n'
        )
        # Write Parser class that imports Config (no typed field — pure import dependency)
        (src_dir / "parser.py").write_text(
            'from config import Config\n'
            '\n'
            'class Parser:\n'
            '    """Parses input.\n\n'
            '    Responsibility:\n'
            '        Parses things.\n'
            '    """\n'
            '    pass\n'
        )

        import_codebase(
            source_dir=src_dir,
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )

        canvas = read_canvas(canvas_path)

        depends_edges = [
            e for e in canvas.edges
            if e.ccoding and e.ccoding.relation == "depends"
        ]
        assert len(depends_edges) >= 1, (
            f"Expected at least one depends edge, got: {canvas.edges}"
        )

    def test_sync_code_added_creates_edges(self, tmp_project: Path):
        """When sync detects a code-added class with a typed field, a composes edge is created."""
        src_dir = tmp_project / "src"
        canvas_path = tmp_project / "design.canvas"

        # Pre-populate with Config class and import it
        (src_dir / "config.py").write_text(
            'class Config:\n'
            '    """Configuration holder.\n\n'
            '    Responsibility:\n'
            '        Holds configuration values.\n'
            '    """\n'
            '    value: str\n'
        )

        import_codebase(
            source_dir=src_dir,
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )

        # Now add a Runner class that uses Config
        (src_dir / "runner.py").write_text(
            'class Runner:\n'
            '    """Runs the application.\n\n'
            '    Responsibility:\n'
            '        Executes tasks.\n'
            '    """\n'
            '    config: Config\n'
        )

        # Sync — Runner is code_added, should trigger edge creation
        sync(canvas_path=canvas_path, project_root=tmp_project)

        canvas = read_canvas(canvas_path)

        composes_edges = [
            e for e in canvas.edges
            if e.ccoding and e.ccoding.relation == "composes"
        ]
        assert len(composes_edges) >= 1, (
            f"Expected at least one composes edge after sync, got: {canvas.edges}"
        )
        assert any("config" in (e.label or "") for e in composes_edges), (
            f"Expected a composes edge with label containing 'config', got: {composes_edges}"
        )


class TestDetailNodePromotion:
    """Verify that methods with significant docs are promoted to detail nodes."""

    def test_import_promotes_method_with_pseudocode(self, tmp_project: Path):
        """Methods with Responsibility + Pseudo Code sections are promoted to detail nodes."""
        src_dir = tmp_project / "src"
        canvas_path = tmp_project / "design.canvas"

        (src_dir / "worker.py").write_text(
            'class Worker:\n'
            '    """A worker class.\n\n'
            '    Responsibility:\n'
            '        Processes tasks.\n'
            '    """\n'
            '\n'
            '    def process(self, task: str) -> bool:\n'
            '        """Process a task.\n\n'
            '        Responsibility:\n'
            '            Execute the given task and return success status.\n\n'
            '        Pseudo Code:\n'
            '            1. Validate task\n'
            '            2. Execute task\n'
            '            3. Return result\n'
            '        """\n'
            '        pass\n'
            '\n'
            '    def status(self) -> str:\n'
            '        """Return worker status."""\n'
            '        return "idle"\n'
        )

        import_codebase(
            source_dir=src_dir,
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )

        canvas = read_canvas(canvas_path)

        # At least one detail edge must exist
        detail_edges = [
            e for e in canvas.edges
            if e.ccoding and e.ccoding.relation == "detail"
        ]
        assert len(detail_edges) >= 1, (
            f"Expected at least one detail edge, got: {canvas.edges}"
        )

        # At least one method node with "process" in qualified_name
        method_nodes = [
            n for n in canvas.nodes
            if n.ccoding and n.ccoding.kind == "method"
        ]
        assert any(
            "process" in (n.ccoding.qualified_name or "")
            for n in method_nodes
        ), f"Expected a method node with 'process' in qualified_name, got: {method_nodes}"

        # The method node text must contain "Pseudo Code"
        assert any(
            "Pseudo Code" in n.text
            for n in method_nodes
            if "process" in (n.ccoding.qualified_name or "")
        ), "Expected 'Pseudo Code' in method detail node text"

        # The class node text must contain the "●" detail marker
        class_nodes = [
            n for n in canvas.nodes
            if n.ccoding and n.ccoding.kind == "class"
        ]
        assert any(
            "●" in n.text
            for n in class_nodes
        ), "Expected '●' detail marker in class node text"

    def test_simple_method_not_promoted(self, tmp_project: Path):
        """Methods without Responsibility or Pseudo Code sections are NOT promoted."""
        src_dir = tmp_project / "src"
        canvas_path = tmp_project / "design.canvas"

        (src_dir / "simple.py").write_text(
            'class Simple:\n'
            '    """A simple class."""\n'
            '\n'
            '    def greet(self) -> str:\n'
            '        """Return a greeting."""\n'
            '        return "hello"\n'
            '\n'
            '    def farewell(self) -> str:\n'
            '        """Return a farewell."""\n'
            '        return "bye"\n'
        )

        import_codebase(
            source_dir=src_dir,
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )

        canvas = read_canvas(canvas_path)

        method_nodes = [
            n for n in canvas.nodes
            if n.ccoding and n.ccoding.kind == "method"
        ]
        assert len(method_nodes) == 0, (
            f"Expected 0 method nodes for simple methods, got: {method_nodes}"
        )


class TestLastSyncTimestamp:
    def test_sync_sets_last_sync(self, tmp_project: Path, fixtures_dir: Path):
        """After sync, the sync state file must contain a non-null lastSync."""
        canvas_path = tmp_project / "design.canvas"
        import_codebase(
            source_dir=fixtures_dir / "sample_python",
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )
        state_raw = json.loads((tmp_project / ".ccoding" / "sync-state.json").read_text())
        assert state_raw["lastSync"] is not None


class TestSpecVersion:
    def test_import_sets_spec_version(self, tmp_project: Path, fixtures_dir: Path):
        """import_codebase must set specVersion in the canvas."""
        canvas_path = tmp_project / "design.canvas"
        import_codebase(
            source_dir=fixtures_dir / "sample_python",
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )
        raw = json.loads(canvas_path.read_text())
        ccoding_meta = raw.get("ccoding", {})
        assert "specVersion" in ccoding_meta
        assert ccoding_meta["specVersion"] == "1.0.0"
