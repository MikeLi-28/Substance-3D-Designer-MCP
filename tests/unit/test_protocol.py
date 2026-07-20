from __future__ import annotations

from uuid import UUID

import pytest

from substance_designer_mcp.bridge.protocol import (
    PROTOCOL_VERSION,
    ProtocolError,
    create_request,
    error_response,
    success_response,
    validate_request,
)


def test_create_request_supplies_uuid_and_protocol_version() -> None:
    request = create_request("sd_ping", {}, "secret")

    assert request["protocol_version"] == PROTOCOL_VERSION
    assert UUID(request["request_id"])
    assert request["command"] == "sd_ping"
    assert request["arguments"] == {}


def test_validate_request_rejects_protocol_mismatch() -> None:
    request = create_request("sd_ping", {}, "secret")
    request["protocol_version"] = "2.0"

    with pytest.raises(ProtocolError) as caught:
        validate_request(request)

    assert caught.value.code == "PROTOCOL_VERSION_MISMATCH"


def test_validate_request_rejects_non_mapping_arguments() -> None:
    request = create_request("sd_ping", {}, "secret")
    request["arguments"] = []

    with pytest.raises(ProtocolError) as caught:
        validate_request(request)

    assert caught.value.code == "INVALID_PARAMETER"


def test_success_response_is_structured() -> None:
    response = success_response("req-1", {"pong": True}, warnings=["untested"])

    assert response == {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": "req-1",
        "ok": True,
        "data": {"pong": True},
        "warnings": ["untested"],
    }


def test_error_response_is_structured_without_traceback() -> None:
    response = error_response(
        "req-2",
        "NO_ACTIVE_GRAPH",
        "No editable graph is currently active.",
        {"editable": False},
    )

    assert response["ok"] is False
    assert response["error"] == {
        "code": "NO_ACTIVE_GRAPH",
        "message": "No editable graph is currently active.",
        "details": {"editable": False},
    }
    assert "traceback" not in response["error"]
