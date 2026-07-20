"""Read-only real-Designer startup probe; run only with Designer --startup-script."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path

ROOT = Path(os.environ["SUBSTANCE_DESIGNER_MCP_PROJECT_ROOT"])
REPORT_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_SMOKE_REPORT"])
SESSION_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_SMOKE_SESSION"])
LOG_PATH = Path(os.environ["SUBSTANCE_DESIGNER_MCP_SMOKE_LOG"])
sys.path.insert(0, str(ROOT / "sd_plugin"))

from substance_designer_mcp_plugin import initializeSDPlugin, uninitializeSDPlugin
from substance_designer_mcp_plugin import plugin as plugin_module


def main() -> None:
    report = {"plugin_initialized": False, "session_created": False, "session_removed": False}
    try:
        use_entry_points = os.getenv("SUBSTANCE_DESIGNER_MCP_SMOKE_ENTRY_POINTS") == "1"
        if use_entry_points:
            initializeSDPlugin()
            runtime = plugin_module._runtime
            active_session_path = plugin_module.SESSION_PATH
        else:
            runtime = plugin_module.initialize_plugin(
                session_path=SESSION_PATH,
                log_path=LOG_PATH,
            )
            active_session_path = SESSION_PATH
        if runtime is None:
            raise RuntimeError("Plugin runtime was not created.")
        report["plugin_initialized"] = True
        report["entry_points_used"] = use_entry_points
        report["session_created"] = active_session_path.exists()
        if active_session_path.exists():
            session = json.loads(active_session_path.read_text(encoding="utf-8"))
            report["session"] = {
                key: session[key]
                for key in (
                    "protocol_version",
                    "host",
                    "port",
                    "pid",
                    "designer_version",
                    "plugin_version",
                )
            }
        executor = runtime.server.executor
        report["application_info"] = executor.execute("sd_get_application_info", {})
        report["capabilities"] = executor.execute("sd_get_capabilities", {})
        report["packages"] = executor.execute("sd_list_packages", {})
    except Exception as exc:
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        port = report.get("session", {}).get("port")
        if os.getenv("SUBSTANCE_DESIGNER_MCP_SMOKE_ENTRY_POINTS") == "1":
            uninitializeSDPlugin()
            active_session_path = plugin_module.SESSION_PATH
        else:
            plugin_module.uninitialize_plugin()
            active_session_path = SESSION_PATH
        report["session_removed"] = not active_session_path.exists()
        if isinstance(port, int):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    report["port_closed"] = False
            except OSError:
                report["port_closed"] = True
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


main()
