from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from substance_designer_mcp.bridge.protocol import create_request, error_response, success_response

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "docs" / "schemas"


def _schema(name: str) -> dict[str, object]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def test_request_schema_accepts_protocol_request() -> None:
    validator = Draft202012Validator(_schema("bridge-request.schema.json"))

    assert list(validator.iter_errors(create_request("sd_ping", {}, "secret"))) == []


def test_response_schema_accepts_success_and_error() -> None:
    validator = Draft202012Validator(_schema("bridge-response.schema.json"))

    assert list(validator.iter_errors(success_response("request", {"pong": True}))) == []
    assert (
        list(validator.iter_errors(error_response("request", "NO_ACTIVE_GRAPH", "No graph."))) == []
    )
