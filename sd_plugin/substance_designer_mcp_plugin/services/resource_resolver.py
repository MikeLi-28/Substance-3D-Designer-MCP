"""Resolve structured references against the current Designer session."""

from __future__ import annotations

from pathlib import PurePath
from typing import Any, Dict, Mapping, Tuple

from ..errors import ErrorCode, PluginError
from ..serialization.references import make_library_resource_ref
from .common import iter_api_array, position_to_list


def package_reference(package: Any) -> Dict[str, Any]:
    file_path = str(package.getFilePath() or "")
    uid = str(package.getUID())
    package_url = (
        "file:///" + file_path.replace("\\", "/") if file_path else "session-package://" + uid
    )
    label = PurePath(file_path).stem if file_path else uid
    return {"package_url": package_url, "file_path": file_path or None, "label": label}


def graph_reference(graph: Any) -> Dict[str, Any]:
    package = package_reference(graph.getPackage())
    return {
        "package_url": package["package_url"],
        "graph_identifier": str(graph.getIdentifier()),
        "graph_type": str(graph.getGraphType()),
    }


def node_reference(graph: Any, node: Any) -> Dict[str, Any]:
    definition = node.getDefinition()
    definition_id = str(definition.getId()) if definition is not None else "unknown"
    label = str(definition.getLabel()) if definition is not None else str(node.getIdentifier())
    graph_ref = graph_reference(graph)
    identifier = str(node.getIdentifier())
    return {
        "package_url": graph_ref["package_url"],
        "graph_identifier": graph_ref["graph_identifier"],
        "node_identifier": identifier,
        "definition_id": definition_id,
        "label": label,
        "session_handle": "{}/{}".format(graph_ref["graph_identifier"], identifier),
        "handle_lifetime": "current_designer_session",
    }


class ResourceResolver:
    def __init__(self, application: Any) -> None:
        self.application = application
        self.package_mgr = application.getPackageMgr()

    def packages(self) -> list[Any]:
        return list(iter_api_array(self.package_mgr.getPackages()))

    def resolve_package(self, reference: Mapping[str, Any]) -> Any:
        requested_url = reference.get("package_url")
        requested_path = reference.get("file_path")
        for package in self.packages():
            current = package_reference(package)
            if requested_url == current["package_url"] or (
                requested_path and requested_path == current["file_path"]
            ):
                return package
        raise PluginError(ErrorCode.PACKAGE_NOT_FOUND, "The package is not open.")

    def resources(self, package: Any) -> list[Any]:
        return list(iter_api_array(package.getChildrenResources(True)))

    def resolve_graph(self, reference: Mapping[str, Any]) -> Any:
        package = self.resolve_package(reference)
        identifier = reference.get("graph_identifier")
        for resource in self.resources(package):
            if (
                callable(getattr(resource, "getNodes", None))
                and str(resource.getIdentifier()) == identifier
            ):
                return resource
        raise PluginError(ErrorCode.GRAPH_NOT_FOUND, "The graph was not found in the package.")

    def resolve_node(self, reference: Mapping[str, Any]) -> Tuple[Any, Any]:
        graph = self.resolve_graph(reference)
        identifier = reference.get("node_identifier")
        node = graph.getNodeFromId(str(identifier))
        if node is None:
            raise PluginError(ErrorCode.NODE_NOT_FOUND, "The node was not found in the graph.")
        return graph, node

    def resolve_library(self, reference: Mapping[str, Any]) -> Any:
        identifier = reference.get("resource_identifier")
        stable_key = reference.get("stable_key")
        for package in self.packages():
            package_ref = package_reference(package)
            for resource in self.resources(package):
                if str(resource.getIdentifier()) != identifier:
                    continue
                current = make_library_resource_ref(
                    package_ref["package_url"],
                    str(resource.getIdentifier()),
                    str(resource.getUrl()),
                    str(resource.getIdentifier()),
                    str(resource.getClassName()),
                )
                if current["stable_key"] == stable_key:
                    return resource
        raise PluginError(
            ErrorCode.LIBRARY_RESOURCE_NOT_FOUND,
            "The library resource is not available in the current session.",
        )


def node_summary(graph: Any, node: Any) -> Dict[str, Any]:
    return {"node": node_reference(graph, node), "position": position_to_list(node.getPosition())}
