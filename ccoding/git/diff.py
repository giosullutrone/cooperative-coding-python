from __future__ import annotations
import subprocess
from pathlib import Path


def git_changed_files(project_root: Path, ref: str = "HEAD") -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", ref],
            cwd=project_root, capture_output=True, text=True,
        )
        if result.returncode != 0:
            return None
        return [Path(line) for line in result.stdout.strip().splitlines() if line.strip()]
    except FileNotFoundError:
        return None
