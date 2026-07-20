from __future__ import annotations

from pathlib import Path

import pytest
from substance_designer_mcp_plugin.config import bridge_timeouts

from substance_designer_mcp.config import Settings


def test_settings_read_timeout_session_and_debug_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SUBSTANCE_DESIGNER_MCP_SESSION_PATH", str(tmp_path / "session.json"))
    monkeypatch.setenv("SUBSTANCE_DESIGNER_MCP_CONNECT_TIMEOUT", "1.5")
    monkeypatch.setenv("SUBSTANCE_DESIGNER_MCP_READ_TIMEOUT", "2.5")
    monkeypatch.setenv("SUBSTANCE_DESIGNER_MCP_WRITE_TIMEOUT", "9")
    monkeypatch.setenv("SUBSTANCE_DESIGNER_MCP_LOG_LEVEL", "DEBUG")

    settings = Settings.from_env()

    assert settings.session_path == tmp_path / "session.json"
    assert settings.connect_timeout == 1.5
    assert settings.read_timeout == 2.5
    assert settings.write_timeout == 9.0
    assert settings.log_level == "DEBUG"


def test_settings_reject_non_positive_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUBSTANCE_DESIGNER_MCP_READ_TIMEOUT", "0")

    with pytest.raises(ValueError, match="positive"):
        Settings.from_env()


def test_plugin_bridge_timeouts_share_documented_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUBSTANCE_DESIGNER_MCP_READ_TIMEOUT", "4")
    monkeypatch.setenv("SUBSTANCE_DESIGNER_MCP_WRITE_TIMEOUT", "12")

    assert bridge_timeouts() == (4.0, 12.0)
