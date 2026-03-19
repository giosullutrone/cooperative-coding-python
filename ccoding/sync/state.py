from __future__ import annotations
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

_STATE_FILE = ".ccoding/sync-state.json"


@dataclass
class ElementState:
    canvas_hash: str
    code_hash: str
    canvas_node_id: str
    source_path: str


@dataclass
class SyncState:
    canvas_file: str
    elements: dict[str, ElementState] = field(default_factory=dict)


def load_sync_state(project_root: Path) -> SyncState:
    state_path = project_root / _STATE_FILE
    if not state_path.exists():
        return SyncState(canvas_file="design.canvas")

    raw = json.loads(state_path.read_text())
    elements: dict[str, ElementState] = {}
    for name, elem in raw.get("elements", {}).items():
        elements[name] = ElementState(
            canvas_hash=elem["canvasHash"],
            code_hash=elem["codeHash"],
            canvas_node_id=elem["canvasNodeId"],
            source_path=elem["sourcePath"],
        )
    return SyncState(
        canvas_file=raw.get("canvasFile", "design.canvas"),
        elements=elements,
    )


def save_sync_state(state: SyncState, project_root: Path) -> None:
    state_path = project_root / _STATE_FILE
    state_path.parent.mkdir(parents=True, exist_ok=True)

    elements_raw: dict[str, dict] = {}
    for name, elem in state.elements.items():
        elements_raw[name] = {
            "canvasHash": elem.canvas_hash,
            "codeHash": elem.code_hash,
            "canvasNodeId": elem.canvas_node_id,
            "sourcePath": elem.source_path,
        }

    raw = {
        "version": 1,
        "lastSync": datetime.now(timezone.utc).isoformat(),
        "canvasFile": state.canvas_file,
        "elements": elements_raw,
    }
    state_path.write_text(json.dumps(raw, indent=2))
