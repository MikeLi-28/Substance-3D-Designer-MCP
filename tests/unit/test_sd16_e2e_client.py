from __future__ import annotations

import asyncio
from typing import Any

import pytest

from tests.manual.sd16_e2e_client import (
    _call,
    _invalid_connection,
    _library_resource,
    created_node_identifiers,
)
from tests.manual.sd16_e2e_support import HarnessError


class FakeServer:
    def __init__(self, structured: dict[str, Any]) -> None:
        self.structured = structured
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def call_tool(
        self, name: str, arguments: dict[str, Any]
    ) -> tuple[list[object], dict[str, Any]]:
        self.calls.append((name, arguments))
        return [], self.structured


def test_call_returns_data_for_structured_success() -> None:
    server = FakeServer({"ok": True, "data": {"value": 7}, "warnings": []})

    result = asyncio.run(_call(server, "sd_ping", {}))

    assert result == {"value": 7}
    assert server.calls == [("sd_ping", {})]


def test_call_accepts_only_the_expected_stable_error() -> None:
    server = FakeServer(
        {
            "ok": False,
            "error": {"code": "INVALID_PARAMETER_TYPE", "message": "wrong type"},
            "warnings": [],
        }
    )

    result = asyncio.run(
        _call(server, "sd_set_node_parameter", {}, expected_error="INVALID_PARAMETER_TYPE")
    )

    assert result["code"] == "INVALID_PARAMETER_TYPE"


def test_call_rejects_unexpected_failure_and_unexpected_success() -> None:
    failed = FakeServer(
        {
            "ok": False,
            "error": {"code": "INTERNAL_ERROR", "message": "failed"},
            "warnings": [],
        }
    )
    succeeded = FakeServer({"ok": True, "data": {}, "warnings": []})

    with pytest.raises(HarnessError, match="unexpected error"):
        asyncio.run(_call(failed, "sd_ping", {}))
    with pytest.raises(HarnessError, match="expected error"):
        asyncio.run(_call(succeeded, "sd_ping", {}, expected_error="SD_NOT_RUNNING"))


def test_created_node_identifiers_include_only_successfully_created_nodes() -> None:
    identifiers = created_node_identifiers(
        [
            {"node": {"node_identifier": "atomic-1"}},
            {"node": {"node_identifier": "instance-2"}},
            {"node": {"label": "missing identifier"}},
            {"unrelated": "existing-node"},
        ]
    )

    assert identifiers == ["atomic-1", "instance-2"]


def test_library_resource_allows_temporary_runtime_url_but_not_temporary_stable_key() -> None:
    selected = _library_resource(
        [
            {
                "package_url": "file:///active.sbs",
                "resource_identifier": "active",
                "stable_key": "file:///active.sbs::active",
                "runtime_url": "pkg:///active",
                "category": "SDSBSCompGraph",
            },
            {
                "package_url": "file:///library.sbs",
                "resource_identifier": "bad",
                "stable_key": "file:///library.sbs::bad?dependency=1",
                "runtime_url": "pkg:///bad?dependency=1",
                "category": "SDSBSCompGraph",
            },
            {
                "package_url": "file:///library.sbs",
                "resource_identifier": "blend",
                "stable_key": "file:///library.sbs::blend",
                "runtime_url": "pkg:///blend?dependency=42",
                "category": "SDSBSCompGraph",
            },
        ],
        "file:///active.sbs",
    )

    assert selected["resource_identifier"] == "blend"
    assert "dependency=42" in selected["runtime_url"]
    assert "dependency=" not in selected["stable_key"]


def test_invalid_connection_never_reuses_ids_present_in_the_required_direction() -> None:
    source_properties = [
        {"direction": "input", "property_id": "shared"},
        {"direction": "output", "property_id": "shared"},
    ]
    target_properties = [
        {"direction": "output", "property_id": "shared"},
        {"direction": "input", "property_id": "shared"},
    ]

    result = _invalid_connection(source_properties, target_properties)

    assert result["source_property"] != "shared"
    assert result["target_property"] != "shared"
