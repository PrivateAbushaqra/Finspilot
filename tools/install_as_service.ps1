<#
Install the OmniFlow launcher as a Windows service using NSSM (Non-Sucking Service Manager).
This script does the following:
 - Checks for administrative privileges
 - Ensures pythonw.exe exists in the project's venv (or finds system pythonw)
 - Downloads NSSM if not found, extracts it, and uses it to install a service named OmniFlowLauncher
 - Configures stdout/stderr redirection to logs and auto-restart
 - Starts the service and sets to automatic start

Run PowerShell as Administrator and run:
  & "pos_system\tools\install_as_service.ps1"

#>
param(
    [string]$ServiceName = 'OmniFlowLauncher',
    [string]$LauncherScript = 'pos_system\tools\launcher.py',
    [string]$VenvPythonw = 'venv_new\Scripts\pythonw.exe'
)

function Assert-Admin {
    $isAdmin = ([bool](([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)))
    if (-not $isAdmin) {
        Write-Error "This script must be run as Administrator. Please re-run in an elevated PowerShell session."
        exit 1
    }
}

function Find-Pythonw {
    $root = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $projectRoot = Resolve-Path (Join-Path $root '..')

    $candidates = @(
        (Join-Path $projectRoot.Path $VenvPythonw),
        "$env:ProgramFiles\Python\pythonw.exe",
        "$env:ProgramFiles(x86)\Python\pythonw.exe",
        "pythonw.exe"
    )

    foreach ($p in $candidates) {
        try { $pp = Resolve-Path $p -ErrorAction Stop; return $pp.Path } catch {}
    }
    return $null
}

function Ensure-NSSM {
    param([string]$destDir)

    $nssmExe = Join-Path $destDir 'nssm.exe'
    if (Test-Path $nssmExe) { return $nssmExe }

    $tmp = Join-Path $env:TEMP "nssm_download_$(Get-Date -Format yyyyMMddHHmmss).zip"
    $url = 'https://nssm.cc/release/nssm-2.24.zip'

    Write-Output "Downloading NSSM from $url..."
    try {
        Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing -ErrorAction Stop
    } catch {
        Write-Error "Failed to download NSSM: $_"
        exit 1
    }

    $extractDir = Join-Path $env:TEMP "nssm_extract_$(Get-Date -Format yyyyMMddHHmmss)"
    Expand-Archive -Path $tmp -DestinationPath $extractDir -Force

    # The zip has subfolders; find win64 or win32
    $archDir = Get-ChildItem -Path $extractDir -Recurse -Filter nssm.exe | Select-Object -First 1
    if (-not $archDir) { Write-Error 'nssm.exe not found in archive'; exit 1 }

    Copy-Item -Path $archDir.FullName -Destination $nssmExe -Force
    Remove-Item -Path $tmp -Force
    Remove-Item -Path $extractDir -Recurse -Force

    return $nssmExe
}

Assert-Admin

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Resolve-Path (Join-Path $root '..')
$launcher = Resolve-Path (Join-Path $projectRoot.Path $LauncherScript)
$pythonw = Find-Pythonw

if (-not $pythonw) {
    Write-Error "pythonw.exe not found in venv or system PATH. Please ensure a pythonw is available."; exit 1
}

$nssmDir = Join-Path $projectRoot.Path 'tools'
$nssmExe = Ensure-NSSM -destDir $nssmDir

$logDir = Join-Path $projectRoot.Path 'tools' 
if (-not (Test-Path $logDir)) { New-Item -Path $logDir -ItemType Directory | Out-Null }
$stdoutLog = Join-Path $logDir 'launcher_stdout.log'
$stderrLog = Join-Path $logDir 'launcher_stderr.log'

# Install service
& $nssmExe install $ServiceName $pythonw $launcher.FullName

# Configure
& $nssmExe set $ServiceName AppDirectory $projectRoot.Path
& $nssmExe set $ServiceName AppStdout $stdoutLog
& $nssmExe set $ServiceName AppStderr $stderrLog
& $nssmExe set $ServiceName AppRestartDelay 5000
& $nssmExe set $ServiceName AppExit Default Restart
& $nssmExe set $ServiceName Start SERVICE_AUTO_START

# Start service
& $nssmExe start $ServiceName

Write-Output "Service '$ServiceName' installed and started. Logs: $stdoutLog, $stderrLog"