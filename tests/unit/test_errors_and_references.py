from __future__ import annotations

import json

from substance_designer_mcp_plugin.serialization.references import (
    make_library_resource_ref,
    strip_temporary_dependency,
)

from substance_designer_mcp.errors import ErrorCode, MCPError
from substance_designer_mcp.models.references import GraphRef, NodeRef, PackageRef


def test_required_error_codes_are_centralized() -> None:
    required = {
        "SD_NOT_RUNNING",
        "BRIDGE_NOT_AVAILABLE",
        "AUTHENTICATION_FAILED",
        "PROTOCOL_VERSION_MISMATCH",
        "REQUEST_TOO_LARGE",
        "REQUEST_TIMEOUT",
        "UNSUPPORTED_DESIGNER_VERSION",
        "UNSUPPORTED_CAPABILITY",
        "NO_ACTIVE_PACKAGE",
        "NO_ACTIVE_GRAPH",
        "GRAPH_NOT_EDITABLE",
        "PACKAGE_NOT_FOUND",
        "GRAPH_NOT_FOUND",
        "NODE_NOT_FOUND",
        "NODE_DEFINITION_NOT_FOUND",
        "LIBRARY_RESOURCE_NOT_FOUND",
        "PROPERTY_NOT_FOUND",
        "INVALID_PROPERTY_DIRECTION",
        "INVALID_PARAMETER",
        "INVALID_PARAMETER_TYPE",
        "CONNECTION_NOT_ALLOWED",
        "CONNECTION_ALREADY_EXISTS",
        "DESTRUCTIVE_CONFIRMATION_REQUIRED",
        "SAVE_FAILED",
        "SD_API_ERROR",
        "INTERNAL_ERROR",
    }

    assert required <= {item.value for item in ErrorCode}


def test_public_error_is_json_serializable_and_sanitized() -> None:
    error = MCPError(
        ErrorCode.NODE_NOT_FOUND,
        "Node was not found.",
        details={"node_identifier": "node-1"},
    )

    encoded = json.dumps(error.to_dict())

    assert "node-1" in encoded
    assert "traceback" not in encoded


def test_structured_refs_round_trip_as_json_without_python_objects() -> None:
    package = PackageRef(package_url="pkg://demo", file_path="C:/demo.sbs", label="Demo")
    graph = GraphRef(package_url=package.package_url, graph_identifier="main")
    node = NodeRef(
        package_url=package.package_url,
        graph_identifier=graph.graph_identifier,
        node_identifier="node-1",
        definition_id="sbs::compositing::uniform",
        label="Uniform",
        session_handle="session-node-1",
    )

    payload = json.loads(node.model_dump_json())

    assert payload["node_identifier"] == "node-1"
    assert payload["handle_lifetime"] == "current_designer_session"
    assert "0x" not in json.dumps(payload)


def test_dependency_query_is_not_part_of_stable_library_identity() -> None:
    runtime_url = "pkg://library/resource?dependency=91823&variant=clean"

    assert strip_temporary_dependency(runtime_url) == "pkg://library/resource?variant=clean"
    resource = make_library_resource_ref(
        package_url="pkg://library",
        resource_identifier="resource",
        runtime_url=runtime_url,
        label="Resource",
        category="generator",
    )
    assert "dependency=" not in resource["stable_key"]
    assert resource["runtime_url"] == runtime_url
