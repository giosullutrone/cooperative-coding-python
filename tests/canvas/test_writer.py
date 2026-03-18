import json
from pathlib import Path
from ccoding.canvas.reader import read_canvas
from ccoding.canvas.writer import write_canvas
from ccoding.canvas.model import Canvas, Node, Edge, CcodingMetadata, EdgeMetadata


class TestWriteCanvas:
    def test_round_trip(self, fixtures_dir: Path, tmp_path: Path):
        original = read_canvas(fixtures_dir / "sample.canvas")
        out_path = tmp_path / "out.canvas"
        write_canvas(original, out_path)
        reloaded = read_canvas(out_path)
        assert len(reloaded.nodes) == len(original.nodes)
        assert len(reloaded.edges) == len(original.edges)
        assert reloaded.nodes[0].ccoding.kind == original.nodes[0].ccoding.kind

    def test_round_trip_preserves_json(self, fixtures_dir: Path, tmp_path: Path):
        original_text = (fixtures_dir / "sample.canvas").read_text()
        original_data = json.loads(original_text)
        canvas = read_canvas(fixtures_dir / "sample.canvas")
        out_path = tmp_path / "out.canvas"
        write_canvas(canvas, out_path)
        written_data = json.loads(out_path.read_text())
        assert written_data == original_data

    def test_preserves_unknown_fields(self, tmp_path: Path):
        data = {
            "nodes": [{
                "id": "n1", "type": "text",
                "x": 0, "y": 0, "width": 100, "height": 100,
                "text": "hi",
                "customField": 42,
            }],
            "edges": [],
            "topExtra": "keep",
        }
        src = tmp_path / "src.canvas"
        src.write_text(json.dumps(data))
        canvas = read_canvas(src)
        dst = tmp_path / "dst.canvas"
        write_canvas(canvas, dst)
        result = json.loads(dst.read_text())
        assert result["topExtra"] == "keep"
        assert result["nodes"][0]["customField"] == 42

    def test_write_new_canvas(self, tmp_path: Path):
        meta = CcodingMetadata(kind="class", stereotype="dataclass")
        node = Node(id="n1", type="text", x=0, y=0, width=300, height=400,
                    text="## Foo", ccoding=meta)
        canvas = Canvas(nodes=[node])
        out = tmp_path / "new.canvas"
        write_canvas(canvas, out)
        data = json.loads(out.read_text())
        assert data["nodes"][0]["ccoding"]["kind"] == "class"
        assert data["nodes"][0]["ccoding"]["stereotype"] == "dataclass"
