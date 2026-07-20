"""Active graph and bounded node reads."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ..errors import ErrorCode, PluginError
from .common import iter_api_array
from .resource_resolver import ResourceResolver, graph_reference, node_reference, package_reference


class GraphService:
    def __init__(self, application: Any, resolver: ResourceResolver, node_service: Any) -> None:
        self.application = application
        self.resolver = resolver
        self.node_service = node_service

    def _current(self) -> Any:
        ui_mgr = self.application.getUIMgr()
        graph = ui_mgr.getCurrentGraph() if ui_mgr is not None else None
        if graph is None:
            raise PluginError(ErrorCode.NO_ACTIVE_GRAPH, "No editable graph is currently active.")
        return graph

    def get_active_graph(self) -> Dict[str, Any]:
        graph = self._current()
        nodes = list(iter_api_array(graph.getNodes()))
        ui_mgr = self.application.getUIMgr()
        selected = list(iter_api_array(ui_mgr.getCurrentGraphSelectedNodes()))
        return {
            "graph": graph_reference(graph),
            "graph_type": str(graph.getGraphType()),
            "editable": callable(getattr(graph, "newNode", None)),
            "package": package_reference(graph.getPackage()),
            "node_count": len(nodes),
            "selection_count": len(selected),
        }

    def list_nodes(
        self,
        graph_ref: Mapping[str, Any],
        *,
        detail: str,
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        graph = self.resolver.resolve_graph(graph_ref)
        all_nodes = list(iter_api_array(graph.getNodes()))
        selected = all_nodes[offset : offset + limit]
        references = [node_reference(graph, node) for node in selected]
        nodes = (
            [self.node_service.get_node(reference, "full") for reference in references]
            if detail == "full"
            else references
        )
        return {
            "nodes": nodes,
            "detail": detail,
            "offset": offset,
            "limit": limit,
            "total": len(all_nodes),
            "truncated": offset + limit < len(all_nodes),
        }
