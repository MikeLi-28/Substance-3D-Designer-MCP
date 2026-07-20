"""Main-thread controller for the Designer 16 real-machine host."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

try:
    from .sd16_e2e_support import make_check, redact
except ImportError:
    from sd16_e2e_support import make_check, redact


@dataclass(frozen=True)
class HostPaths:
    active_package: Path
    library_package: Path
    plugin_parent: Path
    session: Path
    ready: Path
    done: Path
    report: Path
    workspace: Path


class HostController:
    def __init__(
        self,
        *,
        runtime: Any,
        timer: Any,
        paths: HostPaths,
        quit_callback: Callable[[], None],
        timeout: float,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.runtime = runtime
        self.timer = timer
        self.paths = paths
        self.quit_callback = quit_callback
        self.timeout = timeout
        self.time_fn = time_fn
        self.deadline = 0.0
        self.ready = False
        self.finished = False
        self.last_unexpected_path: Optional[str] = None
        required = (
            "fixture_loaded",
            "library_loaded",
            "active_graph_ready",
            "plugin_compatible",
            "plugin_loaded",
            "session_created",
            "loopback_only",
            "done_received",
            "plugin_unloaded",
            "packages_unloaded",
            "session_removed",
            "port_closed",
            "quit_requested",
        )
        self.report = {
            "phase": "designer_host",
            "checks": {
                name: make_check(
                    False,
                    None,
                    {"code": "MISSING_EVIDENCE", "message": "Evidence was not produced."},
                )
                for name in required
            },
        }

    def start(self) -> None:
        self.deadline = self.time_fn() + self.timeout
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll)
        self.timer.start()

    def poll(self) -> None:
        if self.finished:
            return
        now = self.time_fn()
        try:
            if not self.ready:
                current_path = self.runtime.current_graph_path()
                if current_path is not None:
                    if self._same_path(current_path, self.paths.active_package):
                        self._merge(self.runtime.prepare())
                        self.paths.ready.parent.mkdir(parents=True, exist_ok=True)
                        self.paths.ready.write_text("ready\n", encoding="utf-8")
                        self.ready = True
                        self.deadline = now + self.timeout
                        return
                    self.last_unexpected_path = current_path
                if now >= self.deadline:
                    code = (
                        "UNEXPECTED_ACTIVE_PACKAGE"
                        if self.last_unexpected_path is not None
                        else "HOST_TIMEOUT"
                    )
                    self._finish(code, "The owned Graph did not become current before timeout.")
                return
            if self.paths.done.is_file():
                self._finish(None, None)
            elif now >= self.deadline:
                self._finish("HOST_TIMEOUT", "The external client did not finish before timeout.")
        except BaseException as exc:
            self._finish("HOST_RUNTIME_ERROR", str(exc))

    def _finish(self, code: Optional[str], message: Optional[str]) -> None:
        if self.finished:
            return
        self.finished = True
        try:
            self._merge(self.runtime.cleanup())
        except BaseException as exc:
            self.report["cleanup_error"] = {
                "code": "HOST_CLEANUP_FAILED",
                "message": str(exc),
            }
        done_received = self.paths.done.is_file()
        self.report["checks"]["done_received"] = make_check(
            done_received,
            {"done_received": done_received},
        )
        if code is not None:
            self.report["error"] = {"code": code, "message": message}
        self.report["checks"]["quit_requested"] = make_check(True, True)
        self.timer.stop()
        self.paths.report.parent.mkdir(parents=True, exist_ok=True)
        cleaned = redact(self.report, secrets=set(), workspace=str(self.paths.workspace))
        self.paths.report.write_text(
            json.dumps(cleaned, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.quit_callback()

    def _merge(self, patch: dict) -> None:
        for key, value in patch.items():
            if key == "checks":
                self.report["checks"].update(value)
            else:
                self.report[key] = value

    @staticmethod
    def _same_path(actual: str, expected: Path) -> bool:
        return os.path.normcase(os.path.realpath(actual)) == os.path.normcase(
            os.path.realpath(expected)
        )


PLUGIN_NAME = "substance_designer_mcp_plugin"


def _status_name(status: Any) -> str:
    name = getattr(status, "name", None)
    return str(name) if name else str(status)


class DesignerHostRuntime:
    def __init__(
        self,
        *,
        application: Any,
        paths: HostPaths,
        loaded_status: Any,
        unloaded_status: Any,
        port_closed_fn: Callable[[Any], bool],
    ) -> None:
        self.application = application
        self.paths = paths
        self.loaded_status = loaded_status
        self.unloaded_status = unloaded_status
        self.port_closed_fn = port_closed_fn
        self.ui_mgr = application.getUIMgr()
        self.package_mgr = application.getPackageMgr()
        self.plugin_mgr = application.getPluginMgr()
        self.active_package = None
        self.active_package_path: Optional[str] = None
        self.library_package = None
        self.plugin = None
        self.port = None

    def current_graph_path(self) -> Optional[str]:
        current = self.ui_mgr.getCurrentGraph()
        if current is None:
            return None
        return str(current.getPackage().getFilePath())

    def prepare(self) -> dict:
        current = self.ui_mgr.getCurrentGraph()
        if current is None:
            raise RuntimeError("Designer has no current Graph.")
        self.active_package = current.getPackage()
        active_path = str(self.active_package.getFilePath())
        self.active_package_path = active_path
        if not HostController._same_path(active_path, self.paths.active_package):
            raise RuntimeError("The current Graph does not belong to the owned Package.")

        plugin_dir = self.paths.plugin_parent / PLUGIN_NAME
        if str(plugin_dir) not in sys.path:
            sys.path.append(str(plugin_dir))
        metadata_text = (plugin_dir / "pluginInfo.json").read_text(encoding="utf-8")
        compatibility_error = self.plugin_mgr.checkPluginCompatibility(metadata_text)
        if compatibility_error is not None:
            raise RuntimeError("Designer rejected the plugin metadata.")
        self.plugin = self.plugin_mgr.loadPlugin(PLUGIN_NAME, str(plugin_dir))
        status = self.plugin.getStatus()
        if status != self.loaded_status:
            raise RuntimeError("Designer Plugin Manager did not load the plugin.")

        self.library_package = self.package_mgr.loadUserPackage(
            str(self.paths.library_package), True, True
        )
        if self.library_package is None:
            raise RuntimeError("Designer did not load the owned Library Package.")
        if not self.paths.session.is_file():
            raise RuntimeError("The plugin did not create its isolated session file.")
        session = json.loads(self.paths.session.read_text(encoding="utf-8"))
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
        self.port = session_summary["port"]
        loopback = session_summary["host"] == "127.0.0.1"
        if not loopback:
            raise RuntimeError("The plugin bridge is not loopback-only.")
        return {
            "designer_version": str(self.application.getVersion()),
            "python_version": sys.version.split()[0],
            "session": session_summary,
            "checks": {
                "fixture_loaded": make_check(True, {"package": active_path}),
                "active_graph_ready": make_check(
                    True, {"graph_identifier": str(current.getIdentifier())}
                ),
                "plugin_compatible": make_check(True, {"compatibility_error": compatibility_error}),
                "plugin_loaded": make_check(
                    True,
                    {
                        "status": _status_name(status),
                        "error": self.plugin.getLastErrorMessage(),
                    },
                ),
                "library_loaded": make_check(True, {"package": self.paths.library_package.name}),
                "session_created": make_check(True, {"session_file_exists": True}),
                "loopback_only": make_check(True, {"host": session_summary["host"]}),
            },
        }

    def cleanup(self) -> dict:
        plugin_error = None
        plugin_unloaded = self.plugin is None
        if self.plugin is not None:
            try:
                self.plugin_mgr.unloadPlugin(self.plugin)
                plugin_unloaded = self.plugin.getStatus() == self.unloaded_status
            except BaseException as exc:
                plugin_error = {"type": type(exc).__name__, "message": str(exc)}

        package_errors = []
        unloaded_names = []
        owned_packages = (
            (self.library_package, str(self.paths.library_package)),
            (self.active_package, self.active_package_path),
        )
        for package, package_path in owned_packages:
            if package is None:
                continue
            try:
                self.package_mgr.unloadUserPackage(package)
                if package_path is not None:
                    unloaded_names.append(package_path)
            except BaseException as exc:
                package_errors.append({"type": type(exc).__name__, "message": str(exc)})
        session_removed = not self.paths.session.exists()
        port_closed = self.port_closed_fn(self.port)
        return {
            "cleanup": {"unloaded_packages": unloaded_names},
            "checks": {
                "plugin_unloaded": make_check(
                    plugin_unloaded, {"unloaded": plugin_unloaded}, plugin_error
                ),
                "packages_unloaded": make_check(
                    not package_errors,
                    {"unloaded_packages": unloaded_names},
                    package_errors or None,
                ),
                "session_removed": make_check(
                    session_removed, {"session_file_exists": not session_removed}
                ),
                "port_closed": make_check(port_closed, {"port_closed": port_closed}),
            },
        }
