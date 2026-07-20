"""Versioned JSON request and response envelopes."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence
from uuid import UUID, uuid4

PROTOCOL_VERSION = "1.0"


class ProtocolError(ValueError):
    """A stable protocol validation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def create_request(
    command: str,
    arguments: Mapping[str, Any],
    token: str,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a bridge request with a unique request ID."""

    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id or str(uuid4()),
        "token": token,
        "command": command,
        "arguments": dict(arguments),
    }


def validate_request(request: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate the common request envelope without authenticating it."""

    if request.get("protocol_version") != PROTOCOL_VERSION:
        raise ProtocolError("PROTOCOL_VERSION_MISMATCH", "Unsupported protocol version.")
    request_id = request.get("request_id")
    try:
        UUID(str(request_id))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ProtocolError("INVALID_PARAMETER", "request_id must be a UUID.") from exc
    if not isinstance(request.get("token"), str) or not request["token"]:
        raise ProtocolError("AUTHENTICATION_FAILED", "A session token is required.")
    if not isinstance(request.get("command"), str) or not request["command"]:
        raise ProtocolError("INVALID_PARAMETER", "command must be a non-empty string.")
    if not isinstance(request.get("arguments"), dict):
        raise ProtocolError("INVALID_PARAMETER", "arguments must be an object.")
    return dict(request)


def success_response(
    request_id: str,
    data: Mapping[str, Any],
    warnings: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """Create a successful response envelope."""

    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "ok": True,
        "data": dict(data),
        "warnings": list(warnings or []),
    }


def error_response(
    request_id: str,
    code: str,
    message: str,
    details: Optional[Mapping[str, Any]] = None,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a sanitized failure response envelope."""

    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "ok": False,
        "error": {"code": code, "message": message, "details": dict(details or {})},
        "warnings": list(warnings or []),
    }
