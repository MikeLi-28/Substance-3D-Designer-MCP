"""Allow-listed public authoring commands and strict transport validators."""

from __future__ import annotations

from typing import Any, Dict

from ..errors import ErrorCode, PluginError
from .registry import CommandRegistry
from .validators import require_keys, require_mapping, require_string, validate_position


def _bounded_int(value: Any, name: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise PluginError(
            ErrorCode.INVALID_PARAMETER,
            f"{name} must be an integer from {minimum} to {maximum}.",
        )
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise PluginError(ErrorCode.INVALID_PARAMETER, f"{name} must be a boolean.")
    return value


def _graph(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(arguments, required={"graph"}, optional=set())
    result["graph"] = require_mapping(result["graph"], "graph")
    return result


def _create_graph(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments,
        required={"package", "identifier"},
        optional={"graph_type"},
    )
    result["package"] = require_mapping(result["package"], "package")
    result["identifier"] = require_string(result["identifier"], "identifier")
    if "graph_type" in result:
        result["graph_type"] = require_string(result["graph_type"], "graph_type")
    else:
        result["graph_type"] = None
    return result


def _definitions(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments,
        required={"graph"},
        optional={"query", "offset", "limit"},
    )
    result["graph"] = require_mapping(result["graph"], "graph")
    result["query"] = require_string(result.get("query", ""), "query", allow_empty=True)
    result["offset"] = _bounded_int(result.get("offset", 0), "offset", 0, 100000)
    result["limit"] = _bounded_int(result.get("limit", 100), "limit", 1, 200)
    return result


def _snapshot(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments,
        required={"graph"},
        optional={"include_values", "limit"},
    )
    result["graph"] = require_mapping(result["graph"], "graph")
    result["include_values"] = _bool(result.get("include_values", True), "include_values")
    result["limit"] = _bounded_int(result.get("limit", 200), "limit", 1, 200)
    return result


def _output(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments,
        required={
            "graph",
            "identifier",
            "label",
            "description",
            "group",
            "usages",
            "position",
        },
        optional=set(),
    )
    result["graph"] = require_mapping(result["graph"], "graph")
    for key in ("identifier", "label", "description", "group"):
        result[key] = require_string(result[key], key, allow_empty=key in {"description", "group"})
    usages = result["usages"]
    if not isinstance(usages, list) or not 1 <= len(usages) <= 16:
        raise PluginError(ErrorCode.INVALID_PARAMETER, "usages must contain 1 to 16 objects.")
    normalized = []
    for usage in usages:
        item = require_keys(
            require_mapping(usage, "usage"),
            required={"name", "components", "color_space"},
            optional=set(),
        )
        for key in ("name", "components", "color_space"):
            item[key] = require_string(item[key], key)
        normalized.append(item)
    result["usages"] = normalized
    result["position"] = validate_position(result["position"])
    return result


def _save_as(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments,
        required={"package", "file_path", "overwrite", "confirm"},
        optional=set(),
    )
    result["package"] = require_mapping(result["package"], "package")
    result["file_path"] = require_string(result["file_path"], "file_path")
    result["overwrite"] = _bool(result["overwrite"], "overwrite")
    return result


def _patch(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(arguments, required={"graph", "patch"}, optional=set())
    result["graph"] = require_mapping(result["graph"], "graph")
    result["patch"] = require_mapping(result["patch"], "patch")
    return result


def _bitmap(arguments: Dict[str, Any]) -> Dict[str, Any]:
    result = require_keys(
        arguments,
        required={"package", "file_path", "identifier", "embed_method"},
        optional={"graph", "position"},
    )
    result["package"] = require_mapping(result["package"], "package")
    for key in ("file_path", "identifier", "embed_method"):
        result[key] = require_string(result[key], key)
    if "graph" in result:
        result["graph"] = require_mapping(result["graph"], "graph")
    if "position" in result:
        result["position"] = validate_position(result["position"])
    if ("graph" in result) != ("position" in result):
        raise PluginError(
            ErrorCode.INVALID_PARAMETER,
            "graph and position must be provided together.",
        )
    return result


def _sbsar(arguments: Dict[str, Any]) -> Dict[str, Any]:
    required = {
        "package",
        "file_path",
        "compression_mode",
        "expose_output_size",
        "expose_pixel_size",
        "expose_random_seed",
        "icon_enabled",
        "overwrite",
        "confirm",
    }
    result = require_keys(arguments, required=required, optional=set())
    result["package"] = require_mapping(result["package"], "package")
    result["file_path"] = require_string(result["file_path"], "file_path")
    result["compression_mode"] = require_string(result["compression_mode"], "compression_mode")
    for key in required - {"package", "file_path", "compression_mode"}:
        result[key] = _bool(result[key], key)
    return result


def register_authoring_commands(registry: CommandRegistry, services: Any) -> None:
    registry.register(
        "sd_create_package",
        lambda _args: services.authoring.create_package(),
        validator=lambda args: require_keys(args, required=set(), optional=set()),
        write=True,
    )
    registry.register(
        "sd_create_graph",
        lambda args: services.authoring.create_graph(
            args["package"], args["identifier"], args["graph_type"]
        ),
        validator=_create_graph,
        write=True,
    )
    registry.register(
        "sd_list_node_definitions",
        lambda args: services.authoring.list_definitions(
            args["graph"], query=args["query"], offset=args["offset"], limit=args["limit"]
        ),
        validator=_definitions,
    )
    registry.register(
        "sd_get_graph_snapshot",
        lambda args: services.authoring.snapshot(
            args["graph"], include_values=args["include_values"], limit=args["limit"]
        ),
        validator=_snapshot,
    )
    registry.register(
        "sd_open_graph",
        lambda args: services.authoring.open_graph(args["graph"]),
        validator=_graph,
        write=True,
    )
    registry.register(
        "sd_create_graph_output",
        lambda args: services.authoring.create_output(
            args["graph"],
            args["identifier"],
            args["label"],
            args["description"],
            args["group"],
            args["usages"],
            args["position"],
        ),
        validator=_output,
        write=True,
    )
    registry.register(
        "sd_save_package_as",
        lambda args: services.package.save_as(
            args["package"], args["file_path"], args["overwrite"]
        ),
        validator=_save_as,
        write=True,
        destructive=True,
    )
    registry.register(
        "sd_validate_graph_patch",
        lambda args: services.patch.validate(args["graph"], args["patch"]),
        validator=_patch,
    )
    registry.register(
        "sd_apply_graph_patch",
        lambda args: services.patch.apply(args["graph"], args["patch"]),
        validator=_patch,
        write=True,
    )
    registry.register(
        "sd_import_bitmap",
        lambda args: services.delivery.import_bitmap(args),
        validator=_bitmap,
        write=True,
    )
    registry.register(
        "sd_export_package_sbsar",
        lambda args: services.delivery.export_sbsar(args),
        validator=_sbsar,
        write=True,
        destructive=True,
    )
