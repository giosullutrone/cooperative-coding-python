from __future__ import annotations
import json
from pathlib import Path


def merge_canvases(base_path: Path, ours_path: Path, theirs_path: Path) -> int:
    """Three-way merge of canvas files by node ID.

    Merge rules:
    - Text changes: if only one side changed vs base → take that change.
      If both sides changed text differently → conflict (return 1).
    - Position (x, y) changes → last writer (theirs) wins.
    - New nodes from either side → include all.
    - Merged result is written to ours_path.

    Returns 0 on success, non-zero on conflict.
    """
    base = json.loads(base_path.read_text())
    ours = json.loads(ours_path.read_text())
    theirs = json.loads(theirs_path.read_text())

    # Build node maps indexed by id
    base_nodes: dict[str, dict] = {n["id"]: n for n in base.get("nodes", [])}
    ours_nodes: dict[str, dict] = {n["id"]: n for n in ours.get("nodes", [])}
    theirs_nodes: dict[str, dict] = {n["id"]: n for n in theirs.get("nodes", [])}

    all_ids = set(base_nodes) | set(ours_nodes) | set(theirs_nodes)

    merged_nodes: list[dict] = []
    has_conflict = False

    for node_id in all_ids:
        base_node = base_nodes.get(node_id)
        our_node = ours_nodes.get(node_id)
        their_node = theirs_nodes.get(node_id)

        # Node only exists on one side → include it
        if base_node is None:
            # New node added by ours or theirs (or both independently — take ours)
            if our_node is not None:
                merged_nodes.append(dict(our_node))
            elif their_node is not None:
                merged_nodes.append(dict(their_node))
            continue

        # Node existed in base — check for modifications
        if our_node is None and their_node is None:
            # Deleted by both sides — omit
            continue
        if our_node is None:
            # Deleted by ours, kept by theirs — omit (ours wins deletion)
            continue
        if their_node is None:
            # Deleted by theirs, kept by ours — keep ours
            merged_nodes.append(dict(our_node))
            continue

        # All three exist — do field-level merge
        merged = dict(our_node)

        # Text field: three-way merge
        base_text = base_node.get("text", "")
        our_text = our_node.get("text", "")
        their_text = their_node.get("text", "")

        our_changed = our_text != base_text
        their_changed = their_text != base_text

        if our_changed and their_changed and our_text != their_text:
            # True conflict on text content
            has_conflict = True
            # Still write ours as placeholder but signal conflict
            merged["text"] = our_text
        elif their_changed and not our_changed:
            # Only theirs changed text → take theirs
            merged["text"] = their_text
        # else: our_changed or neither → keep ours (already in merged)

        # Position fields: last writer (theirs) wins
        for pos_field in ("x", "y", "width", "height"):
            if pos_field in their_node:
                merged[pos_field] = their_node[pos_field]

        merged_nodes.append(merged)

    # Merge edges: union by id, prefer ours on conflict
    base_edges: dict[str, dict] = {e["id"]: e for e in base.get("edges", [])}
    ours_edges: dict[str, dict] = {e["id"]: e for e in ours.get("edges", [])}
    theirs_edges: dict[str, dict] = {e["id"]: e for e in theirs.get("edges", [])}

    all_edge_ids = set(ours_edges) | set(theirs_edges)
    merged_edges: list[dict] = []
    for edge_id in all_edge_ids:
        if edge_id in ours_edges:
            merged_edges.append(dict(ours_edges[edge_id]))
        else:
            merged_edges.append(dict(theirs_edges[edge_id]))

    result = {
        "nodes": merged_nodes,
        "edges": merged_edges,
    }
    ours_path.write_text(json.dumps(result, indent=2))

    return 1 if has_conflict else 0
