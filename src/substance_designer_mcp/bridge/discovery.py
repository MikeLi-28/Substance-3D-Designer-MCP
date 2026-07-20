"""Discover and validate a locally published Designer bridge session."""

from __future__ import annotations

import contextlib
import ctypes
import json
import os
import socket
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from substance_designer_mcp.errors import ErrorCode, MCPError

from .protocol import PROTOCOL_VERSION

DEFAULT_SESSION_PATH = Path.home() / ".substance-designer-mcp" / "session.json"


@dataclass(frozen=True)
class SessionInfo:
    protocol_version: str
    host: str
    port: int
    token: str
    pid: int
    designer_version: str
    plugin_version: str
    started_at: str


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if os.name == "nt":
        return _windows_pid_is_alive(pid)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _windows_pid_is_alive(pid: int) -> bool:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    process_query_limited_information = 0x1000
    handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
    if handle:
        kernel32.CloseHandle(handle)
        return True
    return ctypes.get_last_error() == 5


def _port_is_open(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _parse_session(payload: dict[str, Any]) -> SessionInfo:
    try:
        return SessionInfo(
            protocol_version=str(payload["protocol_version"]),
            host=str(payload["host"]),
            port=int(payload["port"]),
            token=str(payload["token"]),
            pid=int(payload["pid"]),
            designer_version=str(payload["designer_version"]),
            plugin_version=str(payload["plugin_version"]),
            started_at=str(payload["started_at"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MCPError(ErrorCode.BRIDGE_NOT_AVAILABLE, "The session file is invalid.") from exc


def discover_session(
    path: Path = DEFAULT_SESSION_PATH,
    *,
    check_port: bool = True,
    port_timeout: float = 0.2,
) -> SessionInfo:
    """Load a live, loopback-only session or return a stable diagnostic error."""

    session_path = Path(path)
    if not session_path.exists():
        raise MCPError(ErrorCode.SD_NOT_RUNNING, "No Substance Designer bridge session was found.")
    try:
        payload = json.loads(session_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MCPError(ErrorCode.BRIDGE_NOT_AVAILABLE, "The session file cannot be read.") from exc
    if not isinstance(payload, dict):
        raise MCPError(ErrorCode.BRIDGE_NOT_AVAILABLE, "The session file is invalid.")
    session = _parse_session(payload)
    if session.protocol_version != PROTOCOL_VERSION:
        raise MCPError(ErrorCode.PROTOCOL_VERSION_MISMATCH, "The bridge protocol is incompatible.")
    if session.host != "127.0.0.1" or not 1 <= session.port <= 65535:
        raise MCPError(ErrorCode.BRIDGE_NOT_AVAILABLE, "The bridge session is not loopback-only.")
    if not _pid_is_alive(session.pid):
        with contextlib.suppress(FileNotFoundError):
            session_path.unlink()
        raise MCPError(ErrorCode.SD_NOT_RUNNING, "The Designer bridge session is stale.")
    if check_port and not _port_is_open(session.host, session.port, port_timeout):
        with contextlib.suppress(FileNotFoundError):
            session_path.unlink()
        raise MCPError(ErrorCode.BRIDGE_NOT_AVAILABLE, "The Designer bridge port is unavailable.")
    return session
