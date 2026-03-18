from ccoding.sync.differ import compute_diff, SyncDiff, Conflict
from ccoding.sync.state import SyncState, ElementState

class TestComputeDiff:
    def _make_state(self, elements: dict) -> SyncState:
        return SyncState(canvas_file="test.canvas", elements={
            name: ElementState(
                canvas_hash=e["ch"], code_hash=e["kh"],
                canvas_node_id=e.get("nid", "n1"), source_path=e.get("src", "src/x.py"),
            )
            for name, e in elements.items()
        })

    def test_in_sync(self):
        state = self._make_state({"Foo": {"ch": "aaa", "kh": "bbb"}})
        diff = compute_diff(state, {"Foo": "aaa"}, {"Foo": "bbb"})
        assert diff.in_sync == ["Foo"]
        assert diff.conflicts == []

    def test_canvas_modified(self):
        state = self._make_state({"Foo": {"ch": "aaa", "kh": "bbb"}})
        diff = compute_diff(state, {"Foo": "changed"}, {"Foo": "bbb"})
        assert "Foo" in diff.canvas_modified

    def test_code_modified(self):
        state = self._make_state({"Foo": {"ch": "aaa", "kh": "bbb"}})
        diff = compute_diff(state, {"Foo": "aaa"}, {"Foo": "changed"})
        assert "Foo" in diff.code_modified

    def test_conflict(self):
        state = self._make_state({"Foo": {"ch": "aaa", "kh": "bbb"}})
        diff = compute_diff(state, {"Foo": "new_canvas"}, {"Foo": "new_code"})
        assert len(diff.conflicts) == 1
        assert diff.conflicts[0].qualified_name == "Foo"

    def test_canvas_added(self):
        state = self._make_state({})
        diff = compute_diff(state, {"Foo": "aaa"}, {})
        assert "Foo" in diff.canvas_added

    def test_code_added(self):
        state = self._make_state({})
        diff = compute_diff(state, {}, {"Foo": "bbb"})
        assert "Foo" in diff.code_added

    def test_canvas_deleted(self):
        state = self._make_state({"Foo": {"ch": "aaa", "kh": "bbb"}})
        diff = compute_diff(state, {}, {"Foo": "bbb"})
        assert "Foo" in diff.canvas_deleted

    def test_code_deleted(self):
        state = self._make_state({"Foo": {"ch": "aaa", "kh": "bbb"}})
        diff = compute_diff(state, {"Foo": "aaa"}, {})
        assert "Foo" in diff.code_deleted
