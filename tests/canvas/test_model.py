from ccoding.canvas.model import (
    Canvas, Node, Edge, CcodingMetadata, EdgeMetadata, GroupNode,
)


class TestNode:
    def test_create_class_node(self):
        meta = CcodingMetadata(
            kind="class",
            stereotype="protocol",
            language="python",
            source="src/parsers/document.py",
            qualified_name="parsers.document.DocumentParser",
        )
        node = Node(
            id="node-1", type="text",
            x=100, y=200, width=300, height=400,
            text="## DocumentParser",
            ccoding=meta,
        )
        assert node.id == "node-1"
        assert node.ccoding.kind == "class"
        assert node.ccoding.status == "accepted"
        assert node.ccoding.proposed_by is None

    def test_node_without_ccoding(self):
        node = Node(
            id="note-1", type="text",
            x=0, y=0, width=200, height=100,
            text="Some note",
        )
        assert node.ccoding is None

    def test_ghost_node(self):
        meta = CcodingMetadata(
            kind="class",
            status="proposed",
            proposed_by="agent",
            proposal_rationale="Extracting cache logic",
        )
        node = Node(
            id="node-2", type="text",
            x=0, y=0, width=300, height=400,
            text="## CacheManager",
            ccoding=meta,
        )
        assert node.ccoding.status == "proposed"
        assert node.ccoding.proposal_rationale == "Extracting cache logic"


class TestEdge:
    def test_create_edge(self):
        meta = EdgeMetadata(relation="composes")
        edge = Edge(
            id="edge-1",
            from_node="node-1", to_node="node-2",
            label="plugins",
            ccoding=meta,
        )
        assert edge.from_node == "node-1"
        assert edge.ccoding.relation == "composes"
        assert edge.ccoding.status == "accepted"

    def test_ghost_edge(self):
        meta = EdgeMetadata(
            relation="inherits",
            status="proposed",
            proposed_by="agent",
            proposal_rationale="Base parsing interface",
        )
        edge = Edge(
            id="edge-2",
            from_node="node-1", to_node="node-3",
            ccoding=meta,
        )
        assert edge.ccoding.status == "proposed"


class TestCanvas:
    def test_empty_canvas(self):
        canvas = Canvas()
        assert canvas.nodes == []
        assert canvas.edges == []

    def test_find_by_qualified_name(self):
        meta = CcodingMetadata(
            kind="class",
            qualified_name="parsers.DocumentParser",
        )
        node = Node(id="n1", type="text", x=0, y=0, width=300, height=400,
                     text="", ccoding=meta)
        canvas = Canvas(nodes=[node])
        assert canvas.find_by_qualified_name("parsers.DocumentParser") == node
        assert canvas.find_by_qualified_name("nonexistent") is None

    def test_find_by_source(self):
        meta = CcodingMetadata(kind="class", source="src/parser.py")
        node = Node(id="n1", type="text", x=0, y=0, width=300, height=400,
                     text="", ccoding=meta)
        canvas = Canvas(nodes=[node])
        assert canvas.find_by_source("src/parser.py") == [node]

    def test_ghost_nodes(self):
        accepted = Node(id="n1", type="text", x=0, y=0, width=300, height=400,
                        text="", ccoding=CcodingMetadata(kind="class"))
        proposed = Node(id="n2", type="text", x=0, y=0, width=300, height=400,
                        text="", ccoding=CcodingMetadata(kind="class", status="proposed"))
        plain = Node(id="n3", type="text", x=0, y=0, width=200, height=100, text="note")
        canvas = Canvas(nodes=[accepted, proposed, plain])
        assert canvas.ghost_nodes() == [proposed]

    def test_edges_for(self):
        e1 = Edge(id="e1", from_node="n1", to_node="n2",
                  ccoding=EdgeMetadata(relation="composes"))
        e2 = Edge(id="e2", from_node="n3", to_node="n1",
                  ccoding=EdgeMetadata(relation="depends"))
        e3 = Edge(id="e3", from_node="n3", to_node="n4",
                  ccoding=EdgeMetadata(relation="calls"))
        canvas = Canvas(edges=[e1, e2, e3])
        result = canvas.edges_for("n1")
        assert set(e.id for e in result) == {"e1", "e2"}

    def test_find_detail_nodes(self):
        class_node = Node(id="n1", type="text", x=0, y=0, width=300, height=400,
                          text="", ccoding=CcodingMetadata(kind="class"))
        method_node = Node(id="n2", type="text", x=0, y=0, width=300, height=300,
                           text="", ccoding=CcodingMetadata(kind="method"))
        detail_edge = Edge(id="e1", from_node="n1", to_node="n2",
                           ccoding=EdgeMetadata(relation="detail"))
        canvas = Canvas(nodes=[class_node, method_node], edges=[detail_edge])
        assert canvas.find_detail_nodes("n1") == [method_node]
