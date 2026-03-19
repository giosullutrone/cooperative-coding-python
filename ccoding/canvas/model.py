from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CcodingMetadata:
    kind: str = "class"
    stereotype: str | None = None
    language: str | None = None
    source: str | None = None
    qualified_name: str | None = None
    status: str = "accepted"
    proposed_by: str | None = None
    proposal_rationale: str | None = None
    layout_pending: bool = False


@dataclass
class EdgeMetadata:
    relation: str = "depends"
    status: str = "accepted"
    proposed_by: str | None = None
    proposal_rationale: str | None = None


@dataclass
class Node:
    id: str
    type: str
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    ccoding: CcodingMetadata | None = None
    _extra: dict = field(default_factory=dict, repr=False)


@dataclass
class GroupNode(Node):
    label: str = ""


@dataclass
class Edge:
    id: str
    from_node: str
    to_node: str
    from_side: str | None = None
    to_side: str | None = None
    label: str | None = None
    ccoding: EdgeMetadata | None = None
    _extra: dict = field(default_factory=dict, repr=False)


@dataclass
class Canvas:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    _extra: dict = field(default_factory=dict, repr=False)

    def find_by_qualified_name(self, name: str) -> Node | None:
        for node in self.nodes:
            if node.ccoding and node.ccoding.qualified_name == name:
                return node
        return None

    def find_by_source(self, path: str) -> list[Node]:
        return [n for n in self.nodes if n.ccoding and n.ccoding.source == path]

    def find_detail_nodes(self, class_node_id: str) -> list[Node]:
        detail_target_ids = {
            e.to_node for e in self.edges
            if e.ccoding and e.ccoding.relation == "detail"
            and e.from_node == class_node_id
        }
        return [n for n in self.nodes if n.id in detail_target_ids]

    def edges_for(self, node_id: str) -> list[Edge]:
        return [
            e for e in self.edges
            if e.from_node == node_id or e.to_node == node_id
        ]

    def ghost_nodes(self) -> list[Node]:
        return [
            n for n in self.nodes
            if n.ccoding and n.ccoding.status == "proposed"
        ]

    def ghost_edges(self) -> list[Edge]:
        return [
            e for e in self.edges
            if e.ccoding and e.ccoding.status == "proposed"
        ]

    def stale_nodes(self) -> list[Node]:
        return [n for n in self.nodes if n.ccoding and n.ccoding.status == "stale"]
