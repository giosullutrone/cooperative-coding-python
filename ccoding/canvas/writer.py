from __future__ import annotations
import json
from pathlib import Path
from ccoding.canvas.model import (
    Canvas, Node, GroupNode, Edge, CcodingMetadata, EdgeMetadata,
)

def _serialize_ccoding_meta(meta: CcodingMetadata) -> dict:
    result = {"kind": meta.kind}
    if meta.stereotype is not None:
        result["stereotype"] = meta.stereotype
    if meta.language is not None:
        result["language"] = meta.language
    if meta.source is not None:
        result["source"] = meta.source
    if meta.qualified_name is not None:
        result["qualifiedName"] = meta.qualified_name
    result["status"] = meta.status
    result["proposedBy"] = meta.proposed_by
    result["proposalRationale"] = meta.proposal_rationale
    if meta.layout_pending:
        result["layoutPending"] = True
    return result

def _serialize_edge_meta(meta: EdgeMetadata) -> dict:
    return {
        "relation": meta.relation,
        "status": meta.status,
        "proposedBy": meta.proposed_by,
        "proposalRationale": meta.proposal_rationale,
    }

def _serialize_node(node: Node) -> dict:
    result: dict = {
        "id": node.id, "type": node.type,
        "x": node.x, "y": node.y,
        "width": node.width, "height": node.height,
    }
    if node.text:
        result["text"] = node.text
    if isinstance(node, GroupNode) and node.label:
        result["label"] = node.label
    if node.ccoding is not None:
        result["ccoding"] = _serialize_ccoding_meta(node.ccoding)
    result.update(node._extra)
    return result

def _serialize_edge(edge: Edge) -> dict:
    result: dict = {
        "id": edge.id,
        "fromNode": edge.from_node,
        "toNode": edge.to_node,
    }
    if edge.from_side is not None:
        result["fromSide"] = edge.from_side
    if edge.to_side is not None:
        result["toSide"] = edge.to_side
    if edge.label is not None:
        result["label"] = edge.label
    if edge.ccoding is not None:
        result["ccoding"] = _serialize_edge_meta(edge.ccoding)
    result.update(edge._extra)
    return result

def write_canvas(canvas: Canvas, path: Path) -> None:
    data: dict = {
        "nodes": [_serialize_node(n) for n in canvas.nodes],
        "edges": [_serialize_edge(e) for e in canvas.edges],
    }
    data.update(canvas._extra)
    path.write_text(json.dumps(data, indent=2))
