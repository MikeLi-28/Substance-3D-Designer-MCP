"""Nonblocking Designer host for external MCP real-machine verification."""

from __future__ import annotations

import os
import socket
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(os.environ["SUBSTANCE_DESIGNER_MCP_PROJECT_ROOT"])
PLUGIN_PARENT = Path(os.environ["SUBSTANCE_DESIGNER_MCP_TEST_PLUGIN_PARENT"])
ACTIVE_PACKAGE_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_ACTIVE_PACKAGE"])
LIBRARY_PACKAGE_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_LIBRARY_PACKAGE"])
READY_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_READY_PATH"])
DONE_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_DONE_PATH"])
HOST_REPORT_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_HOST_REPORT"])
SESSION_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_SESSION_PATH"])

sys.path.insert(0, str(ROOT / "tests" / "manual"))

from sd16_e2e_controller import DesignerHostRuntime, HostController, HostPaths

_CONTROLLER: Optional[HostController] = None


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

    paths = HostPaths(
        active_package=ACTIVE_PACKAGE_PATH,
        library_package=LIBRARY_PACKAGE_PATH,
        plugin_parent=PLUGIN_PARENT,
        session=SESSION_PATH,
        ready=READY_PATH,
        done=DONE_PATH,
        report=HOST_REPORT_PATH,
        workspace=ACTIVE_PACKAGE_PATH.parent,
    )
    runtime = DesignerHostRuntime(
        application=sd.getContext().getSDApplication(),
        paths=paths,
        loaded_status=SDPluginStatus.Loaded,
        unloaded_status=SDPluginStatus.Unloaded,
        port_closed_fn=_port_closed,
    )
    timer = QtCore.QTimer(QtCore.QCoreApplication.instance())
    controller = HostController(
        runtime=runtime,
        timer=timer,
        paths=paths,
        quit_callback=QtCore.QCoreApplication.quit,
        timeout=float(os.getenv("SUBSTANCE_DESIGNER_MCP_HOST_TIMEOUT", "60")),
    )
    controller.start()

    global _CONTROLLER
    _CONTROLLER = controller


main()
