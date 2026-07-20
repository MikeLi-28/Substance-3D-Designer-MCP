"""Validated local bitmap import and in-process SBSAR publication."""

from __future__ import annotations

import contextlib
import re
from pathlib import Path
from typing import Any, Dict, Mapping

from ..commands.validators import validate_position
from ..errors import ErrorCode, PluginError
from ..serialization.references import make_library_resource_ref
from .common import position_to_list
from .resource_resolver import ResourceResolver, node_reference, package_reference

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]{0,127}$")
_BITMAP_SUFFIXES = {
    ".bmp",
    ".exr",
    ".hdr",
    ".jpeg",
    ".jpg",
    ".png",
    ".psd",
    ".tga",
    ".tif",
    ".tiff",
}
_EMBED_METHODS = {"binary_embedded", "copied_and_linked", "linked"}
_COMPRESSION_MODES = {"auto", "best", "none"}


class DeliveryService:
    def __init__(self, resolver: ResourceResolver, adapter: Any) -> None:
        self.resolver = resolver
        self.adapter = adapter

    @staticmethod
    def _input_file(file_path: Any) -> Path:
        path = Path(str(file_path))
        if not path.is_absolute() or not path.is_file():
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                "Bitmap import requires an existing absolute file path.",
            )
        path = path.resolve(strict=True)
        if path.suffix.lower() not in _BITMAP_SUFFIXES:
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                "The bitmap file extension is not supported by this tool.",
            )
        return path

    @staticmethod
    def _output_file(file_path: Any, suffix: str, overwrite: bool) -> Path:
        path = Path(str(file_path))
        if not path.is_absolute() or path.suffix.lower() != suffix:
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                f"Export requires an absolute path ending in {suffix}.",
            )
        path = path.resolve(strict=False)
        if not path.parent.is_dir():
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                "The export parent directory must already exist.",
            )
        if path.exists() and not overwrite:
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                "The export target exists; set overwrite=true to replace it.",
            )
        if path.exists() and not path.is_file():
            raise PluginError(ErrorCode.INVALID_PARAMETER, "The export target is not a file.")
        return path

    @staticmethod
    def _identifier(value: Any) -> str:
        if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                "identifier must be a portable identifier without spaces.",
            )
        return value

    def import_bitmap(self, arguments: Mapping[str, Any]) -> Dict[str, Any]:
        package = self.resolver.resolve_package(arguments["package"])
        path = self._input_file(arguments["file_path"])
        identifier = self._identifier(arguments["identifier"])
        embed_method = arguments.get("embed_method")
        if embed_method not in _EMBED_METHODS:
            raise PluginError(ErrorCode.INVALID_PARAMETER, "Unknown bitmap embed method.")
        graph_ref = arguments.get("graph")
        position = arguments.get("position")
        if (graph_ref is None) != (position is None):
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                "graph and position must be provided together.",
            )
        for existing in self.resolver.resources(package):
            if str(existing.getIdentifier()) == identifier:
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER,
                    "The package already contains that resource identifier.",
                )
        graph = None
        xy = None
        if graph_ref is not None:
            graph = self.resolver.resolve_graph(graph_ref)
            if str(graph.getPackage().getUID()) != str(package.getUID()):
                raise PluginError(
                    ErrorCode.INVALID_PARAMETER,
                    "The target graph must belong to the bitmap package.",
                )
            xy = validate_position(position)
        try:
            resource = self.adapter.import_bitmap(package, str(path), str(embed_method))
            if resource is None:
                raise RuntimeError("Designer did not create the bitmap resource.")
            resource.setIdentifier(identifier)
        except Exception as exc:
            raise PluginError(
                ErrorCode.SD_API_ERROR, "Designer could not import the bitmap."
            ) from exc
        package_ref = package_reference(package)
        resource_ref = make_library_resource_ref(
            package_ref["package_url"],
            identifier,
            str(resource.getUrl()),
            identifier,
            str(resource.getClassName()),
        )
        result: Dict[str, Any] = {"resource": resource_ref, "embed_method": embed_method}
        if graph is not None and xy is not None:
            try:
                with self.adapter.undo_group("Import bitmap through MCP"):
                    node = graph.newInstanceNode(resource)
                    if node is None:
                        raise RuntimeError("Designer did not create the bitmap instance node.")
                    node.setPosition(self.adapter.float2(xy[0], xy[1]))
            except Exception as exc:
                with contextlib.suppress(Exception):
                    resource.delete()
                raise PluginError(
                    ErrorCode.SD_API_ERROR,
                    "Designer could not instantiate the bitmap; the resource was removed.",
                ) from exc
            result["node"] = {
                "node": node_reference(graph, node),
                "position": position_to_list(node.getPosition()),
            }
        return result

    def export_sbsar(self, arguments: Mapping[str, Any]) -> Dict[str, Any]:
        package = self.resolver.resolve_package(arguments["package"])
        if not str(package.getFilePath() or ""):
            raise PluginError(
                ErrorCode.SAVE_FAILED,
                "The package must be saved as .sbs before SBSAR export.",
            )
        compression = arguments.get("compression_mode")
        if compression not in _COMPRESSION_MODES:
            raise PluginError(ErrorCode.INVALID_PARAMETER, "Unknown SBSAR compression mode.")
        overwrite = arguments.get("overwrite")
        if not isinstance(overwrite, bool):
            raise PluginError(ErrorCode.INVALID_PARAMETER, "overwrite must be a boolean.")
        target = self._output_file(arguments["file_path"], ".sbsar", overwrite)
        bool_keys = (
            "expose_output_size",
            "expose_pixel_size",
            "expose_random_seed",
            "icon_enabled",
        )
        settings: Dict[str, Any] = {"compression_mode": compression}
        for key in bool_keys:
            value = arguments.get(key)
            if not isinstance(value, bool):
                raise PluginError(ErrorCode.INVALID_PARAMETER, f"{key} must be a boolean.")
            settings[key] = value
        try:
            self.adapter.export_package_sbsar(package, str(target), settings)
        except Exception as exc:
            raise PluginError(
                ErrorCode.SAVE_FAILED, "Designer could not export the SBSAR."
            ) from exc
        return {
            "exported": True,
            "package": package_reference(package),
            "file_path": str(target),
            "settings": settings,
        }
