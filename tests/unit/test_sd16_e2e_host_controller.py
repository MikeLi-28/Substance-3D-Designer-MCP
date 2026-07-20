from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, call

from tests.manual.sd16_e2e_controller import (
    DesignerHostRuntime,
    HostController,
    HostPaths,
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
    def __init__(self, current_path: str | None) -> None:
        self.current_path = current_path
        self.prepared = False
        self.cleaned = False

    def current_graph_path(self) -> str | None:
        return self.current_path

    def prepare(self) -> dict:
        self.prepared = True
        return {
            "checks": {
                "fixture_loaded": {"passed": True, "evidence": "owned"},
                "active_graph_ready": {"passed": True, "evidence": "owned"},
                "library_loaded": {"passed": True, "evidence": "library"},
                "plugin_loaded": {"passed": True, "evidence": "Loaded"},
                "session_created": {"passed": True, "evidence": True},
                "loopback_only": {"passed": True, "evidence": "127.0.0.1"},
            }
        }

    def cleanup(self) -> dict:
        self.cleaned = True
        return {
            "checks": {
                "plugin_unloaded": {"passed": True, "evidence": "Unloaded"},
                "packages_unloaded": {"passed": True, "evidence": True},
                "session_removed": {"passed": True, "evidence": True},
                "port_closed": {"passed": True, "evidence": True},
            }
        }


def make_paths(tmp_path: Path) -> HostPaths:
    return HostPaths(
        active_package=tmp_path / "owned.sbs",
        library_package=tmp_path / "library.sbs",
        plugin_parent=tmp_path / "plugin",
        session=tmp_path / "session.json",
        ready=tmp_path / "ready.txt",
        done=tmp_path / "done.txt",
        report=tmp_path / "host-report.json",
        workspace=tmp_path,
    )


def make_designer_runtime(tmp_path: Path):
    paths = make_paths(tmp_path)
    paths.library_package.write_bytes(b"library")
    plugin_dir = paths.plugin_parent / "substance_designer_mcp_plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "pluginInfo.json").write_text('{"version":"1.0.0"}', encoding="utf-8")
    paths.session.write_text(
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

    active_package = MagicMock()
    active_package.getFilePath.return_value = str(paths.active_package)
    graph = MagicMock()
    graph.getIdentifier.return_value = "alveolus"
    graph.getPackage.return_value = active_package
    ui_mgr = MagicMock()
    ui_mgr.getCurrentGraph.return_value = graph
    library_package = MagicMock()
    package_mgr = MagicMock()
    package_mgr.loadUserPackage.return_value = library_package
    plugin = MagicMock()
    plugin.getStatus.side_effect = ("Loaded", "Unloaded")
    plugin.getLastErrorMessage.return_value = ""
    plugin_mgr = MagicMock()
    plugin_mgr.checkPluginCompatibility.return_value = None
    plugin_mgr.loadPlugin.return_value = plugin
    application = MagicMock()
    application.getUIMgr.return_value = ui_mgr
    application.getPackageMgr.return_value = package_mgr
    application.getPluginMgr.return_value = plugin_mgr
    application.getVersion.return_value = "16.0.3"
    runtime = DesignerHostRuntime(
        application=application,
        paths=paths,
        loaded_status="Loaded",
        unloaded_status="Unloaded",
        port_closed_fn=lambda _port: True,
    )
    return runtime, plugin_mgr, package_mgr, active_package, library_package


def test_runtime_prepares_only_the_exact_current_package_and_redacts_session(
    tmp_path: Path,
) -> None:
    runtime, plugin_mgr, package_mgr, _active, _library = make_designer_runtime(tmp_path)

    result = runtime.prepare()

    assert result["checks"]["plugin_compatible"]["passed"] is True
    assert result["checks"]["active_graph_ready"]["passed"] is True
    plugin_mgr.loadPlugin.assert_called_once_with(
        "substance_designer_mcp_plugin",
        str(tmp_path / "plugin" / "substance_designer_mcp_plugin"),
    )
    package_mgr.loadUserPackage.assert_called_once_with(str(tmp_path / "library.sbs"), True, True)
    assert "token" not in json.dumps(result)


def test_runtime_cleanup_unloads_only_owned_plugin_and_packages(tmp_path: Path) -> None:
    runtime, _plugin_mgr, package_mgr, active_package, library_package = make_designer_runtime(
        tmp_path
    )
    runtime.prepare()

    result = runtime.cleanup()

    assert result["checks"]["plugin_unloaded"]["passed"] is True
    assert result["checks"]["packages_unloaded"]["passed"] is True
    assert package_mgr.unloadUserPackage.call_args_list == [
        call(library_package),
        call(active_package),
    ]


def test_runtime_cleanup_does_not_read_invalidated_package_handles(tmp_path: Path) -> None:
    runtime, _plugin_mgr, _package_mgr, active_package, library_package = make_designer_runtime(
        tmp_path
    )
    runtime.prepare()
    active_package.getFilePath.side_effect = RuntimeError("invalid handle")
    library_package.getFilePath.side_effect = RuntimeError("invalid handle")

    result = runtime.cleanup()

    assert result["checks"]["packages_unloaded"]["passed"] is True
    assert result["cleanup"]["unloaded_packages"] == [
        str(tmp_path / "library.sbs"),
        str(tmp_path / "owned.sbs"),
    ]


def test_start_returns_without_blocking_and_waits_for_current_graph(tmp_path: Path) -> None:
    timer = FakeTimer()
    runtime = FakeRuntime(None)
    quit_calls = []
    controller = HostController(
        runtime=runtime,
        timer=timer,
        paths=make_paths(tmp_path),
        quit_callback=lambda: quit_calls.append(True),
        timeout=10.0,
        time_fn=lambda: 0.0,
    )

    controller.start()
    timer.fire()

    assert timer.started is True
    assert runtime.prepared is False
    assert quit_calls == []


def test_wrong_current_graph_fails_closed_without_loading_plugin(tmp_path: Path) -> None:
    timer = FakeTimer()
    runtime = FakeRuntime(str(tmp_path / "unrelated.sbs"))
    quit_calls = []
    clock = iter((0.0, 0.0, 11.0))
    controller = HostController(
        runtime=runtime,
        timer=timer,
        paths=make_paths(tmp_path),
        quit_callback=lambda: quit_calls.append(True),
        timeout=10.0,
        time_fn=lambda: next(clock),
    )

    controller.start()
    timer.fire()
    assert runtime.prepared is False
    assert quit_calls == []
    timer.fire()

    report = json.loads(make_paths(tmp_path).report.read_text(encoding="utf-8"))
    assert runtime.prepared is False
    assert report["error"]["code"] == "UNEXPECTED_ACTIVE_PACKAGE"
    assert quit_calls == [True]


def test_done_marker_cleans_up_writes_report_and_requests_quit(tmp_path: Path) -> None:
    paths = make_paths(tmp_path)
    paths.active_package.write_bytes(b"fixture")
    timer = FakeTimer()
    runtime = FakeRuntime(str(paths.active_package))
    quit_calls = []
    controller = HostController(
        runtime=runtime,
        timer=timer,
        paths=paths,
        quit_callback=lambda: quit_calls.append(True),
        timeout=10.0,
        time_fn=lambda: 0.0,
    )

    controller.start()
    timer.fire()
    paths.done.write_text("done", encoding="utf-8")
    timer.fire()

    report = json.loads(paths.report.read_text(encoding="utf-8"))
    assert paths.ready.is_file()
    assert runtime.prepared is True
    assert runtime.cleaned is True
    assert report["checks"]["done_received"]["passed"] is True
    assert report["checks"]["quit_requested"]["passed"] is True
    assert timer.stopped is True
    assert quit_calls == [True]


def test_timeout_writes_failure_report_and_requests_quit(tmp_path: Path) -> None:
    clock = iter((0.0, 11.0))
    timer = FakeTimer()
    quit_calls = []
    controller = HostController(
        runtime=FakeRuntime(None),
        timer=timer,
        paths=make_paths(tmp_path),
        quit_callback=lambda: quit_calls.append(True),
        timeout=10.0,
        time_fn=lambda: next(clock),
    )

    controller.start()
    timer.fire()

    report = json.loads(make_paths(tmp_path).report.read_text(encoding="utf-8"))
    assert report["error"]["code"] == "HOST_TIMEOUT"
    assert quit_calls == [True]
