import json
from pathlib import Path
from ccoding.config import ProjectConfig, load_config, init_project


class TestProjectConfig:
    def test_default_values(self):
        config = ProjectConfig()
        assert config.canvas == "design.canvas"
        assert config.source_root == "src/"
        assert config.language == "python"
        assert config.ignore == []
        assert config.live_mode == "auto"
        assert config.git_pre_commit_hook is True
        assert config.git_merge_driver is True
        assert config.git_aware_sync is True

    def test_load_from_file(self, tmp_path: Path):
        ccoding_dir = tmp_path / ".ccoding"
        ccoding_dir.mkdir()
        (ccoding_dir / "config.json").write_text(json.dumps({
            "version": 1,
            "canvas": "arch.canvas",
            "sourceRoot": "lib/",
            "language": "python",
            "ignore": ["**/test_*"],
            "liveMode": "never",
            "git": {
                "preCommitHook": False,
                "mergeDriver": True,
                "gitAwareSync": False,
            },
        }))
        config = load_config(tmp_path)
        assert config.canvas == "arch.canvas"
        assert config.source_root == "lib/"
        assert config.ignore == ["**/test_*"]
        assert config.live_mode == "never"
        assert config.git_pre_commit_hook is False

    def test_load_missing_returns_default(self, tmp_path: Path):
        config = load_config(tmp_path)
        assert config.canvas == "design.canvas"

    def test_init_project_creates_files(self, tmp_path: Path):
        init_project(tmp_path)
        assert (tmp_path / ".ccoding" / "config.json").exists()
        assert (tmp_path / ".ccoding" / "sync-state.json").exists()
        data = json.loads((tmp_path / ".ccoding" / "config.json").read_text())
        assert data["version"] == 1
