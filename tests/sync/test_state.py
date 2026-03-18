import json
from pathlib import Path
from ccoding.sync.state import SyncState, ElementState, load_sync_state, save_sync_state

class TestSyncState:
    def test_load_empty(self, tmp_project: Path):
        state = load_sync_state(tmp_project)
        assert state.elements == {}
        assert state.canvas_file == "design.canvas"

    def test_save_and_reload(self, tmp_project: Path):
        state = SyncState(
            canvas_file="design.canvas",
            elements={
                "parsers.DocumentParser": ElementState(
                    canvas_hash="abc123", code_hash="def456",
                    canvas_node_id="node-1", source_path="src/parsers.py",
                ),
            },
        )
        save_sync_state(state, tmp_project)
        reloaded = load_sync_state(tmp_project)
        assert "parsers.DocumentParser" in reloaded.elements
        elem = reloaded.elements["parsers.DocumentParser"]
        assert elem.canvas_hash == "abc123"
        assert elem.code_hash == "def456"

    def test_update_element(self, tmp_project: Path):
        state = load_sync_state(tmp_project)
        state.elements["Foo"] = ElementState(
            canvas_hash="aaa", code_hash="bbb",
            canvas_node_id="n1", source_path="src/foo.py",
        )
        save_sync_state(state, tmp_project)
        reloaded = load_sync_state(tmp_project)
        assert "Foo" in reloaded.elements
