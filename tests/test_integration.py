# tests/test_integration.py
"""End-to-end test: import codebase → propose changes → accept → sync."""
from pathlib import Path
import ccoding


class TestEndToEnd:
    def test_full_workflow(self, tmp_project: Path, fixtures_dir: Path):
        project = tmp_project
        canvas_path = project / "design.canvas"

        # 1. Import existing code
        result = ccoding.import_codebase(
            source_dir=fixtures_dir / "sample_python",
            canvas_path=canvas_path,
            project_root=project,
            language="python",
        )
        assert len(result.code_to_canvas) > 0

        # 2. Read the canvas
        canvas = ccoding.read_canvas(canvas_path)
        initial_count = len(canvas.nodes)
        assert initial_count >= 3  # DocumentParser, OutputFormat, ParserConfig

        # 3. Agent proposes a new class
        ghost = ccoding.propose_node(
            canvas,
            kind="class",
            name="CacheManager",
            content="## CacheManager\n\n> Manages AST caching",
            rationale="Extract caching from DocumentParser",
        )
        assert ghost.ccoding.status == "proposed"
        # Agent sets qualified name and language so sync can track the node
        ghost.ccoding.qualified_name = "cache_manager.CacheManager"
        ghost.ccoding.language = "python"

        # 4. Save canvas with ghost
        ccoding.write_canvas(canvas, canvas_path)

        # 5. Verify ghost appears
        ghosts = ccoding.list_ghosts(canvas)
        assert len(ghosts) == 1

        # 6. Accept the ghost
        ccoding.accept_node(canvas, ghost.id)
        ccoding.write_canvas(canvas, canvas_path)

        # 7. Sync should generate code for the new class
        sync_result = ccoding.sync(
            canvas_path=canvas_path,
            project_root=project,
        )
        # The newly accepted node should trigger code generation
        assert len(sync_result.canvas_to_code) > 0

        # 8. Verify no conflicts
        assert sync_result.conflicts == []
