"""Ghost Node Manager — proposal lifecycle for canvas nodes and edges."""
from __future__ import annotations

from uuid import uuid4

from ccoding.canvas.model import Canvas, Node, Edge, CcodingMetadata, EdgeMetadata

# Status constants
_PROPOSED = "proposed"
_ACCEPTED = "accepted"
_REJECTED = "rejected"

# Key used in Edge._extra to mark that the rejection was a cascade from a node
_CASCADE_KEY = "_ccoding_cascade_rejected"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_id() -> str:
    return uuid4().hex[:8]


def _find_node(canvas: Canvas, node_id: str) -> Node:
    for n in canvas.nodes:
        if n.id == node_id:
            return n
    raise ValueError(f"Node '{node_id}' not found in canvas.")


def _find_edge(canvas: Canvas, edge_id: str) -> Edge:
    for e in canvas.edges:
        if e.id == edge_id:
            return e
    raise ValueError(f"Edge '{edge_id}' not found in canvas.")


def _node_status(canvas: Canvas, node_id: str) -> str:
    """Return status of node, defaulting to 'accepted' if no ccoding metadata."""
    for n in canvas.nodes:
        if n.id == node_id:
            if n.ccoding is None:
                return _ACCEPTED
            return n.ccoding.status
    raise ValueError(f"Node '{node_id}' not found in canvas.")


def _connected_edges(canvas: Canvas, node_id: str) -> list[Edge]:
    return [e for e in canvas.edges if e.from_node == node_id or e.to_node == node_id]


# ---------------------------------------------------------------------------
# Propose
# ---------------------------------------------------------------------------

def propose_node(
    canvas: Canvas,
    kind: str | None,
    name: str,
    content: str,
    rationale: str,
    proposed_by: str = "agent",
) -> Node:
    """Create a ghost node and add it to canvas.nodes."""
    node_id = _new_id()
    if kind is not None:
        meta = CcodingMetadata(
            kind=kind,
            status=_PROPOSED,
            proposed_by=proposed_by,
            proposal_rationale=rationale,
        )
    else:
        # Context node — minimal metadata
        meta = CcodingMetadata(
            kind="class",
            status=_PROPOSED,
            proposed_by=proposed_by,
            proposal_rationale=rationale,
            layout_pending=False,
        )

    node = Node(
        id=node_id,
        type="text",
        x=0,
        y=0,
        width=300,
        height=400,
        text=content,
        ccoding=meta,
    )
    canvas.nodes.append(node)
    return node


def propose_edge(
    canvas: Canvas,
    from_node: str,
    to_node: str,
    relation: str,
    label: str,
    rationale: str,
    proposed_by: str = "agent",
) -> Edge:
    """Create a ghost edge and add it to canvas.edges. Validates endpoints exist."""
    # Validate both endpoints exist (they don't have to be accepted yet)
    _find_node(canvas, from_node)
    _find_node(canvas, to_node)

    edge_id = _new_id()
    meta = EdgeMetadata(
        relation=relation,
        status=_PROPOSED,
        proposed_by=proposed_by,
        proposal_rationale=rationale,
    )
    edge = Edge(
        id=edge_id,
        from_node=from_node,
        to_node=to_node,
        label=label,
        ccoding=meta,
    )
    canvas.edges.append(edge)
    return edge


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------

def accept_node(canvas: Canvas, node_id: str) -> Node:
    """Accept a proposed node, clearing its rationale."""
    node = _find_node(canvas, node_id)
    if node.ccoding is None:
        raise ValueError(f"Node '{node_id}' has no ccoding metadata.")
    node.ccoding.status = _ACCEPTED
    node.ccoding.proposal_rationale = None
    return node


def accept_edge(canvas: Canvas, edge_id: str) -> Edge:
    """Accept a proposed edge. Both endpoints must be accepted first."""
    edge = _find_edge(canvas, edge_id)
    if edge.ccoding is None:
        raise ValueError(f"Edge '{edge_id}' has no ccoding metadata.")

    from_status = _node_status(canvas, edge.from_node)
    to_status = _node_status(canvas, edge.to_node)

    if from_status != _ACCEPTED or to_status != _ACCEPTED:
        raise ValueError(
            f"Cannot accept edge '{edge_id}': endpoint nodes must be accepted first."
        )

    edge.ccoding.status = _ACCEPTED
    edge.ccoding.proposal_rationale = None
    return edge


# ---------------------------------------------------------------------------
# Reject
# ---------------------------------------------------------------------------

def reject_node(canvas: Canvas, node_id: str) -> Node:
    """Reject a node and cascade-reject all connected edges."""
    node = _find_node(canvas, node_id)
    if node.ccoding is None:
        raise ValueError(f"Node '{node_id}' has no ccoding metadata.")
    node.ccoding.status = _REJECTED

    for edge in _connected_edges(canvas, node_id):
        if edge.ccoding is not None and edge.ccoding.status != _REJECTED:
            edge.ccoding.status = _REJECTED
            edge._extra[_CASCADE_KEY] = True

    return node


def reject_edge(canvas: Canvas, edge_id: str) -> Edge:
    """Reject a single edge without affecting its nodes."""
    edge = _find_edge(canvas, edge_id)
    if edge.ccoding is None:
        raise ValueError(f"Edge '{edge_id}' has no ccoding metadata.")
    edge.ccoding.status = _REJECTED
    return edge


# ---------------------------------------------------------------------------
# Reconsider
# ---------------------------------------------------------------------------

def reconsider_node(canvas: Canvas, node_id: str) -> Node:
    """Restore a rejected node to proposed, also restoring cascade-rejected edges."""
    node = _find_node(canvas, node_id)
    if node.ccoding is None:
        raise ValueError(f"Node '{node_id}' has no ccoding metadata.")
    node.ccoding.status = _PROPOSED

    # Restore any edges that were cascade-rejected due to this node
    for edge in _connected_edges(canvas, node_id):
        if edge.ccoding is not None and edge._extra.get(_CASCADE_KEY):
            edge.ccoding.status = _PROPOSED
            edge._extra.pop(_CASCADE_KEY, None)

    return node


def reconsider_edge(canvas: Canvas, edge_id: str) -> Edge:
    """Restore a rejected edge to proposed. Raises if an endpoint is still rejected."""
    edge = _find_edge(canvas, edge_id)
    if edge.ccoding is None:
        raise ValueError(f"Edge '{edge_id}' has no ccoding metadata.")

    from_status = _node_status(canvas, edge.from_node)
    to_status = _node_status(canvas, edge.to_node)

    # Check for rejected endpoints
    for status, nid in [(from_status, edge.from_node), (to_status, edge.to_node)]:
        if status == _REJECTED:
            raise ValueError(
                f"Cannot reconsider edge '{edge_id}': endpoint '{nid}' is rejected."
            )

    edge.ccoding.status = _PROPOSED
    return edge


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------

def accept_all(canvas: Canvas) -> list[Node | Edge]:
    """Accept all proposed nodes then all proposed edges. Returns accepted items."""
    accepted: list[Node | Edge] = []

    for node in canvas.nodes:
        if node.ccoding and node.ccoding.status == _PROPOSED:
            accept_node(canvas, node.id)
            accepted.append(node)

    for edge in canvas.edges:
        if edge.ccoding and edge.ccoding.status == _PROPOSED:
            try:
                accept_edge(canvas, edge.id)
                accepted.append(edge)
            except ValueError:
                # Skip edges whose endpoints are still not accepted
                pass

    return accepted


def reject_all(canvas: Canvas) -> list[Node | Edge]:
    """Reject all proposed nodes and edges. Returns rejected items."""
    rejected: list[Node | Edge] = []

    for node in list(canvas.nodes):
        if node.ccoding and node.ccoding.status == _PROPOSED:
            reject_node(canvas, node.id)
            rejected.append(node)

    for edge in list(canvas.edges):
        if edge.ccoding and edge.ccoding.status == _PROPOSED:
            reject_edge(canvas, edge.id)
            rejected.append(edge)

    return rejected


def list_ghosts(canvas: Canvas) -> list[Node | Edge]:
    """Return all nodes and edges with proposed status."""
    ghosts: list[Node | Edge] = []
    ghosts.extend(canvas.ghost_nodes())
    ghosts.extend(canvas.ghost_edges())
    return ghosts
