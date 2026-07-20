[CmdletBinding()]
param(
    [string]$ProjectRoot = '',
    [string]$OutputRoot = '',
    [int]$StartupTimeoutSeconds = 60,
    [int]$ExitTimeoutSeconds = 30
)

$ErrorActionPreference = 'Stop'
$scriptRootForDefaults = $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($scriptRootForDefaults)) {
    $scriptRootForDefaults = Split-Path -Parent $MyInvocation.MyCommand.Path
}
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
    $ProjectRoot = Split-Path -Parent $scriptRootForDefaults
}
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $ProjectRoot 'artifacts\sd16-e2e'
}

function Set-TestEnvironment {
    param([hashtable]$Values)
    foreach ($entry in $Values.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable(
            [string]$entry.Key,
            $entry.Value,
            [EnvironmentVariableTarget]::Process
        )
    }
}

function Read-JsonObject {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required JSON report is missing: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Assert-ChecksPassed {
    param(
        [Parameter(Mandatory = $true)]$Report,
        [Parameter(Mandatory = $true)][string[]]$Names,
        [Parameter(Mandatory = $true)][string]$Phase
    )
    foreach ($name in $Names) {
        $check = $Report.checks.$name
        if ($null -eq $check -or $check.passed -ne $true) {
            throw "$Phase check failed: $name"
        }
    }
}

function Wait-NaturalExit {
    param(
        [Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds,
        [Parameter(Mandatory = $true)][string]$Phase
    )
    if (-not $Process.WaitForExit($TimeoutSeconds * 1000)) {
        throw "$Phase did not exit naturally within $TimeoutSeconds seconds. The process was left untouched."
    }
    $Process.Refresh()
    if ($Process.ExitCode -ne 0) {
        throw "$Phase exited with code $($Process.ExitCode)."
    }
}

function Wait-ReadyMarker {
    param(
        [Parameter(Mandatory = $true)][System.Diagnostics.Process]$Process,
        [Parameter(Mandatory = $true)][string]$ReadyPath,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds,
        [Parameter(Mandatory = $true)][string]$Phase
    )
    $clock = [System.Diagnostics.Stopwatch]::StartNew()
    while ($clock.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        if (Test-Path -LiteralPath $ReadyPath -PathType Leaf) {
            return
        }
        if ($Process.HasExited) {
            $Process.Refresh()
            throw "$Phase exited before publishing readiness (exit $($Process.ExitCode))."
        }
        Start-Sleep -Milliseconds 100
    }
    throw "$Phase did not publish readiness within $TimeoutSeconds seconds. The process was left untouched."
}

function Start-DesignerGraphHost {
    param(
        [Parameter(Mandatory = $true)][string]$DesignerExe,
        [Parameter(Mandatory = $true)][string]$StartupScript,
        [Parameter(Mandatory = $true)][string]$DocumentPath
    )
    return Start-Process -FilePath $DesignerExe -ArgumentList @(
        ('"{0}"' -f $DocumentPath),
        '--startup-script',
        ('"{0}"' -f $StartupScript)
    ) -PassThru -WindowStyle Hidden
}

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$pythonExe = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw "Project virtual-environment Python is missing: $pythonExe"
}

$runningDesigner = @(
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ProcessName -match 'Substance.*Designer' }
)
if ($runningDesigner.Count -gt 0) {
    throw 'Adobe Substance 3D Designer is already running. Refusing to disturb an active session.'
}

$appPathKey = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\App Paths\Adobe Substance 3D Designer.exe'
if (-not (Test-Path $appPathKey)) {
    throw 'Designer App Paths registry entry was not found.'
}
$designerExe = ([string](Get-ItemPropertyValue -Path $appPathKey -Name '(default)')).Trim('"')
if (-not (Test-Path -LiteralPath $designerExe -PathType Leaf)) {
    throw "Designer executable does not exist: $designerExe"
}
$designerRoot = Split-Path -Parent $designerExe
$packageRoot = Join-Path $designerRoot 'resources\packages'
$activePackageSource = Join-Path $packageRoot 'pattern_alveolus.sbs'
$libraryPackageSource = Join-Path $packageRoot 'blend.sbs'
foreach ($path in ($activePackageSource, $libraryPackageSource)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw "Required official fixture Package is missing: $path"
    }
}

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$runName = '{0}-{1}' -f ([DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')), $PID
$runRoot = Join-Path ([System.IO.Path]::GetFullPath($OutputRoot)) $runName
$pluginArtifacts = Join-Path $runRoot 'plugin-artifacts'
$pluginParent = Join-Path $runRoot 'plugin'
$fixtures = Join-Path $runRoot 'fixtures'
New-Item -ItemType Directory -Path $pluginArtifacts, $pluginParent, $fixtures -Force | Out-Null

Push-Location $ProjectRoot
try {
    & $pythonExe scripts\build_plugin.py --output $pluginArtifacts
    if ($LASTEXITCODE -ne 0) {
        throw 'Plugin artifact build failed.'
    }
} finally {
    Pop-Location
}
$pluginArchive = Join-Path $pluginArtifacts 'substance_designer_mcp_plugin-1.1.0.zip'
if (-not (Test-Path -LiteralPath $pluginArchive -PathType Leaf)) {
    throw "Plugin archive was not created: $pluginArchive"
}
Expand-Archive -LiteralPath $pluginArchive -DestinationPath $pluginParent
$activePackage1 = Join-Path $fixtures 'pattern_alveolus-1.sbs'
$activePackage2 = Join-Path $fixtures 'pattern_alveolus-2.sbs'
$libraryPackage = Join-Path $fixtures 'blend.sbs'
Copy-Item -LiteralPath $activePackageSource -Destination $activePackage1
Copy-Item -LiteralPath $activePackageSource -Destination $activePackage2
Copy-Item -LiteralPath $libraryPackageSource -Destination $libraryPackage

$hostProbe = Join-Path $ProjectRoot 'tests\manual\sd16_e2e_host.py'
$supportProbe = Join-Path $ProjectRoot 'tests\manual\sd16_e2e_support.py'
$hostReport1 = Join-Path $runRoot 'host-report-1.json'
$hostReport2 = Join-Path $runRoot 'host-report-2.json'
$mcpReport1 = Join-Path $runRoot 'mcp-e2e-report-1.json'
$mcpReport2 = Join-Path $runRoot 'mcp-e2e-report-2.json'
$staleReport = Join-Path $runRoot 'stale-session-report.json'
$restartReport = Join-Path $runRoot 'restart-report.json'
$metadataReport = Join-Path $runRoot 'metadata-report.json'
$combinedReport = Join-Path $runRoot 'sd16-e2e-report.json'

$environmentNames = @(
    'SUBSTANCE_DESIGNER_MCP_PROJECT_ROOT',
    'SUBSTANCE_DESIGNER_MCP_TEST_PLUGIN_PARENT',
    'SUBSTANCE_DESIGNER_MCP_SESSION_PATH',
    'SUBSTANCE_DESIGNER_MCP_PLUGIN_LOG_PATH',
    'SUBSTANCE_DESIGNER_MCP_ACTIVE_PACKAGE',
    'SUBSTANCE_DESIGNER_MCP_LIBRARY_PACKAGE',
    'SUBSTANCE_DESIGNER_MCP_READY_PATH',
    'SUBSTANCE_DESIGNER_MCP_DONE_PATH',
    'SUBSTANCE_DESIGNER_MCP_HOST_REPORT',
    'SUBSTANCE_DESIGNER_MCP_HOST_TIMEOUT',
    'SUBSTANCE_DESIGNER_MCP_CLIENT_MODE',
    'SUBSTANCE_DESIGNER_MCP_CLIENT_REPORT',
    'SUBSTANCE_DESIGNER_MCP_E2E_WORKSPACE'
)
$originalEnvironment = @{}
foreach ($name in $environmentNames) {
    $originalEnvironment[$name] = [Environment]::GetEnvironmentVariable(
        $name,
        [EnvironmentVariableTarget]::Process
    )
}

function Invoke-E2EPhase {
    param(
        [Parameter(Mandatory = $true)][int]$Index,
        [Parameter(Mandatory = $true)][ValidateSet('full', 'snapshot')][string]$Mode,
        [Parameter(Mandatory = $true)][string]$ActivePackage,
        [Parameter(Mandatory = $true)][string]$HostReport,
        [Parameter(Mandatory = $true)][string]$ClientReport
    )
    $sessionPath = Join-Path $runRoot ("session-{0}.json" -f $Index)
    $readyPath = Join-Path $runRoot ("ready-{0}.txt" -f $Index)
    $donePath = Join-Path $runRoot ("done-{0}.txt" -f $Index)
    $logPath = Join-Path $runRoot ("plugin-{0}.log" -f $Index)
    Set-TestEnvironment @{
        SUBSTANCE_DESIGNER_MCP_PROJECT_ROOT = $ProjectRoot
        SUBSTANCE_DESIGNER_MCP_TEST_PLUGIN_PARENT = $pluginParent
        SUBSTANCE_DESIGNER_MCP_SESSION_PATH = $sessionPath
        SUBSTANCE_DESIGNER_MCP_PLUGIN_LOG_PATH = $logPath
        SUBSTANCE_DESIGNER_MCP_ACTIVE_PACKAGE = $ActivePackage
        SUBSTANCE_DESIGNER_MCP_LIBRARY_PACKAGE = $libraryPackage
        SUBSTANCE_DESIGNER_MCP_READY_PATH = $readyPath
        SUBSTANCE_DESIGNER_MCP_DONE_PATH = $donePath
        SUBSTANCE_DESIGNER_MCP_HOST_REPORT = $HostReport
        SUBSTANCE_DESIGNER_MCP_HOST_TIMEOUT = [string]$StartupTimeoutSeconds
        SUBSTANCE_DESIGNER_MCP_CLIENT_MODE = $Mode
        SUBSTANCE_DESIGNER_MCP_CLIENT_REPORT = $ClientReport
        SUBSTANCE_DESIGNER_MCP_E2E_WORKSPACE = $runRoot
    }
    $process = Start-DesignerGraphHost -DesignerExe $designerExe -StartupScript $hostProbe -DocumentPath $ActivePackage
    Wait-ReadyMarker -Process $process -ReadyPath $readyPath -TimeoutSeconds $StartupTimeoutSeconds -Phase "Designer E2E host $Index"
    if ($Index -eq 1) {
        Copy-Item -LiteralPath $sessionPath -Destination (Join-Path $runRoot 'stale-session.json')
    }
    $clientExit = 1
    try {
        Push-Location $ProjectRoot
        try {
            & $pythonExe -m tests.manual.sd16_e2e_client
            $clientExit = $LASTEXITCODE
        } finally {
            Pop-Location
        }
    } finally {
        Set-Content -LiteralPath $donePath -Value 'done' -Encoding UTF8
    }
    Wait-NaturalExit -Process $process -TimeoutSeconds $ExitTimeoutSeconds -Phase "Designer E2E host $Index"
    if ($clientExit -ne 0) {
        throw "External MCP client phase $Index failed with exit code $clientExit."
    }
    $hostReportData = Read-JsonObject -Path $HostReport
    Assert-ChecksPassed -Report $hostReportData -Names @(
        'fixture_loaded',
        'library_loaded',
        'active_graph_ready',
        'plugin_loaded',
        'session_created',
        'loopback_only',
        'done_received',
        'plugin_unloaded',
        'packages_unloaded',
        'session_removed',
        'port_closed'
    ) -Phase "Designer E2E host $Index"
    $client = Read-JsonObject -Path $ClientReport
    if ($null -ne $client.error) {
        throw "External MCP client phase $Index reported an error: $($client.error.message)"
    }
    return @{ Host = $hostReportData; Client = $client; SessionPath = $sessionPath }
}

try {
    $phase1 = Invoke-E2EPhase -Index 1 -Mode full -ActivePackage $activePackage1 -HostReport $hostReport1 -ClientReport $mcpReport1

    $staleSession = Join-Path $runRoot 'stale-session.json'
    Set-TestEnvironment @{
        SUBSTANCE_DESIGNER_MCP_SESSION_PATH = $staleSession
        SUBSTANCE_DESIGNER_MCP_CLIENT_MODE = 'stale'
        SUBSTANCE_DESIGNER_MCP_CLIENT_REPORT = $staleReport
        SUBSTANCE_DESIGNER_MCP_DONE_PATH = $null
        SUBSTANCE_DESIGNER_MCP_E2E_WORKSPACE = $runRoot
    }
    Push-Location $ProjectRoot
    try {
        & $pythonExe -m tests.manual.sd16_e2e_client
        if ($LASTEXITCODE -ne 0) {
            throw 'Stale-session client verification failed.'
        }
    } finally {
        Pop-Location
    }
    $stale = Read-JsonObject -Path $staleReport
    Assert-ChecksPassed -Report $stale -Names @('stale_session_rejected') -Phase 'Stale session'

    $phase2 = Invoke-E2EPhase -Index 2 -Mode snapshot -ActivePackage $activePackage2 -HostReport $hostReport2 -ClientReport $mcpReport2
    $stable1 = [string]$phase1.Client.library.stable_key
    $stable2 = [string]$phase2.Client.library.stable_key
    $stableIdentity = -not [string]::IsNullOrWhiteSpace($stable1) -and $stable1 -eq $stable2
    $restart = @{
        phase = 'restart'
        checks = @{
            stale_session_rejected = $stale.checks.stale_session_rejected
            stable_library_identity = @{
                passed = $stableIdentity
                evidence = @{ first = $stable1; second = $stable2 }
            }
        }
    }
    $restart | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $restartReport -Encoding UTF8
    if (-not $stableIdentity) {
        throw 'Library stable identity changed across isolated Designer sessions.'
    }

    $metadata = @{
        phase = 'metadata'
        tested_at = [DateTime]::UtcNow.ToString('o')
        designer_version = $phase1.Host.designer_version
        python_version = $phase1.Host.python_version
        plugin_version = $phase1.Host.session.plugin_version
        protocol_version = $phase1.Host.session.protocol_version
        plugin_artifact = @{
            file = (Split-Path -Leaf $pluginArchive)
            sha256 = (Get-FileHash -LiteralPath $pluginArchive -Algorithm SHA256).Hash
        }
    }
    $metadata | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $metadataReport -Encoding UTF8

    $aggregateArguments = @(
        $supportProbe,
        'aggregate',
        '--report', $hostReport1,
        '--report', $mcpReport1,
        '--report', $hostReport2,
        '--report', $mcpReport2,
        '--report', $restartReport,
        '--report', $metadataReport,
        '--workspace', $runRoot,
        '--output', $combinedReport
    )
    foreach ($requiredCheck in @(
        'plugin_compatible',
        'plugin_loaded',
        'plugin_unloaded',
        'mcp_connected',
        'active_graph_read',
        'selection_read',
        'nodes_read',
        'node_read',
        'properties_read',
        'library_search',
        'atomic_node_created',
        'instance_node_created',
        'nodes_moved',
        'connection_roundtrip',
        'invalid_connection_rejected',
        'parameter_validation',
        'delete_confirmation',
        'save_confirmation',
        'stale_session_rejected',
        'stable_library_identity',
        'session_removed',
        'port_closed'
    )) {
        $aggregateArguments += @('--required-check', $requiredCheck)
    }
    Push-Location $ProjectRoot
    try {
        & $pythonExe @aggregateArguments
        if ($LASTEXITCODE -ne 0) {
            throw 'Combined SD 16 E2E evidence did not pass every required check.'
        }
    } finally {
        Pop-Location
    }
    Write-Output $combinedReport
} finally {
    foreach ($name in $environmentNames) {
        [Environment]::SetEnvironmentVariable(
            $name,
            $originalEnvironment[$name],
            [EnvironmentVariableTarget]::Process
        )
    }
}
