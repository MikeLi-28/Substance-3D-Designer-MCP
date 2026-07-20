"""Runtime-typed node parameter writes."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ..errors import ErrorCode, PluginError
from .resource_resolver import ResourceResolver, node_reference


class ParameterService:
    def __init__(self, resolver: ResourceResolver, adapter: Any) -> None:
        self.resolver = resolver
        self.adapter = adapter

    def set_parameter(
        self, node_ref: Mapping[str, Any], property_id: str, value: Any
    ) -> Dict[str, Any]:
        graph, node = self.resolver.resolve_node(node_ref)
        prop = node.getPropertyFromId(property_id, self.adapter.INPUT)
        if prop is None:
            raise PluginError(ErrorCode.PROPERTY_NOT_FOUND, "The input property was not found.")
        if prop.isReadOnly():
            raise PluginError(ErrorCode.INVALID_PARAMETER, "The input property is read-only.")
        sd_type = prop.getType()
        if sd_type is None:
            raise PluginError(
                ErrorCode.UNSUPPORTED_CAPABILITY, "The parameter type is unavailable."
            )
        type_id = str(sd_type.getId())
        before_value = node.getInputPropertyValueFromId(property_id)
        before = self.adapter.serialize_value(before_value)
        try:
            converted = self.adapter.to_sd_value(type_id, value, sd_type)
        except TypeError as exc:
            raise PluginError(
                ErrorCode.INVALID_PARAMETER_TYPE,
                "The JSON value does not match the parameter type.",
            ) from exc
        except ValueError as exc:
            raise PluginError(
                ErrorCode.UNSUPPORTED_CAPABILITY,
                "This parameter type is not supported by v1.1.0.",
                {"type_id": type_id},
            ) from exc
        node.setInputPropertyValueFromId(property_id, converted)
        after = self.adapter.serialize_value(node.getInputPropertyValueFromId(property_id))
        return {
            "node": node_reference(graph, node),
            "property_id": property_id,
            "before": before,
            "after": after,
        }
