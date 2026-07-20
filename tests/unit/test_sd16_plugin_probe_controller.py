from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from tests.manual.sd16_plugin_probe_controller import (
    PluginProbeController,
    PluginProbeRuntime,
)


class FakeSignal:
    def __init__(self) -> None:
        self.callback = None

    def connect(self, callback) -> None:
        self.callback = callback


class FakeTimer:
    def __init__(self) -> None:
        self.timeout = FakeSignal()
        self.started = False
        self.stopped = False
        self.interval = None

    def setInterval(self, value: int) -> None:
        self.interval = value

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def fire(self) -> None:
        assert self.timeout.callback is not None
        self.timeout.callback()


class FakeRuntime:
    def __init__(self, report: dict, current_path: str | None = None) -> None:
        self.report = report
        self.current_path = current_path
        self.calls = 0

    def current_graph_path(self) -> str | None:
        return self.current_path

    def run(self) -> dict:
        self.calls += 1
        return self.report


class RaisingRuntime:
    def __init__(self, error: BaseException, current_path: str) -> None:
        self.error = error
        self.current_path = current_path

    def current_graph_path(self) -> str:
        return self.current_path

    def run(self) -> dict:
        raise self.error


def make_passed() -> dict:
    return {"passed": True, "evidence": True}


def make_controller(
    tmp_path: Path,
    timer: FakeTimer,
    runtime,
    quit_calls: list[bool],
) -> PluginProbeController:
    return PluginProbeController(
        runtime=runtime,
        timer=timer,
        active_package=tmp_path / "owned.sbs",
        report_path=tmp_path / "report.json",
        workspace=tmp_path,
        quit_callback=lambda: quit_calls.append(True),
        timeout=10.0,
        time_fn=lambda: 0.0,
    )


def make_runtime(tmp_path: Path):
    plugin_dir = tmp_path / "plugin" / "substance_designer_mcp_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "pluginInfo.json").write_text('{"version":"1.0.0"}', encoding="utf-8")
    session_path = tmp_path / "session.json"
    session_path.write_text(
        json.dumps(
            {
                "protocol_version": "1.0",
                "host": "127.0.0.1",
                "port": 9876,
                "pid": 123,
                "designer_version": "16.0.3",
                "plugin_version": "1.0.0",
                "token": "must-not-leak",
            }
        ),
        encoding="utf-8",
    )
    plugin = MagicMock()
    plugin.getStatus.side_effect = ("Loaded", "Unloaded")
    plugin.getLastErrorMessage.return_value = ""
    plugin_mgr = MagicMock()
    plugin_mgr.checkPluginCompatibility.return_value = None
    plugin_mgr.loadPlugin.return_value = plugin
    application = MagicMock()
    application.getPluginMgr.return_value = plugin_mgr
    application.getVersion.return_value = "16.0.3"
    runtime = PluginProbeRuntime(
        application=application,
        plugin_parent=tmp_path / "plugin",
        session_path=session_path,
        loaded_status="Loaded",
        unloaded_status="Unloaded",
        port_closed_fn=lambda _port: True,
    )
    return runtime, plugin_mgr, plugin


def test_runtime_uses_official_lifecycle_and_redacts_session(tmp_path: Path) -> None:
    runtime, plugin_mgr, plugin = make_runtime(tmp_path)

    report = runtime.run()

    plugin_mgr.checkPluginCompatibility.assert_called_once()
    plugin_mgr.loadPlugin.assert_called_once_with(
        "substance_designer_mcp_plugin",
        str(tmp_path / "plugin" / "substance_designer_mcp_plugin"),
    )
    plugin_mgr.unloadPlugin.assert_called_once_with(plugin)
    assert report["checks"]["plugin_unloaded"]["passed"] is True
    assert "must-not-leak" not in json.dumps(report)
    assert "token" not in json.dumps(report)


def test_start_returns_without_running_runtime(tmp_path: Path) -> None:
    timer = FakeTimer()
    runtime = FakeRuntime({"checks": {}})
    controller = PluginProbeController(
        runtime=runtime,
        timer=timer,
        active_package=tmp_path / "owned.sbs",
        report_path=tmp_path / "report.json",
        workspace=tmp_path,
        quit_callback=lambda: None,
        timeout=10.0,
        time_fn=lambda: 0.0,
    )

    controller.start()

    assert timer.started is True
    assert timer.interval == 100
    assert runtime.calls == 0


def test_timer_runs_probe_once_writes_report_and_requests_quit(tmp_path: Path) -> None:
    timer = FakeTimer()
    runtime = FakeRuntime(
        {"phase": "plugin_manager", "checks": {"plugin_loaded": make_passed()}},
        str(tmp_path / "owned.sbs"),
    )
    quit_calls = []
    controller = make_controller(tmp_path, timer, runtime, quit_calls)

    controller.start()
    timer.fire()
    timer.fire()

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert runtime.calls == 1
    assert report["checks"]["plugin_loaded"]["passed"] is True
    assert report["checks"]["quit_requested"]["passed"] is True
    assert timer.stopped is True
    assert quit_calls == [True]


def test_runtime_error_is_reported_and_requests_quit(tmp_path: Path) -> None:
    timer = FakeTimer()
    quit_calls = []
    controller = make_controller(
        tmp_path,
        timer,
        RaisingRuntime(RuntimeError("probe failed"), str(tmp_path / "owned.sbs")),
        quit_calls,
    )

    controller.start()
    timer.fire()

    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["error"]["code"] == "PLUGIN_PROBE_RUNTIME_ERROR"
    assert quit_calls == [True]


def test_timer_waits_until_the_owned_package_is_current(tmp_path: Path) -> None:
    timer = FakeTimer()
    runtime = FakeRuntime({"phase": "plugin_manager", "checks": {}})
    quit_calls = []
    controller = make_controller(tmp_path, timer, runtime, quit_calls)

    controller.start()
    timer.fire()

    assert runtime.calls == 0
    assert quit_calls == []

    runtime.current_path = str(tmp_path / "owned.sbs")
    timer.fire()

    assert runtime.calls == 1
    assert quit_calls == [True]
