from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from substance_designer_mcp_plugin.bridge.main_thread_dispatcher import MainThreadDispatcher
from substance_designer_mcp_plugin.errors import ErrorCode, PluginError


class ImmediateInvoker:
    def post(self, callback: Callable[[], None]) -> None:
        callback()


class DroppingInvoker:
    def post(self, callback: Callable[[], None]) -> None:
        del callback


def test_dispatcher_executes_request_once_and_returns_result() -> None:
    calls: list[int] = []
    dispatcher = MainThreadDispatcher(invoker=ImmediateInvoker())

    result = dispatcher.call(lambda value: calls.append(value) or {"value": value}, 7, timeout=1)

    assert result == {"value": 7}
    assert calls == [7]


def test_dispatcher_propagates_main_thread_exception() -> None:
    dispatcher = MainThreadDispatcher(invoker=ImmediateInvoker())

    def fail() -> dict[str, Any]:
        raise PluginError(ErrorCode.NO_ACTIVE_GRAPH, "No graph.")

    with pytest.raises(PluginError) as caught:
        dispatcher.call(fail, timeout=1)

    assert caught.value.code is ErrorCode.NO_ACTIVE_GRAPH


def test_dispatcher_timeout_is_structured() -> None:
    dispatcher = MainThreadDispatcher(invoker=DroppingInvoker())

    with pytest.raises(PluginError) as caught:
        dispatcher.call(lambda: {}, timeout=0.01)

    assert caught.value.code is ErrorCode.REQUEST_TIMEOUT
