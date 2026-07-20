from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from substance_designer_mcp_plugin.bridge.server import BridgeServer
from substance_designer_mcp_plugin.commands.executor import build_command_executor
from substance_designer_mcp_plugin.services.container import ServiceContainer

from substance_designer_mcp.bridge.client import BridgeClient
from substance_designer_mcp.server import build_server
from tests.fakes.sd_api import build_fake_designer


class ImmediateDispatcher:
    def call(self, function: Callable[..., Any], *args: Any, timeout: float) -> Any:
        del timeout
        return function(*args)


def test_fake_sd_to_tcp_to_mcp_tool_structured_result(tmp_path: Path) -> None:
    fake = build_fake_designer()
    services = ServiceContainer(fake.application, fake.adapter)
    executor = build_command_executor(services)
    bridge = BridgeServer(
        executor=executor,
        dispatcher=ImmediateDispatcher(),
        session_path=tmp_path / "session.json",
        designer_version="16.0.3",
    )
    bridge.start()
    try:
        mcp = build_server(BridgeClient(session_path=tmp_path / "session.json"))
        _content, structured = asyncio.run(mcp.call_tool("sd_get_active_graph", {}))

        assert structured["ok"] is True
        assert structured["data"]["graph"]["graph_identifier"] == "main"
        assert structured["data"]["node_count"] == 1
    finally:
        bridge.stop()
