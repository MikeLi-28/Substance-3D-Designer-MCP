"""Safely install the plugin into an explicit Designer user-plugin directory."""

from __future__ import annotations

import argparse
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class InstallError(RuntimeError):
    pass


@dataclass(frozen=True)
class InstallResult:
    install_path: Path
    backup_path: Path | None


def _inside_designer_install_tree(target: Path) -> bool:
    for parent in (target, *target.parents):
        if (parent / "Adobe Substance 3D Designer.exe").exists():
            return True
    return False


def install_plugin(source: Path, target: Path) -> InstallResult:
    """Install with staging and backup, refusing Adobe's core installation tree."""

    source = Path(source).resolve()
    target = Path(target).resolve()
    if not source.is_dir() or not (source / "pluginInfo.json").is_file():
        raise InstallError("Plugin source is invalid.")
    if not target.is_dir():
        raise InstallError("The explicit target directory must already exist.")
    if _inside_designer_install_tree(target):
        raise InstallError("Refusing to modify the Adobe Designer installation tree.")
    destination = target / source.name
    stage = target / (f".{source.name}-installing")
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    shutil.copy2(source / "pluginInfo.json", stage / "pluginInfo.json")
    shutil.copytree(
        source,
        stage / source.name,
        ignore=shutil.ignore_patterns("pluginInfo.json"),
    )
    backup: Path | None = None
    try:
        if destination.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = target / (f"{source.name}.backup-{stamp}")
            if backup.exists():
                raise InstallError("A backup with the same timestamp already exists.")
            os.replace(destination, backup)
        os.replace(stage, destination)
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        if backup is not None and backup.exists() and not destination.exists():
            os.replace(backup, destination)
        raise
    return InstallResult(destination, backup)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("sd_plugin/substance_designer_mcp_plugin"),
    )
    arguments = parser.parse_args()
    result = install_plugin(arguments.source, arguments.target)
    print(result.install_path)
    if result.backup_path is not None:
        print(f"Backup: {result.backup_path}")


if __name__ == "__main__":
    main()
