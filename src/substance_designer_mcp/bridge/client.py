"""Synchronous authenticated client for the local Designer bridge."""

from __future__ import annotations

import socket
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from substance_designer_mcp.errors import ErrorCode, MCPError

from .discovery import DEFAULT_SESSION_PATH, discover_session
from .framing import FrameDecoder, FrameTooLarge, encode_message
from .protocol import create_request


class BridgeClient:
    """Send one structured command per loopback connection."""

    def __init__(
        self,
        session_path: Path = DEFAULT_SESSION_PATH,
        connect_timeout: float = 5.0,
        read_timeout: float = 5.0,
        write_timeout: float = 30.0,
    ) -> None:
        self.session_path = Path(session_path)
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout

    def call(
        self,
        command: str,
        arguments: Mapping[str, Any],
        *,
        write: bool = False,
    ) -> dict[str, Any]:
        """Call a bridge command and return its data or raise a stable error."""

        session = discover_session(self.session_path, check_port=False)
        request = create_request(command, arguments, session.token)
        timeout = self.write_timeout if write else self.read_timeout
        try:
            with socket.create_connection(
                (session.host, session.port), timeout=self.connect_timeout
            ) as connection:
                connection.settimeout(timeout)
                connection.sendall(encode_message(request))
                decoder = FrameDecoder()
                while True:
                    chunk = connection.recv(65536)
                    if not chunk:
                        raise MCPError(
                            ErrorCode.BRIDGE_NOT_AVAILABLE,
                            "The Designer bridge closed without a response.",
                        )
                    messages = decoder.feed(chunk)
                    if messages:
                        return self._unwrap(messages[0])
        except TimeoutError as exc:
            raise MCPError(ErrorCode.REQUEST_TIMEOUT, "The Designer request timed out.") from exc
        except FrameTooLarge as exc:
            raise MCPError(ErrorCode.REQUEST_TOO_LARGE, str(exc)) from exc
        except MCPError:
            raise
        except OSError as exc:
            raise MCPError(
                ErrorCode.BRIDGE_NOT_AVAILABLE, "The Designer bridge is unavailable."
            ) from exc

    @staticmethod
    def _unwrap(response: Mapping[str, Any]) -> dict[str, Any]:
        if response.get("ok") is True and isinstance(response.get("data"), dict):
            return dict(response["data"])
        error = response.get("error")
        if not isinstance(error, dict):
            raise MCPError(ErrorCode.INTERNAL_ERROR, "The bridge returned an invalid response.")
        raw_code = str(error.get("code", ErrorCode.INTERNAL_ERROR.value))
        try:
            code = ErrorCode(raw_code)
        except ValueError:
            code = ErrorCode.INTERNAL_ERROR
        details = error.get("details") if isinstance(error.get("details"), dict) else {}
        raise MCPError(code, str(error.get("message", "Designer request failed.")), details)
