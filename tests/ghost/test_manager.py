import pytest
from ccoding.ghost.manager import (
    propose_node, propose_edge, accept_node, accept_edge,
    reject_node, reject_edge, reconsider_node, reconsider_edge,
    accept_all, reject_all, list_ghosts,
)
from ccoding.canvas.model import Canvas, Node, Edge, CcodingMetadata, EdgeMetadata


def _base_canvas() -> Canvas:
    return Canvas(
        nodes=[
            Node(id="n1", type="text", x=0, y=0, width=300, height=400,
                 text="## Foo", ccoding=CcodingMetadata(kind="class")),
        ],
        edges=[],
    )


class TestProposeNode:
    def test_creates_ghost(self):
        canvas = _base_canvas()
        node = propose_node(
            canvas, kind="class", name="Bar",
            content="## Bar", rationale="Extracting logic",
        )
        assert node.ccoding.status == "proposed"
        assert node.ccoding.proposed_by == "agent"
        assert node.ccoding.proposal_rationale == "Extracting logic"
        assert node in canvas.nodes

    def test_propose_context_node(self):
        canvas = _base_canvas()
        node = propose_node(
            canvas, kind=None, name="rationale note",
            content="Design decision: ...", rationale="Explaining choice",
        )
        assert node.ccoding.status == "proposed"


class TestProposeEdge:
    def test_creates_ghost_edge(self):
        canvas = _base_canvas()
        n2 = propose_node(canvas, kind="class", name="Bar", content="## Bar", rationale="test")
        edge = propose_edge(
            canvas, from_node="n1", to_node=n2.id,
            relation="depends", label="uses Bar",
            rationale="Foo depends on Bar",
        )
        assert edge.ccoding.status == "proposed"
        assert edge in canvas.edges


class TestAcceptReject:
    def test_accept_node(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        accepted = accept_node(canvas, ghost.id)
        assert accepted.ccoding.status == "accepted"
        assert accepted.ccoding.proposal_rationale is None

    def test_accept_edge_requires_accepted_endpoints(self):
        canvas = _base_canvas()
        ghost_node = propose_node(canvas, "class", "Bar", "## Bar", "test")
        ghost_edge = propose_edge(canvas, "n1", ghost_node.id, "depends", "x", "test")
        with pytest.raises(ValueError, match="endpoint"):
            accept_edge(canvas, ghost_edge.id)
        accept_node(canvas, ghost_node.id)
        accepted_edge = accept_edge(canvas, ghost_edge.id)
        assert accepted_edge.ccoding.status == "accepted"

    def test_reject_node_cascades_to_edges(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        reject_node(canvas, ghost.id)
        assert ghost.ccoding.status == "rejected"
        assert edge.ccoding.status == "rejected"

    def test_reject_edge_leaves_nodes(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        reject_edge(canvas, edge.id)
        assert edge.ccoding.status == "rejected"
        assert ghost.ccoding.status == "proposed"


class TestReconsider:
    def test_reconsider_node(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        reject_node(canvas, ghost.id)
        reconsider_node(canvas, ghost.id)
        assert ghost.ccoding.status == "proposed"

    def test_reconsider_restores_cascade_rejected_edges(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        reject_node(canvas, ghost.id)
        reconsider_node(canvas, ghost.id)
        assert edge.ccoding.status == "proposed"

    def test_reconsider_edge(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        accept_node(canvas, ghost.id)
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        reject_edge(canvas, edge.id)
        reconsider_edge(canvas, edge.id)
        assert edge.ccoding.status == "proposed"

    def test_reconsider_edge_rejected_endpoint_raises(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        reject_node(canvas, ghost.id)
        with pytest.raises(ValueError, match="endpoint"):
            reconsider_edge(canvas, edge.id)


class TestStateGuards:
    def test_accept_only_from_proposed(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        accept_node(canvas, ghost.id)
        with pytest.raises(ValueError, match="must be 'proposed'"):
            accept_node(canvas, ghost.id)

    def test_accept_rejected_must_go_through_reconsider(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        reject_node(canvas, ghost.id)
        with pytest.raises(ValueError, match="must be 'proposed'"):
            accept_node(canvas, ghost.id)

    def test_reject_only_from_proposed(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        accept_node(canvas, ghost.id)
        with pytest.raises(ValueError, match="must be 'proposed'"):
            reject_node(canvas, ghost.id)

    def test_reconsider_only_from_rejected(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        with pytest.raises(ValueError, match="must be 'rejected'"):
            reconsider_node(canvas, ghost.id)

    def test_reconsider_accepted_raises(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        accept_node(canvas, ghost.id)
        with pytest.raises(ValueError, match="must be 'rejected'"):
            reconsider_node(canvas, ghost.id)

    def test_accept_edge_only_from_proposed(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        accept_node(canvas, ghost.id)
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        accept_edge(canvas, edge.id)
        with pytest.raises(ValueError, match="must be 'proposed'"):
            accept_edge(canvas, edge.id)

    def test_reject_edge_only_from_proposed(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        accept_node(canvas, ghost.id)
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        accept_edge(canvas, edge.id)
        with pytest.raises(ValueError, match="must be 'proposed'"):
            reject_edge(canvas, edge.id)

    def test_reconsider_edge_only_from_rejected(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        accept_node(canvas, ghost.id)
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        with pytest.raises(ValueError, match="must be 'rejected'"):
            reconsider_edge(canvas, edge.id)


class TestBatchOps:
    def test_accept_all(self):
        canvas = _base_canvas()
        propose_node(canvas, "class", "Bar", "## Bar", "test")
        propose_node(canvas, "class", "Baz", "## Baz", "test")
        results = accept_all(canvas)
        assert all(
            n.ccoding.status == "accepted"
            for n in canvas.nodes
            if n.ccoding
        )

    def test_list_ghosts(self):
        canvas = _base_canvas()
        propose_node(canvas, "class", "Bar", "## Bar", "test")
        ghosts = list_ghosts(canvas)
        assert len(ghosts) == 1
