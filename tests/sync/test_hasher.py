from ccoding.sync.hasher import content_hash

class TestContentHash:
    def test_same_content_same_hash(self):
        assert content_hash("hello world") == content_hash("hello world")
    def test_different_content_different_hash(self):
        assert content_hash("hello") != content_hash("world")
    def test_ignores_trailing_whitespace(self):
        assert content_hash("hello  \n") == content_hash("hello")
    def test_ignores_blank_line_differences(self):
        assert content_hash("line1\n\n\nline2") == content_hash("line1\n\nline2")
    def test_preserves_meaningful_indentation(self):
        assert content_hash("  indented") != content_hash("indented")
