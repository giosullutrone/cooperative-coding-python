"""CooperativeCoding CLI — user-facing entry point for all ccoding commands."""
from __future__ import annotations

import sys
import click
from pathlib import Path

from ccoding import __version__


@click.group()
@click.version_option(version=__version__)
@click.option("--project", type=click.Path(exists=True, path_type=Path), default=".")
@click.pass_context
def main(ctx: click.Context, project: Path) -> None:
    """CooperativeCoding — canvas manipulation, bidirectional sync, ghost nodes."""
    ctx.ensure_object(dict)
    ctx.obj["project"] = project.resolve()


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialise a new ccoding project in the current directory."""
    from ccoding.config import init_project

    project: Path = ctx.obj["project"]
    init_project(project)
    click.echo(f"Initialised ccoding project in {project}")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------


@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show the sync status between canvas and code."""
    from ccoding.sync.engine import sync_status

    project: Path = ctx.obj["project"]
    report = sync_status(project)
    click.echo(report)


# ---------------------------------------------------------------------------
# ghosts
# ---------------------------------------------------------------------------


@main.command()
@click.pass_context
def ghosts(ctx: click.Context) -> None:
    """List all ghost (proposed) nodes and edges in the canvas."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.ghost.manager import list_ghosts
    from ccoding.canvas.model import Node

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas

    if not canvas_path.exists():
        click.echo("No pending proposals")
        return

    canvas = read_canvas(canvas_path)
    pending = list_ghosts(canvas)

    if not pending:
        click.echo("No pending proposals")
        return

    for item in pending:
        if isinstance(item, Node):
            name = (item.ccoding.qualified_name if item.ccoding and item.ccoding.qualified_name
                    else item.id)
            rationale = item.ccoding.proposal_rationale if item.ccoding else ""
            click.echo(f"[node] {item.id}  {name}  rationale={rationale!r}")
        else:
            label = item.label or ""
            rationale = item.ccoding.proposal_rationale if item.ccoding else ""
            click.echo(f"[edge] {item.id}  {item.from_node} -> {item.to_node}  "
                       f"label={label!r}  rationale={rationale!r}")


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


@main.command()
@click.pass_context
def check(ctx: click.Context) -> None:
    """Check whether canvas and code are in sync (used by git pre-commit hook)."""
    from ccoding.git.hooks import check_sync

    project: Path = ctx.obj["project"]
    exit_code, report = check_sync(project)
    click.echo(report)
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------


@main.command(name="sync")
@click.option("--canvas-wins", is_flag=True, default=False,
              help="Resolve conflicts by preferring canvas version.")
@click.option("--code-wins", is_flag=True, default=False,
              help="Resolve conflicts by preferring code version.")
@click.pass_context
def sync_cmd(ctx: click.Context, canvas_wins: bool, code_wins: bool) -> None:
    """Perform bidirectional sync between canvas and code."""
    from ccoding.config import load_config
    from ccoding.sync.engine import sync

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas

    strategy: str | None = None
    if canvas_wins:
        strategy = "canvas"
    elif code_wins:
        strategy = "code"

    result = sync(canvas_path, project, strategy=strategy)

    if result.conflicts and not strategy:
        click.echo("Conflicts detected (use --canvas-wins or --code-wins to resolve):")
        for c in result.conflicts:
            click.echo(f"  conflict: {c.qualified_name}")
        sys.exit(1)

    if result.canvas_to_code:
        click.echo("Canvas → Code:")
        for name in result.canvas_to_code:
            click.echo(f"  {name}")

    if result.code_to_canvas:
        click.echo("Code → Canvas:")
        for name in result.code_to_canvas:
            click.echo(f"  {name}")

    if not result.canvas_to_code and not result.code_to_canvas and not result.conflicts:
        click.echo("Everything is already in sync.")


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------


@main.command(name="import")
@click.option("--source", type=click.Path(path_type=Path), required=True,
              help="Source directory to import from.")
@click.option("--canvas", type=click.Path(path_type=Path), required=True,
              help="Canvas file to write.")
@click.pass_context
def import_cmd(ctx: click.Context, source: Path, canvas: Path) -> None:
    """Import an existing codebase into a canvas file."""
    from ccoding.sync.engine import import_codebase

    project: Path = ctx.obj["project"]

    # Resolve relative paths against project root
    source_abs = source if source.is_absolute() else project / source
    canvas_abs = canvas if canvas.is_absolute() else project / canvas

    result = import_codebase(source_abs, canvas_abs, project)

    if result.code_to_canvas:
        click.echo(f"Imported {len(result.code_to_canvas)} class(es) into {canvas_abs}")
        for name in result.code_to_canvas:
            click.echo(f"  {name}")
    else:
        click.echo("No classes found to import.")

    if result.errors:
        for err in result.errors:
            click.echo(f"  error: {err}", err=True)


# ---------------------------------------------------------------------------
# accept
# ---------------------------------------------------------------------------


@main.command()
@click.argument("node_id")
@click.pass_context
def accept(ctx: click.Context, node_id: str) -> None:
    """Accept a proposed ghost node or edge by ID."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas
    from ccoding.ghost.manager import accept_node, accept_edge

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)

    try:
        item = accept_node(canvas, node_id)
        click.echo(f"Accepted node {item.id}")
    except ValueError:
        try:
            item = accept_edge(canvas, node_id)
            click.echo(f"Accepted edge {item.id}")
        except ValueError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    write_canvas(canvas, canvas_path)


# ---------------------------------------------------------------------------
# reject
# ---------------------------------------------------------------------------


@main.command()
@click.argument("node_id")
@click.pass_context
def reject(ctx: click.Context, node_id: str) -> None:
    """Reject a proposed ghost node or edge by ID."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas
    from ccoding.ghost.manager import reject_node, reject_edge

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)

    try:
        item = reject_node(canvas, node_id)
        click.echo(f"Rejected node {item.id}")
    except ValueError:
        try:
            item = reject_edge(canvas, node_id)
            click.echo(f"Rejected edge {item.id}")
        except ValueError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    write_canvas(canvas, canvas_path)


# ---------------------------------------------------------------------------
# reconsider
# ---------------------------------------------------------------------------


@main.command()
@click.argument("node_id")
@click.pass_context
def reconsider(ctx: click.Context, node_id: str) -> None:
    """Restore a rejected ghost node or edge to proposed status."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas
    from ccoding.ghost.manager import reconsider_node, reconsider_edge

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)

    try:
        item = reconsider_node(canvas, node_id)
        click.echo(f"Reconsidered node {item.id}")
    except ValueError:
        try:
            item = reconsider_edge(canvas, node_id)
            click.echo(f"Reconsidered edge {item.id}")
        except ValueError as exc:
            click.echo(f"Error: {exc}", err=True)
            sys.exit(1)

    write_canvas(canvas, canvas_path)


# ---------------------------------------------------------------------------
# accept-all
# ---------------------------------------------------------------------------


@main.command(name="accept-all")
@click.pass_context
def accept_all_cmd(ctx: click.Context) -> None:
    """Accept all pending ghost proposals in the canvas."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas
    from ccoding.ghost.manager import accept_all

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)

    accepted = accept_all(canvas)
    write_canvas(canvas, canvas_path)

    if accepted:
        click.echo(f"Accepted {len(accepted)} item(s).")
    else:
        click.echo("No pending proposals to accept.")


# ---------------------------------------------------------------------------
# reject-all
# ---------------------------------------------------------------------------


@main.command(name="reject-all")
@click.pass_context
def reject_all_cmd(ctx: click.Context) -> None:
    """Reject all pending ghost proposals in the canvas."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas
    from ccoding.ghost.manager import reject_all

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)

    rejected = reject_all(canvas)
    write_canvas(canvas, canvas_path)

    if rejected:
        click.echo(f"Rejected {len(rejected)} item(s).")
    else:
        click.echo("No pending proposals to reject.")


# ---------------------------------------------------------------------------
# propose
# ---------------------------------------------------------------------------


@main.command()
@click.option("--kind", default="class", help="Node kind (e.g. class, interface).")
@click.option("--name", required=True, help="Class/component name.")
@click.option("--stereotype", default=None,
              help="Stereotype (protocol, abstract, dataclass, enum).")
@click.option("--rationale", default="", help="Rationale for the proposal.")
@click.pass_context
def propose(ctx: click.Context, kind: str, name: str, stereotype: str | None, rationale: str) -> None:
    """Propose a new ghost node in the canvas."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas
    from ccoding.ghost.manager import propose_node

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas

    if canvas_path.exists():
        canvas = read_canvas(canvas_path)
    else:
        from ccoding.canvas.model import Canvas
        canvas = Canvas()

    node = propose_node(canvas, kind=kind, name=name, content=name,
                        rationale=rationale, stereotype=stereotype)
    write_canvas(canvas, canvas_path)
    click.echo(f"Proposed node {node.id}  name={name!r}  kind={kind!r}")


# ---------------------------------------------------------------------------
# propose-edge
# ---------------------------------------------------------------------------


@main.command(name="propose-edge")
@click.option("--from", "from_node", required=True, help="Source node ID.")
@click.option("--to", "to_node", required=True, help="Target node ID.")
@click.option("--relation", default="depends", help="Relation type (e.g. inherits, depends).")
@click.option("--label", default="", help="Edge label.")
@click.option("--rationale", default="", help="Rationale for the proposal.")
@click.pass_context
def propose_edge_cmd(
    ctx: click.Context,
    from_node: str,
    to_node: str,
    relation: str,
    label: str,
    rationale: str,
) -> None:
    """Propose a new ghost edge between two nodes in the canvas."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas
    from ccoding.ghost.manager import propose_edge

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)

    try:
        edge = propose_edge(canvas, from_node, to_node, relation, label, rationale)
        write_canvas(canvas, canvas_path)
        click.echo(f"Proposed edge {edge.id}  {from_node} -> {to_node}  relation={relation!r}")
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


@main.command()
@click.argument("qualified_name")
@click.pass_context
def show(ctx: click.Context, qualified_name: str) -> None:
    """Show the canvas content for a node identified by its qualified name."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)

    node = canvas.find_by_qualified_name(qualified_name)
    if node is None:
        click.echo(f"No node found with qualified name: {qualified_name!r}", err=True)
        sys.exit(1)

    click.echo(node.text)


# ---------------------------------------------------------------------------
# set-text
# ---------------------------------------------------------------------------


@main.command(name="set-text")
@click.argument("node_id")
@click.option("--file", "text_file", type=click.File("r"), default="-",
              help="Read text from file (default: stdin).")
@click.pass_context
def set_text(ctx: click.Context, node_id: str, text_file) -> None:
    """Set the text content of a canvas node by ID."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.canvas.writer import write_canvas

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    canvas = read_canvas(canvas_path)

    node = None
    for n in canvas.nodes:
        if n.id == node_id:
            node = n
            break

    if node is None:
        click.echo(f"No node found with ID: {node_id!r}", err=True)
        sys.exit(1)

    new_text = text_file.read()
    node.text = new_text
    write_canvas(canvas, canvas_path)

    name = (node.ccoding.qualified_name if node.ccoding and node.ccoding.qualified_name
            else node_id)
    click.echo(f"Updated text for {name} ({len(new_text)} chars)")


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


@main.command()
@click.pass_context
def diff(ctx: click.Context) -> None:
    """Dry-run sync: show what would change without applying changes."""
    from ccoding.config import load_config
    from ccoding.canvas.reader import read_canvas
    from ccoding.code.parser import PythonAstParser, ClassElement
    from ccoding.sync.differ import compute_diff
    from ccoding.sync.hasher import content_hash
    from ccoding.sync.state import load_sync_state
    from ccoding.sync.engine import _qualified_name, _hash_class_element
    from pathlib import Path as _Path

    project: Path = ctx.obj["project"]
    config = load_config(project)
    canvas_path = project / config.canvas
    source_root = project / config.source_root

    if not canvas_path.exists():
        click.echo("No canvas file found.")
        return

    canvas = read_canvas(canvas_path)

    parser = PythonAstParser()
    code_elements: list[ClassElement] = []
    if source_root.exists():
        all_elements = parser.parse_directory(source_root)
        code_elements = [e for e in all_elements if isinstance(e, ClassElement)]

    state = load_sync_state(project)

    canvas_hashes: dict[str, str] = {}
    for node in canvas.nodes:
        if node.ccoding and node.ccoding.qualified_name:
            if node.ccoding.status in ("proposed", "rejected"):
                continue
            canvas_hashes[node.ccoding.qualified_name] = content_hash(node.text)

    code_hashes: dict[str, str] = {}
    for elem in code_elements:
        qname = _qualified_name(
            _Path(elem.source_path) if elem.source_path else source_root,
            elem.name,
            source_root,
        )
        code_hashes[qname] = _hash_class_element(elem)

    d = compute_diff(state, canvas_hashes, code_hashes)

    has_changes = False

    if d.canvas_modified:
        has_changes = True
        click.echo("Canvas modified (would update code):")
        for name in d.canvas_modified:
            click.echo(f"  ~ {name}")

    if d.code_modified:
        has_changes = True
        click.echo("Code modified (would update canvas):")
        for name in d.code_modified:
            click.echo(f"  ~ {name}")

    if d.canvas_added:
        has_changes = True
        click.echo("Canvas added (would generate code):")
        for name in d.canvas_added:
            click.echo(f"  + {name}")

    if d.code_added:
        has_changes = True
        click.echo("Code added (would add to canvas):")
        for name in d.code_added:
            click.echo(f"  + {name}")

    if d.canvas_deleted:
        has_changes = True
        click.echo("Canvas deleted (would remove code):")
        for name in d.canvas_deleted:
            click.echo(f"  - {name}")

    if d.code_deleted:
        has_changes = True
        click.echo("Code deleted (would remove from canvas):")
        for name in d.code_deleted:
            click.echo(f"  - {name}")

    if d.conflicts:
        has_changes = True
        click.echo("Conflicts (manual resolution required):")
        for c in d.conflicts:
            click.echo(f"  ! {c.qualified_name}")

    if not has_changes:
        click.echo("Everything is in sync — nothing would change.")
