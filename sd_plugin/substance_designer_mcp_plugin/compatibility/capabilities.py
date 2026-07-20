"""Capability names and verification metadata."""

from __future__ import annotations

from typing import Any, Dict

CAPABILITY_NAMES = (
    "application_info",
    "package_read",
    "active_graph",
    "selection_read",
    "graph_read",
    "node_read",
    "library_search",
    "node_write",
    "connection_write",
    "parameter_write",
    "package_save",
    "package_create",
    "graph_create",
    "graph_snapshot",
    "graph_output_write",
    "graph_patch",
    "bitmap_import",
    "package_save_as",
    "package_export_sbsar",
    "ui_open_graph",
)


def capability(available: bool, source: str, real_machine_verified: bool = False) -> Dict[str, Any]:
    """Describe runtime availability separately from real-machine verification."""

    return {
        "available": bool(available),
        "real_machine_verified": bool(real_machine_verified),
        "verification_source": source,
    }
