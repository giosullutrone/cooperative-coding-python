# tests/test_integration.py
"""End-to-end test: import codebase → propose changes → accept → sync."""
import shutil
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


class TestEdgeAwareRoundTrip:
    def test_full_round_trip_with_edges(self, tmp_project: Path, fixtures_dir: Path):
        project = tmp_project
        canvas_path = project / "design.canvas"
        src_dir = project / "src"

        # Copy sample fixtures into the tmp_project src directory
        shutil.copytree(
            fixtures_dir / "sample_python",
            src_dir / "sample_python",
            dirs_exist_ok=True,
        )

        # Import the codebase
        result = ccoding.import_codebase(
            source_dir=src_dir / "sample_python",
            canvas_path=canvas_path,
            project_root=project,
            language="python",
        )
        assert len(result.code_to_canvas) > 0

        # Read the canvas and verify relationship edges were created.
        # DocumentParser has fields of type ParserConfig (tracked class), so at least
        # one 'composes' edge is expected.  'inherits'/'implements' edges are only
        # created between *tracked* classes; Protocol is an external class and is
        # therefore excluded from that check.
        canvas = ccoding.read_canvas(canvas_path)
        structural_edges = [
            e.ccoding.relation
            for e in canvas.edges
            if e.ccoding and e.ccoding.relation in ("inherits", "implements", "composes", "depends")
        ]
        assert len(structural_edges) >= 1, (
            f"Expected at least one structural edge; got edges: "
            f"{[e.ccoding.relation for e in canvas.edges if e.ccoding]}"
        )

        # Verify detail nodes were created for methods with pseudo code
        # parser.py has DocumentParser.parse() with a "Pseudo Code" section
        method_nodes = [
            n for n in canvas.nodes
            if n.ccoding and n.ccoding.kind == "method"
        ]
        assert len(method_nodes) >= 1, (
            f"Expected at least one method detail node; found none among {len(canvas.nodes)} nodes"
        )
        assert any("Pseudo Code" in n.text for n in method_nodes), (
            "Expected at least one method detail node to contain 'Pseudo Code'"
        )

        # Run sync again and verify no conflicts
        sync_result = ccoding.sync(
            canvas_path=canvas_path,
            project_root=project,
        )
        assert sync_result.conflicts == [], (
            f"Expected no conflicts on second sync; got: {sync_result.conflicts}"
        )
