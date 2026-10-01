"""Tests for scripts/vendor.py against a throwaway workspace."""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
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


def _sync(ws: Path, **kwargs) -> list[str]:
    return vendor.sync_target(ws, MODULE3, force=kwargs.pop("force", False), **kwargs)


# Canonical content


def test_canonical_files_include_nested_components_in_sorted_order() -> None:
    files = list(vendor.canonical_files())
    assert files == sorted(files)
    assert "components/__init__.py" in files and "components/metrics.py" in files
    assert not any("__pycache__" in rel for rel in files)


def test_untracked_files_in_the_canonical_package_are_never_vendored() -> None:
    probe = vendor.PACKAGE_DIR / "components" / "status 2.py"  # a cloud-sync conflict copy
    probe.write_text("STRAY = 1\n", encoding="utf-8")
    try:
        assert "components/status 2.py" not in vendor.canonical_files()
        assert "components/status.py" in vendor.canonical_files()
    finally:
        probe.unlink()


def test_manifest_is_deterministic_and_hashes_every_file() -> None:
    files = vendor.canonical_files()
    text = vendor.manifest_text(files)
    assert text == vendor.manifest_text(dict(reversed(list(files.items()))))
    data = json.loads(text)
    assert data["kit"] == "csc8830-ui" and data["kit_version"] == KIT_VERSION
    assert list(data["files"]) == sorted(files)
    for rel, digest in data["files"].items():
        assert digest == hashlib.sha256(files[rel]).hexdigest()


# Fresh vendoring


def test_check_reports_unvendored_target(workspace: Path) -> None:
    problems = vendor.check_target(workspace, MODULE3)
    assert any("not vendored" in p for p in problems)
    assert any("config.toml" in p for p in problems)


def test_sync_copies_nested_directories_byte_for_byte(workspace: Path) -> None:
    assert _sync(workspace) == []
    assert vendor.check_target(workspace, MODULE3) == []
    for rel, data in vendor.canonical_files().items():
        assert (_package(workspace) / rel).read_bytes() == data
    manifest = (_package(workspace) / vendor.MANIFEST_NAME).read_text(encoding="utf-8")
    assert manifest == vendor.manifest_text(vendor.canonical_files())
    config = workspace / "Module_3" / ".streamlit" / "config.toml"
    assert config.read_text(encoding="utf-8") == render_config_toml()


def test_sync_is_idempotent(workspace: Path) -> None:
    _sync(workspace)
    before = {p: p.read_bytes() for p in _package(workspace).rglob("*") if p.is_file()}
    assert _sync(workspace) == []
    after = {p: p.read_bytes() for p in _package(workspace).rglob("*") if p.is_file()}
    assert before == after


def test_sync_writes_nothing_outside_owned_paths(workspace: Path) -> None:
    unrelated = workspace / "Module_3" / "README.md"
    unrelated.write_text("keep me", encoding="utf-8")
    _sync(workspace)
    root = workspace / "Module_3"
    written = {p.relative_to(root) for p in root.rglob("*") if p.is_file()}
    design = Path("src/module3/webapp/design")
    owned = {design / rel for rel in vendor.canonical_files()} | {design / vendor.MANIFEST_NAME}
    assert written == owned | {Path(".streamlit/config.toml"), Path("README.md")}
    assert unrelated.read_text(encoding="utf-8") == "keep me"


def test_caches_are_ignored(workspace: Path) -> None:
    _sync(workspace)
    cache = _package(workspace) / "components" / "__pycache__"
    cache.mkdir()
    (cache / "metrics.cpython-314.pyc").write_bytes(b"\x00")
    assert vendor.check_target(workspace, MODULE3) == []
    assert _sync(workspace) == []


# Ownership and local edits


def test_unknown_nested_file_is_never_overwritten_or_deleted(workspace: Path) -> None:
    _sync(workspace)
    mine = _package(workspace) / "components" / "mine.py"
    mine.write_text("x = 1\n", encoding="utf-8")
    for force in (False, True):
        refusals = _sync(workspace, force=force)
        assert any("unknown files" in r and "components/mine.py" in r for r in refusals)
    assert mine.read_text(encoding="utf-8") == "x = 1\n"
    assert any("components/mine.py" in p for p in vendor.check_target(workspace, MODULE3))


def test_edited_nested_owned_file_needs_force(workspace: Path) -> None:
    _sync(workspace)
    metrics = _package(workspace) / "components" / "metrics.py"
    metrics.write_bytes(metrics.read_bytes() + b"# local edit\n")
    refusals = _sync(workspace)
    assert any("edited after vendoring" in r and "components/metrics.py" in r for r in refusals)
    assert metrics.read_bytes().endswith(b"# local edit\n")  # refused target left untouched
    assert any("components/metrics.py" in p for p in vendor.check_target(workspace, MODULE3))
    assert _sync(workspace, force=True) == []
    assert vendor.check_target(workspace, MODULE3) == []


def test_stale_owned_file_is_removed_and_empty_dirs_pruned(workspace: Path) -> None:
    _sync(workspace)
    package = _package(workspace)
    old = package / "retired" / "old.py"
    old.parent.mkdir()
    old.write_bytes(b"OLD = 1\n")
    manifest = json.loads((package / vendor.MANIFEST_NAME).read_text(encoding="utf-8"))
    manifest["files"]["retired/old.py"] = hashlib.sha256(b"OLD = 1\n").hexdigest()
    (package / vendor.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    assert any("stale kit file" in p for p in vendor.check_target(workspace, MODULE3))
    assert _sync(workspace) == []
    assert not old.exists() and not old.parent.exists()
    assert vendor.check_target(workspace, MODULE3) == []


def test_edited_stale_owned_file_is_not_deleted_without_force(workspace: Path) -> None:
    _sync(workspace)
    package = _package(workspace)
    old = package / "retired.py"
    old.write_bytes(b"OLD = 1\n")
    manifest = json.loads((package / vendor.MANIFEST_NAME).read_text(encoding="utf-8"))
    manifest["files"]["retired.py"] = hashlib.sha256(b"OLD = 0\n").hexdigest()
    (package / vendor.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    assert any("edited after vendoring" in r for r in _sync(workspace))
    assert old.exists()


def test_invalid_manifest_is_refused(workspace: Path) -> None:
    _sync(workspace)
    (_package(workspace) / vendor.MANIFEST_NAME).write_text("{not json", encoding="utf-8")
    assert any("not valid JSON" in r for r in _sync(workspace, force=True))


# Versions


def test_sync_refuses_to_downgrade_unless_allowed(workspace: Path) -> None:
    _sync(workspace)
    version = _package(workspace) / "version.py"
    version.write_text('KIT_VERSION = "99.0.0"\n', encoding="utf-8")
    assert any("downgrade" in r for r in _sync(workspace, force=True))
    assert _sync(workspace, force=True, allow_downgrade=True) == []
    assert vendor.check_target(workspace, MODULE3) == []


def test_check_flags_version_mismatch(workspace: Path) -> None:
    _sync(workspace)
    (_package(workspace) / "version.py").write_text('KIT_VERSION = "0.0.1"\n', encoding="utf-8")
    assert any(f"!= canonical {KIT_VERSION}" in p for p in vendor.check_target(workspace, MODULE3))


def test_legacy_copy_without_manifest_upgrades_cleanly(workspace: Path) -> None:
    """A 0.2.0 copy: top-level files only, no manifest. Its files count as kit-owned."""
    package = _package(workspace)
    package.mkdir()
    for rel, data in vendor.canonical_files().items():
        if "/" not in rel:
            (package / rel).write_bytes(data)
    (package / "version.py").write_text('KIT_VERSION = "0.2.0"\n', encoding="utf-8")
    assert any("missing ownership manifest" in p for p in vendor.check_target(workspace, MODULE3))
    assert _sync(workspace) == []
    assert vendor.check_target(workspace, MODULE3) == []
    assert (package / "components" / "layout.py").is_file()


def test_legacy_copy_with_extra_file_is_refused(workspace: Path) -> None:
    package = _package(workspace)
    package.mkdir()
    (package / "version.py").write_text('KIT_VERSION = "0.2.0"\n', encoding="utf-8")
    (package / "helpers.py").write_text("x = 1\n", encoding="utf-8")
    assert any("unknown files" in r and "helpers.py" in r for r in _sync(workspace, force=True))


def test_sync_refuses_to_overwrite_a_hand_written_config(workspace: Path) -> None:
    config = workspace / "Module_3" / ".streamlit" / "config.toml"
    config.parent.mkdir()
    config.write_text("[server]\nport = 8600\n", encoding="utf-8")
    assert any("not generated" in r for r in _sync(workspace, force=True))
    assert config.read_text(encoding="utf-8") == "[server]\nport = 8600\n"
    assert not _package(workspace).exists()  # nothing written when any check refuses


# Vendored copy works under the module's package name


def test_vendored_copy_imports_under_the_module_package_name(workspace: Path, monkeypatch) -> None:
    _sync(workspace)
    src = workspace / "Module_3" / "src"
    for pkg in (src / "module3", src / "module3" / "webapp"):
        (pkg / "__init__.py").write_text("", encoding="utf-8")
    monkeypatch.syspath_prepend(str(src))
    design = importlib.import_module("module3.webapp.design")
    assert design.KIT_VERSION == KIT_VERSION
    assert design.render_config_toml() == render_config_toml()
    pytest.importorskip("streamlit")
    components = importlib.import_module("module3.webapp.design.components")
    assert callable(components.metric_row) and callable(components.page_header)


def test_dash_guard_passes_for_canonical_kit() -> None:
    vendor.assert_dash_free()


def test_targets_cover_every_module_and_both_dashboards() -> None:
    names = {t.name for t in vendor.TARGETS}
    assert names == {"module2", "module3", "module4", "module5_6", "root-dashboard", "deploy-dashboard"}
