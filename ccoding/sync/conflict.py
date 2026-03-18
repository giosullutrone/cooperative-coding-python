from __future__ import annotations
from enum import Enum
from ccoding.sync.differ import Conflict


class ConflictResolution(Enum):
    USE_CANVAS = "canvas-wins"
    USE_CODE = "code-wins"
    MANUAL = "manual"


def resolve_conflict(conflict: Conflict, strategy: str | None = None) -> ConflictResolution:
    if strategy == "canvas-wins":
        return ConflictResolution.USE_CANVAS
    elif strategy == "code-wins":
        return ConflictResolution.USE_CODE
    return ConflictResolution.MANUAL
