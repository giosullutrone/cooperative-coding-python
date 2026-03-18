from __future__ import annotations
from dataclasses import dataclass, field
from ccoding.sync.state import SyncState


@dataclass
class Conflict:
    qualified_name: str
    canvas_hash: str
    code_hash: str
    stored_canvas_hash: str
    stored_code_hash: str


@dataclass
class SyncDiff:
    in_sync: list[str] = field(default_factory=list)
    canvas_modified: list[str] = field(default_factory=list)
    code_modified: list[str] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    canvas_added: list[str] = field(default_factory=list)
    code_added: list[str] = field(default_factory=list)
    canvas_deleted: list[str] = field(default_factory=list)
    code_deleted: list[str] = field(default_factory=list)


def compute_diff(
    state: SyncState,
    current_canvas_hashes: dict[str, str],
    current_code_hashes: dict[str, str],
) -> SyncDiff:
    diff = SyncDiff()
    known = set(state.elements.keys())
    canvas_names = set(current_canvas_hashes.keys())
    code_names = set(current_code_hashes.keys())

    # Elements already tracked in state
    for name, elem in state.elements.items():
        in_canvas = name in canvas_names
        in_code = name in code_names

        if not in_canvas and not in_code:
            # Both deleted — treat as canvas_deleted (or both; just pick one)
            diff.canvas_deleted.append(name)
            diff.code_deleted.append(name)
            continue

        if not in_canvas:
            diff.canvas_deleted.append(name)
            continue

        if not in_code:
            diff.code_deleted.append(name)
            continue

        cur_canvas = current_canvas_hashes[name]
        cur_code = current_code_hashes[name]
        canvas_changed = cur_canvas != elem.canvas_hash
        code_changed = cur_code != elem.code_hash

        if not canvas_changed and not code_changed:
            diff.in_sync.append(name)
        elif canvas_changed and not code_changed:
            diff.canvas_modified.append(name)
        elif not canvas_changed and code_changed:
            diff.code_modified.append(name)
        else:
            diff.conflicts.append(Conflict(
                qualified_name=name,
                canvas_hash=cur_canvas,
                code_hash=cur_code,
                stored_canvas_hash=elem.canvas_hash,
                stored_code_hash=elem.code_hash,
            ))

    # New elements not yet in state
    for name in canvas_names - known:
        if name not in code_names:
            diff.canvas_added.append(name)

    for name in code_names - known:
        if name not in canvas_names:
            diff.code_added.append(name)

    return diff
