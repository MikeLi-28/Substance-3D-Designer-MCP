from __future__ import annotations

from contextlib import nullcontext
from typing import Any


class FakeAdapter:
    INPUT = "Input"
    OUTPUT = "Output"
    ANNOTATION = "Annotation"

    def __init__(self) -> None:
        self.imported_bitmaps: list[tuple[Any, str, str]] = []
        self.sbsar_exports: list[dict[str, Any]] = []

    def float2(self, x: float, y: float) -> tuple[float, float]:
        return (x, y)

    def serialize_value(self, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return {"type": value.getType().getId(), "value": value.get()}

    def to_sd_value(self, type_id: str, value: Any, sd_type: Any) -> Any:
        from .sd_api import FakeValue

        del sd_type
        supported = {"bool", "int", "float", "string", "float2", "float3", "float4", "color"}
        if type_id not in supported:
            raise ValueError("unsupported")
        return FakeValue(type_id, value)

    def new_compositing_graph(self, package: Any) -> Any:
        from .sd_api import FakeGraph

        graph = FakeGraph(f"graph-{len(package.resources) + 1}")
        graph.nodes = []
        graph.package = package
        package.resources.append(graph)
        return graph

    def supported_graph_types(self, graph: Any) -> list[str]:
        del graph
        return ["substance"]

    def usage_array(self, usages: list[dict[str, str]]) -> Any:
        from .sd_api import FakeValue

        return FakeValue("usage_array", usages)

    def string_value(self, value: str) -> Any:
        from .sd_api import FakeValue

        return FakeValue("string", value)

    def undo_group(self, name: str) -> Any:
        del name
        return nullcontext()

    def import_bitmap(self, package: Any, file_path: str, embed_method: str) -> Any:
        from .sd_api import FakeResource

        resource = FakeResource(
            f"bitmap-{len(package.resources) + 1}",
            f"pkg://demo/bitmap-{len(package.resources) + 1}",
            "SDResourceBitmap",
        )
        resource.package = package
        package.resources.append(resource)
        self.imported_bitmaps.append((package, file_path, embed_method))
        return resource

    def export_package_sbsar(self, package: Any, file_path: str, settings: dict[str, Any]) -> None:
        self.sbsar_exports.append({"package": package, "file_path": file_path, **settings})
