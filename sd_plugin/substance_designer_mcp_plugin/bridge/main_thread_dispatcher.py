"""Dispatch Designer API work to the Qt main thread and await its result."""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

from ..errors import ErrorCode, PluginError


class _Job:
    def __init__(self, function: Callable[..., Any], args: tuple[Any, ...]) -> None:
        self.function = function
        self.args = args
        self.result: Any = None
        self.error: Optional[BaseException] = None
        self.done = threading.Event()
        self._state_lock = threading.Lock()
        self._cancelled = False
        self._started = False

    def run(self) -> None:
        with self._state_lock:
            if self._cancelled or self._started:
                return
            self._started = True
        try:
            self.result = self.function(*self.args)
        except BaseException as exc:
            self.error = exc
        finally:
            self.done.set()

    def cancel_if_pending(self) -> None:
        with self._state_lock:
            if not self._started:
                self._cancelled = True


class _QtInvoker:
    """A queued Qt signal whose receiver is created on the plugin's main thread."""

    def __init__(self) -> None:
        try:
            from PySide6 import QtCore
        except ImportError as exc:
            raise PluginError(
                ErrorCode.UNSUPPORTED_CAPABILITY, "PySide6 is unavailable in this runtime."
            ) from exc

        class Proxy(QtCore.QObject):  # type: ignore[misc, valid-type]
            invoke = QtCore.Signal(object)

            def __init__(self) -> None:
                super().__init__()
                self.invoke.connect(self._run, QtCore.Qt.QueuedConnection)

            @QtCore.Slot(object)
            def _run(self, callback: Callable[[], None]) -> None:
                callback()

        self._proxy = Proxy()

    def post(self, callback: Callable[[], None]) -> None:
        self._proxy.invoke.emit(callback)


class MainThreadDispatcher:
    """Post one callable to Designer's Qt thread and propagate its result."""

    def __init__(self, invoker: Optional[Any] = None) -> None:
        self._invoker = invoker or _QtInvoker()

    def call(self, function: Callable[..., Any], *args: Any, timeout: float) -> Any:
        """Execute once on the receiver thread or fail with a stable timeout."""

        job = _Job(function, args)
        self._invoker.post(job.run)
        if not job.done.wait(timeout):
            job.cancel_if_pending()
            raise PluginError(ErrorCode.REQUEST_TIMEOUT, "Main-thread execution timed out.")
        if job.error is not None:
            raise job.error
        return job.result
