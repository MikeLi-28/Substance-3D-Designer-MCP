"""Package listing and explicitly confirmed in-place save tools."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from substance_designer_mcp.models.references import PackageRef
from substance_designer_mcp.models.responses import BridgeCaller, invoke

from .annotations import DESTRUCTIVE, READ_ONLY


def register(mcp: FastMCP[Any], client: BridgeCaller) -> None:
    @mcp.tool(
        name="sd_list_packages",
        description="List packages currently open in Designer as structured references.",
        annotations=READ_ONLY,
        structured_output=True,
    )
    def sd_list_packages() -> dict[str, Any]:
        return invoke(client, "sd_list_packages", {})

    @mcp.tool(
        name="sd_save_package",
        description="Save one already-saved open package in place; never performs Save As.",
        annotations=DESTRUCTIVE,
        structured_output=True,
    )
    def sd_save_package(package: PackageRef, confirm: bool) -> dict[str, Any]:
        return invoke(
            client,
            "sd_save_package",
            {"package": package.model_dump(mode="json"), "confirm": confirm},
            write=True,
        )
