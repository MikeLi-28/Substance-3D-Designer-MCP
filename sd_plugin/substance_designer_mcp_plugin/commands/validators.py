"""Pure validation helpers shared by command registrations."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Set

from ..errors import ErrorCode, PluginError


def require_keys(
    arguments: Mapping[str, Any], *, required: Set[str], optional: Set[str]
) -> Dict[str, Any]:
    """Reject missing required fields and unknown fields."""

    keys = set(arguments)
    missing = sorted(required - keys)
    unknown = sorted(keys - required - optional)
    if missing or unknown:
        raise PluginError(
            ErrorCode.INVALID_PARAMETER,
            "Command arguments do not match the schema.",
            {"missing": missing, "unknown": unknown},
        )
    return dict(arguments)


def validate_position(value: Any) -> List[float]:
    """Validate a finite two-dimensional graph coordinate."""

    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise PluginError(ErrorCode.INVALID_PARAMETER, "Position must contain two numbers.")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise PluginError(ErrorCode.INVALID_PARAMETER, "Position must contain two numbers.")
    result = [float(value[0]), float(value[1])]
    if not all(math.isfinite(item) for item in result):
        raise PluginError(ErrorCode.INVALID_PARAMETER, "Position values must be finite.")
    return result


def validate_node_identifiers(value: Any, maximum: int = 100) -> List[str]:
    """Validate a non-empty bounded list of node identifiers."""

    if not isinstance(value, list) or not 1 <= len(value) <= maximum:
        raise PluginError(
            ErrorCode.INVALID_PARAMETER,
            "Node identifiers must be a non-empty bounded list.",
        )
    if any(not isinstance(item, str) or not item for item in value):
        raise PluginError(ErrorCode.INVALID_PARAMETER, "Every node identifier must be non-empty.")
    return list(value)


def require_string(value: Any, name: str, *, allow_empty: bool = False) -> str:
    """Validate one string field, non-empty unless explicitly allowed."""

    if not isinstance(value, str) or (not allow_empty and not value):
        requirement = "a string" if allow_empty else "a non-empty string"
        raise PluginError(ErrorCode.INVALID_PARAMETER, f"{name} must be {requirement}.")
    return value


def require_mapping(value: Any, name: str) -> Dict[str, Any]:
    """Validate one object field."""

    if not isinstance(value, dict):
        raise PluginError(ErrorCode.INVALID_PARAMETER, f"{name} must be an object.")
    return dict(value)
