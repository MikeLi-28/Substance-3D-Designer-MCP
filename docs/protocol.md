# Local bridge protocol

Protocol version: `1.0`.

## Transport

- TCP bound only to `127.0.0.1` on an operating-system-selected port.
- Four-byte big-endian unsigned payload length followed by UTF-8 JSON.
- Maximum payload: 4 MiB.
- Default read timeout: 5 seconds; write timeout: 30 seconds.
- One request and one response per connection in v1.1.0.

Schemas are published as [bridge-request.schema.json](schemas/bridge-request.schema.json) and
[bridge-response.schema.json](schemas/bridge-response.schema.json).

## Session file

The plugin atomically creates `~/.substance-designer-mcp/session.json` with protocol version,
loopback host, ephemeral port, 256-bit random token, PID, Designer version, plugin version, and UTC
start time. It attempts mode `0600`. Shutdown deletes the file only if its PID and token still match
the owning plugin. The client removes stale sessions after PID or port validation.

## Authentication

The request token is compared with `hmac.compare_digest` before command lookup or execution. The
token is never returned by tools and is not written to logs. A mismatch returns
`AUTHENTICATION_FAILED` and executes nothing.

## Example

```json
{
  "protocol_version": "1.0",
  "request_id": "80fd8f75-8ca8-47a0-8a47-59baf94da40b",
  "token": "session-secret",
  "command": "sd_get_active_graph",
  "arguments": {}
}
```

Errors use a stable `code`, a safe `message`, and JSON `details`. Tracebacks remain in local logs.
