import pytest
from unittest.mock import patch, MagicMock
from ccoding.live.obsidian import ObsidianBridge


class TestObsidianBridge:
    def test_is_available_false_when_not_installed(self):
        with patch("ccoding.live.obsidian.shutil.which", return_value=None):
            bridge = ObsidianBridge()
            assert bridge.is_available() is False

    def test_is_available_true_when_installed_and_running(self):
        with patch("ccoding.live.obsidian.shutil.which", return_value="/usr/local/bin/obsidian"), \
             patch("ccoding.live.obsidian.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok")
            bridge = ObsidianBridge()
            assert bridge.is_available() is True

    def test_eval_calls_obsidian_cli(self):
        with patch("ccoding.live.obsidian.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="42")
            bridge = ObsidianBridge()
            result = bridge.eval("2 + 40")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "obsidian" in args[0]
            assert "eval" in args
            assert result == "42"

    def test_eval_raises_on_failure(self):
        with patch("ccoding.live.obsidian.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            bridge = ObsidianBridge()
            with pytest.raises(RuntimeError):
                bridge.eval("bad code")
