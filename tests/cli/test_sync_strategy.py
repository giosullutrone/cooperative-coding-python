"""Tests for conflict resolution strategy string correctness."""
from ccoding.sync.conflict import resolve_conflict, ConflictResolution
from ccoding.sync.differ import Conflict


class TestConflictStrategyStrings:
    def test_canvas_wins_resolves(self):
        conflict = Conflict(
            qualified_name="mod.Foo",
            canvas_hash="a",
            code_hash="b",
            stored_canvas_hash="c",
            stored_code_hash="d",
        )
        result = resolve_conflict(conflict, strategy="canvas-wins")
        assert result == ConflictResolution.USE_CANVAS

    def test_code_wins_resolves(self):
        conflict = Conflict(
            qualified_name="mod.Foo",
            canvas_hash="a",
            code_hash="b",
            stored_canvas_hash="c",
            stored_code_hash="d",
        )
        result = resolve_conflict(conflict, strategy="code-wins")
        assert result == ConflictResolution.USE_CODE

    def test_old_strategy_strings_no_longer_resolve(self):
        """The old strings 'canvas' and 'code' must fall through to MANUAL."""
        conflict = Conflict(
            qualified_name="mod.Foo",
            canvas_hash="a",
            code_hash="b",
            stored_canvas_hash="c",
            stored_code_hash="d",
        )
        assert resolve_conflict(conflict, strategy="canvas") == ConflictResolution.MANUAL
        assert resolve_conflict(conflict, strategy="code") == ConflictResolution.MANUAL
