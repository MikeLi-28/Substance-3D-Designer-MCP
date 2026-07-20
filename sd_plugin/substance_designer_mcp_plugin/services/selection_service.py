"""Current Graph View selection reads."""

from __future__ import annotations

from typing import Any, Dict

from ..errors import ErrorCode, PluginError
from .common import iter_api_array
from .resource_resolver import node_reference


class SelectionService:
    def __init__(self, application: Any) -> None:
        self.application = application

    def get_selection(self, limit: int = 100) -> Dict[str, Any]:
        ui_mgr = self.application.getUIMgr()
        graph = ui_mgr.getCurrentGraph() if ui_mgr is not None else None
        if graph is None:
            raise PluginError(ErrorCode.NO_ACTIVE_GRAPH, "No graph is currently active.")
        selected = list(iter_api_array(ui_mgr.getCurrentGraphSelectedNodes()))
        return {
            "nodes": [node_reference(graph, node) for node in selected[:limit]],
            "total": len(selected),
            "truncated": len(selected) > limit,
        }
