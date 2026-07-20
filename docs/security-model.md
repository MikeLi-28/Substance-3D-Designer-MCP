# Security model

## Trust boundary

The MCP host is allowed to request only the 29 published commands. The plugin bridge is a local
privilege boundary, not a general automation endpoint.

Controls:

- Loopback-only ephemeral listener.
- 256-bit random session token and constant-time comparison.
- 4 MiB message limit, request UUID, read/write timeouts, and versioned schema.
- Fixed command allow-list; no Python, code, script, shell, terminal, or system command execution.
- Qt main-thread dispatch for every service call and serialized writes.
- Strict top-level MCP schemas plus plugin-side validation.
- Explicit `confirm: true` for node deletion, package save, Save As, and SBSAR export.
- Save As and SBSAR paths must be absolute, use the required extension, have an existing parent,
  and opt in before overwriting an existing file.
- Versioned graph patches are additive, bounded, dry-runnable, runtime-type checked, cycle checked,
  and roll back every node created by the request if application fails.
- Bitmap import accepts only an existing local bitmap with an explicit embed method and never
  returns file bytes.
- Session-scoped object references and no `repr()` or memory address output.
- Token redaction, no material payload logging, no telemetry, and no internet requests.

## Error handling

Expected failures return stable error codes. Internal exceptions are recorded in the plugin's local
rotating log and converted to `INTERNAL_ERROR` or a narrower safe error. Public responses do not
contain tokens, tracebacks, or unrelated paths.

## Library identity

The search tool scans only resources available through loaded packages. Stable keys remove the
temporary `dependency` query field. The runtime URL is not intended for persistence across sessions.
