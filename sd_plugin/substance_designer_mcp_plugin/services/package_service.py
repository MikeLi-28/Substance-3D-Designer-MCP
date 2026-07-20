"""Open-package listing and confirmed in-place save behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from ..errors import ErrorCode, PluginError
from .resource_resolver import ResourceResolver, package_reference


class PackageService:
    def __init__(self, resolver: ResourceResolver) -> None:
        self.resolver = resolver

    def list_packages(self) -> Dict[str, Any]:
        packages = [package_reference(package) for package in self.resolver.packages()]
        return {"packages": packages, "count": len(packages)}

    def save(self, reference: Mapping[str, Any]) -> Dict[str, Any]:
        package = self.resolver.resolve_package(reference)
        file_path = str(package.getFilePath() or "")
        if not file_path:
            raise PluginError(
                ErrorCode.SAVE_FAILED,
                "The package has no saved path; Save As is not available through MCP.",
            )
        try:
            self.resolver.package_mgr.savePackage(package)
        except Exception as exc:
            raise PluginError(
                ErrorCode.SAVE_FAILED, "Designer could not save the package."
            ) from exc
        return {"saved": True, "package": package_reference(package)}

    def save_as(
        self, reference: Mapping[str, Any], file_path: str, overwrite: bool
    ) -> Dict[str, Any]:
        if not isinstance(overwrite, bool):
            raise PluginError(ErrorCode.INVALID_PARAMETER, "overwrite must be a boolean.")
        package = self.resolver.resolve_package(reference)
        target = Path(file_path)
        if not target.is_absolute() or target.suffix.lower() != ".sbs":
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                "Save As requires an absolute path ending in .sbs.",
            )
        target = target.resolve(strict=False)
        if not target.parent.is_dir():
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                "The Save As parent directory must already exist.",
            )
        if target.exists() and not overwrite:
            raise PluginError(
                ErrorCode.INVALID_PARAMETER,
                "The Save As target exists; set overwrite=true to replace it.",
            )
        if target.exists() and not target.is_file():
            raise PluginError(ErrorCode.INVALID_PARAMETER, "The Save As target is not a file.")
        try:
            self.resolver.package_mgr.savePackageAs(package, str(target))
        except Exception as exc:
            raise PluginError(
                ErrorCode.SAVE_FAILED, "Designer could not save the package to that path."
            ) from exc
        return {"saved": True, "package": package_reference(package), "file_path": str(target)}
