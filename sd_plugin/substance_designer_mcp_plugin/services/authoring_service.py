"""Generic package, graph, definition, snapshot, and output authoring."""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional, Sequence

from ..commands.validators import validate_position
from ..errors import ErrorCode, PluginError
from .common import iter_api_array, position_to_list
from .resource_resolver import (
    ResourceResolver,
    graph_reference,
    node_reference,
    package_reference,
)

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,127}$")


class AuthoringService:
    def __init__(
        self,
        application: Any,
        resolver: ResourceResolver,
        node_service: Any,
        adapter: Any,
    ) -> None:
        self.application = application
        self.resolver = resolver
        self.node_service = node_service
        self.adapter = adapter

    @staticmethod
    def _identifier(value: str, name: str = "identifier") -> str:
        if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                f"{name} must be a portable identifier without spaces.",
            )
        return value

    def create_package(self) -> Dict[str, Any]:
        package = self.resolver.package_mgr.newUserPackage()
        if package is None:
            raise PluginError(ErrorCode.SD_API_ERROR, "Designer did not create the package.")
        return {"package": package_reference(package), "saved": False}

    def create_graph(
        self,
        package_ref: Mapping[str, Any],
        identifier: str,
        graph_type: Optional[str],
    ) -> Dict[str, Any]:
        package = self.resolver.resolve_package(package_ref)
        clean_identifier = self._identifier(identifier)
        for resource in self.resolver.resources(package):
            if str(resource.getIdentifier()) == clean_identifier:
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER,
                    "The package already contains that resource identifier.",
                )
        graph = self.adapter.new_compositing_graph(package)
        graph.setIdentifier(clean_identifier)
        if graph_type is not None:
            supported = self.adapter.supported_graph_types(graph)
            if graph_type not in supported:
                graph.delete()
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER,
                    "The requested graph type is not supported by this Designer runtime.",
                    {"supported_graph_types": supported},
                )
            graph.setGraphType(graph_type)
        return {"graph": graph_reference(graph), "package": package_reference(package)}

    def list_definitions(
        self,
        graph_ref: Mapping[str, Any],
        *,
        query: str,
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        graph = self.resolver.resolve_graph(graph_ref)
        needle = query.casefold()
        definitions = []
        for definition in iter_api_array(graph.getNodeDefinitions()):
            item = {
                "definition_id": str(definition.getId()),
                "label": str(definition.getLabel()),
                "description": str(definition.getDescription()),
            }
            searchable = "{} {} {}".format(*tuple(item.values()))
            if needle and needle not in searchable.casefold():
                continue
            definitions.append(item)
        definitions.sort(key=lambda item: (item["label"].casefold(), item["definition_id"]))
        page = definitions[offset : offset + limit]
        return {
            "definitions": page,
            "query": query,
            "offset": offset,
            "limit": limit,
            "total": len(definitions),
            "truncated": offset + limit < len(definitions),
        }

    def _graph_properties(self, graph: Any, include_values: bool) -> tuple[list, list]:
        result: Dict[str, list] = {"input": [], "output": []}
        for category, direction in (
            (self.adapter.INPUT, "input"),
            (self.adapter.OUTPUT, "output"),
        ):
            for prop in iter_api_array(graph.getProperties(category)):
                item = {
                    "property_id": str(prop.getId()),
                    "label": str(prop.getLabel()),
                    "description": str(prop.getDescription()),
                    "type_id": str(prop.getType().getId()),
                }
                if include_values:
                    value = graph.getPropertyValueFromId(prop.getId(), category)
                    item["value"] = self.adapter.serialize_value(value)
                result[direction].append(item)
        return result["input"], result["output"]

    def _connections(self, nodes: Sequence[Any]) -> list[Dict[str, str]]:
        connections = []
        seen = set()
        selected_ids = {str(node.getIdentifier()) for node in nodes}
        for node in nodes:
            for prop in iter_api_array(node.getProperties(self.adapter.OUTPUT)):
                for connection in iter_api_array(node.getPropertyConnections(prop)):
                    target = connection.getInputPropertyNode()
                    input_prop = connection.getInputProperty()
                    output_prop = connection.getOutputProperty()
                    if target is None or input_prop is None or output_prop is None:
                        continue
                    if str(target.getIdentifier()) not in selected_ids:
                        continue
                    item = {
                        "source_node": str(node.getIdentifier()),
                        "source_property": str(output_prop.getId()),
                        "target_node": str(target.getIdentifier()),
                        "target_property": str(input_prop.getId()),
                    }
                    key = tuple(item.values())
                    if key not in seen:
                        seen.add(key)
                        connections.append(item)
        return connections

    def _presets(self, graph: Any, include_values: bool) -> list[Dict[str, Any]]:
        presets = []
        get_presets = getattr(graph, "getPresets", None)
        if not callable(get_presets):
            return presets
        for preset in iter_api_array(get_presets()):
            inputs = []
            for item in iter_api_array(preset.getInputs()):
                value = self.adapter.serialize_value(item.getValue()) if include_values else None
                entry = {"identifier": str(item.getIdentifier())}
                if include_values:
                    entry["value"] = value
                inputs.append(entry)
            presets.append(
                {
                    "label": str(preset.getLabel()),
                    "user_tags": str(preset.getUserTags()),
                    "inputs": inputs,
                }
            )
        return presets

    def snapshot(
        self, graph_ref: Mapping[str, Any], *, include_values: bool, limit: int
    ) -> Dict[str, Any]:
        graph = self.resolver.resolve_graph(graph_ref)
        all_nodes = list(iter_api_array(graph.getNodes()))
        selected = all_nodes[:limit]
        nodes = []
        for node in selected:
            item = {
                "node": node_reference(graph, node),
                "position": position_to_list(node.getPosition()),
                "properties": self.node_service.list_properties(node_reference(graph, node))[
                    "properties"
                ],
            }
            if not include_values:
                for prop in item["properties"]:
                    prop.pop("value", None)
            nodes.append(item)
        graph_inputs, graph_outputs = self._graph_properties(graph, include_values)
        return {
            "schema_version": "1.0",
            "graph": graph_reference(graph),
            "nodes": nodes,
            "connections": self._connections(selected),
            "graph_inputs": graph_inputs,
            "graph_outputs": graph_outputs,
            "presets": self._presets(graph, include_values),
            "limit": limit,
            "total_nodes": len(all_nodes),
            "truncated": len(all_nodes) > limit,
        }

    def open_graph(self, graph_ref: Mapping[str, Any]) -> Dict[str, Any]:
        graph = self.resolver.resolve_graph(graph_ref)
        ui_mgr = self.application.getUIMgr()
        if ui_mgr is None or not callable(getattr(ui_mgr, "openResourceInEditor", None)):
            raise PluginError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "This Designer runtime cannot open a resource in the editor.",
            )
        ui_mgr.openResourceInEditor(graph)
        return {"opened": True, "graph": graph_reference(graph)}

    def create_output(
        self,
        graph_ref: Mapping[str, Any],
        identifier: str,
        label: str,
        description: str,
        group: str,
        usages: Sequence[Mapping[str, str]],
        position: Sequence[float],
    ) -> Dict[str, Any]:
        graph = self.resolver.resolve_graph(graph_ref)
        clean_identifier = self._identifier(identifier)
        for value, name, allow_empty in (
            (label, "label", False),
            (description, "description", True),
            (group, "group", True),
        ):
            if not isinstance(value, str) or (not allow_empty and not value):
                raise PluginError(ErrorCode.INVALID_PARAMETER, f"{name} is invalid.")
        if not isinstance(usages, (list, tuple)) or not 1 <= len(usages) <= 16:
            raise PluginError(ErrorCode.INVALID_PARAMETER, "usages must contain 1 to 16 objects.")
        normalized_usages = []
        required_usage_keys = {"name", "components", "color_space"}
        for usage in usages:
            if not isinstance(usage, dict) or set(usage) != required_usage_keys:
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER, "Each usage must match the usage schema."
                )
            if any(
                not isinstance(usage[key], str) or not usage[key] for key in required_usage_keys
            ):
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER, "Output usage values must be non-empty strings."
                )
            normalized_usages.append(dict(usage))
        xy = validate_position(position)
        for node in iter_api_array(graph.getNodes()):
            value = node.getAnnotationPropertyValueFromId("identifier")
            if value is not None and str(value.get()) == clean_identifier:
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER, "The output identifier already exists."
                )
        annotation_values = {
            "identifier": self.adapter.string_value(clean_identifier),
            "label": self.adapter.string_value(label),
            "description": self.adapter.string_value(description),
            "group": self.adapter.string_value(group),
            "usages": self.adapter.usage_array(normalized_usages),
        }
        node = None
        try:
            with self.adapter.undo_group("Create MCP graph output"):
                node = graph.newNode("sbs::compositing::output")
                node.setPosition(self.adapter.float2(xy[0], xy[1]))
                for key, value in annotation_values.items():
                    node.setAnnotationPropertyValueFromId(key, value)
        except Exception as exc:
            if node is not None:
                graph.deleteNode(node)
            raise PluginError(
                ErrorCode.SD_API_ERROR, "Designer could not create the graph output."
            ) from exc
        return {
            "node": node_reference(graph, node),
            "position": position_to_list(node.getPosition()),
            "identifier": clean_identifier,
        }
