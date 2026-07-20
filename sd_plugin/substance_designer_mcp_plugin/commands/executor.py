"""Map the fixed v1.1.0 command surface to focused application services."""

from __future__ import annotations

import os
from typing import Any, Dict

from ..bridge.protocol import PROTOCOL_VERSION
from ..errors import ErrorCode, PluginError
from .authoring import register_authoring_commands
from .registry import CommandRegistry
from .validators import (
    require_keys,
    require_mapping,
    require_string,
    validate_node_identifiers,
    validate_position,
)


def _empty(arguments: Dict[str, Any]) -> Dict[str, Any]:
    return require_keys(arguments, required=set(), optional=set())


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise PluginError(
            ErrorCode.INVALID_PARAMETER,
            f"{name} must be an integer from {minimum} to {maximum}.",
        )
    return value


def _detail(value: Any) -> str:
    if value not in {"summary", "full"}:
        raise PluginError(ErrorCode.INVALID_PARAMETER, "detail must be summary or full.")
    return str(value)


def _list_nodes(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments,
        required={"graph"},
        optional={"detail", "offset", "limit"},
    )
    result["graph"] = require_mapping(result["graph"], "graph")
    result["detail"] = _detail(result.get("detail", "summary"))
    result["offset"] = _bounded_int(result.get("offset", 0), "offset", 0, 100000)
    result["limit"] = _bounded_int(result.get("limit", 50), "limit", 1, 200)
    return result


def _selection(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(arguments, required=set(), optional={"detail", "limit"})
    result["detail"] = _detail(result.get("detail", "summary"))
    result["limit"] = _bounded_int(result.get("limit", 100), "limit", 1, 200)
    return result


def _node_read(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(arguments, required={"node"}, optional={"detail"})
    result["node"] = require_mapping(result["node"], "node")
    result["detail"] = _detail(result.get("detail", "full"))
    return result


def _node_properties(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(arguments, required={"node"}, optional=set())
    result["node"] = require_mapping(result["node"], "node")
    return result


def _search(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments,
        required=set(),
        optional={"query", "identifier", "category", "limit"},
    )
    query = result.get("identifier", result.get("query", ""))
    if not isinstance(query, str):
        raise PluginError(ErrorCode.INVALID_PARAMETER, "query must be a string.")
    category = result.get("category")
    if category is not None and not isinstance(category, str):
        raise PluginError(ErrorCode.INVALID_PARAMETER, "category must be a string.")
    result["query"] = query
    result["category"] = category
    result["limit"] = _bounded_int(result.get("limit", 50), "limit", 1, 200)
    return result


def _create_node(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments, required={"graph", "definition_id", "position"}, optional=set()
    )
    result["graph"] = require_mapping(result["graph"], "graph")
    result["definition_id"] = require_string(result["definition_id"], "definition_id")
    result["position"] = validate_position(result["position"])
    return result


def _create_instance(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(arguments, required={"graph", "resource", "position"}, optional=set())
    result["graph"] = require_mapping(result["graph"], "graph")
    result["resource"] = require_mapping(result["resource"], "resource")
    result["position"] = validate_position(result["position"])
    return result


def _move_nodes(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(arguments, required={"graph", "moves"}, optional=set())
    result["graph"] = require_mapping(result["graph"], "graph")
    moves = result["moves"]
    if not isinstance(moves, list) or not 1 <= len(moves) <= 100:
        raise PluginError(ErrorCode.INVALID_PARAMETER, "moves must contain 1 to 100 objects.")
    normalized = []
    for move in moves:
        item = require_keys(
            require_mapping(move, "move"),
            required={"node_identifier", "position"},
            optional=set(),
        )
        item["node_identifier"] = require_string(item["node_identifier"], "node_identifier")
        item["position"] = validate_position(item["position"])
        normalized.append(item)
    result["moves"] = normalized
    return result


def _delete_nodes(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments, required={"graph", "node_identifiers", "confirm"}, optional=set()
    )
    result["graph"] = require_mapping(result["graph"], "graph")
    result["node_identifiers"] = validate_node_identifiers(result["node_identifiers"])
    return result


def _connection(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments,
        required={
            "graph",
            "source_node",
            "source_property",
            "target_node",
            "target_property",
        },
        optional=set(),
    )
    result["graph"] = require_mapping(result["graph"], "graph")
    for key in ("source_node", "source_property", "target_node", "target_property"):
        result[key] = require_string(result[key], key)
    return result


def _parameter(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(arguments, required={"node", "property_id", "value"}, optional=set())
    result["node"] = require_mapping(result["node"], "node")
    result["property_id"] = require_string(result["property_id"], "property_id")
    return result


def _save(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(arguments, required={"package", "confirm"}, optional=set())
    result["package"] = require_mapping(result["package"], "package")
    return result


class CommandExecutor:
    def __init__(self, registry: CommandRegistry) -> None:
        self.registry = registry

    def execute(self, command: str, arguments: Dict[str, Any]) -> Any:
        return self.registry.execute(command, arguments)

    def names(self) -> list[str]:
        return self.registry.names()


def build_command_executor(services: Any, plugin_version: str = "1.1.0") -> CommandExecutor:
    """Register the complete fixed v1.1.0 command surface."""

    registry = CommandRegistry()

    def ping(_arguments: Dict[str, Any]) -> Dict[str, Any]:
        compatibility = services.application.get_capabilities()
        return {
            "mcp_server_running": True,
            "bridge_connected": True,
            "plugin_running": True,
            "designer_version": compatibility["designer_version"],
            "plugin_version": plugin_version,
            "protocol_version": PROTOCOL_VERSION,
            "session_pid": os.getpid(),
            "verification_status": compatibility["verification_status"],
            "compatibility_status": compatibility["compatibility_status"],
            "verified_versions": compatibility["verified_versions"],
            "warning": compatibility["warning"],
        }

    registry.register("sd_ping", ping, validator=_empty)
    registry.register(
        "sd_get_application_info", lambda _args: services.application.get_info(), validator=_empty
    )
    registry.register(
        "sd_get_capabilities",
        lambda _args: services.application.get_capabilities(),
        validator=_empty,
    )
    registry.register(
        "sd_list_packages", lambda _args: services.package.list_packages(), validator=_empty
    )
    registry.register(
        "sd_get_active_graph", lambda _args: services.graph.get_active_graph(), validator=_empty
    )
    registry.register(
        "sd_list_graph_nodes",
        lambda args: services.graph.list_nodes(
            args["graph"], detail=args["detail"], offset=args["offset"], limit=args["limit"]
        ),
        validator=_list_nodes,
    )
    registry.register(
        "sd_get_selection",
        lambda args: services.selection.get_selection(args["limit"]),
        validator=_selection,
    )
    registry.register(
        "sd_get_node",
        lambda args: services.node.get_node(args["node"], args["detail"]),
        validator=_node_read,
    )
    registry.register(
        "sd_list_node_properties",
        lambda args: services.node.list_properties(args["node"]),
        validator=_node_properties,
    )
    registry.register(
        "sd_search_library",
        lambda args: services.library.search(args["query"], args["category"], args["limit"]),
        validator=_search,
    )
    registry.register(
        "sd_create_node",
        lambda args: services.node.create_atomic(
            args["graph"], args["definition_id"], args["position"]
        ),
        validator=_create_node,
        write=True,
    )
    registry.register(
        "sd_create_instance_node",
        lambda args: services.node.create_instance(
            args["graph"], args["resource"], args["position"]
        ),
        validator=_create_instance,
        write=True,
    )
    registry.register(
        "sd_move_nodes",
        lambda args: services.node.move_nodes(args["graph"], args["moves"]),
        validator=_move_nodes,
        write=True,
    )
    registry.register(
        "sd_delete_nodes",
        lambda args: services.node.delete_nodes(args["graph"], args["node_identifiers"]),
        validator=_delete_nodes,
        write=True,
        destructive=True,
    )
    registry.register(
        "sd_connect_nodes",
        lambda args: services.connection.connect(
            args["graph"],
            args["source_node"],
            args["source_property"],
            args["target_node"],
            args["target_property"],
        ),
        validator=_connection,
        write=True,
    )
    registry.register(
        "sd_disconnect_nodes",
        lambda args: services.connection.disconnect(
            args["graph"],
            args["source_node"],
            args["source_property"],
            args["target_node"],
            args["target_property"],
        ),
        validator=_connection,
        write=True,
    )
    registry.register(
        "sd_set_node_parameter",
        lambda args: services.parameter.set_parameter(
            args["node"], args["property_id"], args["value"]
        ),
        validator=_parameter,
        write=True,
    )
    registry.register(
        "sd_save_package",
        lambda args: services.package.save(args["package"]),
        validator=_save,
        write=True,
        destructive=True,
    )
    register_authoring_commands(registry, services)
    return CommandExecutor(registry)
