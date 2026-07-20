# Substance-3D-Designer-MCP

[中文](README.zh-CN.md) | **English**

An independent, security-focused Model Context Protocol server for Adobe Substance 3D Designer.
Version 1.1.0 adds generic authoring tools while keeping the MCP runtime outside Designer so
each Python environment remains isolated.

> **Compatibility status:** Substance 3D Designer 16.0.3 is the supported baseline. The 1.0.0
> capability set is real-machine verified on that version. Authoring extensions introduced in
> 1.1.0 are not yet real-machine verified.

## Compatibility

| Substance Designer version | Status |
|---|---|
| 16.0.3 | Supported baseline; 1.1.0 authoring extensions are not yet real-machine verified |
| Other released 16.x versions | Unverified; capabilities are detected at runtime |
| Newer major versions | Experimental and unverified |

A version is marked as fully tested only after the plugin and MCP tools have been exercised in a real Substance Designer installation. Capability detection does not replace real-version testing.

## What it does

- Reads application, package, graph, selection, node, property, and capability state.
- Searches resources in packages already loaded by Designer.
- Creates verified atomic nodes and instances of resources returned by the search tool.
- Moves and deletes explicit nodes, connects explicit runtime properties, and writes supported
  simple parameters.
- Saves one already-saved package in place after explicit confirmation.
- Creates new packages and compositing graphs without relying on the current selection.
- Reads runtime node definitions and versioned graph snapshots with explicit connections.
- Creates Output nodes with real Designer usage metadata instead of response-only labels.
- Dry-runs and applies bounded additive graph patches with runtime validation and rollback.
- Imports local bitmap resources, performs confirmed Save As, and publishes saved packages to
  SBSAR through the documented in-process API.

It does not generate material recipes, scrape Qt UI, expose Python or shell execution, access the
internet, upload telemetry, or provide remote control.

## Architecture

```text
MCP host
   | stdio
External Python 3.10+ MCP server
   | authenticated length-prefixed JSON on 127.0.0.1
Designer Python plugin
   | allow-listed command registry and Qt main-thread dispatcher
Focused services and compatibility probes
   | verified Adobe Python API calls
Substance 3D Designer (real-machine verified: 16.0.3)
```

The external process never imports Adobe's `sd` module. The bridge contains transport only.
Designer API calls live in plugin services or the compatibility adapter. See
[architecture.md](docs/architecture.md) and [security-model.md](docs/security-model.md).

## Installation

### External MCP server

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Cross-platform:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

The installed command is `substance-designer-mcp` and uses stdio by default.

### Designer plugin

Build the distributable ZIP:

```powershell
.\.venv\Scripts\python.exe scripts\build_plugin.py
```

Install into an explicit **user plugin directory**:

```powershell
.\.venv\Scripts\python.exe scripts\install_plugin.py --target "C:\path\to\Designer\user-plugins"
```

The installer refuses Adobe's application installation tree and backs up an existing plugin.
Manual Plugin Manager loading and uninstall details are in [installation.md](docs/installation.md).

### MCP host configuration

```json
{
  "mcpServers": {
    "substance-designer": {
      "command": "substance-designer-mcp",
      "args": []
    }
  }
}
```

The MCP host starts the installed `substance-designer-mcp` stdio command. The Designer plugin must
also be installed locally before the server can connect to Designer.

## Tools

| Tool | Access | Risk boundary |
| --- | --- | --- |
| `sd_ping` | Read | Reports offline state without crashing |
| `sd_get_application_info` | Read | Runtime-probed information only |
| `sd_get_capabilities` | Read | Separates availability from verification |
| `sd_list_packages` | Read | Open packages only |
| `sd_get_active_graph` | Read | Current graph only |
| `sd_list_graph_nodes` | Read | Bounded pagination |
| `sd_get_selection` | Read | Bounded current selection |
| `sd_get_node` | Read | Structured current-session reference |
| `sd_list_node_properties` | Read | Runtime IDs and types |
| `sd_search_library` | Read | Loaded resources, no UI scraping |
| `sd_create_node` | Write | Verified runtime definition only |
| `sd_create_instance_node` | Write | Search-result resource reference only |
| `sd_move_nodes` | Write | Explicit nodes and finite coordinates |
| `sd_delete_nodes` | Destructive | Requires `confirm: true`; empty list rejected |
| `sd_connect_nodes` | Write | Explicit runtime properties; no port guessing |
| `sd_disconnect_nodes` | Write | Explicit existing connection |
| `sd_set_node_parameter` | Write | Runtime type checked; simple types only |
| `sd_save_package` | Destructive | Requires `confirm: true`; no Save As |
| `sd_create_package` | Write | Creates one unsaved user package |
| `sd_create_graph` | Write | Explicit package and portable unique identifier |
| `sd_list_node_definitions` | Read | Runtime catalog; bounded and searchable |
| `sd_get_graph_snapshot` | Read | Versioned bounded nodes, properties, connections, and presets |
| `sd_open_graph` | Write | Opens one explicit graph in the editor |
| `sd_create_graph_output` | Write | Explicit identifier, label, group, and official usages |
| `sd_validate_graph_patch` | Read | Dry-run only; definitions, ports, types, targets, and cycles |
| `sd_apply_graph_patch` | Write | Additive patch only; rollback of all created nodes on failure |
| `sd_import_bitmap` | Write | Existing local bitmap and explicit embed method only |
| `sd_save_package_as` | Destructive | Absolute `.sbs`, existing parent, overwrite opt-in, confirmation |
| `sd_export_package_sbsar` | Destructive | Saved package, explicit settings, overwrite opt-in, confirmation |

## Configuration

| Environment variable | Default |
| --- | --- |
| `SUBSTANCE_DESIGNER_MCP_SESSION_PATH` | `~/.substance-designer-mcp/session.json` |
| `SUBSTANCE_DESIGNER_MCP_PLUGIN_LOG_PATH` | `~/.substance-designer-mcp/logs/plugin.log` |
| `SUBSTANCE_DESIGNER_MCP_CONNECT_TIMEOUT` | `5` seconds |
| `SUBSTANCE_DESIGNER_MCP_READ_TIMEOUT` | `5` seconds |
| `SUBSTANCE_DESIGNER_MCP_WRITE_TIMEOUT` | `30` seconds |
| `SUBSTANCE_DESIGNER_MCP_LOG_LEVEL` | `INFO` |

Set the session and plugin-log path variables before Designer imports the plugin. This lets an
isolated test session avoid replacing the normal per-user state files.

Logs use stderr or rotating files. Stdio stdout is reserved for MCP protocol messages.

## Development

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\mypy.exe src
.\.venv\Scripts\python.exe -m build
.\.venv\Scripts\python.exe scripts\build_plugin.py
```

API claims must come from Designer's bundled Python API documentation. Contribution and release
rules are in [CONTRIBUTING.md](CONTRIBUTING.md) and [development.md](docs/development.md).

## License and trademarks

MIT. Adobe and Substance 3D Designer are trademarks of Adobe. This project is independent and is
not endorsed by Adobe.
