from pathlib import Path
import json
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def tmp_canvas(tmp_path: Path) -> Path:
    """An empty canvas file in a temp directory."""
    canvas_path = tmp_path / "test.canvas"
    canvas_path.write_text(json.dumps({"nodes": [], "edges": []}))
    return canvas_path


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """A temp directory initialized as a ccoding project."""
    ccoding_dir = tmp_path / ".ccoding"
    ccoding_dir.mkdir()
    (ccoding_dir / "config.json").write_text(json.dumps({
        "version": 1,
        "canvas": "design.canvas",
        "sourceRoot": "src/",
        "language": "python",
        "ignore": [],
        "liveMode": "never",
        "git": {
            "preCommitHook": False,
            "mergeDriver": False,
            "gitAwareSync": False,
        },
    }))
    (ccoding_dir / "sync-state.json").write_text(json.dumps({
        "version": 1,
        "lastSync": None,
        "canvasFile": "design.canvas",
        "elements": {},
    }))
    (tmp_path / "design.canvas").write_text(json.dumps({"nodes": [], "edges": []}))
    (tmp_path / "src").mkdir()
    return tmp_path
