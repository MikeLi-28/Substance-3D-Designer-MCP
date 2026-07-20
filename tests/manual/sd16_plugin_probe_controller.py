"""Main-thread controller for the Designer 16 Plugin Manager probe."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from .sd16_e2e_support import make_check, redact
except ImportError:
    from sd16_e2e_support import make_check, redact


class PluginProbeController:
    def __init__(
        self,
        *,
        runtime: Any,
        timer: Any,
        active_package: Path,
        report_path: Path,
        workspace: Path,
        quit_callback: Callable[[], None],
        timeout: float,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.runtime = runtime
        self.timer = timer
        self.active_package = active_package
        self.report_path = report_path
        self.workspace = workspace
        self.quit_callback = quit_callback
        self.timeout = timeout
        self.time_fn = time_fn
        self.deadline = 0.0
        self.finished = False

    def start(self) -> None:
        self.deadline = self.time_fn() + self.timeout
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    def poll(self) -> None:
        if self.finished:
            return
        if self.time_fn() >= self.deadline:
            self._finish(
                {"phase": "plugin_manager", "checks": {}},
                {
                    "code": "PLUGIN_PROBE_UI_TIMEOUT",
                    "message": "The owned Graph did not become current before timeout.",
                },
            )
            return
        try:
            current_path = self.runtime.current_graph_path()
            if current_path is None or not self._same_path(current_path, self.active_package):
                return
            report = self.runtime.run()
        except BaseException as exc:
            self._finish(
                {"phase": "plugin_manager", "checks": {}},
                {"code": "PLUGIN_PROBE_RUNTIME_ERROR", "message": str(exc)},
            )
            return
        self._finish(report, None)

    def _finish(self, report: dict, error: Optional[dict]) -> None:
        if self.finished:
            return
        self.finished = True
        if error is not None:
            report["error"] = error
        checks = report.setdefault("checks", {})
        checks["quit_requested"] = make_check(True, True)
        self.timer.stop()
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        cleaned = redact(report, secrets=set(), workspace=str(self.workspace))
        self.report_path.write_text(
            json.dumps(cleaned, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.quit_callback()

    @staticmethod
    def _same_path(actual: str, expected: Path) -> bool:
        return os.path.normcase(os.path.realpath(actual)) == os.path.normcase(
            os.path.realpath(expected)
        )


PLUGIN_NAME = "substance_designer_mcp_plugin"


def _status_name(status: Any) -> str:
    name = getattr(status, "name", None)
    return str(name) if name else str(status)


class PluginProbeRuntime:
    def __init__(
        self,
        *,
        application: Any,
        plugin_parent: Path,
        session_path: Path,
        loaded_status: Any,
        unloaded_status: Any,
        port_closed_fn: Callable[[Any], bool],
    ) -> None:
        self.application = application
        self.plugin_parent = plugin_parent
        self.session_path = session_path
        self.loaded_status = loaded_status
        self.unloaded_status = unloaded_status
        self.port_closed_fn = port_closed_fn

    def current_graph_path(self) -> Optional[str]:
        current = self.application.getUIMgr().getCurrentGraph()
        if current is None:
            return None
        return str(current.getPackage().getFilePath())

    def run(self) -> dict:
        checks = {
            name: make_check(
                False,
                None,
                {"code": "MISSING_EVIDENCE", "message": "Evidence was not produced."},
            )
            for name in (
                "plugin_compatible",
                "plugin_loaded",
                "session_created",
                "loopback_only",
                "plugin_unloaded",
                "session_removed",
                "port_closed",
            )
        }
        report = {"phase": "plugin_manager", "checks": checks}
        plugin_mgr = self.application.getPluginMgr()
        plugin = None
        unloaded = False
        port = None
        try:
            plugin_dir = self.plugin_parent / PLUGIN_NAME
            if str(plugin_dir) not in sys.path:
                sys.path.append(str(plugin_dir))
            metadata_text = (plugin_dir / "pluginInfo.json").read_text(encoding="utf-8")
            metadata = json.loads(metadata_text)
            report["designer_version"] = str(self.application.getVersion())
            report["plugin_version"] = str(metadata.get("version", ""))

            compatibility_error = plugin_mgr.checkPluginCompatibility(metadata_text)
            checks["plugin_compatible"] = make_check(
                compatibility_error is None,
                {"compatibility_error": compatibility_error},
            )
            if compatibility_error is not None:
                raise RuntimeError("Designer rejected the plugin metadata.")

            plugin = plugin_mgr.loadPlugin(PLUGIN_NAME, str(plugin_dir))
            status = plugin.getStatus()
            checks["plugin_loaded"] = make_check(
                status == self.loaded_status,
                {"status": _status_name(status), "error": plugin.getLastErrorMessage()},
            )
            if status != self.loaded_status:
                raise RuntimeError("Designer Plugin Manager did not load the plugin.")

            if not self.session_path.is_file():
                raise RuntimeError("The plugin did not create its isolated session file.")
            session = json.loads(self.session_path.read_text(encoding="utf-8"))
            session_summary = {
                key: session.get(key)
                for key in (
                    "protocol_version",
                    "host",
                    "port",
                    "pid",
                    "designer_version",
                    "plugin_version",
                )
            }
            report["session"] = session_summary
            checks["session_created"] = make_check(True, {"session_file_exists": True})
            port = session_summary["port"]
            loopback = session_summary["host"] == "127.0.0.1"
            checks["loopback_only"] = make_check(loopback, {"host": session_summary["host"]})
            if not loopback:
                raise RuntimeError("The plugin bridge is not loopback-only.")

            plugin_mgr.unloadPlugin(plugin)
            unloaded = True
            status = plugin.getStatus()
            checks["plugin_unloaded"] = make_check(
                status == self.unloaded_status,
                {"status": _status_name(status)},
            )
        except BaseException as exc:
            report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        finally:
            if plugin is not None and not unloaded:
                try:
                    plugin_mgr.unloadPlugin(plugin)
                    checks["plugin_unloaded"] = make_check(True, "unloadPlugin returned")
                except BaseException as exc:
                    checks["plugin_unloaded"] = make_check(
                        False,
                        None,
                        {"type": type(exc).__name__, "message": str(exc)},
                    )
            session_removed = not self.session_path.exists()
            checks["session_removed"] = make_check(
                session_removed,
                {"session_file_exists": not session_removed},
            )
            port_closed = self.port_closed_fn(port)
            checks["port_closed"] = make_check(
                port_closed,
                {"port_closed": port_closed},
            )
        return report
