"""Designer plugin composition root and lifecycle ownership."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .bridge.main_thread_dispatcher import MainThreadDispatcher
from .bridge.server import BridgeServer
from .commands.executor import build_command_executor
from .config import LOG_PATH, PLUGIN_VERSION, SESSION_PATH, bridge_timeouts
from .logging_config import configure_plugin_logging
from .services.container import ServiceContainer


@dataclass
class PluginRuntime:
    server: Any
    logger: Any


_runtime: Optional[PluginRuntime] = None


def initialize_plugin(
    *,
    application: Any = None,
    adapter: Any = None,
    dispatcher: Any = None,
    server_factory: Any = BridgeServer,
    session_path: Path = SESSION_PATH,
    log_path: Path = LOG_PATH,
) -> PluginRuntime:
    """Compose and start the plugin once; dependencies are injectable for offline tests."""

    global _runtime
    if _runtime is not None:
        return _runtime
    if application is None:
        import sd

        application = sd.getContext().getSDApplication()
    if adapter is None:
        from .compatibility.sd16 import SD16Adapter

        adapter = SD16Adapter()
    if dispatcher is None:
        dispatcher = MainThreadDispatcher()
    logger = configure_plugin_logging(Path(log_path))
    services = ServiceContainer(application, adapter)
    executor = build_command_executor(services, PLUGIN_VERSION)
    read_timeout, write_timeout = bridge_timeouts()
    server = server_factory(
        executor=executor,
        dispatcher=dispatcher,
        session_path=Path(session_path),
        designer_version=str(application.getVersion()),
        plugin_version=PLUGIN_VERSION,
        read_timeout=read_timeout,
        write_timeout=write_timeout,
    )
    try:
        server.start()
    except Exception:
        logger.exception("Plugin bridge failed to start.")
        server.stop()
        raise
    logger.info("Plugin bridge started for Designer %s.", application.getVersion())
    _runtime = PluginRuntime(server=server, logger=logger)
    return _runtime


def uninitialize_plugin() -> None:
    """Stop only this plugin's owned runtime resources."""

    global _runtime
    runtime = _runtime
    _runtime = None
    if runtime is None:
        return
    try:
        runtime.server.stop()
        runtime.logger.info("Plugin bridge stopped.")
    finally:
        for handler in list(runtime.logger.handlers):
            runtime.logger.removeHandler(handler)
            handler.close()
