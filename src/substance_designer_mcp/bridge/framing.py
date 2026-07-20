"""Dependency-free length-prefixed JSON framing."""

from __future__ import annotations

import json
import struct
from collections.abc import Mapping
from typing import Any

MAX_MESSAGE_SIZE = 4 * 1024 * 1024
_HEADER_SIZE = 4


class FramingError(ValueError):
    """Base class for malformed bridge frames."""


class FrameTooLarge(FramingError):
    """Raised when a frame exceeds the protocol limit."""


class InvalidFrame(FramingError):
    """Raised when a frame body is not a UTF-8 JSON object."""


def encode_message(message: Mapping[str, Any]) -> bytes:
    """Encode a JSON object using the bridge's four-byte length prefix."""

    try:
        body = json.dumps(
            dict(message), ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidFrame("Message is not JSON serializable.") from exc
    if len(body) > MAX_MESSAGE_SIZE:
        raise FrameTooLarge("Message exceeds the 4 MiB limit.")
    return struct.pack(">I", len(body)) + body


class FrameDecoder:
    """Incrementally decode split or coalesced bridge frames."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, data: bytes) -> list[dict[str, Any]]:
        """Append bytes and return all complete JSON objects."""

        self._buffer.extend(data)
        messages: list[dict[str, Any]] = []
        while len(self._buffer) >= _HEADER_SIZE:
            body_size = struct.unpack(">I", self._buffer[:_HEADER_SIZE])[0]
            if body_size > MAX_MESSAGE_SIZE:
                self._buffer.clear()
                raise FrameTooLarge("Message exceeds the 4 MiB limit.")
            frame_size = _HEADER_SIZE + body_size
            if len(self._buffer) < frame_size:
                break
            body = bytes(self._buffer[_HEADER_SIZE:frame_size])
            del self._buffer[:frame_size]
            try:
                decoded = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise InvalidFrame("Frame body is not valid UTF-8 JSON.") from exc
            if not isinstance(decoded, dict):
                raise InvalidFrame("Frame body must be a JSON object.")
            messages.append(decoded)
        return messages
