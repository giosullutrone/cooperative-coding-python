from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CCODING_DIR = ".ccoding"
CONFIG_FILE = "config.json"
SYNC_STATE_FILE = "sync-state.json"


@dataclass
class ProjectConfig:
    canvas: str = "design.canvas"
    source_root: str = "src/"
    language: str = "python"
    ignore: list[str] = field(default_factory=list)
    live_mode: str = "auto"
    git_pre_commit_hook: bool = True
    git_merge_driver: bool = True
    git_aware_sync: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> ProjectConfig:
        git = data.get("git", {})
        return cls(
            canvas=data.get("canvas", "design.canvas"),
            source_root=data.get("sourceRoot", "src/"),
            language=data.get("language", "python"),
            ignore=data.get("ignore", []),
            live_mode=data.get("liveMode", "auto"),
            git_pre_commit_hook=git.get("preCommitHook", True),
            git_merge_driver=git.get("mergeDriver", True),
            git_aware_sync=git.get("gitAwareSync", True),
        )

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "canvas": self.canvas,
            "sourceRoot": self.source_root,
            "language": self.language,
            "ignore": self.ignore,
            "liveMode": self.live_mode,
            "git": {
                "preCommitHook": self.git_pre_commit_hook,
                "mergeDriver": self.git_merge_driver,
                "gitAwareSync": self.git_aware_sync,
            },
        }


def load_config(project_root: Path) -> ProjectConfig:
    config_path = project_root / CCODING_DIR / CONFIG_FILE
    if not config_path.exists():
        return ProjectConfig()
    data = json.loads(config_path.read_text())
    return ProjectConfig.from_dict(data)


def init_project(project_root: Path, config: ProjectConfig | None = None) -> ProjectConfig:
    config = config or ProjectConfig()
    ccoding_dir = project_root / CCODING_DIR
    ccoding_dir.mkdir(exist_ok=True)
    (ccoding_dir / CONFIG_FILE).write_text(
        json.dumps(config.to_dict(), indent=2) + "\n"
    )
    (ccoding_dir / SYNC_STATE_FILE).write_text(
        json.dumps({
            "version": 1,
            "lastSync": None,
            "canvasFile": config.canvas,
            "elements": {},
        }, indent=2) + "\n"
    )
    return config
