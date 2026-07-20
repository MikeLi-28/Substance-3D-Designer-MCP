"""Generic public authoring tools backed by Designer's documented API."""

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP

from substance_designer_mcp.models.references import GraphRef, PackageRef
from substance_designer_mcp.models.requests import GraphPatch, UsageSpec
from substance_designer_mcp.models.responses import BridgeCaller, invoke

from .annotations import DESTRUCTIVE, READ_ONLY, WRITE


def register(mcp: FastMCP[Any], client: BridgeCaller) -> None:
    @mcp.tool(
        name="sd_create_package",
        description="Create one unsaved Designer user package through the official package API.",
        annotations=WRITE,
        structured_output=True,
    )
    def sd_create_package() -> dict[str, Any]:
        return invoke(client, "sd_create_package", {}, write=True)

    @mcp.tool(
        name="sd_create_graph",
        description="Create one empty compositing graph in an explicit open package.",
        annotations=WRITE,
        structured_output=True,
    )
    def sd_create_graph(
        package: PackageRef, identifier: str, graph_type: str | None = None
    ) -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "package": package.model_dump(mode="json"),
            "identifier": identifier,
        }
        if graph_type is not None:
            arguments["graph_type"] = graph_type
        return invoke(client, "sd_create_graph", arguments, write=True)

    @mcp.tool(
        name="sd_list_node_definitions",
        description="Search a bounded page of atomic definitions available in one graph.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_list_node_definitions(
        graph: GraphRef, query: str = "", offset: int = 0, limit: int = 100
    ) -> dict[str, Any]:
        return invoke(
            client,
            "sd_list_node_definitions",
            {
                "graph": graph.model_dump(mode="json"),
                "query": query,
                "offset": offset,
                "limit": limit,
            },
        )

    @mcp.tool(
        name="sd_get_graph_snapshot",
        description="Read a bounded versioned graph snapshot including explicit connections.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_get_graph_snapshot(
        graph: GraphRef, include_values: bool = True, limit: int = 200
    ) -> dict[str, Any]:
        return invoke(
            client,
            "sd_get_graph_snapshot",
            {
                "graph": graph.model_dump(mode="json"),
                "include_values": include_values,
                "limit": limit,
            },
        )

    @mcp.tool(
        name="sd_open_graph",
        description="Open one explicit graph resource in Designer's editor.",
        annotations=WRITE,
        structured_output=True,
    )
    def sd_open_graph(graph: GraphRef) -> dict[str, Any]:
        return invoke(
            client,
            "sd_open_graph",
            {"graph": graph.model_dump(mode="json")},
            write=True,
        )

    @mcp.tool(
        name="sd_create_graph_output",
        description="Create an Output node with explicit official usage metadata.",
        annotations=WRITE,
        structured_output=True,
    )
    def sd_create_graph_output(
        graph: GraphRef,
        identifier: str,
        label: str,
        usages: list[UsageSpec],
        position: tuple[float, float],
        description: str = "",
        group: str = "",
    ) -> dict[str, Any]:
        return invoke(
            client,
            "sd_create_graph_output",
            {
                "graph": graph.model_dump(mode="json"),
                "identifier": identifier,
                "label": label,
                "description": description,
                "group": group,
                "usages": [usage.model_dump(mode="json") for usage in usages],
                "position": [float(position[0]), float(position[1])],
            },
            write=True,
        )

    @mcp.tool(
        name="sd_save_package_as",
        description="Save an open package to an absolute .sbs path after explicit confirmation.",
        annotations=DESTRUCTIVE,
        structured_output=True,
    )
    def sd_save_package_as(
        package: PackageRef, file_path: str, overwrite: bool, confirm: bool
    ) -> dict[str, Any]:
        return invoke(
            client,
            "sd_save_package_as",
            {
                "package": package.model_dump(mode="json"),
                "file_path": file_path,
                "overwrite": overwrite,
                "confirm": confirm,
            },
            write=True,
        )

    def patch_call(
        command: str, graph: GraphRef, patch: GraphPatch, *, write: bool
    ) -> dict[str, Any]:
        return invoke(
            client,
            command,
            {"graph": graph.model_dump(mode="json"), "patch": patch.model_dump(mode="json")},
            write=write,
        )

    @mcp.tool(
        name="sd_validate_graph_patch",
        description="Dry-run a versioned additive graph patch without changing Designer.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_validate_graph_patch(graph: GraphRef, patch: GraphPatch) -> dict[str, Any]:
        return patch_call("sd_validate_graph_patch", graph, patch, write=False)

    @mcp.tool(
        name="sd_apply_graph_patch",
        description="Apply a preflighted additive graph patch with rollback on failure.",
        annotations=WRITE,
        structured_output=True,
    )
    def sd_apply_graph_patch(graph: GraphRef, patch: GraphPatch) -> dict[str, Any]:
        return patch_call("sd_apply_graph_patch", graph, patch, write=True)

    @mcp.tool(
        name="sd_import_bitmap",
        description="Import one existing local bitmap resource and optionally instantiate it.",
        annotations=WRITE,
        structured_output=True,
    )
    def sd_import_bitmap(
        package: PackageRef,
        file_path: str,
        identifier: str,
        embed_method: Literal["binary_embedded", "copied_and_linked", "linked"],
        graph: GraphRef | None = None,
        position: tuple[float, float] | None = None,
    ) -> dict[str, Any]:
        arguments: dict[str, Any] = {
            "package": package.model_dump(mode="json"),
            "file_path": file_path,
            "identifier": identifier,
            "embed_method": embed_method,
        }
        if graph is not None:
            arguments["graph"] = graph.model_dump(mode="json")
        if position is not None:
            arguments["position"] = [float(position[0]), float(position[1])]
        return invoke(client, "sd_import_bitmap", arguments, write=True)

    @mcp.tool(
        name="sd_export_package_sbsar",
        description="Export one saved package to .sbsar with explicit publication settings.",
        annotations=DESTRUCTIVE,
        structured_output=True,
    )
    def sd_export_package_sbsar(
        package: PackageRef,
        file_path: str,
        compression_mode: Literal["auto", "best", "none"],
        expose_output_size: bool,
        expose_pixel_size: bool,
        expose_random_seed: bool,
        icon_enabled: bool,
        overwrite: bool,
        confirm: bool,
    ) -> dict[str, Any]:
        return invoke(
            client,
            "sd_export_package_sbsar",
            {
                "package": package.model_dump(mode="json"),
                "file_path": file_path,
                "compression_mode": compression_mode,
                "expose_output_size": expose_output_size,
                "expose_pixel_size": expose_pixel_size,
                "expose_random_seed": expose_random_seed,
                "icon_enabled": icon_enabled,
                "overwrite": overwrite,
                "confirm": confirm,
            },
            write=True,
        )
