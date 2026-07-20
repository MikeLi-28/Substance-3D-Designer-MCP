"""Nonblocking real-Designer Plugin Manager lifecycle probe."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(os.environ["SUBSTANCE_DESIGNER_MCP_PROJECT_ROOT"])
PLUGIN_PARENT = Path(os.environ["SUBSTANCE_DESIGNER_MCP_TEST_PLUGIN_PARENT"])
REPORT_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_PLUGIN_MANAGER_REPORT"])
SESSION_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_SESSION_PATH"])
ACTIVE_PACKAGE_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_ACTIVE_PACKAGE"])

sys.path.insert(0, str(ROOT / "tests" / "manual"))

from sd16_plugin_probe_controller import PluginProbeController, PluginProbeRuntime

_CONTROLLER: Optional[PluginProbeController] = None


def _port_closed(port: Any) -> bool:
    if not isinstance(port, int):
        return False
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return False
    except OSError:
        return True


def main() -> None:
    import sd
    from PySide6 import QtCore
    from sd.api.sdplugin import SDPluginStatus

    runtime = PluginProbeRuntime(
        application=sd.getContext().getSDApplication(),
        plugin_parent=PLUGIN_PARENT,
        session_path=SESSION_PATH,
        loaded_status=SDPluginStatus.Loaded,
        unloaded_status=SDPluginStatus.Unloaded,
        port_closed_fn=_port_closed,
    )
    timer = QtCore.QTimer(QtCore.QCoreApplication.instance())
    controller = PluginProbeController(
        runtime=runtime,
        timer=timer,
        active_package=ACTIVE_PACKAGE_PATH,
        report_path=REPORT_PATH,
        workspace=PLUGIN_PARENT.parent,
        quit_callback=QtCore.QCoreApplication.quit,
        timeout=float(os.getenv("SUBSTANCE_DESIGNER_MCP_PLUGIN_PROBE_TIMEOUT", "60")),
    )
    controller.start()

    global _CONTROLLER
    _CONTROLLER = controller


main()
