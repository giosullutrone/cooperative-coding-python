import json
from pathlib import Path
from ccoding.git.merge import merge_canvases


class TestMergeCanvases:
    def test_non_overlapping_merge(self, tmp_path: Path):
        base = {"nodes": [{"id": "n1", "type": "text", "x": 0, "y": 0, "width": 100, "height": 100, "text": "original"}], "edges": []}
        ours = {"nodes": [
            {"id": "n1", "type": "text", "x": 0, "y": 0, "width": 100, "height": 100, "text": "original"},
            {"id": "n2", "type": "text", "x": 200, "y": 0, "width": 100, "height": 100, "text": "ours"},
        ], "edges": []}
        theirs = {"nodes": [
            {"id": "n1", "type": "text", "x": 0, "y": 0, "width": 100, "height": 100, "text": "original"},
            {"id": "n3", "type": "text", "x": 400, "y": 0, "width": 100, "height": 100, "text": "theirs"},
        ], "edges": []}
        base_p, ours_p, theirs_p = tmp_path / "base.canvas", tmp_path / "ours.canvas", tmp_path / "theirs.canvas"
        base_p.write_text(json.dumps(base))
        ours_p.write_text(json.dumps(ours))
        theirs_p.write_text(json.dumps(theirs))
        exit_code = merge_canvases(base_p, ours_p, theirs_p)
        assert exit_code == 0
        result = json.loads(ours_p.read_text())
        node_ids = {n["id"] for n in result["nodes"]}
        assert node_ids == {"n1", "n2", "n3"}

    def test_conflicting_node_returns_nonzero(self, tmp_path: Path):
        base = {"nodes": [{"id": "n1", "type": "text", "x": 0, "y": 0, "width": 100, "height": 100, "text": "original"}], "edges": []}
        ours = {"nodes": [{"id": "n1", "type": "text", "x": 0, "y": 0, "width": 100, "height": 100, "text": "ours version"}], "edges": []}
        theirs = {"nodes": [{"id": "n1", "type": "text", "x": 0, "y": 0, "width": 100, "height": 100, "text": "theirs version"}], "edges": []}
        base_p, ours_p, theirs_p = tmp_path / "base.canvas", tmp_path / "ours.canvas", tmp_path / "theirs.canvas"
        base_p.write_text(json.dumps(base))
        ours_p.write_text(json.dumps(ours))
        theirs_p.write_text(json.dumps(theirs))
        exit_code = merge_canvases(base_p, ours_p, theirs_p)
        assert exit_code != 0

    def test_position_changes_last_writer_wins(self, tmp_path: Path):
        base = {"nodes": [{"id": "n1", "type": "text", "x": 0, "y": 0, "width": 100, "height": 100, "text": "same"}], "edges": []}
        ours = {"nodes": [{"id": "n1", "type": "text", "x": 50, "y": 0, "width": 100, "height": 100, "text": "same"}], "edges": []}
        theirs = {"nodes": [{"id": "n1", "type": "text", "x": 0, "y": 99, "width": 100, "height": 100, "text": "same"}], "edges": []}
        base_p, ours_p, theirs_p = tmp_path / "base.canvas", tmp_path / "ours.canvas", tmp_path / "theirs.canvas"
        base_p.write_text(json.dumps(base))
        ours_p.write_text(json.dumps(ours))
        theirs_p.write_text(json.dumps(theirs))
        exit_code = merge_canvases(base_p, ours_p, theirs_p)
        assert exit_code == 0
