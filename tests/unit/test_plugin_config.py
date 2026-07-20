from __future__ import annotations

import importlib
from pathlib import Path

import substance_designer_mcp_plugin.config as plugin_config


def test_plugin_paths_honor_explicit_environment_overrides(monkeypatch, tmp_path: Path) -> None:
    session = tmp_path / "isolated" / "session.json"
    log = tmp_path / "isolated" / "plugin.log"
    monkeypatch.setenv("SUBSTANCE_DESIGNER_MCP_SESSION_PATH", str(session))
    monkeypatch.setenv("SUBSTANCE_DESIGNER_MCP_PLUGIN_LOG_PATH", str(log))

    reloaded = importlib.reload(plugin_config)

    assert session == reloaded.SESSION_PATH
    assert log == reloaded.LOG_PATH

    monkeypatch.delenv("SUBSTANCE_DESIGNER_MCP_SESSION_PATH")
    monkeypatch.delenv("SUBSTANCE_DESIGNER_MCP_PLUGIN_LOG_PATH")
    importlib.reload(plugin_config)
