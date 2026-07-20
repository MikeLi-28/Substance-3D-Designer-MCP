# Installation

## External server

Python 3.10-3.13 is supported by CI configuration.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
substance-designer-mcp
```

The command runs stdio. Starting it without Designer is safe: tool calls return `SD_NOT_RUNNING`.

## Designer compatibility

Designer 16.0.3 is the supported baseline. The `1.0.0` capability set is real-machine verified on
that version; authoring extensions introduced in `1.1.0` are not yet real-machine verified. Other
released Designer 16.x versions are unverified and use runtime capability detection. Newer major
versions are experimental. See [compatibility.md](compatibility.md).

## Plugin build and install

```powershell
.\.venv\Scripts\python.exe scripts\build_plugin.py
.\.venv\Scripts\python.exe scripts\install_plugin.py --target "C:\explicit\user-plugin-dir"
```

The target must already exist and must be a Designer user-plugin directory, not Adobe's application
installation tree. An existing `substance_designer_mcp_plugin` directory is renamed to a timestamped
backup before replacement.

To uninstall:

```powershell
.\.venv\Scripts\python.exe scripts\uninstall_plugin.py --target "C:\explicit\user-plugin-dir"
```

Only the exact child directory `substance_designer_mcp_plugin` is removed.

## Manual Plugin Manager loading

1. Build the ZIP and extract `substance_designer_mcp_plugin` to a writable user location.
2. Open Designer's Plugin Manager.
3. Load the extracted directory containing `pluginInfo.json`.
4. Confirm the plugin status is Loaded and inspect its local log on failure.

The plugin stores session state under `~/.substance-designer-mcp/` and does not modify Adobe core
files or user preferences.

## MCP Inspector

After installing the external package, run the official MCP Inspector against the command
`substance-designer-mcp`. Confirm initialization, the 18 tool names, strict schemas, annotations,
structured offline errors, and no non-protocol stdout. This is an MCP protocol check, not a
Designer 16.0.3 real-machine check.
