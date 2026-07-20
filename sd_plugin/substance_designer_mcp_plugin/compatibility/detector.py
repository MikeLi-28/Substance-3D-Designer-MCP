"""Feature probes that avoid scattered version checks."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from .capabilities import capability

_SOURCE = "Adobe Substance 3D Designer 16.0.3 Python API documentation"
_VERIFIED_SOURCE = "Substance 3D Designer 16.0.3 compatibility baseline"
VERIFIED_VERSIONS = ("16.0.3",)

_INDIVIDUAL_TEST_WARNING = "This Designer version has not been individually tested."
_EXPERIMENTAL_WARNING = (
    "This Designer major version has not been verified. Available tools are enabled "
    "through runtime capability detection."
)
_UNSUPPORTED_WARNING = "This Designer version is outside the Designer 16 compatibility baseline."
_UNKNOWN_VERSION_WARNING = "The Designer version could not be identified and has not been verified."


def _call_optional(owner: Any, name: str) -> Optional[Any]:
    method = getattr(owner, name, None)
    if not callable(method):
        return None
    try:
        return method()
    except Exception:
        return None


def _has(owner: Any, *names: str) -> bool:
    return owner is not None and all(callable(getattr(owner, name, None)) for name in names)


def _major_version(version: str) -> Optional[int]:
    match = re.match(r"\s*(\d+)", version)
    return int(match.group(1)) if match else None


def _classify_version(version: str) -> Tuple[str, str, Optional[str]]:
    if version in VERIFIED_VERSIONS:
        return "verified", "supported", None
    major = _major_version(version)
    if major == 16:
        return "untested", "capability_detected", _INDIVIDUAL_TEST_WARNING
    if major is not None and major > 16:
        return "untested", "experimental", _EXPERIMENTAL_WARNING
    if major is not None:
        return "untested", "unsupported", _UNSUPPORTED_WARNING
    return "untested", "unsupported", _UNKNOWN_VERSION_WARNING


def detect_compatibility(application: Any) -> Dict[str, Any]:
    """Probe actual objects and report formal availability and compatibility metadata."""

    version_method = getattr(application, "getVersion", None)
    version = str(version_method()) if callable(version_method) else "unknown"
    package_mgr = _call_optional(application, "getPackageMgr")
    ui_mgr = _call_optional(application, "getUIMgr")
    graph = _call_optional(ui_mgr, "getCurrentGraph") if ui_mgr is not None else None
    nodes = _call_optional(graph, "getNodes") if graph is not None else None
    first_node = None
    if nodes is not None:
        try:
            if hasattr(nodes, "getSize") and nodes.getSize() > 0:
                first_node = nodes.getItem(0)
            elif len(nodes) > 0:
                first_node = nodes[0]
        except Exception:
            first_node = None

    package_read = _has(package_mgr, "getPackages")
    active_graph = _has(ui_mgr, "getCurrentGraph")
    graph_read = _has(graph, "getNodes", "getIdentifier")
    node_read = graph_read and (
        first_node is None or _has(first_node, "getDefinition", "getProperties")
    )
    baseline_verified = version in VERIFIED_VERSIONS
    verification_source = _VERIFIED_SOURCE if baseline_verified else _SOURCE
    capabilities = {
        "application_info": capability(
            callable(version_method),
            verification_source,
            baseline_verified,
        ),
        "package_read": capability(
            package_read,
            verification_source,
            baseline_verified,
        ),
        "active_graph": capability(
            active_graph,
            verification_source,
            baseline_verified,
        ),
        "selection_read": capability(
            _has(ui_mgr, "getCurrentGraphSelectedNodes"),
            verification_source,
            baseline_verified,
        ),
        "graph_read": capability(graph_read, verification_source, baseline_verified),
        "node_read": capability(node_read, verification_source, baseline_verified),
        "library_search": capability(package_read, verification_source, baseline_verified),
        "node_write": capability(
            _has(graph, "newNode", "newInstanceNode", "deleteNode"),
            verification_source,
            baseline_verified,
        ),
        "connection_write": capability(
            first_node is not None
            and _has(first_node, "newPropertyConnection", "getPropertyConnections"),
            verification_source,
            baseline_verified,
        ),
        "parameter_write": capability(
            first_node is not None
            and _has(
                first_node,
                "getInputPropertyValueFromId",
                "setInputPropertyValueFromId",
            ),
            verification_source,
            baseline_verified,
        ),
        "package_save": capability(
            _has(package_mgr, "savePackage"),
            verification_source,
            baseline_verified,
        ),
    }
    new_source = _SOURCE
    package_create = _has(package_mgr, "newUserPackage")
    package_save_as = _has(package_mgr, "savePackageAs")
    node_write = _has(graph, "newNode", "newInstanceNode", "deleteNode")
    connection_write = first_node is not None and _has(
        first_node, "newPropertyConnection", "getPropertyConnections"
    )
    parameter_write = first_node is not None and _has(
        first_node,
        "getInputPropertyValueFromId",
        "setInputPropertyValueFromId",
    )
    capabilities.update(
        {
            "package_create": capability(package_create, new_source),
            "graph_create": capability(package_create, new_source),
            "graph_snapshot": capability(graph_read and node_read, new_source),
            "graph_output_write": capability(
                node_write
                and (first_node is None or _has(first_node, "setAnnotationPropertyValueFromId")),
                new_source,
            ),
            "graph_patch": capability(
                node_write and connection_write and parameter_write,
                new_source,
            ),
            "bitmap_import": capability(package_create and node_write, new_source),
            "package_save_as": capability(package_save_as, new_source),
            "package_export_sbsar": capability(_has(package_mgr, "savePackage"), new_source),
            "ui_open_graph": capability(_has(ui_mgr, "openResourceInEditor"), new_source),
        }
    )
    verification_status, compatibility_status, warning = _classify_version(version)
    return {
        "designer_version": version,
        "verification_status": verification_status,
        "compatibility_status": compatibility_status,
        "verified_versions": list(VERIFIED_VERSIONS),
        "warning": warning,
        "capabilities": capabilities,
    }
