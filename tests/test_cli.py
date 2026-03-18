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
