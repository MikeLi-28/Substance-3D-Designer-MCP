from __future__ import annotations

import threading
import time
from typing import Any

import pytest
from substance_designer_mcp_plugin.commands.registry import CommandRegistry
from substance_designer_mcp_plugin.errors import ErrorCode, PluginError


def test_registry_rejects_duplicate_command() -> None:
    registry = CommandRegistry()
    registry.register("sd_ping", lambda arguments: arguments)

    with pytest.raises(ValueError, match="already registered"):
        registry.register("sd_ping", lambda arguments: arguments)


def test_registry_returns_stable_error_for_unknown_command() -> None:
    registry = CommandRegistry()

    with pytest.raises(PluginError) as caught:
        registry.execute("execute_python", {})

    assert caught.value.code is ErrorCode.UNSUPPORTED_CAPABILITY


def test_destructive_command_requires_explicit_confirmation() -> None:
    registry = CommandRegistry()
    registry.register("sd_delete_nodes", lambda arguments: arguments, destructive=True)

    with pytest.raises(PluginError) as caught:
        registry.execute("sd_delete_nodes", {"confirm": False})

    assert caught.value.code is ErrorCode.DESTRUCTIVE_CONFIRMATION_REQUIRED


def test_validator_runs_before_handler() -> None:
    calls: list[dict[str, Any]] = []
    registry = CommandRegistry()

    def validator(arguments: dict[str, Any]) -> dict[str, Any]:
        return {"value": int(arguments["value"])}

    registry.register("normalized", calls.append, validator=validator)

    registry.execute("normalized", {"value": "7"})

    assert calls == [{"value": 7}]


def test_write_commands_are_serialized() -> None:
    registry = CommandRegistry()
    start = threading.Barrier(3)
    active = 0
    maximum_active = 0
    guard = threading.Lock()

    def write_handler(arguments: dict[str, Any]) -> dict[str, Any]:
        nonlocal active, maximum_active
        del arguments
        with guard:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.03)
        with guard:
            active -= 1
        return {}

    registry.register("write", write_handler, write=True)

    def worker() -> None:
        start.wait()
        registry.execute("write", {})

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    start.wait()
    for thread in threads:
        thread.join()

    assert maximum_active == 1
