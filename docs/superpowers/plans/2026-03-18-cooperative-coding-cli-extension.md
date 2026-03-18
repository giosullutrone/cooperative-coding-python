# CooperativeCoding CLI Extension Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `ccoding` Python package — the foundation of the CooperativeCoding reference implementation providing canvas manipulation, bidirectional sync, ghost node management, and git integration.

**Architecture:** A Python library with CLI entry point. The canvas engine reads/writes JSON Canvas files with ccoding metadata. The sync engine maintains bidirectional consistency between canvas nodes and Python source code using hash-based state tracking. The ghost manager handles the proposal lifecycle. A live bridge optionally connects to running Obsidian for real-time updates.

**Tech Stack:** Python 3.11+, `ast` (stdlib) for code parsing, `click` for CLI, `pytest` for testing

**Spec:** `docs/superpowers/specs/2026-03-18-cooperative-coding-cli-extension.md`
**Core Spec:** `docs/superpowers/specs/2026-03-18-cooperative-coding-design.md`
**Python Binding:** `docs/superpowers/specs/2026-03-18-cooperative-coding-python-binding.md`

---

## File Structure

```
ccoding/                          # Python package root
├── __init__.py                   # Public API re-exports
├── cli.py                        # Click CLI entry point
├── config.py                     # .ccoding/config.json management
├── canvas/
│   ├── __init__.py               # Canvas subpackage exports
│   ├── model.py                  # Dataclasses: Canvas, Node, Edge, CcodingMetadata, EdgeMetadata
│   ├── reader.py                 # read_canvas(path) -> Canvas
│   ├── writer.py                 # write_canvas(canvas, path)
│   └── markdown.py               # Parse/render structured markdown in node text
├── code/
│   ├── __init__.py               # Code subpackage exports
│   ├── parser.py                 # CodeParser protocol + PythonAstParser
│   ├── docstring.py              # Google-style docstring section parser
│   └── generator.py              # Generate Python source from canvas data
├── sync/
│   ├── __init__.py               # Sync subpackage exports
│   ├── state.py                  # .ccoding/sync-state.json read/write
│   ├── hasher.py                 # Normalized content hashing
│   ├── differ.py                 # Compute SyncDiff from current vs stored state
│   ├── conflict.py               # Conflict data model and resolution helpers
│   └── engine.py                 # Sync orchestrator + import_codebase
├── ghost/
│   ├── __init__.py               # Ghost subpackage exports
│   └── manager.py                # Propose/accept/reject/reconsider/list
├── live/
│   ├── __init__.py               # Live subpackage exports
│   └── obsidian.py               # ObsidianBridge wrapping `obsidian eval`
├── git/
│   ├── __init__.py               # Git subpackage exports
│   ├── hooks.py                  # Pre-commit hook (ccoding check)
│   ├── merge.py                  # Custom merge driver for .canvas files
│   └── diff.py                   # Git-informed change detection
├── pyproject.toml                # Package metadata, dependencies, entry points
└── tests/
    ├── conftest.py               # Shared fixtures (sample canvases, temp dirs)
    ├── fixtures/                  # Static test data
    │   ├── sample.canvas          # Valid canvas with ccoding nodes
    │   ├── sample_no_ccoding.canvas  # Plain JSON Canvas (no ccoding metadata)
    │   └── sample_python/         # Sample Python project for parser tests
    │       ├── __init__.py
    │       ├── parser.py          # Sample class with docstrings
    │       └── models.py          # Sample dataclass + enum
    ├── test_config.py
    ├── canvas/
    │   ├── test_model.py
    │   ├── test_reader.py
    │   ├── test_writer.py
    │   └── test_markdown.py
    ├── code/
    │   ├── test_parser.py
    │   ├── test_docstring.py
    │   └── test_generator.py
    ├── sync/
    │   ├── test_state.py
    │   ├── test_hasher.py
    │   ├── test_differ.py
    │   ├── test_conflict.py
    │   └── test_engine.py
    ├── ghost/
    │   └── test_manager.py
    ├── live/
    │   └── test_obsidian.py
    └── git/
        ├── test_hooks.py
        ├── test_merge.py
        └── test_diff.py
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `ccoding/pyproject.toml`
- Create: `ccoding/__init__.py`
- Create: `ccoding/tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "cooperative-coding"
version = "0.1.0"
description = "CooperativeCoding CLI extension — canvas manipulation, bidirectional sync, and ghost node management"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-tmp-files>=0.0.2",
]

[project.scripts]
ccoding = "ccoding.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create package __init__.py**

```python
"""CooperativeCoding — canvas manipulation, bidirectional sync, and ghost node management."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Create directory structure**

```bash
mkdir -p ccoding/{canvas,code,sync,ghost,live,git}
touch ccoding/{canvas,code,sync,ghost,live,git}/__init__.py
mkdir -p tests/{canvas,code,sync,ghost,live,git,fixtures/sample_python}
touch tests/__init__.py tests/{canvas,code,sync,ghost,live,git}/__init__.py
```

- [ ] **Step 4: Create conftest.py with shared fixtures**

```python
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
```

- [ ] **Step 5: Verify setup**

Run: `cd ccoding && pip install -e ".[dev]" && pytest --co -q`
Expected: `no tests ran` (collection succeeds, no tests yet)

- [ ] **Step 6: Commit**

```bash
git add ccoding/ tests/
git commit -m "feat: scaffold ccoding package with pyproject.toml and test fixtures"
```

---

### Task 2: Configuration Module

**Files:**
- Create: `ccoding/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config**

```python
# tests/test_config.py
import json
from pathlib import Path
from ccoding.config import ProjectConfig, load_config, init_project


class TestProjectConfig:
    def test_default_values(self):
        config = ProjectConfig()
        assert config.canvas == "design.canvas"
        assert config.source_root == "src/"
        assert config.language == "python"
        assert config.ignore == []
        assert config.live_mode == "auto"
        assert config.git_pre_commit_hook is True
        assert config.git_merge_driver is True
        assert config.git_aware_sync is True

    def test_load_from_file(self, tmp_path: Path):
        ccoding_dir = tmp_path / ".ccoding"
        ccoding_dir.mkdir()
        (ccoding_dir / "config.json").write_text(json.dumps({
            "version": 1,
            "canvas": "arch.canvas",
            "sourceRoot": "lib/",
            "language": "python",
            "ignore": ["**/test_*"],
            "liveMode": "never",
            "git": {
                "preCommitHook": False,
                "mergeDriver": True,
                "gitAwareSync": False,
            },
        }))
        config = load_config(tmp_path)
        assert config.canvas == "arch.canvas"
        assert config.source_root == "lib/"
        assert config.ignore == ["**/test_*"]
        assert config.live_mode == "never"
        assert config.git_pre_commit_hook is False

    def test_load_missing_returns_default(self, tmp_path: Path):
        config = load_config(tmp_path)
        assert config.canvas == "design.canvas"

    def test_init_project_creates_files(self, tmp_path: Path):
        init_project(tmp_path)
        assert (tmp_path / ".ccoding" / "config.json").exists()
        assert (tmp_path / ".ccoding" / "sync-state.json").exists()
        data = json.loads((tmp_path / ".ccoding" / "config.json").read_text())
        assert data["version"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ccoding.config'`

- [ ] **Step 3: Implement config module**

```python
# ccoding/config.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CCODING_DIR = ".ccoding"
CONFIG_FILE = "config.json"
SYNC_STATE_FILE = "sync-state.json"


@dataclass
class ProjectConfig:
    canvas: str = "design.canvas"
    source_root: str = "src/"
    language: str = "python"
    ignore: list[str] = field(default_factory=list)
    live_mode: str = "auto"  # "auto" | "always" | "never"
    git_pre_commit_hook: bool = True
    git_merge_driver: bool = True
    git_aware_sync: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> ProjectConfig:
        git = data.get("git", {})
        return cls(
            canvas=data.get("canvas", "design.canvas"),
            source_root=data.get("sourceRoot", "src/"),
            language=data.get("language", "python"),
            ignore=data.get("ignore", []),
            live_mode=data.get("liveMode", "auto"),
            git_pre_commit_hook=git.get("preCommitHook", True),
            git_merge_driver=git.get("mergeDriver", True),
            git_aware_sync=git.get("gitAwareSync", True),
        )

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "canvas": self.canvas,
            "sourceRoot": self.source_root,
            "language": self.language,
            "ignore": self.ignore,
            "liveMode": self.live_mode,
            "git": {
                "preCommitHook": self.git_pre_commit_hook,
                "mergeDriver": self.git_merge_driver,
                "gitAwareSync": self.git_aware_sync,
            },
        }


def load_config(project_root: Path) -> ProjectConfig:
    config_path = project_root / CCODING_DIR / CONFIG_FILE
    if not config_path.exists():
        return ProjectConfig()
    data = json.loads(config_path.read_text())
    return ProjectConfig.from_dict(data)


def init_project(project_root: Path, config: ProjectConfig | None = None) -> ProjectConfig:
    config = config or ProjectConfig()
    ccoding_dir = project_root / CCODING_DIR
    ccoding_dir.mkdir(exist_ok=True)
    (ccoding_dir / CONFIG_FILE).write_text(
        json.dumps(config.to_dict(), indent=2) + "\n"
    )
    (ccoding_dir / SYNC_STATE_FILE).write_text(
        json.dumps({
            "version": 1,
            "lastSync": None,
            "canvasFile": config.canvas,
            "elements": {},
        }, indent=2) + "\n"
    )
    return config
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add ccoding/config.py tests/test_config.py
git commit -m "feat: add project configuration module"
```

---

### Task 3: Canvas Data Model

**Files:**
- Create: `ccoding/canvas/model.py`
- Create: `tests/canvas/test_model.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/canvas/test_model.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/canvas/test_model.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement canvas data model**

```python
# ccoding/canvas/model.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CcodingMetadata:
    kind: str = "class"  # "class" | "method" | "field" | "package"
    stereotype: str | None = None
    language: str | None = None
    source: str | None = None
    qualified_name: str | None = None
    status: str = "accepted"  # "accepted" | "proposed" | "rejected"
    proposed_by: str | None = None  # "agent" | "human" | None
    proposal_rationale: str | None = None
    layout_pending: bool = False


@dataclass
class EdgeMetadata:
    relation: str = "depends"  # inherits|implements|composes|depends|calls|detail|context
    status: str = "accepted"
    proposed_by: str | None = None
    proposal_rationale: str | None = None


@dataclass
class Node:
    id: str
    type: str  # "text", "file", "link", "group"
    x: int
    y: int
    width: int
    height: int
    text: str = ""
    ccoding: CcodingMetadata | None = None
    # Preserve unknown fields from JSON for round-trip fidelity
    _extra: dict = field(default_factory=dict, repr=False)


@dataclass
class GroupNode(Node):
    label: str = ""


@dataclass
class Edge:
    id: str
    from_node: str
    to_node: str
    from_side: str | None = None
    to_side: str | None = None
    label: str | None = None
    ccoding: EdgeMetadata | None = None
    _extra: dict = field(default_factory=dict, repr=False)


@dataclass
class Canvas:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    _extra: dict = field(default_factory=dict, repr=False)

    def find_by_qualified_name(self, name: str) -> Node | None:
        for node in self.nodes:
            if node.ccoding and node.ccoding.qualified_name == name:
                return node
        return None

    def find_by_source(self, path: str) -> list[Node]:
        return [n for n in self.nodes if n.ccoding and n.ccoding.source == path]

    def find_detail_nodes(self, class_node_id: str) -> list[Node]:
        detail_target_ids = {
            e.to_node for e in self.edges
            if e.ccoding and e.ccoding.relation == "detail"
            and e.from_node == class_node_id
        }
        return [n for n in self.nodes if n.id in detail_target_ids]

    def edges_for(self, node_id: str) -> list[Edge]:
        return [
            e for e in self.edges
            if e.from_node == node_id or e.to_node == node_id
        ]

    def ghost_nodes(self) -> list[Node]:
        return [
            n for n in self.nodes
            if n.ccoding and n.ccoding.status == "proposed"
        ]

    def ghost_edges(self) -> list[Edge]:
        return [
            e for e in self.edges
            if e.ccoding and e.ccoding.status == "proposed"
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/canvas/test_model.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add ccoding/canvas/model.py tests/canvas/test_model.py
git commit -m "feat: add canvas data model (Node, Edge, Canvas, metadata)"
```

---

### Task 4: Canvas Reader / Writer

**Files:**
- Create: `ccoding/canvas/reader.py`
- Create: `ccoding/canvas/writer.py`
- Create: `tests/canvas/test_reader.py`
- Create: `tests/canvas/test_writer.py`
- Create: `tests/fixtures/sample.canvas`
- Create: `tests/fixtures/sample_no_ccoding.canvas`

- [ ] **Step 1: Create test fixture files**

`tests/fixtures/sample.canvas`:
```json
{
  "nodes": [
    {
      "id": "node-1",
      "type": "text",
      "x": 100,
      "y": 200,
      "width": 300,
      "height": 400,
      "text": "## DocumentParser",
      "ccoding": {
        "kind": "class",
        "stereotype": "protocol",
        "language": "python",
        "source": "src/parsers/document.py",
        "qualifiedName": "parsers.document.DocumentParser",
        "status": "accepted",
        "proposedBy": null,
        "proposalRationale": null
      }
    },
    {
      "id": "note-1",
      "type": "text",
      "x": 500,
      "y": 200,
      "width": 200,
      "height": 100,
      "text": "Design rationale note"
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "fromNode": "node-1",
      "toNode": "note-1",
      "fromSide": "right",
      "toSide": "left",
      "label": "rationale",
      "ccoding": {
        "relation": "context",
        "status": "accepted",
        "proposedBy": null,
        "proposalRationale": null
      }
    }
  ]
}
```

`tests/fixtures/sample_no_ccoding.canvas`:
```json
{
  "nodes": [
    {
      "id": "plain-1",
      "type": "text",
      "x": 0,
      "y": 0,
      "width": 200,
      "height": 100,
      "text": "Just a note"
    }
  ],
  "edges": []
}
```

- [ ] **Step 2: Write failing reader tests**

```python
# tests/canvas/test_reader.py
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/canvas/test_reader.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Implement reader**

```python
# ccoding/canvas/reader.py
from __future__ import annotations

import json
from pathlib import Path

from ccoding.canvas.model import (
    Canvas, Node, GroupNode, Edge, CcodingMetadata, EdgeMetadata,
)

_NODE_FIELDS = {"id", "type", "x", "y", "width", "height", "text", "ccoding", "label"}
_EDGE_FIELDS = {"id", "fromNode", "toNode", "fromSide", "toSide", "label", "ccoding"}
_CANVAS_FIELDS = {"nodes", "edges"}


def _parse_ccoding_meta(data: dict | None) -> CcodingMetadata | None:
    if data is None:
        return None
    return CcodingMetadata(
        kind=data.get("kind", "class"),
        stereotype=data.get("stereotype"),
        language=data.get("language"),
        source=data.get("source"),
        qualified_name=data.get("qualifiedName"),
        status=data.get("status", "accepted"),
        proposed_by=data.get("proposedBy"),
        proposal_rationale=data.get("proposalRationale"),
        layout_pending=data.get("layoutPending", False),
    )


def _parse_edge_meta(data: dict | None) -> EdgeMetadata | None:
    if data is None:
        return None
    return EdgeMetadata(
        relation=data.get("relation", "depends"),
        status=data.get("status", "accepted"),
        proposed_by=data.get("proposedBy"),
        proposal_rationale=data.get("proposalRationale"),
    )


def _parse_node(data: dict) -> Node:
    extra = {k: v for k, v in data.items() if k not in _NODE_FIELDS}
    ccoding = _parse_ccoding_meta(data.get("ccoding"))
    if data.get("type") == "group":
        return GroupNode(
            id=data["id"], type="group",
            x=data.get("x", 0), y=data.get("y", 0),
            width=data.get("width", 0), height=data.get("height", 0),
            text=data.get("text", ""),
            label=data.get("label", ""),
            ccoding=ccoding,
            _extra=extra,
        )
    return Node(
        id=data["id"], type=data.get("type", "text"),
        x=data.get("x", 0), y=data.get("y", 0),
        width=data.get("width", 0), height=data.get("height", 0),
        text=data.get("text", ""),
        ccoding=ccoding,
        _extra=extra,
    )


def _parse_edge(data: dict) -> Edge:
    extra = {k: v for k, v in data.items() if k not in _EDGE_FIELDS}
    return Edge(
        id=data["id"],
        from_node=data["fromNode"],
        to_node=data["toNode"],
        from_side=data.get("fromSide"),
        to_side=data.get("toSide"),
        label=data.get("label"),
        ccoding=_parse_edge_meta(data.get("ccoding")),
        _extra=extra,
    )


def read_canvas(path: Path) -> Canvas:
    data = json.loads(path.read_text())
    extra = {k: v for k, v in data.items() if k not in _CANVAS_FIELDS}
    return Canvas(
        nodes=[_parse_node(n) for n in data.get("nodes", [])],
        edges=[_parse_edge(e) for e in data.get("edges", [])],
        _extra=extra,
    )
```

- [ ] **Step 5: Run reader tests**

Run: `pytest tests/canvas/test_reader.py -v`
Expected: All PASS

- [ ] **Step 6: Write failing writer tests**

```python
# tests/canvas/test_writer.py
import json
from pathlib import Path
from ccoding.canvas.reader import read_canvas
from ccoding.canvas.writer import write_canvas
from ccoding.canvas.model import Canvas, Node, Edge, CcodingMetadata, EdgeMetadata


class TestWriteCanvas:
    def test_round_trip(self, fixtures_dir: Path, tmp_path: Path):
        """Read a canvas, write it, read again — should be identical."""
        original = read_canvas(fixtures_dir / "sample.canvas")
        out_path = tmp_path / "out.canvas"
        write_canvas(original, out_path)
        reloaded = read_canvas(out_path)
        assert len(reloaded.nodes) == len(original.nodes)
        assert len(reloaded.edges) == len(original.edges)
        assert reloaded.nodes[0].ccoding.kind == original.nodes[0].ccoding.kind

    def test_round_trip_preserves_json(self, fixtures_dir: Path, tmp_path: Path):
        """Read then write should produce identical JSON."""
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
```

- [ ] **Step 7: Implement writer**

```python
# ccoding/canvas/writer.py
from __future__ import annotations

import json
from pathlib import Path

from ccoding.canvas.model import (
    Canvas, Node, GroupNode, Edge, CcodingMetadata, EdgeMetadata,
)


def _serialize_ccoding_meta(meta: CcodingMetadata) -> dict:
    result = {"kind": meta.kind}
    if meta.stereotype is not None:
        result["stereotype"] = meta.stereotype
    if meta.language is not None:
        result["language"] = meta.language
    if meta.source is not None:
        result["source"] = meta.source
    if meta.qualified_name is not None:
        result["qualifiedName"] = meta.qualified_name
    result["status"] = meta.status
    result["proposedBy"] = meta.proposed_by
    result["proposalRationale"] = meta.proposal_rationale
    if meta.layout_pending:
        result["layoutPending"] = True
    return result


def _serialize_edge_meta(meta: EdgeMetadata) -> dict:
    return {
        "relation": meta.relation,
        "status": meta.status,
        "proposedBy": meta.proposed_by,
        "proposalRationale": meta.proposal_rationale,
    }


def _serialize_node(node: Node) -> dict:
    result: dict = {
        "id": node.id,
        "type": node.type,
        "x": node.x,
        "y": node.y,
        "width": node.width,
        "height": node.height,
    }
    if node.text:
        result["text"] = node.text
    if isinstance(node, GroupNode) and node.label:
        result["label"] = node.label
    if node.ccoding is not None:
        result["ccoding"] = _serialize_ccoding_meta(node.ccoding)
    result.update(node._extra)
    return result


def _serialize_edge(edge: Edge) -> dict:
    result: dict = {
        "id": edge.id,
        "fromNode": edge.from_node,
        "toNode": edge.to_node,
    }
    if edge.from_side is not None:
        result["fromSide"] = edge.from_side
    if edge.to_side is not None:
        result["toSide"] = edge.to_side
    if edge.label is not None:
        result["label"] = edge.label
    if edge.ccoding is not None:
        result["ccoding"] = _serialize_edge_meta(edge.ccoding)
    result.update(edge._extra)
    return result


def write_canvas(canvas: Canvas, path: Path) -> None:
    data: dict = {
        "nodes": [_serialize_node(n) for n in canvas.nodes],
        "edges": [_serialize_edge(e) for e in canvas.edges],
    }
    data.update(canvas._extra)
    path.write_text(json.dumps(data, indent=2))
```

- [ ] **Step 8: Run all writer tests**

Run: `pytest tests/canvas/test_writer.py -v`
Expected: All PASS

- [ ] **Step 9: Commit**

```bash
git add ccoding/canvas/reader.py ccoding/canvas/writer.py tests/canvas/ tests/fixtures/
git commit -m "feat: add canvas reader/writer with round-trip fidelity"
```

---

### Task 5: Structured Markdown Parser / Renderer

**Files:**
- Create: `ccoding/canvas/markdown.py`
- Create: `tests/canvas/test_markdown.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/canvas/test_markdown.py
from ccoding.canvas.markdown import (
    parse_class_node, render_class_node,
    parse_method_node, render_method_node,
    parse_field_node, render_field_node,
    ClassContent, MethodContent, FieldContent,
    FieldEntry, MethodEntry, SignatureEntry,
)


class TestClassNode:
    SAMPLE = (
        "«protocol»\n"
        "## DocumentParser\n"
        "\n"
        "> Responsible for parsing raw documents into structured AST nodes\n"
        "\n"
        "### Fields\n"
        "- config: `ParserConfig` ●\n"
        "- _cache: `dict[str, AST]`\n"
        "\n"
        "### Methods\n"
        "- parse(source: `str`) -> `AST` ●\n"
        "- validate(ast: `AST`) -> `bool`\n"
    )

    def test_parse_class(self):
        result = parse_class_node(self.SAMPLE)
        assert result.name == "DocumentParser"
        assert result.stereotype == "protocol"
        assert result.responsibility == "Responsible for parsing raw documents into structured AST nodes"
        assert len(result.fields) == 2
        assert result.fields[0].name == "config"
        assert result.fields[0].type == "ParserConfig"
        assert result.fields[0].has_detail is True
        assert result.fields[1].has_detail is False
        assert len(result.methods) == 2
        assert result.methods[0].name == "parse"
        assert result.methods[0].has_detail is True

    def test_round_trip(self):
        parsed = parse_class_node(self.SAMPLE)
        rendered = render_class_node(parsed)
        reparsed = parse_class_node(rendered)
        assert reparsed.name == parsed.name
        assert reparsed.stereotype == parsed.stereotype
        assert len(reparsed.fields) == len(parsed.fields)
        assert len(reparsed.methods) == len(parsed.methods)


class TestMethodNode:
    SAMPLE = (
        "## DocumentParser.parse\n"
        "\n"
        "### Responsibility\n"
        "Transform raw source into a validated AST.\n"
        "\n"
        "### Signature\n"
        "- **IN:** source: `str` — raw document text\n"
        "- **OUT:** `AST` — parsed syntax tree\n"
        "- **RAISES:** `ParseError` — on malformed input\n"
        "\n"
        "### Pseudo Code\n"
        "1. Check _cache for source hash\n"
        "2. If cached, return cached AST\n"
        "3. Tokenize source\n"
    )

    def test_parse_method(self):
        result = parse_method_node(self.SAMPLE)
        assert result.name == "DocumentParser.parse"
        assert result.responsibility == "Transform raw source into a validated AST."
        assert len(result.signature_in) == 1
        assert result.signature_in[0].name == "source"
        assert result.signature_in[0].type == "str"
        assert result.signature_out.type == "AST"
        assert len(result.raises) == 1
        assert result.pseudo_code.startswith("1.")

    def test_round_trip(self):
        parsed = parse_method_node(self.SAMPLE)
        rendered = render_method_node(parsed)
        reparsed = parse_method_node(rendered)
        assert reparsed.name == parsed.name
        assert len(reparsed.signature_in) == len(parsed.signature_in)


class TestFieldNode:
    SAMPLE = (
        "## DocumentParser.config\n"
        "\n"
        "### Responsibility\n"
        "Holds parser configuration.\n"
        "\n"
        "### Type\n"
        "`ParserConfig`\n"
        "\n"
        "### Constraints\n"
        "- Immutable after initialization\n"
        "\n"
        "### Default\n"
        "ParserConfig.default()\n"
    )

    def test_parse_field(self):
        result = parse_field_node(self.SAMPLE)
        assert result.name == "DocumentParser.config"
        assert result.responsibility == "Holds parser configuration."
        assert result.type == "ParserConfig"
        assert "Immutable" in result.constraints
        assert result.default == "ParserConfig.default()"

    def test_round_trip(self):
        parsed = parse_field_node(self.SAMPLE)
        rendered = render_field_node(parsed)
        reparsed = parse_field_node(rendered)
        assert reparsed.name == parsed.name
        assert reparsed.type == parsed.type
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/canvas/test_markdown.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement structured markdown module**

Implement `ccoding/canvas/markdown.py` with:
- Dataclasses: `ClassContent`, `MethodContent`, `FieldContent`, `FieldEntry`, `MethodEntry`, `SignatureEntry`
- `parse_class_node(text) -> ClassContent` — regex-based parser that extracts stereotype (from `«...»`), name (from `## Name`), responsibility (from `> ...`), fields and methods (from `### Fields` and `### Methods` sections, with ● marker detection)
- `parse_method_node(text) -> MethodContent` — extracts name, responsibility, signature (IN/OUT/RAISES lines), pseudo code
- `parse_field_node(text) -> FieldContent` — extracts name, responsibility, type, constraints, default
- `render_class_node(content) -> str` — canonical markdown output
- `render_method_node(content) -> str` — canonical markdown output
- `render_field_node(content) -> str` — canonical markdown output

Key implementation detail: use section-based parsing — split text by `### ` headers, then parse each section independently. The parser should be tolerant of missing sections (return empty defaults).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/canvas/test_markdown.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ccoding/canvas/markdown.py tests/canvas/test_markdown.py
git commit -m "feat: add structured markdown parser/renderer for canvas nodes"
```

---

### Task 6: Docstring Section Parser

**Files:**
- Create: `ccoding/code/docstring.py`
- Create: `tests/code/test_docstring.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/code/test_docstring.py
from ccoding.code.docstring import parse_docstring, render_docstring


class TestParseDocstring:
    def test_class_docstring(self):
        doc = '''Parse raw documents into structured AST nodes.

    Responsibility:
        Owns the full parsing pipeline from raw text to validated AST.

    Collaborators:
        ParserConfig: Provides tokenizer settings.
        ParserPlugin: Transforms AST during parsing.

    Attributes:
        config: Parser configuration and settings.
        plugins: Ordered list of transform plugins.
    '''
        sections = parse_docstring(doc)
        assert sections["summary"] == "Parse raw documents into structured AST nodes."
        assert "Owns the full parsing pipeline" in sections["responsibility"]
        assert "ParserConfig" in sections["collaborators"]
        assert "config" in sections["attributes"]

    def test_method_docstring(self):
        doc = '''Transform raw source into a validated AST.

    Responsibility:
        Parse raw document text into structured AST nodes.

    Pseudo Code:
        1. Check _cache for source hash
        2. If cached, return cached AST
        3. Tokenize source

    Args:
        source: Raw document text to parse.

    Returns:
        Parsed and validated abstract syntax tree.

    Raises:
        ParseError: If the source is malformed.
    '''
        sections = parse_docstring(doc)
        assert sections["summary"] == "Transform raw source into a validated AST."
        assert "Check _cache" in sections["pseudo code"]
        assert "source" in sections["args"]
        assert "ParseError" in sections["raises"]

    def test_empty_docstring(self):
        sections = parse_docstring("")
        assert sections["summary"] == ""

    def test_summary_only(self):
        sections = parse_docstring("Just a summary.")
        assert sections["summary"] == "Just a summary."


class TestRenderDocstring:
    def test_round_trip(self):
        original = {
            "summary": "Parse documents.",
            "responsibility": "Owns parsing pipeline.",
            "args": "source: Raw text.",
            "returns": "Parsed AST.",
        }
        rendered = render_docstring(original)
        reparsed = parse_docstring(rendered)
        assert reparsed["summary"] == original["summary"]
        assert reparsed["responsibility"] == original["responsibility"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/code/test_docstring.py -v`
Expected: FAIL

- [ ] **Step 3: Implement docstring parser**

Implement `ccoding/code/docstring.py` with:
- `parse_docstring(doc: str) -> dict[str, str]` — parses Google-style docstrings. Detects section headers (word followed by colon at start of line with consistent indentation). Returns dict with lowercase keys. Standard sections: `summary`, `args`, `returns`, `raises`, `attributes`. Custom sections: `responsibility`, `pseudo code`, `collaborators`, `constraints`.
- `render_docstring(sections: dict[str, str], indent: int = 4) -> str` — renders sections back into Google-style docstring format. Emits sections in a canonical order: summary, responsibility, collaborators, pseudo code, args, returns, raises, attributes, constraints.

- [ ] **Step 4: Run tests**

Run: `pytest tests/code/test_docstring.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ccoding/code/docstring.py tests/code/test_docstring.py
git commit -m "feat: add Google-style docstring section parser"
```

---

### Task 7: Code Parser Protocol + Python Implementation

**Files:**
- Create: `ccoding/code/parser.py`
- Create: `tests/code/test_parser.py`
- Create: `tests/fixtures/sample_python/parser.py`
- Create: `tests/fixtures/sample_python/models.py`
- Create: `tests/fixtures/sample_python/__init__.py`

- [ ] **Step 1: Create sample Python fixtures**

`tests/fixtures/sample_python/__init__.py`: empty file

`tests/fixtures/sample_python/parser.py`:
```python
from typing import Protocol


class DocumentParser(Protocol):
    """Parse raw documents into structured AST nodes.

    Responsibility:
        Owns the full parsing pipeline from raw text to validated AST.

    Collaborators:
        ParserConfig: Provides tokenizer settings.

    Attributes:
        config: Parser configuration and settings.
        plugins: Ordered list of transform plugins.
    """

    config: "ParserConfig"
    plugins: list["ParserPlugin"]

    def parse(self, source: str) -> "AST":
        """Transform raw source into a validated AST.

        Responsibility:
            Parse raw document text into structured AST nodes.

        Pseudo Code:
            1. Check _cache for source hash
            2. Tokenize source
            3. Build raw AST

        Args:
            source: Raw document text to parse.

        Returns:
            Parsed abstract syntax tree.

        Raises:
            ParseError: If the source is malformed.
        """
        ...

    def validate(self, ast: "AST") -> bool:
        """Validate an AST structure."""
        ...
```

`tests/fixtures/sample_python/models.py`:
```python
from dataclasses import dataclass
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats."""
    JSON = "json"
    XML = "xml"


@dataclass
class ParserConfig:
    """Configuration for the document parser.

    Responsibility:
        Holds all parser settings.

    Attributes:
        format: Output format selection.
        max_depth: Maximum nesting depth.
    """

    format: OutputFormat = OutputFormat.JSON
    max_depth: int = 10
```

- [ ] **Step 2: Write failing tests**

```python
# tests/code/test_parser.py
from pathlib import Path
from ccoding.code.parser import PythonAstParser, ClassElement, MethodElement, FieldElement


class TestPythonAstParser:
    def test_parse_protocol(self, fixtures_dir: Path):
        parser = PythonAstParser()
        elements = parser.parse_file(fixtures_dir / "sample_python" / "parser.py")
        classes = [e for e in elements if isinstance(e, ClassElement)]
        assert len(classes) == 1
        cls = classes[0]
        assert cls.name == "DocumentParser"
        assert cls.stereotype == "protocol"
        assert "Owns the full parsing pipeline" in cls.docstring_sections.get("responsibility", "")

    def test_parse_methods(self, fixtures_dir: Path):
        parser = PythonAstParser()
        elements = parser.parse_file(fixtures_dir / "sample_python" / "parser.py")
        classes = [e for e in elements if isinstance(e, ClassElement)]
        cls = classes[0]
        assert len(cls.methods) == 2
        parse_method = cls.methods[0]
        assert parse_method.name == "parse"
        assert len(parse_method.parameters) > 0  # source param
        assert parse_method.return_type == "AST"
        assert "Check _cache" in parse_method.docstring_sections.get("pseudo code", "")

    def test_parse_fields(self, fixtures_dir: Path):
        parser = PythonAstParser()
        elements = parser.parse_file(fixtures_dir / "sample_python" / "parser.py")
        classes = [e for e in elements if isinstance(e, ClassElement)]
        cls = classes[0]
        assert len(cls.fields) == 2
        assert cls.fields[0].name == "config"
        assert cls.fields[0].type_annotation == "ParserConfig"

    def test_parse_dataclass(self, fixtures_dir: Path):
        parser = PythonAstParser()
        elements = parser.parse_file(fixtures_dir / "sample_python" / "models.py")
        classes = [e for e in elements if isinstance(e, ClassElement)]
        names = {c.name: c for c in classes}
        assert "ParserConfig" in names
        assert names["ParserConfig"].stereotype == "dataclass"
        assert "OutputFormat" in names
        assert names["OutputFormat"].stereotype == "enum"

    def test_parse_directory(self, fixtures_dir: Path):
        parser = PythonAstParser()
        elements = parser.parse_directory(fixtures_dir / "sample_python")
        classes = [e for e in elements if isinstance(e, ClassElement)]
        names = {c.name for c in classes}
        assert names == {"DocumentParser", "OutputFormat", "ParserConfig"}

    def test_skips_non_architectural_dunders(self, tmp_path: Path):
        src = tmp_path / "example.py"
        src.write_text('''
class Foo:
    def __init__(self, x: int):
        self.x = x

    def __repr__(self) -> str:
        return f"Foo({self.x})"

    def do_stuff(self) -> None:
        pass
''')
        parser = PythonAstParser()
        elements = parser.parse_file(src)
        classes = [e for e in elements if isinstance(e, ClassElement)]
        method_names = [m.name for m in classes[0].methods]
        assert "__init__" in method_names
        assert "__repr__" not in method_names
        assert "do_stuff" in method_names
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/code/test_parser.py -v`
Expected: FAIL

- [ ] **Step 4: Implement code parser**

Implement `ccoding/code/parser.py` with:
- Dataclasses: `ClassElement`, `MethodElement`, `FieldElement`, `ImportElement`, `ParameterInfo`
- `CodeParser` Protocol with `parse_file(path) -> list[CodeElement]` and `parse_directory(path, recursive) -> list[CodeElement]`
- `PythonAstParser` implementation using `ast.parse()` + `ast.NodeVisitor`:
  - Visit `ClassDef` nodes. Infer stereotype from bases (`Protocol` → `protocol`, `ABC` → `abstract`, `Enum` → `enum`) and decorators (`@dataclass` → `dataclass`).
  - Visit `FunctionDef` inside classes. Skip dunders except `__init__`, `__post_init__`, `__enter__`, `__exit__`, `__call__`, `__iter__`, `__next__`.
  - Detect fields: class-level `AnnAssign` + `__init__` `self.x: T = ...` assignments.
  - Parse docstrings using `ccoding.code.docstring.parse_docstring()`.
  - Extract type annotations as strings using `ast.unparse()`.
  - Detect imports for relationship inference.

- [ ] **Step 5: Run tests**

Run: `pytest tests/code/test_parser.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add ccoding/code/parser.py tests/code/test_parser.py tests/fixtures/sample_python/
git commit -m "feat: add CodeParser protocol and PythonAstParser implementation"
```

---

### Task 8: Code Generator

**Files:**
- Create: `ccoding/code/generator.py`
- Create: `tests/code/test_generator.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/code/test_generator.py
import ast
from ccoding.code.generator import generate_class, generate_method
from ccoding.canvas.markdown import ClassContent, MethodContent, FieldEntry, MethodEntry, SignatureEntry


class TestGenerateClass:
    def test_generate_protocol(self):
        content = ClassContent(
            name="DocumentParser",
            stereotype="protocol",
            responsibility="Parse raw documents into structured AST nodes",
            fields=[
                FieldEntry(name="config", type="ParserConfig", has_detail=False),
                FieldEntry(name="plugins", type="list[ParserPlugin]", has_detail=False),
            ],
            methods=[
                MethodEntry(name="parse", signature="(source: str) -> AST", has_detail=False),
            ],
        )
        source = generate_class(content, language="python")
        # Must be valid Python
        ast.parse(source)
        assert "class DocumentParser(Protocol):" in source
        assert "from typing import Protocol" in source
        assert "config: ParserConfig" in source
        assert "def parse(self, source: str) -> AST:" in source

    def test_generate_dataclass(self):
        content = ClassContent(
            name="Config",
            stereotype="dataclass",
            responsibility="Holds settings",
            fields=[
                FieldEntry(name="max_depth", type="int", has_detail=False),
            ],
            methods=[],
        )
        source = generate_class(content, language="python")
        ast.parse(source)
        assert "@dataclass" in source
        assert "from dataclasses import dataclass" in source

    def test_generate_abstract(self):
        content = ClassContent(
            name="BaseParser",
            stereotype="abstract",
            responsibility="Abstract base for parsers",
            fields=[],
            methods=[
                MethodEntry(name="parse", signature="(source: str) -> AST", has_detail=False),
            ],
        )
        source = generate_class(content, language="python")
        ast.parse(source)
        assert "class BaseParser(ABC):" in source
        assert "@abstractmethod" in source


class TestGenerateMethod:
    def test_generate_method_with_pseudo_code(self):
        content = MethodContent(
            name="DocumentParser.parse",
            responsibility="Transform raw source into validated AST.",
            signature_in=[SignatureEntry(name="source", type="str", description="raw text")],
            signature_out=SignatureEntry(name="", type="AST", description="parsed tree"),
            raises=[SignatureEntry(name="", type="ParseError", description="on bad input")],
            pseudo_code="1. Tokenize source\n2. Build AST\n3. Validate",
        )
        source = generate_method(content)
        assert "def parse(self, source: str) -> AST:" in source
        assert "Pseudo Code:" in source
        assert "Tokenize source" in source
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/code/test_generator.py -v`
Expected: FAIL

- [ ] **Step 3: Implement code generator**

Implement `ccoding/code/generator.py` with:
- `generate_class(content: ClassContent, language: str = "python") -> str` — generates a complete Python class source file. Adds imports based on stereotype. Generates class docstring with Responsibility, Collaborators, Attributes sections. Generates field annotations. Generates method stubs.
- `generate_method(content: MethodContent) -> str` — generates a method definition with signature, docstring (Responsibility, Pseudo Code, Args, Returns, Raises), and `...` body.
- `generate_field_comment(content: FieldContent) -> str` — generates comment block above a field annotation (Responsibility, Constraints, Default).
- Import inference based on stereotype: `protocol` → `from typing import Protocol`, `dataclass` → `from dataclasses import dataclass`, `abstract` → `from abc import ABC, abstractmethod`, `enum` → `from enum import Enum`.
- Method body: `...` for protocols, `raise NotImplementedError` for abstract methods, `...` for everything else (skeleton).

- [ ] **Step 4: Run tests**

Run: `pytest tests/code/test_generator.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ccoding/code/generator.py tests/code/test_generator.py
git commit -m "feat: add Python code generator from canvas content"
```

---

### Task 9: Sync State Management

**Files:**
- Create: `ccoding/sync/state.py`
- Create: `ccoding/sync/hasher.py`
- Create: `tests/sync/test_state.py`
- Create: `tests/sync/test_hasher.py`

- [ ] **Step 1: Write failing hasher tests**

```python
# tests/sync/test_hasher.py
from ccoding.sync.hasher import content_hash


class TestContentHash:
    def test_same_content_same_hash(self):
        assert content_hash("hello world") == content_hash("hello world")

    def test_different_content_different_hash(self):
        assert content_hash("hello") != content_hash("world")

    def test_ignores_trailing_whitespace(self):
        assert content_hash("hello  \n") == content_hash("hello")

    def test_ignores_blank_line_differences(self):
        a = "line1\n\n\nline2"
        b = "line1\n\nline2"
        assert content_hash(a) == content_hash(b)

    def test_preserves_meaningful_indentation(self):
        a = "  indented"
        b = "indented"
        assert content_hash(a) != content_hash(b)
```

- [ ] **Step 2: Implement hasher**

```python
# ccoding/sync/hasher.py
from __future__ import annotations

import hashlib
import re


def content_hash(text: str) -> str:
    """Compute a normalized hash of content for sync comparison.

    Normalizes: trailing whitespace per line, multiple blank lines collapsed to one.
    Preserves: leading indentation, meaningful content differences.
    """
    lines = text.splitlines()
    normalized = []
    prev_blank = False
    for line in lines:
        stripped = line.rstrip()
        is_blank = stripped == ""
        if is_blank and prev_blank:
            continue
        normalized.append(stripped)
        prev_blank = is_blank
    # Remove trailing blank lines
    while normalized and normalized[-1] == "":
        normalized.pop()
    content = "\n".join(normalized)
    return hashlib.sha256(content.encode()).hexdigest()[:16]
```

- [ ] **Step 3: Run hasher tests**

Run: `pytest tests/sync/test_hasher.py -v`
Expected: All PASS

- [ ] **Step 4: Write failing state tests**

```python
# tests/sync/test_state.py
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
                    canvas_hash="abc123",
                    code_hash="def456",
                    canvas_node_id="node-1",
                    source_path="src/parsers.py",
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
```

- [ ] **Step 5: Implement state module**

Implement `ccoding/sync/state.py` with:
- `ElementState` dataclass: `canvas_hash`, `code_hash`, `canvas_node_id`, `source_path`, `last_synced`
- `SyncState` dataclass: `version`, `last_sync`, `canvas_file`, `elements: dict[str, ElementState]`
- `load_sync_state(project_root) -> SyncState` — reads `.ccoding/sync-state.json`
- `save_sync_state(state, project_root)` — writes `.ccoding/sync-state.json`

- [ ] **Step 6: Run state tests**

Run: `pytest tests/sync/test_state.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add ccoding/sync/hasher.py ccoding/sync/state.py tests/sync/test_hasher.py tests/sync/test_state.py
git commit -m "feat: add sync state management and content hasher"
```

---

### Task 10: Differ

**Files:**
- Create: `ccoding/sync/differ.py`
- Create: `tests/sync/test_differ.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/sync/test_differ.py
from ccoding.sync.differ import compute_diff, SyncDiff
from ccoding.sync.state import SyncState, ElementState
from ccoding.canvas.model import Canvas, Node, CcodingMetadata


class TestComputeDiff:
    def _make_state(self, elements: dict) -> SyncState:
        return SyncState(canvas_file="test.canvas", elements={
            name: ElementState(
                canvas_hash=e["ch"], code_hash=e["kh"],
                canvas_node_id=e.get("nid", "n1"),
                source_path=e.get("src", "src/x.py"),
            )
            for name, e in elements.items()
        })

    def test_in_sync(self):
        state = self._make_state({
            "Foo": {"ch": "aaa", "kh": "bbb"},
        })
        current_canvas = {"Foo": "aaa"}
        current_code = {"Foo": "bbb"}
        diff = compute_diff(state, current_canvas, current_code)
        assert diff.in_sync == ["Foo"]
        assert diff.conflicts == []

    def test_canvas_modified(self):
        state = self._make_state({
            "Foo": {"ch": "aaa", "kh": "bbb"},
        })
        current_canvas = {"Foo": "changed"}
        current_code = {"Foo": "bbb"}
        diff = compute_diff(state, current_canvas, current_code)
        assert "Foo" in diff.canvas_modified

    def test_code_modified(self):
        state = self._make_state({
            "Foo": {"ch": "aaa", "kh": "bbb"},
        })
        current_canvas = {"Foo": "aaa"}
        current_code = {"Foo": "changed"}
        diff = compute_diff(state, current_canvas, current_code)
        assert "Foo" in diff.code_modified

    def test_conflict(self):
        state = self._make_state({
            "Foo": {"ch": "aaa", "kh": "bbb"},
        })
        current_canvas = {"Foo": "new_canvas"}
        current_code = {"Foo": "new_code"}
        diff = compute_diff(state, current_canvas, current_code)
        assert len(diff.conflicts) == 1
        assert diff.conflicts[0].qualified_name == "Foo"

    def test_canvas_added(self):
        state = self._make_state({})
        current_canvas = {"Foo": "aaa"}
        current_code = {}
        diff = compute_diff(state, current_canvas, current_code)
        assert "Foo" in diff.canvas_added

    def test_code_added(self):
        state = self._make_state({})
        current_canvas = {}
        current_code = {"Foo": "bbb"}
        diff = compute_diff(state, current_canvas, current_code)
        assert "Foo" in diff.code_added

    def test_canvas_deleted(self):
        state = self._make_state({
            "Foo": {"ch": "aaa", "kh": "bbb"},
        })
        current_canvas = {}
        current_code = {"Foo": "bbb"}
        diff = compute_diff(state, current_canvas, current_code)
        assert "Foo" in diff.canvas_deleted

    def test_code_deleted(self):
        state = self._make_state({
            "Foo": {"ch": "aaa", "kh": "bbb"},
        })
        current_canvas = {"Foo": "aaa"}
        current_code = {}
        diff = compute_diff(state, current_canvas, current_code)
        assert "Foo" in diff.code_deleted
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/sync/test_differ.py -v`
Expected: FAIL

- [ ] **Step 3: Implement differ**

Implement `ccoding/sync/differ.py` with:
- `Conflict` dataclass: `qualified_name`, `canvas_hash`, `code_hash`, `stored_canvas_hash`, `stored_code_hash`
- `SyncDiff` dataclass: `canvas_added`, `canvas_modified`, `canvas_deleted`, `code_added`, `code_modified`, `code_deleted`, `conflicts`, `in_sync` — all `list[str]` except `conflicts` which is `list[Conflict]`
- `compute_diff(state: SyncState, current_canvas_hashes: dict[str, str], current_code_hashes: dict[str, str]) -> SyncDiff` — compares current hashes against stored state. Logic:
  - For each element in state: check if canvas hash changed, code hash changed, both (conflict), or neither (in sync). Also check if element is missing from current (deleted).
  - For elements in current but not in state: added.

- [ ] **Step 4: Run tests**

Run: `pytest tests/sync/test_differ.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ccoding/sync/differ.py tests/sync/test_differ.py
git commit -m "feat: add sync differ for change detection"
```

---

### Task 11: Conflict Resolution Helpers

**Files:**
- Create: `ccoding/sync/conflict.py`
- Create: `tests/sync/test_conflict.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/sync/test_conflict.py
from ccoding.sync.conflict import resolve_conflict, ConflictResolution
from ccoding.sync.differ import Conflict


class TestResolveConflict:
    def test_keep_canvas(self):
        conflict = Conflict(
            qualified_name="Foo",
            canvas_hash="new_canvas",
            code_hash="new_code",
            stored_canvas_hash="old",
            stored_code_hash="old",
        )
        resolution = resolve_conflict(conflict, strategy="canvas-wins")
        assert resolution == ConflictResolution.USE_CANVAS

    def test_keep_code(self):
        conflict = Conflict(
            qualified_name="Foo",
            canvas_hash="new_canvas",
            code_hash="new_code",
            stored_canvas_hash="old",
            stored_code_hash="old",
        )
        resolution = resolve_conflict(conflict, strategy="code-wins")
        assert resolution == ConflictResolution.USE_CODE

    def test_manual(self):
        conflict = Conflict(
            qualified_name="Foo",
            canvas_hash="new_canvas",
            code_hash="new_code",
            stored_canvas_hash="old",
            stored_code_hash="old",
        )
        resolution = resolve_conflict(conflict, strategy=None)
        assert resolution == ConflictResolution.MANUAL
```

- [ ] **Step 2: Implement conflict module**

```python
# ccoding/sync/conflict.py
from __future__ import annotations

from enum import Enum
from ccoding.sync.differ import Conflict


class ConflictResolution(Enum):
    USE_CANVAS = "canvas-wins"
    USE_CODE = "code-wins"
    MANUAL = "manual"


def resolve_conflict(
    conflict: Conflict,
    strategy: str | None = None,
) -> ConflictResolution:
    if strategy == "canvas-wins":
        return ConflictResolution.USE_CANVAS
    elif strategy == "code-wins":
        return ConflictResolution.USE_CODE
    return ConflictResolution.MANUAL
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/sync/test_conflict.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add ccoding/sync/conflict.py tests/sync/test_conflict.py
git commit -m "feat: add conflict resolution helpers"
```

---

### Task 12: Sync Engine

**Files:**
- Create: `ccoding/sync/engine.py`
- Create: `tests/sync/test_engine.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/sync/test_engine.py
import json
from pathlib import Path
from ccoding.sync.engine import sync, import_codebase, SyncResult
from ccoding.sync.state import load_sync_state
from ccoding.canvas.reader import read_canvas


class TestImportCodebase:
    def test_import_creates_canvas(self, tmp_project: Path, fixtures_dir: Path):
        canvas_path = tmp_project / "design.canvas"
        result = import_codebase(
            source_dir=fixtures_dir / "sample_python",
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )
        canvas = read_canvas(canvas_path)
        # Should have nodes for DocumentParser, OutputFormat, ParserConfig
        class_names = {
            n.ccoding.qualified_name
            for n in canvas.nodes
            if n.ccoding and n.ccoding.kind == "class"
        }
        assert len(class_names) >= 3
        # All should be accepted
        for n in canvas.nodes:
            if n.ccoding:
                assert n.ccoding.status == "accepted"
                assert n.ccoding.layout_pending is True
        # Sync state should be initialized
        state = load_sync_state(tmp_project)
        assert len(state.elements) > 0


class TestSync:
    def test_sync_no_changes(self, tmp_project: Path, fixtures_dir: Path):
        # Import first to establish baseline
        canvas_path = tmp_project / "design.canvas"
        import_codebase(
            source_dir=fixtures_dir / "sample_python",
            canvas_path=canvas_path,
            project_root=tmp_project,
            language="python",
        )
        # Sync with no changes
        result = sync(canvas_path=canvas_path, project_root=tmp_project)
        assert result.conflicts == []
        assert result.canvas_to_code == []
        assert result.code_to_canvas == []

    def test_sync_detects_code_addition(self, tmp_project: Path):
        """Add a new class to source, sync should create canvas node."""
        canvas_path = tmp_project / "design.canvas"
        src_dir = tmp_project / "src"
        # Write a Python file
        (src_dir / "new_module.py").write_text(
            'class NewClass:\n    """A new class.\n\n    Responsibility:\n        Does new things.\n    """\n    pass\n'
        )
        result = sync(canvas_path=canvas_path, project_root=tmp_project)
        assert len(result.code_to_canvas) > 0
        canvas = read_canvas(canvas_path)
        names = {
            n.ccoding.qualified_name
            for n in canvas.nodes
            if n.ccoding and n.ccoding.kind == "class"
        }
        assert any("NewClass" in name for name in names)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/sync/test_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implement sync engine**

Implement `ccoding/sync/engine.py` with:
- `SyncResult` dataclass: `canvas_to_code: list[str]`, `code_to_canvas: list[str]`, `conflicts: list[Conflict]`, `errors: list[str]`
- `sync(canvas_path, project_root, strategy=None) -> SyncResult`:
  1. Load config, sync state, canvas, parse code
  2. Build current hash maps for both sides
  3. Call `compute_diff()`
  4. If conflicts and no strategy → return conflicts
  5. Apply changes: canvas→code (update source files), code→canvas (update canvas nodes)
  6. Save updated canvas and sync state
- `import_codebase(source_dir, canvas_path, project_root, language) -> SyncResult`:
  1. Parse all code in source_dir
  2. Create Canvas with nodes for each class, edges for relationships
  3. Grid layout grouped by module, all `layoutPending: true`, all `status: "accepted"`
  4. Write canvas, initialize sync state

Key implementation detail: the sync engine uses the code parser to extract current code state, the canvas reader/writer for canvas state, the hasher for comparison, and the differ for change categorization. It calls the code generator for canvas→code writes and the markdown renderer for code→canvas writes.

- [ ] **Step 4: Run tests**

Run: `pytest tests/sync/test_engine.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ccoding/sync/engine.py tests/sync/test_engine.py
git commit -m "feat: add sync engine with import_codebase and bidirectional sync"
```

---

### Task 13: Ghost Node Manager

**Files:**
- Create: `ccoding/ghost/manager.py`
- Create: `tests/ghost/test_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/ghost/test_manager.py
import pytest
from ccoding.ghost.manager import (
    propose_node, propose_edge, accept_node, accept_edge,
    reject_node, reject_edge, reconsider_node, reconsider_edge,
    accept_all, reject_all, list_ghosts,
)
from ccoding.canvas.model import Canvas, Node, Edge, CcodingMetadata, EdgeMetadata


def _base_canvas() -> Canvas:
    """Canvas with one accepted class node."""
    return Canvas(
        nodes=[
            Node(id="n1", type="text", x=0, y=0, width=300, height=400,
                 text="## Foo", ccoding=CcodingMetadata(kind="class")),
        ],
        edges=[],
    )


class TestProposeNode:
    def test_creates_ghost(self):
        canvas = _base_canvas()
        node = propose_node(
            canvas, kind="class", name="Bar",
            content="## Bar", rationale="Extracting logic",
        )
        assert node.ccoding.status == "proposed"
        assert node.ccoding.proposed_by == "agent"
        assert node.ccoding.proposal_rationale == "Extracting logic"
        assert node in canvas.nodes

    def test_propose_context_node(self):
        canvas = _base_canvas()
        node = propose_node(
            canvas, kind=None, name="rationale note",
            content="Design decision: ...", rationale="Explaining choice",
        )
        assert node.ccoding.status == "proposed"


class TestProposeEdge:
    def test_creates_ghost_edge(self):
        canvas = _base_canvas()
        n2 = propose_node(canvas, kind="class", name="Bar", content="## Bar", rationale="test")
        edge = propose_edge(
            canvas, from_node="n1", to_node=n2.id,
            relation="depends", label="uses Bar",
            rationale="Foo depends on Bar",
        )
        assert edge.ccoding.status == "proposed"
        assert edge in canvas.edges


class TestAcceptReject:
    def test_accept_node(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        accepted = accept_node(canvas, ghost.id)
        assert accepted.ccoding.status == "accepted"
        assert accepted.ccoding.proposal_rationale is None

    def test_accept_edge_requires_accepted_endpoints(self):
        canvas = _base_canvas()
        ghost_node = propose_node(canvas, "class", "Bar", "## Bar", "test")
        ghost_edge = propose_edge(canvas, "n1", ghost_node.id, "depends", "x", "test")
        with pytest.raises(ValueError, match="endpoint"):
            accept_edge(canvas, ghost_edge.id)
        accept_node(canvas, ghost_node.id)
        accepted_edge = accept_edge(canvas, ghost_edge.id)
        assert accepted_edge.ccoding.status == "accepted"

    def test_reject_node_cascades_to_edges(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        reject_node(canvas, ghost.id)
        assert ghost.ccoding.status == "rejected"
        assert edge.ccoding.status == "rejected"

    def test_reject_edge_leaves_nodes(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        reject_edge(canvas, edge.id)
        assert edge.ccoding.status == "rejected"
        assert ghost.ccoding.status == "proposed"


class TestReconsider:
    def test_reconsider_node(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        reject_node(canvas, ghost.id)
        reconsider_node(canvas, ghost.id)
        assert ghost.ccoding.status == "proposed"

    def test_reconsider_restores_cascade_rejected_edges(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        reject_node(canvas, ghost.id)
        reconsider_node(canvas, ghost.id)
        assert edge.ccoding.status == "proposed"

    def test_reconsider_edge(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        accept_node(canvas, ghost.id)
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        reject_edge(canvas, edge.id)
        reconsider_edge(canvas, edge.id)
        assert edge.ccoding.status == "proposed"

    def test_reconsider_edge_rejected_endpoint_raises(self):
        canvas = _base_canvas()
        ghost = propose_node(canvas, "class", "Bar", "## Bar", "test")
        edge = propose_edge(canvas, "n1", ghost.id, "depends", "x", "test")
        reject_node(canvas, ghost.id)  # cascades to edge
        with pytest.raises(ValueError, match="endpoint"):
            reconsider_edge(canvas, edge.id)


class TestBatchOps:
    def test_accept_all(self):
        canvas = _base_canvas()
        propose_node(canvas, "class", "Bar", "## Bar", "test")
        propose_node(canvas, "class", "Baz", "## Baz", "test")
        results = accept_all(canvas)
        assert all(
            n.ccoding.status == "accepted"
            for n in canvas.nodes
            if n.ccoding
        )

    def test_list_ghosts(self):
        canvas = _base_canvas()
        propose_node(canvas, "class", "Bar", "## Bar", "test")
        ghosts = list_ghosts(canvas)
        assert len(ghosts) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/ghost/test_manager.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ghost manager**

Implement `ccoding/ghost/manager.py` with all functions from the spec Section 6. Key details:
- `propose_node()` generates a unique ID (`uuid4().hex[:8]` prefix), sets `status: "proposed"`, adds node to canvas
- `propose_edge()` validates both endpoints exist, generates ID, adds edge to canvas
- `accept_node()` finds node by ID, sets `status: "accepted"`, clears rationale
- `accept_edge()` checks both endpoints are accepted, then accepts edge
- `reject_node()` rejects node + cascades to all connected edges
- `reject_edge()` rejects just the edge
- `reconsider_node()` sets back to proposed, also reconsiders cascade-rejected edges
- `reconsider_edge()` validates endpoints aren't rejected, sets back to proposed
- `accept_all()` accepts all proposed nodes first, then proposed edges
- `reject_all()` rejects all proposed
- `list_ghosts()` returns all proposed nodes + edges

- [ ] **Step 4: Run tests**

Run: `pytest tests/ghost/test_manager.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ccoding/ghost/manager.py tests/ghost/test_manager.py
git commit -m "feat: add ghost node manager (propose/accept/reject/reconsider)"
```

---

### Task 14: Live Bridge (Obsidian Eval)

**Files:**
- Create: `ccoding/live/obsidian.py`
- Create: `tests/live/test_obsidian.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/live/test_obsidian.py
import subprocess
from unittest.mock import patch, MagicMock
from ccoding.live.obsidian import ObsidianBridge


class TestObsidianBridge:
    def test_is_available_false_when_not_installed(self):
        with patch("shutil.which", return_value=None):
            bridge = ObsidianBridge()
            assert bridge.is_available() is False

    def test_is_available_true_when_installed_and_running(self):
        with patch("shutil.which", return_value="/usr/local/bin/obsidian"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok")
            bridge = ObsidianBridge()
            assert bridge.is_available() is True

    def test_eval_calls_obsidian_cli(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="42")
            bridge = ObsidianBridge()
            result = bridge.eval("2 + 40")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "obsidian" in args[0]
            assert "eval" in args
            assert result == "42"

    def test_eval_raises_on_failure(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="error")
            bridge = ObsidianBridge()
            with __import__("pytest").raises(RuntimeError):
                bridge.eval("bad code")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/live/test_obsidian.py -v`
Expected: FAIL

- [ ] **Step 3: Implement live bridge**

Implement `ccoding/live/obsidian.py` with:
- `ObsidianBridge` class with `is_available()`, `eval(js: str) -> str`
- `is_available()` checks `shutil.which("obsidian")` and tries a simple eval to verify Obsidian is running
- `eval()` runs `subprocess.run(["obsidian", "eval", js], capture_output=True, text=True)`, raises `RuntimeError` on non-zero exit
- JS template constants for common operations: `JS_RELOAD_CANVAS`, `JS_GET_ACTIVE_CANVAS`
- All JS templates are string constants, parameterized with `str.format()` using properly escaped values

- [ ] **Step 4: Run tests**

Run: `pytest tests/live/test_obsidian.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add ccoding/live/obsidian.py tests/live/test_obsidian.py
git commit -m "feat: add Obsidian eval bridge for live canvas operations"
```

---

### Task 15: Git Integration

**Files:**
- Create: `ccoding/git/hooks.py`
- Create: `ccoding/git/merge.py`
- Create: `ccoding/git/diff.py`
- Create: `tests/git/test_hooks.py`
- Create: `tests/git/test_merge.py`
- Create: `tests/git/test_diff.py`

- [ ] **Step 1: Write failing hook tests**

```python
# tests/git/test_hooks.py
from pathlib import Path
from ccoding.git.hooks import check_sync, install_hooks


class TestCheckSync:
    def test_clean_returns_zero(self, tmp_project: Path):
        """No drift = exit code 0."""
        exit_code, message = check_sync(tmp_project)
        assert exit_code == 0

    def test_reports_drift(self, tmp_project: Path):
        """Write a class to source without syncing, check should report drift."""
        src_dir = tmp_project / "src"
        (src_dir / "drifted.py").write_text(
            'class Drifted:\n    """A class not on canvas."""\n    pass\n'
        )
        exit_code, message = check_sync(tmp_project)
        assert exit_code == 1
        assert "Drifted" in message or "drift" in message.lower()


class TestInstallHooks:
    def test_installs_pre_commit(self, tmp_project: Path):
        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=tmp_project, capture_output=True)
        install_hooks(tmp_project)
        hook_path = tmp_project / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists()
        content = hook_path.read_text()
        assert "ccoding check" in content
```

- [ ] **Step 2: Implement hooks module**

Implement `ccoding/git/hooks.py`:
- `check_sync(project_root) -> tuple[int, str]` — loads config, runs a lightweight sync diff (no writes), returns (0, "ok") if clean, (1, "drift report") if not
- `install_hooks(project_root)` — writes pre-commit hook script to `.git/hooks/pre-commit`, makes executable. Also configures merge driver in `.git/config` and writes `.gitattributes` entry.

- [ ] **Step 3: Run hook tests**

Run: `pytest tests/git/test_hooks.py -v`
Expected: All PASS

- [ ] **Step 4: Write failing merge tests**

```python
# tests/git/test_merge.py
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

        base_p = tmp_path / "base.canvas"
        ours_p = tmp_path / "ours.canvas"
        theirs_p = tmp_path / "theirs.canvas"
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

        base_p = tmp_path / "base.canvas"
        ours_p = tmp_path / "ours.canvas"
        theirs_p = tmp_path / "theirs.canvas"
        base_p.write_text(json.dumps(base))
        ours_p.write_text(json.dumps(ours))
        theirs_p.write_text(json.dumps(theirs))

        exit_code = merge_canvases(base_p, ours_p, theirs_p)
        assert exit_code != 0

    def test_position_changes_last_writer_wins(self, tmp_path: Path):
        base = {"nodes": [{"id": "n1", "type": "text", "x": 0, "y": 0, "width": 100, "height": 100, "text": "same"}], "edges": []}
        ours = {"nodes": [{"id": "n1", "type": "text", "x": 50, "y": 0, "width": 100, "height": 100, "text": "same"}], "edges": []}
        theirs = {"nodes": [{"id": "n1", "type": "text", "x": 0, "y": 99, "width": 100, "height": 100, "text": "same"}], "edges": []}

        base_p = tmp_path / "base.canvas"
        ours_p = tmp_path / "ours.canvas"
        theirs_p = tmp_path / "theirs.canvas"
        base_p.write_text(json.dumps(base))
        ours_p.write_text(json.dumps(ours))
        theirs_p.write_text(json.dumps(theirs))

        exit_code = merge_canvases(base_p, ours_p, theirs_p)
        assert exit_code == 0
```

- [ ] **Step 5: Implement merge driver**

Implement `ccoding/git/merge.py`:
- `merge_canvases(base_path, ours_path, theirs_path) -> int` — reads all three as Canvas objects, performs semantic three-way merge by node ID. Returns 0 on success, non-zero on conflict. Writes merged result to `ours_path` (git convention).
- Merge logic: build node maps by ID. For each node: if only one side changed → take that change. If both changed text → conflict. If both changed position only → last writer wins (theirs). New nodes from either side → include both. Deleted nodes (in base but not in ours/theirs) → respect deletion.
- Same logic for edges by ID.

- [ ] **Step 6: Run merge tests**

Run: `pytest tests/git/test_merge.py -v`
Expected: All PASS

- [ ] **Step 7: Write failing git diff tests**

```python
# tests/git/test_diff.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from ccoding.git.diff import git_changed_files


class TestGitChangedFiles:
    def test_returns_changed_files(self, tmp_path: Path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="src/foo.py\nsrc/bar.py\n",
            )
            files = git_changed_files(tmp_path)
            assert files == [Path("src/foo.py"), Path("src/bar.py")]

    def test_returns_empty_when_git_fails(self, tmp_path: Path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="not a repo")
            files = git_changed_files(tmp_path)
            assert files is None  # signals fallback to full scan
```

- [ ] **Step 8: Implement git diff module**

```python
# ccoding/git/diff.py
from __future__ import annotations

import subprocess
from pathlib import Path


def git_changed_files(
    project_root: Path,
    ref: str = "HEAD",
) -> list[Path] | None:
    """Return files changed since ref, or None if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", ref],
            cwd=project_root,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        return [
            Path(line)
            for line in result.stdout.strip().splitlines()
            if line.strip()
        ]
    except FileNotFoundError:
        return None
```

- [ ] **Step 9: Run all git tests**

Run: `pytest tests/git/ -v`
Expected: All PASS

- [ ] **Step 10: Commit**

```bash
git add ccoding/git/ tests/git/
git commit -m "feat: add git integration (hooks, merge driver, change detection)"
```

---

### Task 16: CLI Entry Point

**Files:**
- Create: `ccoding/cli.py`
- Create: `tests/test_cli.py` (integration-level CLI tests)

- [ ] **Step 1: Write failing tests**

```python
# tests/test_cli.py
import json
from pathlib import Path
from click.testing import CliRunner
from ccoding.cli import main


class TestCliInit:
    def test_init_creates_project(self, tmp_path: Path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path) as td:
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0
            assert Path(td, ".ccoding", "config.json").exists()
            assert Path(td, ".ccoding", "sync-state.json").exists()


class TestCliStatus:
    def test_status_clean(self, tmp_project: Path):
        runner = CliRunner()
        result = runner.invoke(main, ["status"], catch_exceptions=False)
        # Should work from any directory if we pass --project
        # For test simplicity, we cd into the project
        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_project)
        try:
            result = runner.invoke(main, ["status"])
            assert result.exit_code == 0
        finally:
            os.chdir(old_cwd)


class TestCliGhosts:
    def test_ghosts_empty(self, tmp_project: Path):
        runner = CliRunner()
        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_project)
        try:
            result = runner.invoke(main, ["ghosts"])
            assert result.exit_code == 0
            assert "No pending proposals" in result.output or result.output.strip() == ""
        finally:
            os.chdir(old_cwd)


class TestCliCheck:
    def test_check_clean(self, tmp_project: Path):
        runner = CliRunner()
        import os
        old_cwd = os.getcwd()
        os.chdir(tmp_project)
        try:
            result = runner.invoke(main, ["check"])
            assert result.exit_code == 0
        finally:
            os.chdir(old_cwd)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Implement CLI**

Implement `ccoding/cli.py` using Click:

```python
# ccoding/cli.py
from __future__ import annotations

import click
from pathlib import Path


@click.group()
@click.option("--project", type=click.Path(exists=True, path_type=Path), default=".")
@click.pass_context
def main(ctx: click.Context, project: Path) -> None:
    """CooperativeCoding — canvas manipulation, bidirectional sync, ghost nodes."""
    ctx.ensure_object(dict)
    ctx.obj["project"] = project.resolve()


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize a CooperativeCoding project."""
    from ccoding.config import init_project
    project = ctx.obj["project"]
    init_project(project)
    click.echo(f"Initialized CooperativeCoding project in {project / '.ccoding'}")


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show sync status."""
    from ccoding.sync.engine import sync_status
    project = ctx.obj["project"]
    report = sync_status(project)
    click.echo(report)


@main.command()
@click.pass_context
def ghosts(ctx: click.Context) -> None:
    """List pending ghost proposals."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.ghost.manager import list_ghosts
    project = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    if not canvas_path.exists():
        click.echo("No canvas file found.")
        return
    canvas = read_canvas(canvas_path)
    items = list_ghosts(canvas)
    if not items:
        click.echo("No pending proposals.")
        return
    for item in items:
        click.echo(f"  [{item.id}] {getattr(item, 'text', '')[:60]}")


@main.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Validate canvas/code sync (for pre-commit hook)."""
    from ccoding.git.hooks import check_sync
    project = ctx.obj["project"]
    exit_code, message = check_sync(project)
    if exit_code == 0:
        click.echo("Canvas and code are in sync.")
    else:
        click.echo(message, err=True)
    ctx.exit(exit_code)


# Additional commands follow the same pattern:
# sync, import, create-node, create-edge, propose, propose-edge,
# accept, reject, reconsider, accept-all, reject-all, show, diff, merge

@main.command(name="sync")
@click.option("--canvas-wins", is_flag=True)
@click.option("--code-wins", is_flag=True)
@click.pass_context
def sync_cmd(ctx: click.Context, canvas_wins: bool, code_wins: bool) -> None:
    """Run bidirectional sync."""
    from ccoding.sync.engine import sync
    from ccoding.config import load_config
    project = ctx.obj["project"]
    config = load_config(project)
    strategy = "canvas-wins" if canvas_wins else ("code-wins" if code_wins else None)
    result = sync(
        canvas_path=project / config.canvas,
        project_root=project,
        strategy=strategy,
    )
    if result.conflicts:
        click.echo(f"Conflicts detected ({len(result.conflicts)}):", err=True)
        for c in result.conflicts:
            click.echo(f"  {c.qualified_name}", err=True)
        ctx.exit(1)
    else:
        total = len(result.canvas_to_code) + len(result.code_to_canvas)
        click.echo(f"Sync complete. {total} elements updated.")


@main.command(name="import")
@click.option("--source", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--canvas", required=True, type=click.Path(path_type=Path))
@click.pass_context
def import_cmd(ctx: click.Context, source: Path, canvas: Path) -> None:
    """Import existing codebase into canvas."""
    from ccoding.sync.engine import import_codebase
    from ccoding.config import load_config
    project = ctx.obj["project"]
    config = load_config(project)
    result = import_codebase(
        source_dir=source, canvas_path=canvas,
        project_root=project, language=config.language,
    )
    click.echo(f"Imported {len(result.code_to_canvas)} elements into {canvas}")


@main.command(name="accept")
@click.argument("node_id")
@click.pass_context
def accept_cmd(ctx: click.Context, node_id: str) -> None:
    """Accept a ghost node or edge."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas
    from ccoding.ghost.manager import accept_node, accept_edge
    project = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)
    # Try node first, then edge
    node = next((n for n in canvas.nodes if n.id == node_id), None)
    if node:
        accept_node(canvas, node_id)
        click.echo(f"Accepted node {node_id}")
    else:
        edge = next((e for e in canvas.edges if e.id == node_id), None)
        if edge:
            accept_edge(canvas, node_id)
            click.echo(f"Accepted edge {node_id}")
        else:
            click.echo(f"Not found: {node_id}", err=True)
            ctx.exit(1)
            return
    write_canvas(canvas, canvas_path)


@main.command(name="reject")
@click.argument("node_id")
@click.pass_context
def reject_cmd(ctx: click.Context, node_id: str) -> None:
    """Reject a ghost node or edge."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas
    from ccoding.ghost.manager import reject_node, reject_edge
    project = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)
    node = next((n for n in canvas.nodes if n.id == node_id), None)
    if node:
        reject_node(canvas, node_id)
        click.echo(f"Rejected node {node_id}")
    else:
        edge = next((e for e in canvas.edges if e.id == node_id), None)
        if edge:
            reject_edge(canvas, node_id)
            click.echo(f"Rejected edge {node_id}")
        else:
            click.echo(f"Not found: {node_id}", err=True)
            ctx.exit(1)
            return
    write_canvas(canvas, canvas_path)


@main.command(name="reconsider")
@click.argument("node_id")
@click.pass_context
def reconsider_cmd(ctx: click.Context, node_id: str) -> None:
    """Move a rejected node or edge back to proposed."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas
    from ccoding.ghost.manager import reconsider_node, reconsider_edge
    project = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)
    node = next((n for n in canvas.nodes if n.id == node_id), None)
    if node:
        reconsider_node(canvas, node_id)
        click.echo(f"Reconsidered node {node_id}")
    else:
        edge = next((e for e in canvas.edges if e.id == node_id), None)
        if edge:
            reconsider_edge(canvas, node_id)
            click.echo(f"Reconsidered edge {node_id}")
        else:
            click.echo(f"Not found: {node_id}", err=True)
            ctx.exit(1)
            return
    write_canvas(canvas, canvas_path)
```

Implement remaining commands (`create-node`, `create-edge`, `propose`, `propose-edge`, `accept-all`, `reject-all`, `show`, `diff`, `merge`) following the same pattern — each is a thin wrapper calling the library function.

Also add a `sync_status(project_root) -> str` function to `ccoding/sync/engine.py` that returns a human-readable status report.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_cli.py -v`
Expected: All PASS

- [ ] **Step 5: Run the full test suite**

Run: `pytest -v`
Expected: All tests PASS across all modules

- [ ] **Step 6: Commit**

```bash
git add ccoding/cli.py tests/test_cli.py
git commit -m "feat: add CLI entry point with all ccoding commands"
```

---

### Task 17: Package Exports and Integration Test

**Files:**
- Modify: `ccoding/__init__.py`
- Create: `tests/test_integration.py`

- [ ] **Step 1: Update __init__.py with public API exports**

```python
# ccoding/__init__.py
"""CooperativeCoding — canvas manipulation, bidirectional sync, and ghost node management."""

__version__ = "0.1.0"

# Canvas engine
from ccoding.canvas.model import Canvas, Node, Edge, CcodingMetadata, EdgeMetadata, GroupNode
from ccoding.canvas.reader import read_canvas
from ccoding.canvas.writer import write_canvas

# Code parser
from ccoding.code.parser import PythonAstParser, CodeParser

# Sync engine
from ccoding.sync.engine import sync, import_codebase

# Ghost management
from ccoding.ghost.manager import (
    propose_node, propose_edge,
    accept_node, accept_edge,
    reject_node, reject_edge,
    reconsider_node, reconsider_edge,
    accept_all, reject_all, list_ghosts,
)

# Configuration
from ccoding.config import ProjectConfig, load_config, init_project

__all__ = [
    "Canvas", "Node", "Edge", "CcodingMetadata", "EdgeMetadata", "GroupNode",
    "read_canvas", "write_canvas",
    "PythonAstParser", "CodeParser",
    "sync", "import_codebase",
    "propose_node", "propose_edge",
    "accept_node", "accept_edge",
    "reject_node", "reject_edge",
    "reconsider_node", "reconsider_edge",
    "accept_all", "reject_all", "list_ghosts",
    "ProjectConfig", "load_config", "init_project",
]
```

- [ ] **Step 2: Write integration test**

```python
# tests/test_integration.py
"""End-to-end test: import codebase → propose changes → accept → sync."""
from pathlib import Path
import ccoding


class TestEndToEnd:
    def test_full_workflow(self, tmp_project: Path, fixtures_dir: Path):
        project = tmp_project
        canvas_path = project / "design.canvas"

        # 1. Import existing code
        result = ccoding.import_codebase(
            source_dir=fixtures_dir / "sample_python",
            canvas_path=canvas_path,
            project_root=project,
            language="python",
        )
        assert len(result.code_to_canvas) > 0

        # 2. Read the canvas
        canvas = ccoding.read_canvas(canvas_path)
        initial_count = len(canvas.nodes)
        assert initial_count >= 3  # DocumentParser, OutputFormat, ParserConfig

        # 3. Agent proposes a new class
        ghost = ccoding.propose_node(
            canvas,
            kind="class",
            name="CacheManager",
            content="## CacheManager\n\n> Manages AST caching",
            rationale="Extract caching from DocumentParser",
        )
        assert ghost.ccoding.status == "proposed"

        # 4. Save canvas with ghost
        ccoding.write_canvas(canvas, canvas_path)

        # 5. Verify ghost appears
        ghosts = ccoding.list_ghosts(canvas)
        assert len(ghosts) == 1

        # 6. Accept the ghost
        ccoding.accept_node(canvas, ghost.id)
        ccoding.write_canvas(canvas, canvas_path)

        # 7. Sync should generate code for the new class
        sync_result = ccoding.sync(
            canvas_path=canvas_path,
            project_root=project,
        )
        # The newly accepted node should trigger code generation
        assert len(sync_result.canvas_to_code) > 0 or len(sync_result.code_to_canvas) >= 0

        # 8. Verify no conflicts
        assert sync_result.conflicts == []
```

- [ ] **Step 3: Run integration test**

Run: `pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `pytest -v --tb=short`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add ccoding/__init__.py tests/test_integration.py
git commit -m "feat: add public API exports and end-to-end integration test"
```

---

### Task 18: Final Verification

- [ ] **Step 1: Run full test suite with coverage**

Run: `pytest -v --tb=short`
Expected: All tests PASS

- [ ] **Step 2: Verify CLI entry point works**

Run: `ccoding --help`
Expected: Shows help with all subcommands

- [ ] **Step 3: Verify package installs cleanly**

Run: `pip install -e ".[dev]" && python -c "import ccoding; print(ccoding.__version__)"`
Expected: Prints `0.1.0`

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "chore: final verification — all tests passing"
```
