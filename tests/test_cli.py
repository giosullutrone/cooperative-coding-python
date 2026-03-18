import json
import os
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
        old_cwd = os.getcwd()
        os.chdir(tmp_project)
        try:
            result = runner.invoke(main, ["check"])
            assert result.exit_code == 0
        finally:
            os.chdir(old_cwd)


class TestCliProposeStereotype:
    def test_propose_with_stereotype(self, tmp_project: Path):
        runner = CliRunner()
        old_cwd = os.getcwd()
        os.chdir(tmp_project)
        try:
            result = runner.invoke(main, [
                "propose", "--kind", "class", "--name", "MyProto",
                "--stereotype", "protocol", "--rationale", "test",
            ])
            assert result.exit_code == 0
            assert "Proposed node" in result.output

            # Verify stereotype was persisted in canvas
            canvas_data = json.loads((tmp_project / "design.canvas").read_text())
            node = canvas_data["nodes"][0]
            assert node["ccoding"]["stereotype"] == "protocol"
        finally:
            os.chdir(old_cwd)

    def test_propose_without_stereotype(self, tmp_project: Path):
        runner = CliRunner()
        old_cwd = os.getcwd()
        os.chdir(tmp_project)
        try:
            result = runner.invoke(main, [
                "propose", "--kind", "class", "--name", "PlainClass",
                "--rationale", "test",
            ])
            assert result.exit_code == 0

            canvas_data = json.loads((tmp_project / "design.canvas").read_text())
            node = canvas_data["nodes"][0]
            # stereotype should be absent or null
            assert node["ccoding"].get("stereotype") is None
        finally:
            os.chdir(old_cwd)


class TestCliSetText:
    def test_set_text_from_stdin(self, tmp_project: Path):
        runner = CliRunner()
        old_cwd = os.getcwd()
        os.chdir(tmp_project)
        try:
            # First create a node
            result = runner.invoke(main, [
                "propose", "--name", "Foo", "--rationale", "test",
            ])
            assert result.exit_code == 0
            node_id = result.output.split()[2]  # "Proposed node <id> ..."

            # Set text via stdin
            new_text = "# Foo\n## Responsibility\nDoes foo things."
            result = runner.invoke(main, ["set-text", node_id], input=new_text)
            assert result.exit_code == 0
            assert "Updated text" in result.output

            # Verify text was persisted
            canvas_data = json.loads((tmp_project / "design.canvas").read_text())
            node = canvas_data["nodes"][0]
            assert node["text"] == new_text
        finally:
            os.chdir(old_cwd)

    def test_set_text_from_file(self, tmp_project: Path):
        runner = CliRunner()
        old_cwd = os.getcwd()
        os.chdir(tmp_project)
        try:
            # Create a node
            result = runner.invoke(main, [
                "propose", "--name", "Bar", "--rationale", "test",
            ])
            assert result.exit_code == 0
            node_id = result.output.split()[2]

            # Write content to a temp file
            content_file = tmp_project / "content.md"
            content_file.write_text("# Bar\nSome content here.")

            result = runner.invoke(main, [
                "set-text", node_id, "--file", str(content_file),
            ])
            assert result.exit_code == 0
            assert "Updated text" in result.output

            canvas_data = json.loads((tmp_project / "design.canvas").read_text())
            node = canvas_data["nodes"][0]
            assert node["text"] == "# Bar\nSome content here."
        finally:
            os.chdir(old_cwd)

    def test_set_text_nonexistent_node(self, tmp_project: Path):
        runner = CliRunner()
        old_cwd = os.getcwd()
        os.chdir(tmp_project)
        try:
            result = runner.invoke(main, ["set-text", "nonexistent"], input="hello")
            assert result.exit_code != 0
            assert "No node found" in result.output or "No node found" in (result.output + (result.stderr_bytes or b"").decode())
        finally:
            os.chdir(old_cwd)
