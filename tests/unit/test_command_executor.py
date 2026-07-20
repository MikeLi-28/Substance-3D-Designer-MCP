from __future__ import annotations

import pytest
from substance_designer_mcp_plugin.commands.executor import build_command_executor
from substance_designer_mcp_plugin.errors import ErrorCode, PluginError
from substance_designer_mcp_plugin.services.container import ServiceContainer

from tests.fakes.sd_api import build_fake_designer

EXPECTED_COMMANDS = {
    "sd_ping",
    "sd_get_application_info",
    "sd_get_capabilities",
    "sd_list_packages",
    "sd_get_active_graph",
    "sd_list_graph_nodes",
    "sd_get_selection",
    "sd_get_node",
    "sd_list_node_properties",
    "sd_search_library",
    "sd_create_node",
    "sd_create_instance_node",
    "sd_move_nodes",
    "sd_delete_nodes",
    "sd_connect_nodes",
    "sd_disconnect_nodes",
    "sd_set_node_parameter",
    "sd_save_package",
    "sd_create_package",
    "sd_create_graph",
    "sd_list_node_definitions",
    "sd_get_graph_snapshot",
    "sd_open_graph",
    "sd_create_graph_output",
    "sd_save_package_as",
    "sd_validate_graph_patch",
    "sd_apply_graph_patch",
    "sd_import_bitmap",
    "sd_export_package_sbsar",
}


def _executor() -> tuple[object, object]:
    fake = build_fake_designer()
    services = ServiceContainer(fake.application, fake.adapter)
    return build_command_executor(services), fake


def test_executor_registers_exact_v110_command_surface() -> None:
    executor, _fake = _executor()

    assert set(executor.names()) == EXPECTED_COMMANDS
    assert not {"execute_python", "run_script", "shell", "terminal"} & set(executor.names())


def test_executor_routes_system_and_graph_reads() -> None:
    executor, _fake = _executor()

    ping = executor.execute("sd_ping", {})
    active = executor.execute("sd_get_active_graph", {})
    nodes = executor.execute(
        "sd_list_graph_nodes",
        {"graph": active["graph"], "detail": "summary", "offset": 0, "limit": 20},
    )

    assert ping["plugin_running"] is True
    assert ping["protocol_version"] == "1.0"
    assert ping["verification_status"] == "verified"
    assert ping["compatibility_status"] == "supported"
    assert ping["verified_versions"] == ["16.0.3"]
    assert ping["warning"] is None
    assert nodes["total"] == 1


def test_executor_rejects_unknown_arguments_before_service() -> None:
    executor, _fake = _executor()

    with pytest.raises(PluginError) as caught:
        executor.execute("sd_get_active_graph", {"surprise": True})

    assert caught.value.code is ErrorCode.INVALID_PARAMETER


def test_delete_and_save_require_confirmation() -> None:
    executor, _fake = _executor()
    active = executor.execute("sd_get_active_graph", {})
    packages = executor.execute("sd_list_packages", {})

    with pytest.raises(PluginError) as delete_error:
        executor.execute(
            "sd_delete_nodes",
            {"graph": active["graph"], "node_identifiers": ["node-1"], "confirm": False},
        )
    with pytest.raises(PluginError) as save_error:
        executor.execute("sd_save_package", {"package": packages["packages"][0], "confirm": False})

    assert delete_error.value.code is ErrorCode.DESTRUCTIVE_CONFIRMATION_REQUIRED
    assert save_error.value.code is ErrorCode.DESTRUCTIVE_CONFIRMATION_REQUIRED


def test_executor_routes_create_move_parameter_and_save() -> None:
    executor, _fake = _executor()
    graph = executor.execute("sd_get_active_graph", {})["graph"]
    created = executor.execute(
        "sd_create_node",
        {"graph": graph, "definition_id": "sbs::compositing::blend", "position": [32, 64]},
    )
    moved = executor.execute(
        "sd_move_nodes",
        {
            "graph": graph,
            "moves": [
                {"node_identifier": created["node"]["node_identifier"], "position": [96, 128]}
            ],
        },
    )
    node = executor.execute("sd_get_node", {"node": created["node"], "detail": "full"})
    parameter = executor.execute(
        "sd_set_node_parameter",
        {"node": created["node"], "property_id": "amount", "value": 0.25},
    )
    package = executor.execute("sd_list_packages", {})["packages"][0]
    saved = executor.execute("sd_save_package", {"package": package, "confirm": True})

    assert moved["nodes"][0]["position"] == [96.0, 128.0]
    assert node["properties"]
    assert parameter["after"]["value"] == 0.25
    assert saved["saved"] is True


def test_executor_routes_public_authoring_core() -> None:
    executor, fake = _executor()
    package = executor.execute("sd_create_package", {})["package"]
    created = executor.execute(
        "sd_create_graph",
        {"package": package, "identifier": "public_graph"},
    )
    graph = created["graph"]
    definitions = executor.execute(
        "sd_list_node_definitions",
        {"graph": graph, "query": "blend", "offset": 0, "limit": 10},
    )
    snapshot = executor.execute(
        "sd_get_graph_snapshot",
        {"graph": graph, "include_values": True, "limit": 20},
    )
    opened = executor.execute("sd_open_graph", {"graph": graph})

    assert definitions["definitions"][0]["definition_id"] == "sbs::compositing::blend"
    assert snapshot["schema_version"] == "1.0"
    assert opened["opened"] is True
    assert fake.application.ui_mgr.opened[-1].getIdentifier() == "public_graph"


def test_executor_rejects_invalid_authoring_arguments_before_mutation() -> None:
    executor, fake = _executor()
    package = executor.execute("sd_list_packages", {})["packages"][0]
    graph = executor.execute("sd_get_active_graph", {})["graph"]
    before = len(fake.graph.nodes)

    with pytest.raises(PluginError) as bad_limit:
        executor.execute(
            "sd_list_node_definitions",
            {"graph": graph, "query": "", "offset": 0, "limit": 1000},
        )
    with pytest.raises(PluginError) as bad_output:
        executor.execute(
            "sd_create_graph_output",
            {
                "graph": graph,
                "identifier": "bad output",
                "label": "Bad",
                "description": "",
                "group": "",
                "usages": [],
                "position": [0, 0],
            },
        )
    with pytest.raises(PluginError) as no_confirm:
        executor.execute(
            "sd_save_package_as",
            {
                "package": package,
                "file_path": "C:/output.sbs",
                "overwrite": False,
                "confirm": False,
            },
        )

    assert bad_limit.value.code is ErrorCode.INVALID_PARAMETER
    assert bad_output.value.code is ErrorCode.INVALID_PARAMETER
    assert no_confirm.value.code is ErrorCode.DESTRUCTIVE_CONFIRMATION_REQUIRED
    assert len(fake.graph.nodes) == before
