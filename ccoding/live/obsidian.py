from __future__ import annotations
import shutil
import subprocess

# JS template constants for common operations
JS_RELOAD_CANVAS = "app.workspace.activeLeaf?.view?.requestSave?.()"
JS_GET_ACTIVE_CANVAS = "app.workspace.activeLeaf?.view?.file?.path"


class ObsidianBridge:
    def is_available(self) -> bool:
        if shutil.which("obsidian") is None:
            return False
        try:
            result = subprocess.run(
                ["obsidian", "eval", "1+1"],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def eval(self, js: str) -> str:
        result = subprocess.run(
            ["obsidian", "eval", js],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Obsidian eval failed: {result.stderr}")
        return result.stdout.strip()
