"""Construct the focused service set without a global service locator."""

from __future__ import annotations

from typing import Any

from .application_service import ApplicationService
from .authoring_service import AuthoringService
from .connection_service import ConnectionService
from .delivery_service import DeliveryService
from .graph_service import GraphService
from .library_service import LibraryService
from .node_service import NodeService
from .package_service import PackageService
from .parameter_service import ParameterService
from .patch_service import PatchService
from .resource_resolver import ResourceResolver
from .selection_service import SelectionService


class ServiceContainer:
    def __init__(self, application: Any, adapter: Any) -> None:
        resolver = ResourceResolver(application)
        self.application = ApplicationService(application)
        self.package = PackageService(resolver)
        self.selection = SelectionService(application)
        self.node = NodeService(resolver, adapter)
        self.graph = GraphService(application, resolver, self.node)
        self.authoring = AuthoringService(application, resolver, self.node, adapter)
        self.connection = ConnectionService(resolver, adapter)
        self.parameter = ParameterService(resolver, adapter)
        self.patch = PatchService(resolver, adapter)
        self.delivery = DeliveryService(resolver, adapter)
        self.library = LibraryService(resolver)
