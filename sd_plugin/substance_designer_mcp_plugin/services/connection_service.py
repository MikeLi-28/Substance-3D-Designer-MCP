"""Validated property connection creation and removal."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Set

from ..errors import ErrorCode, PluginError
from .common import iter_api_array
from .resource_resolver import ResourceResolver


class ConnectionService:
    def __init__(self, resolver: ResourceResolver, adapter: Any) -> None:
        self.resolver = resolver
        self.adapter = adapter

    @staticmethod
    def _type_ids(prop: Any) -> Set[str]:
        types = list(iter_api_array(prop.getTypes()))
        if not types and prop.getType() is not None:
            types = [prop.getType()]
        return {str(item.getId()) for item in types}

    def _endpoints(
        self,
        graph_ref: Mapping[str, Any],
        source_id: str,
        output_id: str,
        target_id: str,
        input_id: str,
    ) -> tuple[Any, Any, Any, Any, Any]:
        graph = self.resolver.resolve_graph(graph_ref)
        source = graph.getNodeFromId(source_id)
        target = graph.getNodeFromId(target_id)
        if source is None or target is None:
            raise PluginError(ErrorCode.NODE_NOT_FOUND, "A connection endpoint was not found.")
        output = source.getPropertyFromId(output_id, self.adapter.OUTPUT)
        input_property = target.getPropertyFromId(input_id, self.adapter.INPUT)
        if output is None or input_property is None:
            raise PluginError(ErrorCode.PROPERTY_NOT_FOUND, "A connection property was not found.")
        if not output.isConnectable() or not input_property.isConnectable():
            raise PluginError(
                ErrorCode.INVALID_PROPERTY_DIRECTION,
                "Both connection properties must be connectable.",
            )
        if not self._type_ids(output).intersection(self._type_ids(input_property)):
            raise PluginError(ErrorCode.CONNECTION_NOT_ALLOWED, "Property types are incompatible.")
        return graph, source, output, target, input_property

    @staticmethod
    def _matches(connection: Any, target: Any, input_property: Any) -> bool:
        connection_target = connection.getInputPropertyNode()
        connection_input = connection.getInputProperty()
        return (
            not getattr(connection, "disconnected", False)
            and connection_target is not None
            and connection_input is not None
            and connection_target.getIdentifier() == target.getIdentifier()
            and connection_input.getId() == input_property.getId()
        )

    def connect(
        self,
        graph_ref: Mapping[str, Any],
        source_id: str,
        output_id: str,
        target_id: str,
        input_id: str,
    ) -> Dict[str, Any]:
        _graph, source, output, target, input_property = self._endpoints(
            graph_ref, source_id, output_id, target_id, input_id
        )
        if any(
            self._matches(connection, target, input_property)
            for connection in iter_api_array(source.getPropertyConnections(output))
        ):
            raise PluginError(ErrorCode.CONNECTION_ALREADY_EXISTS, "The connection already exists.")
        source.newPropertyConnection(output, target, input_property)
        return {
            "connection": {
                "source_node": source_id,
                "source_property": output_id,
                "target_node": target_id,
                "target_property": input_id,
            }
        }

    def disconnect(
        self,
        graph_ref: Mapping[str, Any],
        source_id: str,
        output_id: str,
        target_id: str,
        input_id: str,
    ) -> Dict[str, Any]:
        _graph, source, output, target, input_property = self._endpoints(
            graph_ref, source_id, output_id, target_id, input_id
        )
        for connection in iter_api_array(source.getPropertyConnections(output)):
            if self._matches(connection, target, input_property):
                connection.disconnect()
                return {"disconnected": True}
        raise PluginError(ErrorCode.CONNECTION_NOT_ALLOWED, "The connection does not exist.")
