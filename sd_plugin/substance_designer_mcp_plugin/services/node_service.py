"""Node reads and validated node mutations."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from ..commands.validators import validate_position
from ..errors import ErrorCode, PluginError
from .common import iter_api_array, position_to_list
from .resource_resolver import ResourceResolver, node_reference


class NodeService:
    def __init__(self, resolver: ResourceResolver, adapter: Any) -> None:
        self.resolver = resolver
        self.adapter = adapter

    def _property_data(self, node: Any, prop: Any, direction: str) -> Dict[str, Any]:
        sd_type = prop.getType()
        connections = list(iter_api_array(node.getPropertyConnections(prop)))
        value = None
        if direction == "input":
            value = self.adapter.serialize_value(node.getInputPropertyValueFromId(prop.getId()))
        return {
            "property_id": str(prop.getId()),
            "label": str(prop.getLabel()),
            "description": str(prop.getDescription()),
            "direction": direction,
            "type_id": str(sd_type.getId()) if sd_type is not None else "unknown",
            "connectable": bool(prop.isConnectable()),
            "read_only": bool(prop.isReadOnly()),
            "variadic": bool(prop.isVariadic()),
            "connected": bool(connections),
            "value": value,
        }

    def list_properties(self, reference: Mapping[str, Any]) -> Dict[str, Any]:
        graph, node = self.resolver.resolve_node(reference)
        properties = []
        for category, direction in ((self.adapter.INPUT, "input"), (self.adapter.OUTPUT, "output")):
            properties.extend(
                self._property_data(node, prop, direction)
                for prop in iter_api_array(node.getProperties(category))
            )
        return {"node": node_reference(graph, node), "properties": properties}

    def get_node(self, reference: Mapping[str, Any], detail: str = "full") -> Dict[str, Any]:
        graph, node = self.resolver.resolve_node(reference)
        result = {
            "node": node_reference(graph, node),
            "position": position_to_list(node.getPosition()),
            "detail": detail,
        }
        if detail == "full":
            result["properties"] = self.list_properties(reference)["properties"]
        return result

    def _editable_graph(self, reference: Mapping[str, Any]) -> Any:
        graph = self.resolver.resolve_graph(reference)
        if not all(callable(getattr(graph, name, None)) for name in ("newNode", "deleteNode")):
            raise PluginError(ErrorCode.GRAPH_NOT_EDITABLE, "The graph is not editable.")
        return graph

    def create_atomic(
        self, graph_ref: Mapping[str, Any], definition_id: str, position: Sequence[float]
    ) -> Dict[str, Any]:
        graph = self._editable_graph(graph_ref)
        definitions = {str(item.getId()) for item in iter_api_array(graph.getNodeDefinitions())}
        if definition_id not in definitions:
            raise PluginError(
                ErrorCode.NODE_DEFINITION_NOT_FOUND,
                "The atomic node definition is not available in this graph.",
            )
        xy = validate_position(position)
        node = graph.newNode(definition_id)
        node.setPosition(self.adapter.float2(xy[0], xy[1]))
        return {
            "node": node_reference(graph, node),
            "position": position_to_list(node.getPosition()),
        }

    def create_instance(
        self,
        graph_ref: Mapping[str, Any],
        resource_ref: Mapping[str, Any],
        position: Sequence[float],
    ) -> Dict[str, Any]:
        graph = self._editable_graph(graph_ref)
        resource = self.resolver.resolve_library(resource_ref)
        xy = validate_position(position)
        node = graph.newInstanceNode(resource)
        if node is None:
            raise PluginError(ErrorCode.SD_API_ERROR, "Designer did not create the instance node.")
        node.setPosition(self.adapter.float2(xy[0], xy[1]))
        return {
            "node": node_reference(graph, node),
            "position": position_to_list(node.getPosition()),
        }

    def move_nodes(
        self, graph_ref: Mapping[str, Any], moves: Sequence[Mapping[str, Any]]
    ) -> Dict[str, Any]:
        graph = self._editable_graph(graph_ref)
        if not 1 <= len(moves) <= 100:
            raise PluginError(ErrorCode.INVALID_PARAMETER, "moves must contain 1 to 100 items.")
        results = []
        for move in moves:
            node = graph.getNodeFromId(str(move.get("node_identifier", "")))
            if node is None:
                raise PluginError(ErrorCode.NODE_NOT_FOUND, "A node to move was not found.")
            xy = validate_position(move.get("position"))
            node.setPosition(self.adapter.float2(xy[0], xy[1]))
            results.append(
                {
                    "node": node_reference(graph, node),
                    "position": position_to_list(node.getPosition()),
                }
            )
        return {"nodes": results}

    def delete_nodes(
        self, graph_ref: Mapping[str, Any], node_identifiers: Sequence[str]
    ) -> Dict[str, Any]:
        graph = self._editable_graph(graph_ref)
        if not 1 <= len(node_identifiers) <= 100:
            raise PluginError(ErrorCode.INVALID_PARAMETER, "node_identifiers cannot be empty.")
        deleted = []
        failed = []
        for identifier in node_identifiers:
            node = graph.getNodeFromId(str(identifier))
            if node is None:
                failed.append(
                    {"node_identifier": identifier, "code": ErrorCode.NODE_NOT_FOUND.value}
                )
                continue
            summary = node_reference(graph, node)
            graph.deleteNode(node)
            deleted.append(summary)
        return {"deleted": deleted, "failed": failed}
