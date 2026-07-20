"""Structured MCP tool success and failure envelopes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from substance_designer_mcp.errors import MCPError


class BridgeCaller(Protocol):
    def call(
        self, command: str, arguments: Mapping[str, Any], *, write: bool = False
    ) -> dict[str, Any]: ...


def tool_success(data: Mapping[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": dict(data), "warnings": []}


def tool_failure(error: MCPError, data: Mapping[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"ok": False, "error": error.to_dict(), "warnings": []}
    if data is not None:
        result["data"] = dict(data)
    return result


def invoke(
    client: BridgeCaller,
    command: str,
    arguments: Mapping[str, Any],
    *,
    write: bool = False,
) -> dict[str, Any]:
    try:
        return tool_success(client.call(command, arguments, write=write))
    except MCPError as error:
        return tool_failure(error)


def invoke_ping(client: BridgeCaller) -> dict[str, Any]:
    try:
        return tool_success(client.call("sd_ping", {}))
    except MCPError as error:
        return tool_failure(
            error,
            {
                "mcp_server_running": True,
                "bridge_connected": False,
                "plugin_running": False,
            },
        )
