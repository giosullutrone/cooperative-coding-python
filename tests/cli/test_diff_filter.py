"""Tests for diff command filtering (C15)."""
import json
from pathlib import Path
import shutil

from click.testing import CliRunner

from ccoding.cli import main


class TestDiffFilterDetailNodes:
    def test_diff_excludes_method_detail_nodes(self, tmp_project: Path, fixtures_dir: Path):
        """Method detail nodes must not appear in diff output."""
        from ccoding.sync.engine import import_codebase

        canvas_path = tmp_project / "design.canvas"
        src_dir = tmp_project / "src"
        shutil.copytree(fixtures_dir / "sample_python", src_dir, dirs_exist_ok=True)

        import_codebase(
            source_dir=src_dir,
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )

        # Verify canvas has method detail nodes
        raw = json.loads(canvas_path.read_text())
        method_nodes = [
            n for n in raw["nodes"]
            if n.get("ccoding", {}).get("kind") == "method"
        ]
        assert len(method_nodes) >= 1, "Fixture should produce method detail nodes"

        # Diff should show "in sync" — no phantom changes from detail nodes
        runner = CliRunner()
        result = runner.invoke(main, ["--project", str(tmp_project), "diff"])
        assert result.exit_code == 0
        assert "nothing would change" in result.output.lower() or "in sync" in result.output.lower()
