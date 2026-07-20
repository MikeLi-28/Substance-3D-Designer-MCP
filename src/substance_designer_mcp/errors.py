"""Stable public error codes and sanitized exceptions."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    SD_NOT_RUNNING = "SD_NOT_RUNNING"
    BRIDGE_NOT_AVAILABLE = "BRIDGE_NOT_AVAILABLE"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    PROTOCOL_VERSION_MISMATCH = "PROTOCOL_VERSION_MISMATCH"
    REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"
    REQUEST_TIMEOUT = "REQUEST_TIMEOUT"
    UNSUPPORTED_DESIGNER_VERSION = "UNSUPPORTED_DESIGNER_VERSION"
    UNSUPPORTED_CAPABILITY = "UNSUPPORTED_CAPABILITY"
    NO_ACTIVE_PACKAGE = "NO_ACTIVE_PACKAGE"
    NO_ACTIVE_GRAPH = "NO_ACTIVE_GRAPH"
    GRAPH_NOT_EDITABLE = "GRAPH_NOT_EDITABLE"
    PACKAGE_NOT_FOUND = "PACKAGE_NOT_FOUND"
    GRAPH_NOT_FOUND = "GRAPH_NOT_FOUND"
    NODE_NOT_FOUND = "NODE_NOT_FOUND"
    NODE_DEFINITION_NOT_FOUND = "NODE_DEFINITION_NOT_FOUND"
    LIBRARY_RESOURCE_NOT_FOUND = "LIBRARY_RESOURCE_NOT_FOUND"
    PROPERTY_NOT_FOUND = "PROPERTY_NOT_FOUND"
    INVALID_PROPERTY_DIRECTION = "INVALID_PROPERTY_DIRECTION"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    INVALID_PARAMETER_TYPE = "INVALID_PARAMETER_TYPE"
    CONNECTION_NOT_ALLOWED = "CONNECTION_NOT_ALLOWED"
    CONNECTION_ALREADY_EXISTS = "CONNECTION_ALREADY_EXISTS"
    DESTRUCTIVE_CONFIRMATION_REQUIRED = "DESTRUCTIVE_CONFIRMATION_REQUIRED"
    SAVE_FAILED = "SAVE_FAILED"
    SD_API_ERROR = "SD_API_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class MCPError(Exception):
    """An expected failure safe to serialize to the MCP host."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        """Return the public error payload without internal diagnostics."""

        return {"code": self.code.value, "message": self.message, "details": self.details}
