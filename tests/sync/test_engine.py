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
