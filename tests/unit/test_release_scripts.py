from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from scripts.build_plugin import build_plugin
from scripts.install_plugin import InstallError, install_plugin
from scripts.uninstall_plugin import uninstall_plugin

ROOT = Path(__file__).resolve().parents[2]


def test_build_plugin_creates_distributable_zip_with_manifest(tmp_path: Path) -> None:
    archive = build_plugin(
        ROOT / "sd_plugin" / "substance_designer_mcp_plugin",
        tmp_path / "artifacts",
    )

    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        manifest = json.loads(
            bundle.read("substance_designer_mcp_plugin/pluginInfo.json").decode("utf-8")
        )

    assert "substance_designer_mcp_plugin/substance_designer_mcp_plugin/__init__.py" in names
    assert "substance_designer_mcp_plugin/pluginInfo.json" in names
    assert manifest["version"] == "1.1.0"
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)


def test_install_plugin_requires_explicit_existing_target_and_backs_up_existing(
    tmp_path: Path,
) -> None:
    target = tmp_path / "user-plugins"
    target.mkdir()
    existing = target / "substance_designer_mcp_plugin"
    existing.mkdir()
    (existing / "old.txt").write_text("old", encoding="utf-8")

    result = install_plugin(
        ROOT / "sd_plugin" / "substance_designer_mcp_plugin",
        target,
    )

    assert result.install_path.joinpath("pluginInfo.json").exists()
    assert result.install_path.joinpath("substance_designer_mcp_plugin", "__init__.py").exists()
    assert result.backup_path is not None
    assert result.backup_path.joinpath("old.txt").read_text(encoding="utf-8") == "old"


def test_install_refuses_designer_core_tree(tmp_path: Path) -> None:
    install_root = tmp_path / "Adobe Substance 3D Designer"
    plugins = install_root / "plugins"
    plugins.mkdir(parents=True)
    (install_root / "Adobe Substance 3D Designer.exe").write_bytes(b"")

    with pytest.raises(InstallError, match="installation tree"):
        install_plugin(ROOT / "sd_plugin" / "substance_designer_mcp_plugin", plugins)


def test_uninstall_removes_only_named_plugin_directory(tmp_path: Path) -> None:
    target = tmp_path / "user-plugins"
    plugin = target / "substance_designer_mcp_plugin"
    plugin.mkdir(parents=True)
    sentinel = target / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    removed = uninstall_plugin(target)

    assert removed is True
    assert not plugin.exists()
    assert sentinel.exists()
