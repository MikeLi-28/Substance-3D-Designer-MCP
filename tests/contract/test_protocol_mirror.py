from __future__ import annotations

from substance_designer_mcp_plugin.bridge import framing as plugin_framing
from substance_designer_mcp_plugin.bridge import protocol as plugin_protocol

from substance_designer_mcp.bridge import framing as external_framing
from substance_designer_mcp.bridge import protocol as external_protocol


def test_protocol_constants_match_between_runtimes() -> None:
    assert external_framing.MAX_MESSAGE_SIZE == plugin_framing.MAX_MESSAGE_SIZE
    assert external_protocol.PROTOCOL_VERSION == plugin_protocol.PROTOCOL_VERSION


def test_framing_bytes_match_between_runtimes() -> None:
    message = {"request_id": "same", "arguments": {"value": 1}}

    assert external_framing.encode_message(message) == plugin_framing.encode_message(message)


def test_protocol_envelopes_match_between_runtimes() -> None:
    assert external_protocol.success_response("same", {"value": 1}) == (
        plugin_protocol.success_response("same", {"value": 1})
    )
