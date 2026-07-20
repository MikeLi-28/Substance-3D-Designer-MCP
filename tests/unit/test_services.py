from __future__ import annotations

from pathlib import Path

import pytest
from substance_designer_mcp_plugin.errors import ErrorCode, PluginError
from substance_designer_mcp_plugin.services.container import ServiceContainer

from tests.fakes.sd_api import FakeValue, build_fake_designer


def _container() -> tuple[ServiceContainer, object]:
    fake = build_fake_designer()
    return ServiceContainer(fake.application, fake.adapter), fake


def test_application_graph_selection_and_package_reads_are_structured() -> None:
    services, fake = _container()

    info = services.application.get_info()
    active = services.graph.get_active_graph()
    selection = services.selection.get_selection()
    packages = services.package.list_packages()

    assert info["designer_version"] == "16.0.3"
    assert info["verification_status"] == "verified"
    assert info["compatibility_status"] == "supported"
    assert info["verified_versions"] == ["16.0.3"]
    assert info["warning"] is None
    assert info["open_package_count"] == 1
    assert active["graph"]["graph_identifier"] == "main"
    assert active["node_count"] == 1
    assert selection["nodes"][0]["node_identifier"] == "node-1"
    assert packages["packages"][0]["file_path"] == "C:/demo.sbs"
    assert fake.graph.getNodes().getSize() == 1


def test_node_listing_and_properties_are_bounded_and_structured() -> None:
    services, _fake = _container()
    graph_ref = services.graph.get_active_graph()["graph"]
    nodes = services.graph.list_nodes(graph_ref, detail="summary", offset=0, limit=20)
    node_ref = nodes["nodes"][0]

    node = services.node.get_node(node_ref, detail="full")
    properties = services.node.list_properties(node_ref)

    assert node["node"]["definition_id"] == "sbs::compositing::uniform"
    assert {item["direction"] for item in properties["properties"]} == {"input", "output"}
    assert all("type_id" in item for item in properties["properties"])


def test_full_graph_node_listing_expands_position_and_properties() -> None:
    services, _fake = _container()
    graph_ref = services.graph.get_active_graph()["graph"]

    result = services.graph.list_nodes(graph_ref, detail="full", offset=0, limit=20)

    assert result["nodes"][0]["node"]["node_identifier"] == "node-1"
    assert result["nodes"][0]["position"] == [0.0, 0.0]
    assert result["nodes"][0]["properties"]


def test_library_search_removes_dependency_from_stable_key() -> None:
    services, _fake = _container()

    result = services.library.search("sample", category=None, limit=20)

    assert result["resources"][0]["resource_identifier"] == "sample_generator"
    assert "dependency=" not in result["resources"][0]["stable_key"]
    assert "dependency=" in result["resources"][0]["runtime_url"]


def test_create_move_delete_node_and_confirmation_boundary() -> None:
    services, fake = _container()
    graph_ref = services.graph.get_active_graph()["graph"]

    created = services.node.create_atomic(graph_ref, "sbs::compositing::blend", [32.0, 64.0])
    moved = services.node.move_nodes(
        graph_ref, [{"node_identifier": created["node"]["node_identifier"], "position": [96, 128]}]
    )
    deleted = services.node.delete_nodes(graph_ref, [created["node"]["node_identifier"]])

    assert created["node"]["definition_id"] == "sbs::compositing::blend"
    assert moved["nodes"][0]["position"] == [96.0, 128.0]
    assert deleted["deleted"][0]["node_identifier"] == created["node"]["node_identifier"]
    assert len(fake.graph.deleted) == 1


def test_create_atomic_rejects_unverified_definition() -> None:
    services, _fake = _container()
    graph_ref = services.graph.get_active_graph()["graph"]

    with pytest.raises(PluginError) as caught:
        services.node.create_atomic(graph_ref, "sbs::compositing::guessed", [0, 0])

    assert caught.value.code is ErrorCode.NODE_DEFINITION_NOT_FOUND


def test_create_instance_resolves_runtime_resource_from_stable_ref() -> None:
    services, _fake = _container()
    graph_ref = services.graph.get_active_graph()["graph"]
    resource = services.library.search("sample", category=None, limit=20)["resources"][0]

    result = services.node.create_instance(graph_ref, resource, [10, 20])

    assert result["node"]["label"] == "sample_generator"


def test_connect_disconnect_uses_runtime_properties_and_detects_duplicates() -> None:
    services, fake = _container()
    graph_ref = services.graph.get_active_graph()["graph"]
    created = services.node.create_atomic(graph_ref, "sbs::compositing::blend", [0, 0])

    connected = services.connection.connect(
        graph_ref, "node-1", "output", created["node"]["node_identifier"], "input"
    )
    with pytest.raises(PluginError) as duplicate:
        services.connection.connect(
            graph_ref, "node-1", "output", created["node"]["node_identifier"], "input"
        )
    disconnected = services.connection.disconnect(
        graph_ref, "node-1", "output", created["node"]["node_identifier"], "input"
    )

    assert connected["connection"]["source_property"] == "output"
    assert duplicate.value.code is ErrorCode.CONNECTION_ALREADY_EXISTS
    assert disconnected["disconnected"] is True
    assert fake.graph.nodes[0].connections[0].disconnected is True


def test_duplicate_connection_matches_distinct_wrappers_by_node_identifier() -> None:
    services, fake = _container()
    graph_ref = services.graph.get_active_graph()["graph"]
    created = services.node.create_atomic(graph_ref, "sbs::compositing::blend", [0, 0])
    target_id = created["node"]["node_identifier"]
    services.connection.connect(graph_ref, "node-1", "output", target_id, "input")

    class NodeProxy:
        def getIdentifier(self) -> str:
            return target_id

    fake.graph.nodes[0].connections[0].target = NodeProxy()

    with pytest.raises(PluginError) as duplicate:
        services.connection.connect(graph_ref, "node-1", "output", target_id, "input")

    assert duplicate.value.code is ErrorCode.CONNECTION_ALREADY_EXISTS


def test_parameter_write_reads_runtime_type_and_returns_before_after() -> None:
    services, fake = _container()
    node_ref = services.graph.list_nodes(
        services.graph.get_active_graph()["graph"], detail="summary", offset=0, limit=20
    )["nodes"][0]

    result = services.parameter.set_parameter(node_ref, "amount", 0.75)

    assert result["before"] == {"type": "float", "value": 0.5}
    assert result["after"] == {"type": "float", "value": 0.75}
    assert isinstance(fake.graph.nodes[0].values["amount"], FakeValue)


def test_parameter_write_rejects_complex_unverified_type() -> None:
    services, fake = _container()
    fake.graph.nodes[0].input_properties.append(
        fake.graph.nodes[0]
        .input_properties[0]
        .__class__("gradient", "Input", "gradient", connectable=False)
    )
    fake.graph.nodes[0].values["gradient"] = FakeValue("gradient", {})
    node_ref = services.graph.list_nodes(
        services.graph.get_active_graph()["graph"], detail="summary", offset=0, limit=20
    )["nodes"][0]

    with pytest.raises(PluginError) as caught:
        services.parameter.set_parameter(node_ref, "gradient", {})

    assert caught.value.code is ErrorCode.UNSUPPORTED_CAPABILITY


def test_save_requires_existing_path_and_saves_only_selected_package() -> None:
    services, fake = _container()
    package_ref = services.package.list_packages()["packages"][0]

    result = services.package.save(package_ref)

    assert result["saved"] is True
    assert fake.application.package_mgr.saved == [fake.package]


def test_create_package_and_graph_use_structured_references() -> None:
    services, fake = _container()

    package_result = services.authoring.create_package()
    graph_result = services.authoring.create_graph(package_result["package"], "fresh_graph", None)

    assert package_result["package"]["package_url"].startswith("session-package://")
    assert graph_result["graph"]["graph_identifier"] == "fresh_graph"
    assert graph_result["graph"]["package_url"] == package_result["package"]["package_url"]
    assert fake.application.package_mgr.created_packages[-1].resources[-1].getIdentifier() == (
        "fresh_graph"
    )


def test_create_graph_rejects_duplicate_or_invalid_identifier() -> None:
    services, _fake = _container()
    package = services.package.list_packages()["packages"][0]

    with pytest.raises(PluginError) as duplicate:
        services.authoring.create_graph(package, "main", None)
    with pytest.raises(PluginError) as invalid:
        services.authoring.create_graph(package, "has spaces", None)

    assert duplicate.value.code is ErrorCode.INVALID_PARAMETER
    assert invalid.value.code is ErrorCode.INVALID_PARAMETER


def test_list_definitions_filters_and_paginates_runtime_catalog() -> None:
    services, _fake = _container()
    graph = services.graph.get_active_graph()["graph"]

    result = services.authoring.list_definitions(graph, query="blend", offset=0, limit=10)

    assert result["definitions"] == [
        {
            "definition_id": "sbs::compositing::blend",
            "label": "Blend",
            "description": "Blend inputs",
        }
    ]
    assert result["total"] == 1
    assert result["truncated"] is False


def test_graph_snapshot_contains_connections_graph_properties_and_presets() -> None:
    services, _fake = _container()
    graph = services.graph.get_active_graph()["graph"]
    created = services.node.create_atomic(graph, "sbs::compositing::blend", [100, 0])
    services.connection.connect(
        graph,
        "node-1",
        "output",
        created["node"]["node_identifier"],
        "input",
    )

    snapshot = services.authoring.snapshot(graph, include_values=True, limit=20)

    assert snapshot["schema_version"] == "1.0"
    assert len(snapshot["nodes"]) == 2
    assert snapshot["connections"] == [
        {
            "source_node": "node-1",
            "source_property": "output",
            "target_node": created["node"]["node_identifier"],
            "target_property": "input",
        }
    ]
    assert snapshot["graph_inputs"][0]["property_id"] == "$outputsize"
    assert snapshot["presets"][0]["label"] == "Default"


def test_graph_snapshot_only_returns_connections_internal_to_bounded_node_page() -> None:
    services, _fake = _container()
    graph = services.graph.get_active_graph()["graph"]
    created = services.node.create_atomic(graph, "sbs::compositing::blend", [100, 0])
    services.connection.connect(
        graph,
        "node-1",
        "output",
        created["node"]["node_identifier"],
        "input",
    )

    snapshot = services.authoring.snapshot(graph, include_values=False, limit=1)

    assert snapshot["truncated"] is True
    assert snapshot["connections"] == []


def test_open_graph_uses_official_ui_manager_call() -> None:
    services, fake = _container()
    graph = services.graph.get_active_graph()["graph"]

    result = services.authoring.open_graph(graph)

    assert result == {"opened": True, "graph": graph}
    assert fake.application.ui_mgr.opened == [fake.graph]


def test_create_output_writes_identifier_label_and_real_usage_array() -> None:
    services, fake = _container()
    graph = services.graph.get_active_graph()["graph"]

    result = services.authoring.create_output(
        graph,
        "basecolor",
        "Base Color",
        "Material base color",
        "Material",
        [{"name": "baseColor", "components": "RGBA", "color_space": "sRGB"}],
        [640, 0],
    )

    node = fake.graph.getNodeFromId(result["node"]["node_identifier"])
    assert node is not None
    assert node.annotations["identifier"].get() == "basecolor"
    assert node.annotations["label"].get() == "Base Color"
    assert node.annotations["usages"].get() == [
        {"name": "baseColor", "components": "RGBA", "color_space": "sRGB"}
    ]


def test_create_output_rejects_duplicate_identifier_without_new_node() -> None:
    services, fake = _container()
    graph = services.graph.get_active_graph()["graph"]
    args = (
        graph,
        "height",
        "Height",
        "",
        "",
        [{"name": "height", "components": "L", "color_space": "Raw"}],
        [640, 0],
    )
    services.authoring.create_output(*args)
    before = len(fake.graph.nodes)

    with pytest.raises(PluginError) as caught:
        services.authoring.create_output(*args)

    assert caught.value.code is ErrorCode.INVALID_PARAMETER
    assert len(fake.graph.nodes) == before


def test_create_output_rejects_invalid_usage_and_non_finite_position_before_mutation() -> None:
    services, fake = _container()
    graph = services.graph.get_active_graph()["graph"]
    before = len(fake.graph.nodes)

    with pytest.raises(PluginError) as usage:
        services.authoring.create_output(
            graph,
            "basecolor",
            "Base Color",
            "",
            "",
            [{"name": "baseColor", "components": "RGBA"}],
            [0, 0],
        )
    with pytest.raises(PluginError) as position:
        services.authoring.create_output(
            graph,
            "basecolor",
            "Base Color",
            "",
            "",
            [{"name": "baseColor", "components": "RGBA", "color_space": "sRGB"}],
            [float("inf"), 0],
        )

    assert usage.value.code is ErrorCode.INVALID_PARAMETER
    assert position.value.code is ErrorCode.INVALID_PARAMETER
    assert len(fake.graph.nodes) == before


def test_save_as_requires_absolute_sbs_path_existing_parent_and_overwrite_opt_in(
    tmp_path: Path,
) -> None:
    services, fake = _container()
    package = services.package.list_packages()["packages"][0]
    target = tmp_path / "saved.sbs"

    result = services.package.save_as(package, str(target), overwrite=False)
    saved_package = result["package"]
    target.write_text("occupied", encoding="utf-8")
    with pytest.raises(PluginError) as exists:
        services.package.save_as(saved_package, str(target), overwrite=False)
    result_overwrite = services.package.save_as(saved_package, str(target), overwrite=True)
    with pytest.raises(PluginError) as relative:
        services.package.save_as(saved_package, "relative.sbs", overwrite=False)
    with pytest.raises(PluginError) as suffix:
        services.package.save_as(saved_package, str(tmp_path / "wrong.txt"), overwrite=False)
    with pytest.raises(PluginError) as missing_parent:
        services.package.save_as(
            saved_package,
            str(tmp_path / "missing" / "saved.sbs"),
            overwrite=False,
        )
    with pytest.raises(PluginError) as overwrite_type:
        services.package.save_as(saved_package, str(target), overwrite="yes")  # type: ignore[arg-type]

    assert result["saved"] is True
    assert result_overwrite["saved"] is True
    assert fake.application.package_mgr.saved_as[-1][1] == str(target.resolve())
    assert exists.value.code is ErrorCode.INVALID_PARAMETER
    assert relative.value.code is ErrorCode.INVALID_PARAMETER
    assert suffix.value.code is ErrorCode.INVALID_PARAMETER
    assert missing_parent.value.code is ErrorCode.INVALID_PARAMETER
    assert overwrite_type.value.code is ErrorCode.INVALID_PARAMETER
