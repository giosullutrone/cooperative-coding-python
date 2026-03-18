from pathlib import Path
from unittest.mock import patch, MagicMock
from ccoding.git.diff import git_changed_files


class TestGitChangedFiles:
    def test_returns_changed_files(self, tmp_path: Path):
        with patch("ccoding.git.diff.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="src/foo.py\nsrc/bar.py\n")
            files = git_changed_files(tmp_path)
            assert files == [Path("src/foo.py"), Path("src/bar.py")]

    def test_returns_none_when_git_fails(self, tmp_path: Path):
        with patch("ccoding.git.diff.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="not a repo")
            files = git_changed_files(tmp_path)
            assert files is None
