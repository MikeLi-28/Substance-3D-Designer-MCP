from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_VERSION = "1.1.0"
OLD_VERSION = "0.1.0"

CURRENT_RELEASE_FILES = (
    "src/substance_designer_mcp/__init__.py",
    "src/substance_designer_mcp/server.py",
    "sd_plugin/substance_designer_mcp_plugin/config.py",
    "sd_plugin/substance_designer_mcp_plugin/bridge/server.py",
    "sd_plugin/substance_designer_mcp_plugin/bridge/session.py",
    "sd_plugin/substance_designer_mcp_plugin/commands/executor.py",
    "sd_plugin/substance_designer_mcp_plugin/services/parameter_service.py",
    "scripts/verify_release.py",
    "scripts/run_sd16_e2e.ps1",
    ".github/workflows/ci.yml",
    "CHANGELOG.md",
    "docs/compatibility.md",
    "docs/development.md",
    "docs/protocol.md",
)


def test_current_release_metadata_is_consistently_1_1_0() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    manifest = json.loads(
        (ROOT / "sd_plugin" / "substance_designer_mcp_plugin" / "pluginInfo.json").read_text(
            encoding="utf-8"
        )
    )

    assert f'version = "{RELEASE_VERSION}"' in project
    assert f'version = "{OLD_VERSION}"' not in project
    assert manifest["version"] == RELEASE_VERSION

    for relative in CURRENT_RELEASE_FILES:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert RELEASE_VERSION in text, relative
        assert OLD_VERSION not in text, relative
