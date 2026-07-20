"""Authenticated loopback TCP bridge for the Designer plugin."""

from __future__ import annotations

import contextlib
import hmac
import socket
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from .framing import FrameDecoder, FrameTooLarge, InvalidFrame, encode_message
from .protocol import ProtocolError, error_response, success_response, validate_request
from .session import SessionFile


class BridgeServer:
    """Transport-only server that dispatches authenticated allow-listed commands."""

    def __init__(
        self,
        executor: Any,
        dispatcher: Any,
        session_path: Path,
        designer_version: str,
        plugin_version: str = "1.1.0",
        read_timeout: float = 5.0,
        write_timeout: float = 30.0,
    ) -> None:
        self.executor = executor
        self.dispatcher = dispatcher
        self.session_path = Path(session_path)
        self.designer_version = designer_version
        self.plugin_version = plugin_version
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self._listener: Optional[socket.socket] = None
        self._session_file: Optional[SessionFile] = None
        self._session: Optional[Dict[str, Any]] = None
        self._thread: Optional[threading.Thread] = None
        self._stopping = threading.Event()

    def start(self) -> Dict[str, Any]:
        """Bind loopback, publish the session, and start the accept thread."""

        if self._listener is not None:
            return dict(self._session or {})
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen(8)
        listener.settimeout(0.2)
        port = int(listener.getsockname()[1])
        session_file = SessionFile(
            path=self.session_path,
            port=port,
            designer_version=self.designer_version,
            plugin_version=self.plugin_version,
        )
        self._listener = listener
        self._session_file = session_file
        self._session = session_file.publish()
        self._stopping.clear()
        self._thread = threading.Thread(
            target=self._serve, name="substance-designer-mcp-bridge", daemon=True
        )
        self._thread.start()
        return dict(self._session)

    def stop(self) -> None:
        """Stop accepting connections and remove only this server's session."""

        self._stopping.set()
        listener = self._listener
        self._listener = None
        if listener is not None:
            with contextlib.suppress(OSError):
                listener.close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._session_file is not None:
            self._session_file.cleanup()
            self._session_file = None
        self._session = None

    def _serve(self) -> None:
        while not self._stopping.is_set():
            listener = self._listener
            if listener is None:
                return
            try:
                connection, _address = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            with connection:
                self._handle_connection(connection)

    def _handle_connection(self, connection: socket.socket) -> None:
        connection.settimeout(self.read_timeout)
        decoder = FrameDecoder()
        request_id = "unknown"
        try:
            request = self._receive_request(connection, decoder)
            request_id = str(request.get("request_id", "unknown"))
            validated = validate_request(request)
            token = str(validated["token"])
            expected = str((self._session or {}).get("token", ""))
            if not hmac.compare_digest(token, expected):
                response = error_response(
                    request_id, "AUTHENTICATION_FAILED", "The session token is invalid."
                )
            else:
                timeout = self.write_timeout
                data = self.dispatcher.call(
                    self.executor.execute,
                    str(validated["command"]),
                    dict(validated["arguments"]),
                    timeout=timeout,
                )
                response = success_response(request_id, data)
        except ProtocolError as exc:
            response = error_response(request_id, exc.code, exc.message)
        except FrameTooLarge:
            response = error_response(request_id, "REQUEST_TOO_LARGE", "Request exceeds 4 MiB.")
        except (InvalidFrame, socket.timeout):
            response = error_response(request_id, "INVALID_PARAMETER", "Invalid bridge request.")
        except Exception as exc:
            code = getattr(exc, "code", "INTERNAL_ERROR")
            if hasattr(code, "value"):
                code = code.value
            message = getattr(exc, "message", "The Designer command failed.")
            details = getattr(exc, "details", {})
            response = error_response(request_id, str(code), str(message), details)
        try:
            connection.sendall(encode_message(response))
        except OSError:
            return

    @staticmethod
    def _receive_request(connection: socket.socket, decoder: FrameDecoder) -> Dict[str, Any]:
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                raise InvalidFrame("Connection closed before a complete request.")
            messages = decoder.feed(chunk)
            if messages:
                return messages[0]
