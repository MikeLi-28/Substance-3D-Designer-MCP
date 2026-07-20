from __future__ import annotations

import socket
import time
from pathlib import Path
from typing import Any

import pytest
from substance_designer_mcp_plugin.bridge.server import BridgeServer

from substance_designer_mcp.bridge.client import BridgeClient
from substance_designer_mcp.bridge.framing import FrameDecoder, encode_message
from substance_designer_mcp.bridge.protocol import create_request
from substance_designer_mcp.errors import ErrorCode, MCPError


class ImmediateDispatcher:
    def call(self, function: Any, *args: Any, timeout: float) -> dict[str, Any]:
        del timeout
        return function(*args)


class RecordingExecutor:
    def __init__(self, delay: float = 0.0) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.delay = delay

    def execute(self, command: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((command, arguments))
        if self.delay:
            time.sleep(self.delay)
        return {"command": command, "arguments": arguments}


def test_tcp_bridge_round_trip(tmp_path: Path) -> None:
    executor = RecordingExecutor()
    server = BridgeServer(
        executor=executor,
        dispatcher=ImmediateDispatcher(),
        session_path=tmp_path / "session.json",
        designer_version="16.0.3",
    )
    server.start()
    try:
        client = BridgeClient(session_path=tmp_path / "session.json")

        result = client.call("sd_ping", {"detail": "summary"})

        assert result == {"command": "sd_ping", "arguments": {"detail": "summary"}}
        assert executor.calls == [("sd_ping", {"detail": "summary"})]
    finally:
        server.stop()


def test_wrong_token_never_reaches_executor(tmp_path: Path) -> None:
    executor = RecordingExecutor()
    server = BridgeServer(
        executor=executor,
        dispatcher=ImmediateDispatcher(),
        session_path=tmp_path / "session.json",
        designer_version="16.0.3",
    )
    session = server.start()
    try:
        request = create_request("sd_ping", {}, "bad-token")
        with socket.create_connection((session["host"], session["port"]), timeout=1) as sock:
            sock.sendall(encode_message(request))
            decoder = FrameDecoder()
            response = decoder.feed(sock.recv(4096))[0]

        assert response["ok"] is False
        assert response["error"]["code"] == "AUTHENTICATION_FAILED"
        assert executor.calls == []
    finally:
        server.stop()


def test_client_without_session_returns_sd_not_running(tmp_path: Path) -> None:
    client = BridgeClient(session_path=tmp_path / "missing.json")

    with pytest.raises(MCPError) as caught:
        client.call("sd_ping", {})

    assert caught.value.code is ErrorCode.SD_NOT_RUNNING


def test_read_timeout_maps_to_stable_error(tmp_path: Path) -> None:
    server = BridgeServer(
        executor=RecordingExecutor(delay=0.2),
        dispatcher=ImmediateDispatcher(),
        session_path=tmp_path / "session.json",
        designer_version="16.0.3",
    )
    server.start()
    try:
        client = BridgeClient(session_path=tmp_path / "session.json", read_timeout=0.05)

        with pytest.raises(MCPError) as caught:
            client.call("sd_ping", {})

        assert caught.value.code is ErrorCode.REQUEST_TIMEOUT
    finally:
        server.stop()
