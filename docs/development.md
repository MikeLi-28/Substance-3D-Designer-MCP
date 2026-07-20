# Development

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\mypy.exe src
.\.venv\Scripts\python.exe -m build
.\.venv\Scripts\python.exe scripts\build_plugin.py
.\.venv\Scripts\python.exe scripts\verify_release.py --plugin-archive artifacts\substance_designer_mcp_plugin-1.1.0.zip
```

The release scanner checks forbidden arbitrary execution, `subprocess`, `os.system`, non-loopback
socket binding, external `sd` imports, Python 3.9 plugin syntax, the 500-line limit, and artifacts.

## Testing layers

- Unit: framing, session, registry, validation, compatibility, services, tools, lifecycle, scripts.
- Contract: request/response JSON Schema and duplicate protocol behavior.
- Integration: fake plugin bridge over real TCP through `BridgeClient` and a FastMCP tool.
- Real machine: the manual SD 16 checklist only.

Test doubles reproduce only the narrow interfaces required by automated tests and do not establish
Adobe API compatibility. New Adobe API use must match Designer's bundled Python API documentation.

## Python 3.9 plugin boundary

Plugin code uses no Pydantic, MCP SDK, or third-party web framework. CI parses and compiles it for
Python 3.9 compatibility and runs the plugin-only test subset on Python 3.9.
