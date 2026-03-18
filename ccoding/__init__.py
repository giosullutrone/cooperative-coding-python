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
from ccoding.sync.engine import sync, import_codebase, sync_status

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
    "sync", "import_codebase", "sync_status",
    "propose_node", "propose_edge",
    "accept_node", "accept_edge",
    "reject_node", "reject_edge",
    "reconsider_node", "reconsider_edge",
    "accept_all", "reject_all", "list_ghosts",
    "ProjectConfig", "load_config", "init_project",
]
