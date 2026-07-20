from __future__ import annotations

import json
import struct

import pytest

from substance_designer_mcp.bridge.framing import (
    MAX_MESSAGE_SIZE,
    FrameDecoder,
    FrameTooLarge,
    encode_message,
)


def test_encode_message_uses_big_endian_length_and_utf8_json() -> None:
    message = {"text": "材质", "count": 2}

    frame = encode_message(message)

    payload_size = struct.unpack(">I", frame[:4])[0]
    assert payload_size == len(frame[4:])
    assert json.loads(frame[4:].decode("utf-8")) == message


def test_decoder_accepts_split_frame() -> None:
    frame = encode_message({"ok": True})
    decoder = FrameDecoder()

    assert decoder.feed(frame[:2]) == []
    assert decoder.feed(frame[2:6]) == []
    assert decoder.feed(frame[6:]) == [{"ok": True}]


def test_decoder_returns_every_coalesced_frame() -> None:
    decoder = FrameDecoder()
    combined = encode_message({"index": 1}) + encode_message({"index": 2})

    assert decoder.feed(combined) == [{"index": 1}, {"index": 2}]


def test_decoder_rejects_payload_above_limit_before_buffering_body() -> None:
    decoder = FrameDecoder()

    with pytest.raises(FrameTooLarge):
        decoder.feed(struct.pack(">I", MAX_MESSAGE_SIZE + 1))


def test_encode_message_rejects_payload_above_limit() -> None:
    with pytest.raises(FrameTooLarge):
        encode_message({"data": "x" * MAX_MESSAGE_SIZE})
