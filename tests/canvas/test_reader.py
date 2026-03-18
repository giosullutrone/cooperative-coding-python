import json
from pathlib import Path
from ccoding.canvas.reader import read_canvas


class TestReadCanvas:
    def test_read_sample(self, fixtures_dir: Path):
        canvas = read_canvas(fixtures_dir / "sample.canvas")
        assert len(canvas.nodes) == 2
        assert len(canvas.edges) == 1
        node = canvas.nodes[0]
        assert node.id == "node-1"
        assert node.ccoding is not None
        assert node.ccoding.kind == "class"
        assert node.ccoding.stereotype == "protocol"
        assert node.ccoding.qualified_name == "parsers.document.DocumentParser"
        note = canvas.nodes[1]
        assert note.id == "note-1"
        assert note.ccoding is None
        edge = canvas.edges[0]
        assert edge.from_node == "node-1"
        assert edge.ccoding.relation == "context"

    def test_read_no_ccoding(self, fixtures_dir: Path):
        canvas = read_canvas(fixtures_dir / "sample_no_ccoding.canvas")
        assert len(canvas.nodes) == 1
        assert canvas.nodes[0].ccoding is None

    def test_preserves_unknown_fields(self, tmp_path: Path):
        data = {
            "nodes": [{
                "id": "n1", "type": "text",
                "x": 0, "y": 0, "width": 100, "height": 100,
                "text": "hi",
                "unknownField": "preserve me",
            }],
            "edges": [],
            "someTopLevelExtra": True,
        }
        p = tmp_path / "test.canvas"
        p.write_text(json.dumps(data))
        canvas = read_canvas(p)
        assert canvas._extra.get("someTopLevelExtra") is True
        assert canvas.nodes[0]._extra.get("unknownField") == "preserve me"
