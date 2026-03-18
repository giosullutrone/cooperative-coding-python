from ccoding.sync.conflict import resolve_conflict, ConflictResolution
from ccoding.sync.differ import Conflict

class TestResolveConflict:
    def test_keep_canvas(self):
        conflict = Conflict(qualified_name="Foo", canvas_hash="a", code_hash="b",
                           stored_canvas_hash="c", stored_code_hash="d")
        assert resolve_conflict(conflict, strategy="canvas-wins") == ConflictResolution.USE_CANVAS

    def test_keep_code(self):
        conflict = Conflict(qualified_name="Foo", canvas_hash="a", code_hash="b",
                           stored_canvas_hash="c", stored_code_hash="d")
        assert resolve_conflict(conflict, strategy="code-wins") == ConflictResolution.USE_CODE

    def test_manual(self):
        conflict = Conflict(qualified_name="Foo", canvas_hash="a", code_hash="b",
                           stored_canvas_hash="c", stored_code_hash="d")
        assert resolve_conflict(conflict, strategy=None) == ConflictResolution.MANUAL
