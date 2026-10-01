"""Tests for scripts/vendor.py against a throwaway workspace."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from csc8830_ui import KIT_VERSION, render_config_toml

REPO_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("vendor", REPO_ROOT / "scripts" / "vendor.py")
vendor = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["vendor"] = vendor  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(vendor)

MODULE3 = vendor.Target("module3", "Module_3", "src/module3/webapp/design")


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "Module_3" / "src" / "module3" / "webapp").mkdir(parents=True)
    return tmp_path


def _package(ws: Path) -> Path:
    return ws / "Module_3" / "src" / "module3" / "webapp" / "design"


def test_check_reports_unvendored_target(workspace: Path) -> None:
    problems = vendor.check_target(workspace, MODULE3)
    assert any("not vendored" in p for p in problems)
    assert any("config.toml" in p for p in problems)


def test_sync_then_check_is_clean_and_byte_identical(workspace: Path) -> None:
    assert vendor.sync_target(workspace, MODULE3, force=False) == []
    assert vendor.check_target(workspace, MODULE3) == []
    for name, data in vendor.canonical_files().items():
        assert (_package(workspace) / name).read_bytes() == data
    config = workspace / "Module_3" / ".streamlit" / "config.toml"
    assert config.read_text(encoding="utf-8") == render_config_toml()


def test_sync_writes_nothing_outside_owned_paths(workspace: Path) -> None:
    unrelated = workspace / "Module_3" / "README.md"
    unrelated.write_text("keep me", encoding="utf-8")
    vendor.sync_target(workspace, MODULE3, force=False)
    written = {p.relative_to(workspace / "Module_3") for p in (workspace / "Module_3").rglob("*") if p.is_file()}
    owned = {Path("src/module3/webapp/design") / n for n in vendor.canonical_files()}
    assert written == owned | {Path(".streamlit/config.toml"), Path("README.md")}
    assert unrelated.read_text(encoding="utf-8") == "keep me"


def test_sync_refuses_to_downgrade(workspace: Path) -> None:
    vendor.sync_target(workspace, MODULE3, force=False)
    (_package(workspace) / "version.py").write_text('KIT_VERSION = "99.0.0"\n', encoding="utf-8")
    refusals = vendor.sync_target(workspace, MODULE3, force=True)
    assert any("downgrade" in r for r in refusals)


def test_sync_refuses_same_version_local_edits_without_force(workspace: Path) -> None:
    vendor.sync_target(workspace, MODULE3, force=False)
    tokens = _package(workspace) / "tokens.py"
    tokens.write_bytes(tokens.read_bytes() + b"# local edit\n")
    assert any("edited locally" in r for r in vendor.sync_target(workspace, MODULE3, force=False))
    assert vendor.check_target(workspace, MODULE3)  # check mode flags the drift
    assert vendor.sync_target(workspace, MODULE3, force=True) == []
    assert vendor.check_target(workspace, MODULE3) == []


def test_sync_refuses_extra_files_in_the_design_package(workspace: Path) -> None:
    vendor.sync_target(workspace, MODULE3, force=False)
    (_package(workspace) / "mine.py").write_text("x = 1\n", encoding="utf-8")
    assert any("extra files" in r for r in vendor.sync_target(workspace, MODULE3, force=True))


def test_sync_refuses_to_overwrite_a_hand_written_config(workspace: Path) -> None:
    config = workspace / "Module_3" / ".streamlit" / "config.toml"
    config.parent.mkdir()
    config.write_text("[server]\nport = 8600\n", encoding="utf-8")
    assert any("not generated" in r for r in vendor.sync_target(workspace, MODULE3, force=True))
    assert config.read_text(encoding="utf-8") == "[server]\nport = 8600\n"


def test_check_flags_version_mismatch(workspace: Path) -> None:
    vendor.sync_target(workspace, MODULE3, force=False)
    (_package(workspace) / "version.py").write_text('KIT_VERSION = "0.0.1"\n', encoding="utf-8")
    assert any(f"!= canonical {KIT_VERSION}" in p for p in vendor.check_target(workspace, MODULE3))


def test_vendored_copy_imports_under_the_module_package_name(workspace: Path, monkeypatch) -> None:
    vendor.sync_target(workspace, MODULE3, force=False)
    src = workspace / "Module_3" / "src"
    for pkg in (src / "module3", src / "module3" / "webapp"):
        (pkg / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(src))
    import importlib

    design = importlib.import_module("module3.webapp.design")
    assert design.KIT_VERSION == KIT_VERSION
    assert design.render_config_toml() == render_config_toml()


def test_targets_cover_every_module_and_both_dashboards() -> None:
    names = {t.name for t in vendor.TARGETS}
    assert names == {"module2", "module3", "module4", "module5_6", "root-dashboard", "deploy-dashboard"}
