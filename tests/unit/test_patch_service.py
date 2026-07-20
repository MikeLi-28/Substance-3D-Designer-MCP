from __future__ import annotations

import pytest
from substance_designer_mcp_plugin.errors import ErrorCode, PluginError
from substance_designer_mcp_plugin.services.container import ServiceContainer

from tests.fakes.sd_api import build_fake_designer


def _setup() -> tuple[ServiceContainer, object, dict]:
    fake = build_fake_designer()
    services = ServiceContainer(fake.application, fake.adapter)
    graph = services.graph.get_active_graph()["graph"]
    return services, fake, graph


def _valid_patch() -> dict:
    return {
        "version": "1.0",
        "nodes": [
            {
                "alias": "source",
                "kind": "atomic",
                "definition_id": "sbs::compositing::uniform",
                "position": [0, 0],
            },
            {
                "alias": "blend",
                "kind": "atomic",
                "definition_id": "sbs::compositing::blend",
                "position": [160, 0],
            },
        ],
        "parameters": [{"node": "source", "property_id": "amount", "value": 0.75}],
        "connections": [
            {
                "source_node": "source",
                "source_property": "output",
                "target_node": "blend",
                "target_property": "input",
            }
        ],
    }


def test_validate_patch_is_read_only_and_reports_counts() -> None:
    services, fake, graph = _setup()
    before = len(fake.graph.nodes)

    result = services.patch.validate(graph, _valid_patch())

    assert result == {
        "valid": True,
        "patch_version": "1.0",
        "node_count": 2,
        "parameter_count": 1,
        "connection_count": 1,
    }
    assert len(fake.graph.nodes) == before


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"version": "2.0"}, ErrorCode.INVALID_PARAMETER),
        (
            {
                "nodes": [
                    {
                        "alias": "same",
                        "kind": "atomic",
                        "definition_id": "sbs::compositing::uniform",
                        "position": [0, 0],
                    },
                    {
                        "alias": "same",
                        "kind": "atomic",
                        "definition_id": "sbs::compositing::blend",
                        "position": [160, 0],
                    },
                ]
            },
            ErrorCode.INVALID_PARAMETER,
        ),
        (
            {
                "nodes": [
                    {
                        "alias": "missing",
                        "kind": "atomic",
                        "definition_id": "sbs::compositing::missing",
                        "position": [0, 0],
                    }
                ]
            },
            ErrorCode.NODE_DEFINITION_NOT_FOUND,
        ),
        (
            {"parameters": [{"node": "source", "property_id": "missing", "value": 1.0}]},
            ErrorCode.PROPERTY_NOT_FOUND,
        ),
    ],
)
def test_validate_patch_rejects_invalid_schema_or_runtime_contract(
    change: dict, code: ErrorCode
) -> None:
    services, _fake, graph = _setup()
    patch = _valid_patch()
    patch.update(change)

    with pytest.raises(PluginError) as caught:
        services.patch.validate(graph, patch)

    assert caught.value.code is code


def test_validate_patch_rejects_type_mismatch_duplicate_target_and_cycle() -> None:
    services, fake, graph = _setup()
    blend_definition = next(
        definition
        for definition in fake.graph.definitions
        if definition.getId() == "sbs::compositing::blend"
    )
    blend_input = blend_definition.getPropertyFromId("input", "Input")
    assert blend_input is not None
    blend_input.type = blend_input.type.__class__("float")
    with pytest.raises(PluginError) as mismatch:
        services.patch.validate(graph, _valid_patch())
    assert mismatch.value.code is ErrorCode.CONNECTION_NOT_ALLOWED

    blend_input.type = blend_input.type.__class__("image")
    duplicate = _valid_patch()
    duplicate["connections"].append(
        {
            "source_node": "blend",
            "source_property": "output",
            "target_node": "blend",
            "target_property": "input",
        }
    )
    with pytest.raises(PluginError) as duplicate_target:
        services.patch.validate(graph, duplicate)
    assert duplicate_target.value.code is ErrorCode.CONNECTION_ALREADY_EXISTS

    cycle = _valid_patch()
    cycle["connections"].append(
        {
            "source_node": "blend",
            "source_property": "output",
            "target_node": "source",
            "target_property": "input",
        }
    )
    with pytest.raises(PluginError) as cycle_error:
        services.patch.validate(graph, cycle)
    assert cycle_error.value.code is ErrorCode.CONNECTION_NOT_ALLOWED


def test_validate_patch_resolves_instance_resource_without_mutation() -> None:
    services, fake, graph = _setup()
    resource = services.library.search("sample", category=None, limit=10)["resources"][0]
    patch = {
        "version": "1.0",
        "nodes": [
            {
                "alias": "library_node",
                "kind": "instance",
                "resource": resource,
                "position": [0, 0],
            }
        ],
        "parameters": [],
        "connections": [],
    }
    before = len(fake.graph.nodes)

    assert services.patch.validate(graph, patch)["valid"] is True
    assert len(fake.graph.nodes) == before


def test_apply_patch_creates_parameters_and_connections() -> None:
    services, fake, graph = _setup()
    before = len(fake.graph.nodes)

    result = services.patch.apply(graph, _valid_patch())

    assert result["applied"] is True
    assert set(result["node_map"]) == {"source", "blend"}
    assert result["connection_count"] == 1
    assert len(fake.graph.nodes) == before + 2
    source = fake.graph.getNodeFromId(result["node_map"]["source"]["node_identifier"])
    assert source is not None
    assert source.values["amount"].get() == 0.75


def test_apply_patch_rolls_back_every_created_node_after_runtime_failure() -> None:
    services, fake, graph = _setup()
    before_ids = [node.getIdentifier() for node in fake.graph.nodes]
    fake.graph.fail_definition_id = "sbs::compositing::blend"

    with pytest.raises(PluginError) as caught:
        services.patch.apply(graph, _valid_patch())

    assert caught.value.code is ErrorCode.SD_API_ERROR
    assert caught.value.details["rolled_back_nodes"] == 1
    assert [node.getIdentifier() for node in fake.graph.nodes] == before_ids
