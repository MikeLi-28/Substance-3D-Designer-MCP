"""Static security, compatibility, size, and artifact checks for a release."""

from __future__ import annotations

import argparse
import ast
import json
import tarfile
import zipfile
from collections.abc import Iterable
from pathlib import Path

SOURCE_DIRECTORIES = ("src", "sd_plugin", "scripts")
FORBIDDEN_CALLS = {"eval", "exec"}
ALLOWED_SDIST_ROOTS = frozenset(
    {
        ".gitignore",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "LICENSE",
        "PKG-INFO",
        "README.md",
        "README.zh-CN.md",
        "SECURITY.md",
        "assets",
        "docs",
        "examples",
        "pyproject.toml",
        "scripts",
        "sd_plugin",
        "src",
        "tests",
    }
)


def _python_files(root: Path) -> Iterable[Path]:
    for directory in SOURCE_DIRECTORIES:
        base = root / directory
        if base.exists():
            yield from base.rglob("*.py")


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return f"{node.func.value.id}.{node.func.attr}"
    return ""


def scan_source_tree(root: Path) -> list[str]:
    """Return every high-risk source finding without modifying the tree."""

    root = Path(root).resolve()
    issues: list[str] = []
    for path in _python_files(root):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) > 500:
            issues.append(f"{relative} exceeds 500 handwritten lines ({len(lines)}).")
        try:
            tree = ast.parse(text, filename=relative)
        except SyntaxError as exc:
            issues.append(f"{relative} has invalid Python syntax: {exc.msg}.")
            continue
        if relative.startswith("sd_plugin/"):
            try:
                ast.parse(text, filename=relative, feature_version=(3, 9))
            except SyntaxError as exc:
                issues.append(f"{relative} is not Python 3.9 compatible: {exc.msg}.")
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name for alias in node.names]
                module = node.module if isinstance(node, ast.ImportFrom) else None
                if "subprocess" in names or module == "subprocess":
                    issues.append(f"{relative} imports forbidden subprocess support.")
                if relative.startswith("src/") and (
                    "sd" in names or module == "sd" or (module and module.startswith("sd."))
                ):
                    issues.append(f"{relative} imports Adobe sd in the external server.")
            if isinstance(node, ast.Call):
                call_name = _call_name(node)
                if call_name in FORBIDDEN_CALLS:
                    issues.append(f"{relative} calls forbidden {call_name}.")
                if call_name == "os.system":
                    issues.append(f"{relative} calls forbidden os.system.")
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "bind"
                    and node.args
                    and isinstance(node.args[0], (ast.Tuple, ast.List))
                    and node.args[0].elts
                    and isinstance(node.args[0].elts[0], ast.Constant)
                    and node.args[0].elts[0].value == "0.0.0.0"
                ):
                    issues.append(f"{relative} binds a listener to non-loopback 0.0.0.0.")
    return sorted(set(issues))


def verify_artifacts(root: Path, plugin_archive: Path) -> list[str]:
    """Verify expected Python and plugin release artifacts."""

    root = Path(root).resolve()
    issues: list[str] = []
    wheels = list((root / "dist").glob("substance_designer_mcp-1.1.0-*.whl"))
    sdists = list((root / "dist").glob("substance_designer_mcp-1.1.0.tar.gz"))
    if not wheels:
        issues.append("Python wheel is missing from dist/.")
    if not sdists:
        issues.append("Python sdist is missing from dist/.")
    for sdist in sdists:
        try:
            with tarfile.open(sdist, "r:gz") as bundle:
                unexpected: set[str] = set()
                for name in bundle.getnames():
                    parts = Path(name).parts
                    if len(parts) >= 2 and parts[1] not in ALLOWED_SDIST_ROOTS:
                        unexpected.add(parts[1])
                for path in sorted(unexpected):
                    issues.append(f"Python sdist contains unexpected top-level path: {path}.")
        except (OSError, tarfile.TarError) as exc:
            issues.append(f"Python sdist cannot be verified: {exc}.")
    plugin_archive = Path(plugin_archive)
    if not plugin_archive.is_file():
        issues.append(f"Plugin ZIP is missing: {plugin_archive}.")
        return issues
    try:
        with zipfile.ZipFile(plugin_archive) as bundle:
            names = set(bundle.namelist())
            manifest_name = "substance_designer_mcp_plugin/pluginInfo.json"
            if manifest_name not in names:
                issues.append("Plugin ZIP does not contain pluginInfo.json at the expected path.")
            else:
                manifest = json.loads(bundle.read(manifest_name).decode("utf-8"))
                if manifest.get("version") != "1.1.0":
                    issues.append("Plugin manifest version is not 1.1.0.")
            if any("__pycache__" in name or name.endswith(".pyc") for name in names):
                issues.append("Plugin ZIP contains Python cache files.")
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        issues.append(f"Plugin ZIP cannot be verified: {exc}.")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--plugin-archive", required=True, type=Path)
    arguments = parser.parse_args()
    issues = scan_source_tree(arguments.root)
    issues.extend(verify_artifacts(arguments.root, arguments.plugin_archive))
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}")
        raise SystemExit(1)
    print("Release verification passed.")


if __name__ == "__main__":
    main()
