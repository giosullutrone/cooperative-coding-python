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


class TestInstallHooks:
    def test_installs_pre_commit(self, tmp_project: Path):
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_project, capture_output=True)
        install_hooks(tmp_project)
        hook_path = tmp_project / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists()
        content = hook_path.read_text()
        assert "ccoding check" in content
