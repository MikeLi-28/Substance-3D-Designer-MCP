from __future__ import annotations

import asyncio
from typing import Any

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from substance_designer_mcp.errors import ErrorCode, MCPError
from substance_designer_mcp.server import build_server

TOOL_NAMES = {
    "sd_ping",
    "sd_get_application_info",
    "sd_get_capabilities",
    "sd_list_packages",
    "sd_get_active_graph",
    "sd_list_graph_nodes",
    "sd_get_selection",
    "sd_get_node",
    "sd_list_node_properties",
    "sd_search_library",
    "sd_create_node",
    "sd_create_instance_node",
    "sd_move_nodes",
    "sd_delete_nodes",
    "sd_connect_nodes",
    "sd_disconnect_nodes",
    "sd_set_node_parameter",
    "sd_save_package",
    "sd_create_package",
    "sd_create_graph",
    "sd_list_node_definitions",
    "sd_get_graph_snapshot",
    "sd_open_graph",
    "sd_create_graph_output",
    "sd_save_package_as",
    "sd_validate_graph_patch",
    "sd_apply_graph_patch",
    "sd_import_bitmap",
    "sd_export_package_sbsar",
}


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], bool]] = []

    def call(
        self, command: str, arguments: dict[str, Any], *, write: bool = False
    ) -> dict[str, Any]:
        self.calls.append((command, arguments, write))
        return {"command": command, "arguments": arguments}


class OfflineClient:
    def call(
        self, command: str, arguments: dict[str, Any], *, write: bool = False
    ) -> dict[str, Any]:
        del command, arguments, write
        raise MCPError(ErrorCode.SD_NOT_RUNNING, "No Designer session.")


def _tools(client: object) -> list[Any]:
    return asyncio.run(build_server(client).list_tools())


def _call(client: object, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = asyncio.run(build_server(client).call_tool(name, arguments))
    assert isinstance(result, tuple)
    _content, structured = result
    assert isinstance(structured, dict)
    return structured


def test_server_exposes_exact_v110_tools_with_closed_world_annotations() -> None:
    tools = _tools(RecordingClient())

    assert {tool.name for tool in tools} == TOOL_NAMES
    assert all(tool.annotations.openWorldHint is False for tool in tools)


def test_read_and_destructive_annotations_are_accurate() -> None:
    tools = {tool.name: tool for tool in _tools(RecordingClient())}

    assert tools["sd_get_active_graph"].annotations.readOnlyHint is True
    assert tools["sd_get_active_graph"].annotations.destructiveHint is False
    assert tools["sd_create_node"].annotations.readOnlyHint is False
    assert tools["sd_create_node"].annotations.destructiveHint is False
    assert tools["sd_delete_nodes"].annotations.destructiveHint is True
    assert tools["sd_save_package"].annotations.destructiveHint is True
    assert tools["sd_list_node_definitions"].annotations.readOnlyHint is True
    assert tools["sd_get_graph_snapshot"].annotations.readOnlyHint is True
    assert tools["sd_validate_graph_patch"].annotations.readOnlyHint is True
    assert tools["sd_create_package"].annotations.destructiveHint is False
    assert tools["sd_apply_graph_patch"].annotations.destructiveHint is False
    assert tools["sd_save_package_as"].annotations.destructiveHint is True
    assert tools["sd_export_package_sbsar"].annotations.destructiveHint is True


def test_tool_schemas_forbid_unknown_fields_and_require_confirmation() -> None:
    tools = {tool.name: tool for tool in _tools(RecordingClient())}

    create_schema = tools["sd_create_node"].inputSchema
    delete_schema = tools["sd_delete_nodes"].inputSchema

    assert create_schema["additionalProperties"] is False
    assert {"graph", "definition_id", "position"} <= set(create_schema["required"])
    assert "confirm" in delete_schema["required"]
    assert tools["sd_create_graph_output"].inputSchema["additionalProperties"] is False
    assert tools["sd_apply_graph_patch"].inputSchema["additionalProperties"] is False
    assert "confirm" in tools["sd_save_package_as"].inputSchema["required"]
    assert "confirm" in tools["sd_export_package_sbsar"].inputSchema["required"]


def test_create_graph_output_routes_structured_usage_metadata() -> None:
    client = RecordingClient()
    graph = {"package_url": "file:///C:/demo.sbs", "graph_identifier": "main"}

    result = _call(
        client,
        "sd_create_graph_output",
        {
            "graph": graph,
            "identifier": "basecolor",
            "label": "Base Color",
            "description": "Material base color",
            "group": "Material",
            "usages": [{"name": "baseColor", "components": "RGBA", "color_space": "sRGB"}],
            "position": [640, 0],
        },
    )

    assert result["ok"] is True
    assert client.calls[0] == (
        "sd_create_graph_output",
        {
            "graph": {**graph, "graph_type": "substance"},
            "identifier": "basecolor",
            "label": "Base Color",
            "description": "Material base color",
            "group": "Material",
            "usages": [{"name": "baseColor", "components": "RGBA", "color_space": "sRGB"}],
            "position": [640.0, 0.0],
        },
        True,
    )


def test_graph_patch_schema_is_versioned_and_forbids_nested_unknown_fields() -> None:
    client = RecordingClient()
    graph = {"package_url": "file:///C:/demo.sbs", "graph_identifier": "main"}
    patch = {
        "version": "1.0",
        "nodes": [
            {
                "alias": "source",
                "kind": "atomic",
                "definition_id": "sbs::compositing::uniform",
                "position": [0, 0],
            }
        ],
        "parameters": [],
        "connections": [],
    }

    result = _call(client, "sd_validate_graph_patch", {"graph": graph, "patch": patch})

    assert result["ok"] is True
    assert client.calls[0][0] == "sd_validate_graph_patch"
    assert client.calls[0][1]["patch"] == patch
    assert client.calls[0][2] is False

    invalid = {
        **patch,
        "nodes": [{**patch["nodes"][0], "unexpected": True}],
    }
    with pytest.raises(ToolError, match="Extra inputs are not permitted"):
        asyncio.run(
            build_server(client).call_tool(
                "sd_validate_graph_patch", {"graph": graph, "patch": invalid}
            )
        )


def test_write_tool_routes_only_to_bridge_client_with_structured_result() -> None:
    client = RecordingClient()
    graph = {"package_url": "file:///C:/demo.sbs", "graph_identifier": "main"}

    result = _call(
        client,
        "sd_create_node",
        {"graph": graph, "definition_id": "sbs::compositing::uniform", "position": [0, 0]},
    )

    assert result["ok"] is True
    assert client.calls == [
        (
            "sd_create_node",
            {
                "graph": {**graph, "graph_type": "substance"},
                "definition_id": "sbs::compositing::uniform",
                "position": [0.0, 0.0],
            },
            True,
        )
    ]


def test_offline_tool_returns_structured_sd_not_running() -> None:
    result = _call(OfflineClient(), "sd_get_active_graph", {})

    assert result == {
        "ok": False,
        "error": {
            "code": "SD_NOT_RUNNING",
            "message": "No Designer session.",
            "details": {},
        },
        "warnings": [],
    }


def test_ping_reports_external_server_even_when_designer_is_offline() -> None:
    result = _call(OfflineClient(), "sd_ping", {})

    assert result["ok"] is False
    assert result["data"] == {
        "mcp_server_running": True,
        "bridge_connected": False,
        "plugin_running": False,
    }
