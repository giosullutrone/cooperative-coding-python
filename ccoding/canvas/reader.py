from __future__ import annotations
import json
from pathlib import Path
from ccoding.canvas.model import (
    Canvas, Node, GroupNode, Edge, CcodingMetadata, EdgeMetadata,
)

_NODE_FIELDS = {"id", "type", "x", "y", "width", "height", "text", "ccoding", "label"}
_EDGE_FIELDS = {"id", "fromNode", "toNode", "fromSide", "toSide", "label", "ccoding"}
_CANVAS_FIELDS = {"nodes", "edges"}

def _parse_ccoding_meta(data: dict | None) -> CcodingMetadata | None:
    if data is None:
        return None
    return CcodingMetadata(
        kind=data.get("kind"),
        stereotype=data.get("stereotype"),
        language=data.get("language"),
        source=data.get("source"),
        qualified_name=data.get("qualifiedName"),
        status=data.get("status", "accepted"),
        proposed_by=data.get("proposedBy"),
        proposal_rationale=data.get("proposalRationale"),
        layout_pending=data.get("layoutPending", False),
    )

def _parse_edge_meta(data: dict | None) -> EdgeMetadata | None:
    if data is None:
        return None
    return EdgeMetadata(
        relation=data.get("relation", "depends"),
        status=data.get("status", "accepted"),
        proposed_by=data.get("proposedBy"),
        proposal_rationale=data.get("proposalRationale"),
    )

def _parse_node(data: dict) -> Node:
    extra = {k: v for k, v in data.items() if k not in _NODE_FIELDS}
    ccoding = _parse_ccoding_meta(data.get("ccoding"))
    if data.get("type") == "group":
        return GroupNode(
            id=data["id"], type="group",
            x=data.get("x", 0), y=data.get("y", 0),
            width=data.get("width", 0), height=data.get("height", 0),
            text=data.get("text", ""),
            label=data.get("label", ""),
            ccoding=ccoding, _extra=extra,
        )
    return Node(
        id=data["id"], type=data.get("type", "text"),
        x=data.get("x", 0), y=data.get("y", 0),
        width=data.get("width", 0), height=data.get("height", 0),
        text=data.get("text", ""),
        ccoding=ccoding, _extra=extra,
    )

def _parse_edge(data: dict) -> Edge:
    extra = {k: v for k, v in data.items() if k not in _EDGE_FIELDS}
    return Edge(
        id=data["id"],
        from_node=data["fromNode"],
        to_node=data["toNode"],
        from_side=data.get("fromSide"),
        to_side=data.get("toSide"),
        label=data.get("label"),
        ccoding=_parse_edge_meta(data.get("ccoding")),
        _extra=extra,
    )

def read_canvas(path: Path) -> Canvas:
    data = json.loads(path.read_text())
    extra = {k: v for k, v in data.items() if k not in _CANVAS_FIELDS}
    return Canvas(
        nodes=[_parse_node(n) for n in data.get("nodes", [])],
        edges=[_parse_edge(e) for e in data.get("edges", [])],
        _extra=extra,
    )
