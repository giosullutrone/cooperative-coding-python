from __future__ import annotations

import os
import stat
from pathlib import Path

from ccoding.canvas.reader import read_canvas
from ccoding.code.parser import PythonAstParser, ClassElement
from ccoding.config import load_config
from ccoding.sync.differ import compute_diff
from ccoding.sync.hasher import content_hash
from ccoding.sync.state import load_sync_state


# ---------------------------------------------------------------------------
# Helpers (mirrors engine.py logic, kept local to avoid circular imports)
# ---------------------------------------------------------------------------


def _qualified_name(source_path: Path, class_name: str, source_root: Path) -> str:
    try:
        rel = source_path.relative_to(source_root)
    except ValueError:
        rel = source_path
    module = str(rel.with_suffix("")).replace("/", ".").replace("\\", ".")
    return f"{module}.{class_name}"


def _hash_class_element(elem: ClassElement) -> str:
    parts = [elem.name]
    for f in elem.fields:
        parts.append(f"field:{f.name}:{f.type_annotation or ''}")
    for m in elem.methods:
        parts.append(f"method:{m.name}:{m.return_type or ''}")
    for section_key in sorted(elem.docstring_sections.keys()):
        parts.append(f"doc:{section_key}:{elem.docstring_sections[section_key]}")
    return content_hash("\n".join(parts))


# ---------------------------------------------------------------------------
# check_sync
# ---------------------------------------------------------------------------


def check_sync(project_root: Path) -> tuple[int, str]:
    """Lightweight sync check for use in pre-commit hooks.

    Returns (0, "ok") when everything is in sync, or (1, report) when drift
    is detected (code_added, code_modified, canvas_modified, conflicts, etc.).
    """
    config = load_config(project_root)
    canvas_path = project_root / config.canvas
    source_root = project_root / config.source_root

    # Canvas may not exist yet → no drift to report
    if not canvas_path.exists():
        return 0, "ok"

    canvas = read_canvas(canvas_path)

    parser = PythonAstParser()
    code_elements: list[ClassElement] = []
    if source_root.exists():
        all_elements = parser.parse_directory(source_root)
        code_elements = [e for e in all_elements if isinstance(e, ClassElement)]

    state = load_sync_state(project_root)

    # Build canvas hashes
    canvas_hashes: dict[str, str] = {}
    for node in canvas.nodes:
        if node.ccoding and node.ccoding.qualified_name:
            if node.ccoding.kind != "class":
                continue
            if node.ccoding.status in ("proposed", "rejected", "stale"):
                continue
            canvas_hashes[node.ccoding.qualified_name] = content_hash(node.text)

    # Build code hashes
    code_hashes: dict[str, str] = {}
    for elem in code_elements:
        qname = _qualified_name(
            Path(elem.source_path) if elem.source_path else source_root,
            elem.name,
            source_root,
        )
        code_hashes[qname] = _hash_class_element(elem)

    diff = compute_diff(state, canvas_hashes, code_hashes)

    # Collect all drift indicators
    drift_items: list[str] = []

    for qname in diff.code_added:
        drift_items.append(f"  code added (not on canvas): {qname}")

    for qname in diff.code_modified:
        drift_items.append(f"  code modified: {qname}")

    for qname in diff.canvas_modified:
        drift_items.append(f"  canvas modified: {qname}")

    for qname in diff.canvas_added:
        drift_items.append(f"  canvas added (not in code): {qname}")

    for qname in diff.canvas_deleted:
        drift_items.append(f"  canvas deleted: {qname}")

    for qname in diff.code_deleted:
        drift_items.append(f"  code deleted: {qname}")

    for conflict in diff.conflicts:
        drift_items.append(f"  conflict (drift on both sides): {conflict.qualified_name}")

    if drift_items:
        report = "Sync drift detected:\n" + "\n".join(drift_items)
        return 1, report

    return 0, "ok"


# ---------------------------------------------------------------------------
# install_hooks
# ---------------------------------------------------------------------------

_PRE_COMMIT_SCRIPT = """\
#!/bin/sh
# CCode pre-commit hook — checks canvas/code sync
ccoding check
exit $?
"""

_GITATTRIBUTES_ENTRY = "*.canvas merge=ccoding-canvas\n"


def install_hooks(project_root: Path) -> None:
    """Install git pre-commit hook and .gitattributes merge driver entry."""
    git_dir = project_root / ".git"
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(_PRE_COMMIT_SCRIPT)

    # Make executable (rwxr-xr-x)
    current_mode = hook_path.stat().st_mode
    hook_path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # Write .gitattributes entry
    gitattributes = project_root / ".gitattributes"
    existing = gitattributes.read_text() if gitattributes.exists() else ""
    if _GITATTRIBUTES_ENTRY.strip() not in existing:
        with gitattributes.open("a") as f:
            f.write(_GITATTRIBUTES_ENTRY)
