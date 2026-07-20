from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .sd_adapter import FakeAdapter
from .sd_preset import FakePreset


class FakeArray(list[Any]):
    def getSize(self) -> int:
        return len(self)

    def getItem(self, index: int) -> Any:
        return self[index]


class FakeType:
    def __init__(self, identifier: str) -> None:
        self.identifier = identifier

    def getId(self) -> str:
        return self.identifier

    def getClassName(self) -> str:
        return f"SDType{self.identifier.title()}"


class FakeValue:
    def __init__(self, type_id: str, value: Any) -> None:
        self.type = FakeType(type_id)
        self.value = value

    def getType(self) -> FakeType:
        return self.type

    def get(self) -> Any:
        return self.value

    def getClassName(self) -> str:
        return f"SDValue{self.type.identifier.title()}"


class FakeProperty:
    def __init__(
        self,
        identifier: str,
        category: str,
        type_id: str,
        *,
        connectable: bool = True,
        read_only: bool = False,
        label: Optional[str] = None,
    ) -> None:
        self.identifier = identifier
        self.category = category
        self.type = FakeType(type_id)
        self.connectable = connectable
        self.read_only = read_only
        self.label = label or identifier

    def getId(self) -> str:
        return self.identifier

    def getCategory(self) -> str:
        return self.category

    def getType(self) -> FakeType:
        return self.type

    def getTypes(self) -> FakeArray:
        return FakeArray([self.type])

    def getLabel(self) -> str:
        return self.label

    def getDescription(self) -> str:
        return ""

    def isConnectable(self) -> bool:
        return self.connectable

    def isReadOnly(self) -> bool:
        return self.read_only

    def isVariadic(self) -> bool:
        return False

    def isPrimary(self) -> bool:
        return False

    def isFunctionOnly(self) -> bool:
        return False


class FakeDefinition:
    def __init__(
        self,
        identifier: str,
        label: str,
        description: str = "",
        properties: Optional[list[FakeProperty]] = None,
    ) -> None:
        self.identifier = identifier
        self.label = label
        self.description = description
        self.properties = properties or []

    def getId(self) -> str:
        return self.identifier

    def getLabel(self) -> str:
        return self.label

    def getDescription(self) -> str:
        return self.description

    def getProperties(self, category: str) -> FakeArray:
        return FakeArray(prop for prop in self.properties if prop.getCategory() == category)

    def getPropertyFromId(self, identifier: str, category: str) -> Optional[FakeProperty]:
        return next(
            (
                prop
                for prop in self.properties
                if prop.getCategory() == category and prop.getId() == identifier
            ),
            None,
        )


class FakeConnection:
    def __init__(
        self,
        source: FakeNode,
        output: FakeProperty,
        target: FakeNode,
        input_property: FakeProperty,
    ) -> None:
        self.source = source
        self.output = output
        self.target = target
        self.input = input_property
        self.disconnected = False

    def getOutputPropertyNode(self) -> FakeNode:
        return self.source

    def getOutputProperty(self) -> FakeProperty:
        return self.output

    def getInputPropertyNode(self) -> FakeNode:
        return self.target

    def getInputProperty(self) -> FakeProperty:
        return self.input

    def disconnect(self) -> None:
        self.disconnected = True


class FakeNode:
    def __init__(
        self,
        identifier: str,
        definition_id: str,
        label: str,
        position: tuple[float, float] = (0.0, 0.0),
    ) -> None:
        self.identifier = identifier
        self.definition = FakeDefinition(definition_id, label)
        self.position = position
        self.input_properties = [
            FakeProperty("input", "Input", "image"),
            FakeProperty("amount", "Input", "float", connectable=False),
        ]
        self.output_properties = [FakeProperty("output", "Output", "image")]
        self.annotation_properties = [
            FakeProperty("identifier", "Annotation", "string", connectable=False),
            FakeProperty("label", "Annotation", "string", connectable=False),
            FakeProperty("description", "Annotation", "string", connectable=False),
            FakeProperty("group", "Annotation", "string", connectable=False),
            FakeProperty("usages", "Annotation", "usage_array", connectable=False),
        ]
        self.values: dict[str, FakeValue] = {"amount": FakeValue("float", 0.5)}
        self.annotations: dict[str, FakeValue] = {}
        self.connections: list[FakeConnection] = []
        self.referenced_resource: Optional[FakeResource] = None

    def getIdentifier(self) -> str:
        return self.identifier

    def getDefinition(self) -> FakeDefinition:
        return self.definition

    def getPosition(self) -> tuple[float, float]:
        return self.position

    def setPosition(self, value: tuple[float, float]) -> None:
        self.position = value

    def getProperties(self, category: str) -> FakeArray:
        if category == "Input":
            return FakeArray(self.input_properties)
        if category == "Output":
            return FakeArray(self.output_properties)
        if category == "Annotation":
            return FakeArray(self.annotation_properties)
        return FakeArray()

    def getPropertyFromId(self, identifier: str, category: str) -> Optional[FakeProperty]:
        for prop in self.getProperties(category):
            if prop.getId() == identifier:
                return prop
        return None

    def getPropertyConnections(self, prop: FakeProperty) -> FakeArray:
        return FakeArray(
            connection
            for connection in self.connections
            if connection.output is prop or connection.input is prop
        )

    def newPropertyConnection(
        self, output: FakeProperty, target: FakeNode, input_property: FakeProperty
    ) -> FakeConnection:
        connection = FakeConnection(self, output, target, input_property)
        self.connections.append(connection)
        target.connections.append(connection)
        return connection

    def getInputPropertyValueFromId(self, identifier: str) -> Optional[FakeValue]:
        return self.values.get(identifier)

    def setInputPropertyValueFromId(self, identifier: str, value: FakeValue) -> None:
        self.values[identifier] = value

    def setAnnotationPropertyValueFromId(self, identifier: str, value: FakeValue) -> None:
        self.annotations[identifier] = value

    def getAnnotationPropertyValueFromId(self, identifier: str) -> Optional[FakeValue]:
        return self.annotations.get(identifier)

    def getReferencedResource(self) -> Optional[FakeResource]:
        return self.referenced_resource


class FakeResource:
    def __init__(self, identifier: str, url: str, class_name: str = "SDSBSCompGraph") -> None:
        self.identifier = identifier
        self.url = url
        self.class_name = class_name
        self.package: Optional[FakePackage] = None

    def getIdentifier(self) -> str:
        return self.identifier

    def setIdentifier(self, value: str) -> None:
        self.identifier = value

    def getUrl(self) -> str:
        return self.url

    def getClassName(self) -> str:
        return self.class_name

    def getPackage(self) -> FakePackage:
        assert self.package is not None
        return self.package

    def delete(self) -> None:
        if self.package is not None:
            self.package.resources.remove(self)


class FakeGraph(FakeResource):
    def __init__(self, identifier: str, url: str = "pkg://demo/main") -> None:
        super().__init__(identifier, url, "SDSBSCompGraph")
        self.nodes = [FakeNode("node-1", "sbs::compositing::uniform", "Uniform")]
        image_input = FakeProperty("input", "Input", "image")
        amount_input = FakeProperty("amount", "Input", "float", connectable=False)
        image_output = FakeProperty("output", "Output", "image")
        self.definitions = [
            FakeDefinition(
                "sbs::compositing::uniform",
                "Uniform",
                "Uniform source",
                [image_input, amount_input, image_output],
            ),
            FakeDefinition(
                "sbs::compositing::blend",
                "Blend",
                "Blend inputs",
                [image_input, amount_input, image_output],
            ),
            FakeDefinition(
                "sbs::compositing::output",
                "Output",
                "Graph output",
                [
                    FakeProperty("input", "Input", "image"),
                    FakeProperty("output", "Output", "image"),
                ],
            ),
        ]
        self.deleted: list[FakeNode] = []
        self.graph_type = "substance"
        self.input_properties = [FakeProperty("$outputsize", "Input", "int2", connectable=False)]
        self.output_properties: list[FakeProperty] = []
        self.values = {"$outputsize": FakeValue("int2", [10, 10])}
        self.presets = [FakePreset("Default")]

    def getGraphType(self) -> str:
        return self.graph_type

    def setGraphType(self, value: str) -> None:
        self.graph_type = value

    def setIdentifier(self, value: str) -> None:
        self.identifier = value
        self.url = f"pkg://demo/{value}"

    def getUID(self) -> str:
        return "graph-uid"

    def getNodes(self) -> FakeArray:
        return FakeArray(self.nodes)

    def getNodeFromId(self, identifier: str) -> Optional[FakeNode]:
        return next((node for node in self.nodes if node.identifier == identifier), None)

    def getNodeDefinitions(self) -> FakeArray:
        return FakeArray(self.definitions)

    def getProperties(self, category: str) -> FakeArray:
        if category == "Input":
            return FakeArray(self.input_properties)
        if category == "Output":
            return FakeArray(self.output_properties)
        return FakeArray()

    def getPropertyValueFromId(self, identifier: str, category: str) -> Optional[FakeValue]:
        del category
        return self.values.get(identifier)

    def getPropertyFromId(self, identifier: str, category: str) -> Optional[FakeProperty]:
        return next(
            (prop for prop in self.getProperties(category) if prop.getId() == identifier),
            None,
        )

    def getInputPropertyValueFromId(self, identifier: str) -> Optional[FakeValue]:
        return self.values.get(identifier)

    def getPresets(self) -> FakeArray:
        return FakeArray(self.presets)

    def newNode(self, definition_id: str) -> FakeNode:
        if getattr(self, "fail_definition_id", None) == definition_id:
            raise RuntimeError("injected node creation failure")
        definition = next(item for item in self.definitions if item.identifier == definition_id)
        node = FakeNode("node-%s" % (len(self.nodes) + 1), definition_id, definition.label)
        self.nodes.append(node)
        return node

    def newInstanceNode(self, resource: FakeResource) -> FakeNode:
        node = FakeNode("node-%s" % (len(self.nodes) + 1), "instance", resource.identifier)
        node.referenced_resource = resource
        self.nodes.append(node)
        return node

    def deleteNode(self, node: FakeNode) -> None:
        self.nodes.remove(node)
        self.deleted.append(node)

    def delete(self) -> None:
        if self.package is not None:
            self.package.resources.remove(self)


class FakePackage:
    def __init__(self, file_path: str, uid: str, resources: list[FakeResource]) -> None:
        self.file_path = file_path
        self.uid = uid
        self.resources = resources
        for resource in resources:
            resource.package = self

    def getFilePath(self) -> str:
        return self.file_path

    def getUID(self) -> str:
        return self.uid

    def getChildrenResources(self, recursive: bool) -> FakeArray:
        assert recursive is True
        return FakeArray(self.resources)


class FakePackageMgr:
    def __init__(self, packages: list[FakePackage]) -> None:
        self.packages = packages
        self.saved: list[FakePackage] = []
        self.created_packages: list[FakePackage] = []
        self.saved_as: list[tuple[FakePackage, str]] = []

    def getPackages(self) -> FakeArray:
        return FakeArray(self.packages)

    def getUserPackages(self) -> FakeArray:
        return FakeArray(self.packages)

    def savePackage(self, package: FakePackage) -> None:
        self.saved.append(package)

    def newUserPackage(self) -> FakePackage:
        package = FakePackage("", "package-%s" % (len(self.packages) + 1), [])
        self.packages.append(package)
        self.created_packages.append(package)
        return package

    def savePackageAs(self, package: FakePackage, file_path: str) -> None:
        package.file_path = file_path
        self.saved_as.append((package, file_path))


class FakeUIMgr:
    def __init__(self, graph: Optional[FakeGraph]) -> None:
        self.graph = graph
        self.opened: list[FakeResource] = []

    def getCurrentGraph(self) -> Optional[FakeGraph]:
        return self.graph

    def getCurrentGraphSelectedNodes(self) -> FakeArray:
        return FakeArray(self.graph.nodes[:1] if self.graph else [])

    def openResourceInEditor(self, resource: FakeResource) -> None:
        self.opened.append(resource)


class FakeApplication:
    def __init__(self, version: str, package_mgr: FakePackageMgr, ui_mgr: FakeUIMgr) -> None:
        self.version = version
        self.package_mgr = package_mgr
        self.ui_mgr = ui_mgr

    def getVersion(self) -> str:
        return self.version

    def getPackageMgr(self) -> FakePackageMgr:
        return self.package_mgr

    def getUIMgr(self) -> FakeUIMgr:
        return self.ui_mgr


@dataclass
class FakeDesigner:
    application: FakeApplication
    package: FakePackage
    graph: FakeGraph
    library_resource: FakeResource
    adapter: FakeAdapter


def build_fake_designer(version: str = "16.0.3") -> FakeDesigner:
    graph = FakeGraph("main")
    library = FakeGraph(
        "sample_generator",
        "pkg://library/sample_generator?dependency=123",
    )
    library.input_properties = [FakeProperty("input", "Input", "image")]
    library.output_properties = [FakeProperty("output", "Output", "image")]
    package = FakePackage("C:/demo.sbs", "package-uid", [graph, library])
    manager = FakePackageMgr([package])
    application = FakeApplication(version, manager, FakeUIMgr(graph))
    return FakeDesigner(application, package, graph, library, FakeAdapter())
