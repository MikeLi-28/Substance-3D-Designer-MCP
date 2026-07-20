from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_plugin_manager_probe_uses_official_lifecycle_and_redacts_session() -> None:
    runtime_path = ROOT / "tests/manual/sd16_plugin_probe_controller.py"
    probe_path = ROOT / "tests/manual/sd16_plugin_manager_smoke.py"
    assert runtime_path.exists()
    assert probe_path.exists()
    runtime_text = runtime_path.read_text(encoding="utf-8")
    probe_text = probe_path.read_text(encoding="utf-8")
    tree = ast.parse(runtime_text, feature_version=(3, 9))
    calls = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }

    assert {"checkPluginCompatibility", "loadPlugin", "getStatus", "unloadPlugin"} <= calls
    assert "token" not in {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)}
    assert "PluginProbeController" in probe_text
    assert "PluginProbeRuntime" in probe_text
    assert "QTimer(QtCore.QCoreApplication.instance())" in probe_text
    assert "controller.start()" in probe_text
    assert "SUBSTANCE_DESIGNER_MCP_ACTIVE_PACKAGE" in probe_text
    assert "active_package=ACTIVE_PACKAGE_PATH" in probe_text
    assert "QEventLoop" not in probe_text
    assert "time.sleep(" not in probe_text
    assert "subprocess" not in runtime_text
    assert "os.system" not in runtime_text


def test_e2e_host_bootstraps_a_nonblocking_main_thread_controller() -> None:
    path = ROOT / "tests/manual/sd16_e2e_host.py"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, feature_version=(3, 9))

    assert "HostController" in text
    assert "DesignerHostRuntime" in text
    assert "QTimer(QtCore.QCoreApplication.instance())" in text
    assert "controller.start()" in text
    assert "QEventLoop" not in text
    assert "time.sleep(" not in text
    assert "openResourceInEditor" not in text
    for variable in (
        "SUBSTANCE_DESIGNER_MCP_ACTIVE_PACKAGE",
        "SUBSTANCE_DESIGNER_MCP_LIBRARY_PACKAGE",
        "SUBSTANCE_DESIGNER_MCP_READY_PATH",
        "SUBSTANCE_DESIGNER_MCP_DONE_PATH",
        "SUBSTANCE_DESIGNER_MCP_HOST_REPORT",
        "SUBSTANCE_DESIGNER_MCP_SESSION_PATH",
    ):
        assert variable in text
    for forbidden in ("Stop-Process", "subprocess", "os.system"):
        assert forbidden not in text
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"eval", "exec"}
        for node in ast.walk(tree)
    )


def test_powershell_orchestrator_guards_processes_and_never_kills_designer() -> None:
    path = ROOT / "scripts/run_sd16_e2e.ps1"
    assert path.exists()
    text = path.read_text(encoding="utf-8")

    for required in (
        "Get-Process",
        "Start-Process",
        "-WindowStyle Hidden",
        "App Paths\\Adobe Substance 3D Designer.exe",
        "WaitForExit",
        "build_plugin.py",
        "Expand-Archive",
        "pattern_alveolus.sbs",
        "blend.sbs",
        "host-report-1.json",
        "mcp-e2e-report-1.json",
        "restart-report.json",
        "sd16-e2e-report.json",
    ):
        assert required in text
    for forbidden in (
        "Stop-Process",
        "taskkill",
        "Remove-Item -Recurse",
        "D:\\07_Software\\Adobe Substance 3D Designer",
    ):
        assert forbidden not in text


def test_orchestrator_defers_psscriptroot_defaults_until_script_body() -> None:
    path = ROOT / "scripts/run_sd16_e2e.ps1"
    text = path.read_text(encoding="utf-8")
    parameter_block = text.split("$ErrorActionPreference", maxsplit=1)[0]

    assert "[string]$ProjectRoot = ''" in parameter_block
    assert "[string]$OutputRoot = ''" in parameter_block
    assert "$scriptRootForDefaults = $PSScriptRoot" in text
    assert "if ([string]::IsNullOrWhiteSpace($ProjectRoot))" in text
    assert "if ([string]::IsNullOrWhiteSpace($OutputRoot))" in text


def test_orchestrator_uses_only_graph_hosts_for_release_evidence() -> None:
    text = (ROOT / "scripts/run_sd16_e2e.ps1").read_text(encoding="utf-8")
    graph = text.split("function Start-DesignerGraphHost", 1)[1].split("$ProjectRoot =", 1)[0]

    assert "'--quit'" not in graph
    assert "DocumentPath" in graph
    assert "-DocumentPath $ActivePackage" in text
    assert "function Start-DesignerStartupProbe" not in text
    assert "$pluginManagerProbe" not in text
    assert "plugin-manager-report.json" not in text


def test_orchestrator_runs_client_as_a_project_module() -> None:
    text = (ROOT / "scripts/run_sd16_e2e.ps1").read_text(encoding="utf-8")

    assert "& $pythonExe -m tests.manual.sd16_e2e_client" in text
    assert "& $pythonExe $clientProbe" not in text


def test_orchestrator_does_not_shadow_powershell_host_variable() -> None:
    text = (ROOT / "scripts/run_sd16_e2e.ps1").read_text(encoding="utf-8")

    assert "$host =" not in text.casefold()
    assert "$hostReportData = Read-JsonObject" in text


def test_designer_probes_load_plugin_from_extracted_plugin_root() -> None:
    probe_runtime_text = (ROOT / "tests/manual/sd16_plugin_probe_controller.py").read_text(
        encoding="utf-8"
    )
    controller_text = (ROOT / "tests/manual/sd16_e2e_controller.py").read_text(encoding="utf-8")

    assert "plugin_dir = self.plugin_parent / PLUGIN_NAME" in probe_runtime_text
    assert "sys.path.append(str(plugin_dir))" in probe_runtime_text
    assert "loadPlugin(PLUGIN_NAME, str(plugin_dir))" in probe_runtime_text
    assert "plugin_dir = self.paths.plugin_parent / PLUGIN_NAME" in controller_text
    assert "sys.path.append(str(plugin_dir))" in controller_text
    assert "loadPlugin(PLUGIN_NAME, str(plugin_dir))" in controller_text
