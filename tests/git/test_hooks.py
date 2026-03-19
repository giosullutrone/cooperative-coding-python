import shutil
from pathlib import Path

from ccoding.git.hooks import check_sync, install_hooks


class TestCheckSync:
    def test_clean_returns_zero(self, tmp_project: Path):
        exit_code, message = check_sync(tmp_project)
        assert exit_code == 0

    def test_reports_drift(self, tmp_project: Path):
        src_dir = tmp_project / "src"
        (src_dir / "drifted.py").write_text(
            'class Drifted:\n    """A class not on canvas."""\n    pass\n'
        )
        exit_code, message = check_sync(tmp_project)
        assert exit_code == 1
        assert "Drifted" in message or "drift" in message.lower()


class TestCheckSyncFilters:
    def test_check_sync_excludes_rejected_nodes(self, tmp_project: Path, fixtures_dir: Path):
        """Rejected nodes should be excluded from canvas hashes in check_sync.

        After import, we reject all class nodes, delete the source files,
        and remove sync-state entries so the only trace is the rejected canvas
        nodes. check_sync must ignore them entirely.
        """
        import json as _json

        from ccoding.canvas.reader import read_canvas
        from ccoding.canvas.writer import write_canvas
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

        # Set all class nodes to rejected and remember their qualified names
        canvas = read_canvas(canvas_path)
        rejected_qnames: list[str] = []
        for node in canvas.nodes:
            if node.ccoding and node.ccoding.kind == "class":
                node.ccoding.status = "rejected"
                if node.ccoding.qualified_name:
                    rejected_qnames.append(node.ccoding.qualified_name)
        write_canvas(canvas, canvas_path)

        # Remove source files and sync-state entries so only rejected
        # canvas nodes remain (prevents drift from code-side).
        shutil.rmtree(src_dir)
        src_dir.mkdir()

        state_path = tmp_project / ".ccoding" / "sync-state.json"
        state_data = _json.loads(state_path.read_text())
        for qn in rejected_qnames:
            state_data["elements"].pop(qn, None)
        state_path.write_text(_json.dumps(state_data))

        # check_sync should not report drift for rejected nodes
        exit_code, report = check_sync(tmp_project)
        assert exit_code == 0, f"Rejected node caused false drift: {report}"

    def test_check_sync_excludes_detail_nodes(self, tmp_project: Path, fixtures_dir: Path):
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

        # check_sync should not report drift from method detail nodes
        exit_code, report = check_sync(tmp_project)
        assert exit_code == 0, f"Detail nodes caused false drift: {report}"


class TestInstallHooks:
    def test_installs_pre_commit(self, tmp_project: Path):
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_project, capture_output=True)
        install_hooks(tmp_project)
        hook_path = tmp_project / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists()
        content = hook_path.read_text()
        assert "ccoding check" in content
