"""Versioned additive graph patch preflight and rollback-safe application."""

from __future__ import annotations

import re
from contextlib import suppress
from typing import Any, Dict, Mapping, Set, Tuple

from ..commands.validators import validate_position
from ..errors import ErrorCode, PluginError
from .common import iter_api_array
from .resource_resolver import ResourceResolver, node_reference

_ALIAS = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


def _keys(
    value: Any,
    name: str,
    required: Set[str],
    optional: Set[str] = None,
) -> Dict[str, Any]:
    if optional is None:
        optional = set()
    if not isinstance(value, dict):
        raise PluginError(ErrorCode.INVALID_PARAMETER, f"{name} must be an object.")
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing or unknown:
        raise PluginError(
            ErrorCode.INVALID_PARAMETER,
            f"{name} does not match the graph patch schema.",
            {"missing": sorted(missing), "unknown": sorted(unknown)},
        )
    return dict(value)


def _items(value: Any, name: str, minimum: int, maximum: int) -> list:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise PluginError(
            ErrorCode.INVALID_PARAMETER,
            f"{name} must contain {minimum} to {maximum} items.",
        )
    return value


def _alias(value: Any, name: str) -> str:
    if not isinstance(value, str) or _ALIAS.fullmatch(value) is None:
        raise PluginError(ErrorCode.INVALID_PARAMETER, f"{name} is not a valid patch alias.")
    return value


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise PluginError(ErrorCode.INVALID_PARAMETER, f"{name} must be non-empty.")
    return value


class PatchService:
    def __init__(self, resolver: ResourceResolver, adapter: Any) -> None:
        self.resolver = resolver
        self.adapter = adapter

    def _property(self, owner: Any, identifier: str, category: Any) -> Any:
        method = getattr(owner, "getPropertyFromId", None)
        if callable(method):
            return method(identifier, category)
        for prop in iter_api_array(owner.getProperties(category)):
            if str(prop.getId()) == identifier:
                return prop
        return None

    @staticmethod
    def _type_ids(prop: Any) -> Set[str]:
        values = list(iter_api_array(prop.getTypes()))
        if not values and prop.getType() is not None:
            values = [prop.getType()]
        return {str(value.getId()) for value in values}

    def _nodes(self, graph: Any, raw_nodes: Any) -> tuple[list, Dict[str, Any], Dict[str, Any]]:
        nodes = _items(raw_nodes, "patch.nodes", 1, 100)
        definitions = {
            str(definition.getId()): definition
            for definition in iter_api_array(graph.getNodeDefinitions())
        }
        normalized = []
        providers: Dict[str, Any] = {}
        resources: Dict[str, Any] = {}
        for index, raw in enumerate(nodes):
            base = _keys(
                raw,
                f"patch.nodes[{index}]",
                {"alias", "kind", "position"},
                {"definition_id", "resource"},
            )
            alias = _alias(base["alias"], f"patch.nodes[{index}].alias")
            if alias in providers:
                raise PluginError(ErrorCode.INVALID_PARAMETER, "Patch node aliases must be unique.")
            position = validate_position(base["position"])
            kind = base.get("kind")
            if kind == "atomic":
                if set(base) != {"alias", "kind", "definition_id", "position"}:
                    raise PluginError(
                        ErrorCode.INVALID_PARAMETER, "Atomic patch node fields are invalid."
                    )
                definition_id = _string(base["definition_id"], "definition_id")
                provider = definitions.get(definition_id)
                if provider is None:
                    raise PluginError(
                        ErrorCode.NODE_DEFINITION_NOT_FOUND,
                        "A patch atomic definition is not available in this graph.",
                    )
                item = {
                    "alias": alias,
                    "kind": kind,
                    "definition_id": definition_id,
                    "position": position,
                }
            elif kind == "instance":
                if set(base) != {"alias", "kind", "resource", "position"}:
                    raise PluginError(
                        ErrorCode.INVALID_PARAMETER, "Instance patch node fields are invalid."
                    )
                if not isinstance(base["resource"], dict):
                    raise PluginError(ErrorCode.INVALID_PARAMETER, "resource must be an object.")
                provider = self.resolver.resolve_library(base["resource"])
                resources[alias] = provider
                item = {
                    "alias": alias,
                    "kind": kind,
                    "resource": dict(base["resource"]),
                    "position": position,
                }
            else:
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER, "Patch node kind must be atomic or instance."
                )
            providers[alias] = provider
            normalized.append(item)
        return normalized, providers, resources

    def _parameters(self, raw: Any, providers: Mapping[str, Any]) -> list:
        parameters = _items(raw, "patch.parameters", 0, 300)
        normalized = []
        seen = set()
        for index, value in enumerate(parameters):
            item = _keys(
                value,
                f"patch.parameters[{index}]",
                {"node", "property_id", "value"},
            )
            alias = _alias(item["node"], "parameter.node")
            provider = providers.get(alias)
            if provider is None:
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER, "Parameter node alias was not found."
                )
            property_id = _string(item["property_id"], "property_id")
            key = (alias, property_id)
            if key in seen:
                raise PluginError(ErrorCode.INVALID_PARAMETER, "Patch parameters must be unique.")
            seen.add(key)
            prop = self._property(provider, property_id, self.adapter.INPUT)
            if prop is None:
                raise PluginError(ErrorCode.PROPERTY_NOT_FOUND, "A patch parameter was not found.")
            if prop.isReadOnly():
                raise PluginError(ErrorCode.INVALID_PARAMETER, "A patch parameter is read-only.")
            sd_type = prop.getType()
            try:
                self.adapter.to_sd_value(str(sd_type.getId()), item["value"], sd_type)
            except TypeError as exc:
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER_TYPE,
                    "A patch parameter JSON value has the wrong type.",
                ) from exc
            except ValueError as exc:
                raise PluginError(
                    ErrorCode.UNSUPPORTED_CAPABILITY,
                    "A patch parameter uses an unsupported SD value type.",
                ) from exc
            normalized.append({"node": alias, "property_id": property_id, "value": item["value"]})
        return normalized

    def _connections(self, raw: Any, providers: Mapping[str, Any]) -> list:
        connections = _items(raw, "patch.connections", 0, 300)
        normalized = []
        targets = set()
        edges: Dict[str, Set[str]] = {alias: set() for alias in providers}
        required = {"source_node", "source_property", "target_node", "target_property"}
        for index, value in enumerate(connections):
            item = _keys(value, f"patch.connections[{index}]", required)
            source_alias = _alias(item["source_node"], "source_node")
            target_alias = _alias(item["target_node"], "target_node")
            if source_alias not in providers or target_alias not in providers:
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER, "Connection node alias was not found."
                )
            source_id = _string(item["source_property"], "source_property")
            target_id = _string(item["target_property"], "target_property")
            output = self._property(providers[source_alias], source_id, self.adapter.OUTPUT)
            input_prop = self._property(providers[target_alias], target_id, self.adapter.INPUT)
            if output is None or input_prop is None:
                raise PluginError(
                    ErrorCode.PROPERTY_NOT_FOUND, "A patch connection port was not found."
                )
            if not output.isConnectable() or not input_prop.isConnectable():
                raise PluginError(
                    ErrorCode.INVALID_PROPERTY_DIRECTION,
                    "Patch connection ports must be connectable.",
                )
            if not self._type_ids(output).intersection(self._type_ids(input_prop)):
                raise PluginError(
                    ErrorCode.CONNECTION_NOT_ALLOWED, "Patch connection types are incompatible."
                )
            target_key = (target_alias, target_id)
            if target_key in targets:
                raise PluginError(
                    ErrorCode.CONNECTION_ALREADY_EXISTS,
                    "A patch target input can have only one incoming connection.",
                )
            targets.add(target_key)
            edges[source_alias].add(target_alias)
            normalized.append(
                {
                    "source_node": source_alias,
                    "source_property": source_id,
                    "target_node": target_alias,
                    "target_property": target_id,
                }
            )
        self._reject_cycles(edges)
        return normalized

    @staticmethod
    def _reject_cycles(edges: Mapping[str, Set[str]]) -> None:
        visiting: Set[str] = set()
        visited: Set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                raise PluginError(
                    ErrorCode.CONNECTION_NOT_ALLOWED, "Graph patches cannot contain cycles."
                )
            if node in visited:
                return
            visiting.add(node)
            for target in edges[node]:
                visit(target)
            visiting.remove(node)
            visited.add(node)

        for alias in edges:
            visit(alias)

    def _preflight(self, graph_ref: Mapping[str, Any], patch: Any) -> Tuple[Any, dict]:
        graph = self.resolver.resolve_graph(graph_ref)
        if not all(callable(getattr(graph, name, None)) for name in ("newNode", "deleteNode")):
            raise PluginError(ErrorCode.GRAPH_NOT_EDITABLE, "The graph is not editable.")
        root = _keys(
            patch,
            "patch",
            {"version", "nodes"},
            {"parameters", "connections"},
        )
        if root["version"] != "1.0":
            raise PluginError(ErrorCode.INVALID_PARAMETER, "Unsupported graph patch version.")
        nodes, providers, resources = self._nodes(graph, root["nodes"])
        parameters = self._parameters(root.get("parameters", []), providers)
        connections = self._connections(root.get("connections", []), providers)
        return graph, {
            "version": "1.0",
            "nodes": nodes,
            "parameters": parameters,
            "connections": connections,
            "resources": resources,
        }

    def validate(self, graph_ref: Mapping[str, Any], patch: Any) -> Dict[str, Any]:
        _graph, plan = self._preflight(graph_ref, patch)
        return {
            "valid": True,
            "patch_version": plan["version"],
            "node_count": len(plan["nodes"]),
            "parameter_count": len(plan["parameters"]),
            "connection_count": len(plan["connections"]),
        }

    def apply(self, graph_ref: Mapping[str, Any], patch: Any) -> Dict[str, Any]:
        graph, plan = self._preflight(graph_ref, patch)
        created: list[Any] = []
        node_map: Dict[str, Any] = {}
        try:
            with self.adapter.undo_group("Apply validated MCP graph patch"):
                for spec in plan["nodes"]:
                    if spec["kind"] == "atomic":
                        node = graph.newNode(spec["definition_id"])
                    else:
                        node = graph.newInstanceNode(plan["resources"][spec["alias"]])
                    if node is None:
                        raise RuntimeError("Designer did not create a patch node.")
                    node.setPosition(self.adapter.float2(*spec["position"]))
                    created.append(node)
                    node_map[spec["alias"]] = node
                for parameter in plan["parameters"]:
                    node = node_map[parameter["node"]]
                    prop = node.getPropertyFromId(parameter["property_id"], self.adapter.INPUT)
                    sd_type = prop.getType()
                    value = self.adapter.to_sd_value(
                        str(sd_type.getId()), parameter["value"], sd_type
                    )
                    node.setInputPropertyValueFromId(parameter["property_id"], value)
                for connection in plan["connections"]:
                    source = node_map[connection["source_node"]]
                    target = node_map[connection["target_node"]]
                    output = source.getPropertyFromId(
                        connection["source_property"], self.adapter.OUTPUT
                    )
                    input_prop = target.getPropertyFromId(
                        connection["target_property"], self.adapter.INPUT
                    )
                    source.newPropertyConnection(output, target, input_prop)
        except Exception as exc:
            rolled_back = 0
            for node in reversed(created):
                with suppress(Exception):
                    graph.deleteNode(node)
                    rolled_back += 1
            raise PluginError(
                ErrorCode.SD_API_ERROR,
                "Designer could not apply the validated graph patch; "
                "created nodes were rolled back.",
                {"rolled_back_nodes": rolled_back, "created_before_failure": len(created)},
            ) from exc
        return {
            "applied": True,
            "patch_version": plan["version"],
            "node_map": {alias: node_reference(graph, node) for alias, node in node_map.items()},
            "parameter_count": len(plan["parameters"]),
            "connection_count": len(plan["connections"]),
        }
