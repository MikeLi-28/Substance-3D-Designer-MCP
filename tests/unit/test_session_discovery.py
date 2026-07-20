from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from substance_designer_mcp_plugin.bridge.session import SessionFile

from substance_designer_mcp.bridge import discovery
from substance_designer_mcp.bridge.discovery import discover_session
from substance_designer_mcp.errors import ErrorCode, MCPError


def test_session_file_is_atomic_contains_256_bit_token_and_cleans_own_file(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    session = SessionFile(
        path=path,
        port=54321,
        designer_version="16.0.3",
        plugin_version="1.0.0",
    )

    info = session.publish()

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved == info
    assert saved["host"] == "127.0.0.1"
    assert len(bytes.fromhex(saved["token"])) == 32
    assert not path.with_suffix(".tmp").exists()

    session.cleanup()
    assert not path.exists()


def test_session_cleanup_does_not_remove_another_session(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    session = SessionFile(path=path, port=1, designer_version="16.0.3")
    session.publish()
    replacement = json.loads(path.read_text(encoding="utf-8"))
    replacement["token"] = "different"
    path.write_text(json.dumps(replacement), encoding="utf-8")

    session.cleanup()

    assert path.exists()


def test_discover_session_accepts_current_process(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    session = SessionFile(path=path, port=54321, designer_version="16.0.3")
    published = session.publish()

    discovered = discover_session(path, check_port=False)

    assert discovered.pid == os.getpid()
    assert discovered.token == published["token"]


@pytest.mark.skipif(os.name != "nt", reason="Windows process probing regression")
def test_windows_pid_probe_accepts_live_process() -> None:
    assert discovery._windows_pid_is_alive(os.getpid()) is True


def test_discover_session_removes_stale_pid(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    path.write_text(
        json.dumps(
            {
                "protocol_version": "1.0",
                "host": "127.0.0.1",
                "port": 1234,
                "token": "00" * 32,
                "pid": 2_147_483_000,
                "designer_version": "16.0.3",
                "plugin_version": "1.0.0",
                "started_at": "2026-07-13T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(MCPError) as caught:
        discover_session(path, check_port=False)

    assert caught.value.code is ErrorCode.SD_NOT_RUNNING
    assert not path.exists()


def test_discover_session_rejects_non_loopback_host(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    session = SessionFile(path=path, port=1234, designer_version="16.0.3")
    info = session.publish()
    info["host"] = "0.0.0.0"
    path.write_text(json.dumps(info), encoding="utf-8")

    with pytest.raises(MCPError) as caught:
        discover_session(path, check_port=False)

    assert caught.value.code is ErrorCode.BRIDGE_NOT_AVAILABLE
