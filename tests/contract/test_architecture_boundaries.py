from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module)
    return result


def test_external_server_never_imports_adobe_sd() -> None:
    external = ROOT / "src" / "substance_designer_mcp"

    for path in external.rglob("*.py"):
        imports = _imports(path)
        assert not any(name == "sd" or name.startswith("sd.") for name in imports), path


def test_mcp_tools_do_not_import_plugin_services_or_adobe_modules() -> None:
    tools = ROOT / "src" / "substance_designer_mcp" / "tools"

    for path in tools.glob("*.py"):
        imports = _imports(path)
        assert not any("substance_designer_mcp_plugin" in name for name in imports), path
        assert not any(name == "sd" or name.startswith("sd.") for name in imports), path


def test_plugin_bridge_contains_no_service_business_imports() -> None:
    bridge = ROOT / "sd_plugin" / "substance_designer_mcp_plugin" / "bridge"

    for path in bridge.glob("*.py"):
        assert not any("services" in name for name in _imports(path)), path


def test_adobe_imports_are_confined_to_bootstrap_and_compatibility() -> None:
    plugin = ROOT / "sd_plugin" / "substance_designer_mcp_plugin"
    allowed = {
        "plugin.py",
        "compatibility/sd16.py",
    }

    for path in plugin.rglob("*.py"):
        imports = _imports(path)
        has_adobe = any(name == "sd" or name.startswith("sd.") for name in imports)
        if has_adobe:
            assert path.relative_to(plugin).as_posix() in allowed
