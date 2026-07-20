"""External FastMCP client for isolated Designer 16 real-machine verification."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional, Union

from substance_designer_mcp.bridge.client import BridgeClient
from substance_designer_mcp.server import build_server
from tests.manual.sd16_e2e_support import (
    HarnessError,
    choose_connection,
    choose_parameter,
    make_check,
    redact,
)

ExpectedError = Optional[Union[str, Sequence[str]]]


async def _call(
    server: Any,
    name: str,
    arguments: dict[str, Any],
    expected_error: ExpectedError = None,
) -> dict[str, Any]:
    _content, structured = await server.call_tool(name, arguments)
    if not isinstance(structured, Mapping):
        raise HarnessError(f"{name} returned no structured result.")
    expected = {expected_error} if isinstance(expected_error, str) else set(expected_error or ())
    if structured.get("ok") is True:
        if expected:
            raise HarnessError(f"{name} succeeded but an expected error was required.")
        data = structured.get("data")
        if not isinstance(data, Mapping):
            raise HarnessError(f"{name} returned invalid success data.")
        return dict(data)
    error = structured.get("error")
    if not isinstance(error, Mapping):
        raise HarnessError(f"{name} returned an invalid error envelope.")
    code = str(error.get("code", "INTERNAL_ERROR"))
    if code not in expected:
        raise HarnessError(f"{name} returned unexpected error {code}.")
    return dict(error)


def created_node_identifiers(results: Sequence[Mapping[str, Any]]) -> list[str]:
    identifiers = []
    for result in results:
        node = result.get("node")
        if not isinstance(node, Mapping):
            continue
        identifier = node.get("node_identifier")
        if isinstance(identifier, str) and identifier:
            identifiers.append(identifier)
    return identifiers


def _library_resource(resources: object, active_package_url: str) -> dict[str, Any]:
    if not isinstance(resources, list):
        raise HarnessError("Library search returned no resource list.")
    for resource in resources:
        if not isinstance(resource, Mapping):
            continue
        category = str(resource.get("category", ""))
        stable_key = str(resource.get("stable_key", ""))
        if resource.get("package_url") == active_package_url:
            continue
        if "graph" not in category.casefold():
            continue
        if not stable_key or "dependency=" in stable_key.casefold():
            continue
        return dict(resource)
    raise HarnessError("No stable instanceable Library graph resource was returned.")


def _invalid_connection(
    source_properties: Sequence[Mapping[str, Any]],
    target_properties: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    source_output_ids = {
        str(item["property_id"])
        for item in source_properties
        if item.get("direction") == "output" and isinstance(item.get("property_id"), str)
    }
    target_input_ids = {
        str(item["property_id"])
        for item in target_properties
        if item.get("direction") == "input" and isinstance(item.get("property_id"), str)
    }
    source_property = next(
        (
            str(item["property_id"])
            for item in source_properties
            if item.get("direction") == "input"
            and isinstance(item.get("property_id"), str)
            and str(item["property_id"]) not in source_output_ids
        ),
        "__substance_designer_mcp_missing_output__",
    )
    target_property = next(
        (
            str(item["property_id"])
            for item in target_properties
            if item.get("direction") == "output"
            and isinstance(item.get("property_id"), str)
            and str(item["property_id"]) not in target_input_ids
        ),
        "__substance_designer_mcp_missing_input__",
    )
    return {
        "source_property": source_property,
        "target_property": target_property,
    }


async def _run_snapshot(server: Any, report: dict[str, Any]) -> None:
    executed = report["executed_tools"]

    async def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        executed.append(name)
        return await _call(server, name, arguments)

    ping = await call("sd_ping", {})
    report["checks"]["mcp_connected"] = make_check(True, ping)
    graph_data = await call("sd_get_active_graph", {})
    report["checks"]["active_graph_read"] = make_check(True, graph_data)
    library = await call("sd_search_library", {"query": "blend", "limit": 50})
    resource = _library_resource(library.get("resources"), graph_data["graph"]["package_url"])
    report["library"] = {
        "stable_key": resource["stable_key"],
        "runtime_url": resource["runtime_url"],
        "resource_identifier": resource["resource_identifier"],
    }
    report["checks"]["library_search"] = make_check(True, report["library"])


async def _run_stale(server: Any, report: dict[str, Any]) -> None:
    report["executed_tools"].append("sd_ping")
    error = await _call(
        server,
        "sd_ping",
        {},
        expected_error=("SD_NOT_RUNNING", "BRIDGE_NOT_AVAILABLE"),
    )
    report["checks"]["stale_session_rejected"] = make_check(True, error)


async def _run_full(server: Any, report: dict[str, Any]) -> None:
    executed = report["executed_tools"]
    graph: Optional[dict[str, Any]] = None
    created: list[dict[str, Any]] = []

    async def call(
        name: str,
        arguments: dict[str, Any],
        expected_error: ExpectedError = None,
    ) -> dict[str, Any]:
        executed.append(name)
        return await _call(server, name, arguments, expected_error)

    try:
        ping = await call("sd_ping", {})
        report["checks"]["mcp_connected"] = make_check(True, ping)
        application = await call("sd_get_application_info", {})
        report["checks"]["application_info_read"] = make_check(True, application)
        capabilities = await call("sd_get_capabilities", {})
        report["checks"]["capabilities_read"] = make_check(True, capabilities)
        packages = await call("sd_list_packages", {})
        report["checks"]["packages_read"] = make_check(True, {"count": packages.get("count")})
        active = await call("sd_get_active_graph", {})
        graph = dict(active["graph"])
        package = dict(active["package"])
        report["checks"]["active_graph_read"] = make_check(True, active)
        nodes = await call(
            "sd_list_graph_nodes",
            {"graph": graph, "detail": "summary", "offset": 0, "limit": 50},
        )
        report["checks"]["nodes_read"] = make_check(True, {"total": nodes.get("total")})
        selection = await call("sd_get_selection", {"detail": "summary", "limit": 50})
        report["checks"]["selection_read"] = make_check(
            True, {"count": len(selection.get("nodes", []))}
        )

        uniform = await call(
            "sd_create_node",
            {
                "graph": graph,
                "definition_id": "sbs::compositing::uniform",
                "position": [0.0, 0.0],
            },
        )
        created.append(uniform)
        blend = await call(
            "sd_create_node",
            {
                "graph": graph,
                "definition_id": "sbs::compositing::blend",
                "position": [256.0, 0.0],
            },
        )
        created.append(blend)
        report["checks"]["atomic_node_created"] = make_check(
            True,
            {"nodes": created_node_identifiers((uniform, blend))},
        )

        uniform_node = dict(uniform["node"])
        blend_node = dict(blend["node"])
        node_detail = await call("sd_get_node", {"node": uniform_node, "detail": "full"})
        report["checks"]["node_read"] = make_check(True, {"node": node_detail["node"]})
        uniform_properties_data = await call("sd_list_node_properties", {"node": uniform_node})
        blend_properties_data = await call("sd_list_node_properties", {"node": blend_node})
        uniform_properties = uniform_properties_data["properties"]
        blend_properties = blend_properties_data["properties"]
        report["checks"]["properties_read"] = make_check(
            True,
            {
                "uniform": len(uniform_properties),
                "blend": len(blend_properties),
            },
        )

        moved = await call(
            "sd_move_nodes",
            {
                "graph": graph,
                "moves": [
                    {
                        "node_identifier": uniform_node["node_identifier"],
                        "position": [32.0, 64.0],
                    }
                ],
            },
        )
        report["checks"]["nodes_moved"] = make_check(True, moved)

        parameter = choose_parameter(uniform_properties)
        invalid_parameter = await call(
            "sd_set_node_parameter",
            {
                "node": uniform_node,
                "property_id": parameter["property_id"],
                "value": parameter["invalid_value"],
            },
            "INVALID_PARAMETER_TYPE",
        )
        valid_parameter = await call(
            "sd_set_node_parameter",
            {
                "node": uniform_node,
                "property_id": parameter["property_id"],
                "value": parameter["valid_value"],
            },
        )
        report["checks"]["parameter_validation"] = make_check(
            True,
            {"invalid": invalid_parameter, "valid": valid_parameter},
        )

        connection = choose_connection(uniform_properties, blend_properties)
        connection_args = {
            "graph": graph,
            "source_node": uniform_node["node_identifier"],
            "source_property": connection["source_property"],
            "target_node": blend_node["node_identifier"],
            "target_property": connection["target_property"],
        }
        connected = await call("sd_connect_nodes", connection_args)
        duplicate = await call("sd_connect_nodes", connection_args, "CONNECTION_ALREADY_EXISTS")
        disconnected = await call("sd_disconnect_nodes", connection_args)
        report["checks"]["connection_roundtrip"] = make_check(
            True,
            {"connected": connected, "duplicate": duplicate, "disconnected": disconnected},
        )
        invalid = _invalid_connection(blend_properties, uniform_properties)
        invalid_args = {
            "graph": graph,
            "source_node": blend_node["node_identifier"],
            "source_property": invalid["source_property"],
            "target_node": uniform_node["node_identifier"],
            "target_property": invalid["target_property"],
        }
        invalid_error = await call(
            "sd_connect_nodes",
            invalid_args,
            ("PROPERTY_NOT_FOUND", "INVALID_PROPERTY_DIRECTION"),
        )
        report["checks"]["invalid_connection_rejected"] = make_check(True, invalid_error)

        library = await call("sd_search_library", {"query": "blend", "limit": 50})
        resource = _library_resource(library.get("resources"), graph["package_url"])
        report["checks"]["library_search"] = make_check(
            True,
            {
                "stable_key": resource["stable_key"],
                "runtime_url": resource["runtime_url"],
            },
        )
        report["library"] = {
            "stable_key": resource["stable_key"],
            "runtime_url": resource["runtime_url"],
            "resource_identifier": resource["resource_identifier"],
        }
        instance = await call(
            "sd_create_instance_node",
            {"graph": graph, "resource": resource, "position": [512.0, 0.0]},
        )
        created.append(instance)
        report["checks"]["instance_node_created"] = make_check(True, instance)

        identifiers = created_node_identifiers(created)
        delete_args = {"graph": graph, "node_identifiers": identifiers}
        delete_rejected = await call(
            "sd_delete_nodes",
            {**delete_args, "confirm": False},
            "DESTRUCTIVE_CONFIRMATION_REQUIRED",
        )
        deleted = await call("sd_delete_nodes", {**delete_args, "confirm": True})
        created.clear()
        report["checks"]["delete_confirmation"] = make_check(
            True,
            {"rejected": delete_rejected, "deleted": deleted},
        )

        save_rejected = await call(
            "sd_save_package",
            {"package": package, "confirm": False},
            "DESTRUCTIVE_CONFIRMATION_REQUIRED",
        )
        saved = await call("sd_save_package", {"package": package, "confirm": True})
        report["checks"]["save_confirmation"] = make_check(
            True,
            {"rejected": save_rejected, "saved": saved},
        )
    finally:
        identifiers = created_node_identifiers(created)
        if graph is not None and identifiers:
            try:
                await call(
                    "sd_delete_nodes",
                    {"graph": graph, "node_identifiers": identifiers, "confirm": True},
                )
                report["cleanup"] = {"deleted_test_nodes": identifiers}
            except BaseException as exc:
                report["cleanup"] = {"error": {"type": type(exc).__name__, "message": str(exc)}}


async def _execute(mode: str, session_path: Path) -> dict[str, Any]:
    report: dict[str, Any] = {"phase": mode, "checks": {}, "executed_tools": []}
    server = build_server(BridgeClient(session_path=session_path))
    try:
        if mode == "full":
            await _run_full(server, report)
        elif mode == "snapshot":
            await _run_snapshot(server, report)
        elif mode == "stale":
            await _run_stale(server, report)
        else:
            raise HarnessError(f"Unsupported client mode: {mode}")
    except BaseException as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    return report


def main() -> int:
    mode = os.getenv("SUBSTANCE_DESIGNER_MCP_CLIENT_MODE", "full")
    session_path = Path(os.environ["SUBSTANCE_DESIGNER_MCP_SESSION_PATH"])
    report_path = Path(os.environ["SUBSTANCE_DESIGNER_MCP_CLIENT_REPORT"])
    done_value = os.getenv("SUBSTANCE_DESIGNER_MCP_DONE_PATH")
    workspace = os.getenv("SUBSTANCE_DESIGNER_MCP_E2E_WORKSPACE", "")
    try:
        report = asyncio.run(_execute(mode, session_path))
        cleaned = redact(report, secrets=set(), workspace=workspace)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(cleaned, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return 0 if "error" not in report else 1
    finally:
        if done_value:
            done_path = Path(done_value)
            done_path.parent.mkdir(parents=True, exist_ok=True)
            done_path.write_text("done\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
