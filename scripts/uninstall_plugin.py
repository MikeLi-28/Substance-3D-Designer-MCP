"""Remove only substance_designer_mcp_plugin from an explicit target directory."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

try:
    from scripts.install_plugin import InstallError, _inside_designer_install_tree
except ModuleNotFoundError:  # Direct execution from the scripts directory.
    from install_plugin import InstallError, _inside_designer_install_tree


PLUGIN_DIRECTORY = "substance_designer_mcp_plugin"


def uninstall_plugin(target: Path) -> bool:
    """Remove the exact plugin child and leave every sibling untouched."""

    target = Path(target).resolve()
    if not target.is_dir():
        raise InstallError("The explicit target directory must already exist.")
    if _inside_designer_install_tree(target):
        raise InstallError("Refusing to modify the Adobe Designer installation tree.")
    plugin = (target / PLUGIN_DIRECTORY).resolve()
    if plugin.parent != target:
        raise InstallError("Resolved plugin path escaped the target directory.")
    if not plugin.exists():
        return False
    if not plugin.is_dir():
        raise InstallError("The plugin path is not a directory.")
    shutil.rmtree(plugin)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, type=Path)
    arguments = parser.parse_args()
    print("Removed" if uninstall_plugin(arguments.target) else "Not installed")


if __name__ == "__main__":
    main()
