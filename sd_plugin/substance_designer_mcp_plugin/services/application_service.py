"""Application status and compatibility reads."""

from __future__ import annotations

import platform
import sys
from typing import Any, Dict

from ..compatibility.detector import detect_compatibility
from .common import iter_api_array


class ApplicationService:
    def __init__(self, application: Any) -> None:
        self.application = application

    def get_capabilities(self) -> Dict[str, Any]:
        return detect_compatibility(self.application)

    def get_info(self) -> Dict[str, Any]:
        package_mgr = self.application.getPackageMgr()
        ui_mgr = self.application.getUIMgr()
        graph = ui_mgr.getCurrentGraph() if ui_mgr is not None else None
        compatibility = self.get_capabilities()
        return {
            "designer_version": str(self.application.getVersion()),
            "python_version": platform.python_version(),
            "platform": sys.platform,
            "open_package_count": len(list(iter_api_array(package_mgr.getPackages()))),
            "has_active_graph": graph is not None,
            "capabilities": compatibility["capabilities"],
            "verification_status": compatibility["verification_status"],
            "compatibility_status": compatibility["compatibility_status"],
            "verified_versions": compatibility["verified_versions"],
            "warning": compatibility["warning"],
        }
