param(
    [string]$ServiceName = 'OmniFlowLauncher'
)

function Assert-Admin {
    $isAdmin = ([bool](([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)))
    if (-not $isAdmin) {
        Write-Error "This script must be run as Administrator. Please re-run in an elevated PowerShell session."
        exit 1
    }
}

Assert-Admin

$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
$projectRoot = Resolve-Path (Join-Path $root '..')
$nssmExe = Join-Path $projectRoot.Path 'tools\nssm.exe'
if (-not (Test-Path $nssmExe)) { Write-Warning "nssm.exe not found in tools folder. Trying to remove service with sc.exe..." }

try {
    if (Test-Path $nssmExe) {
        & $nssmExe remove $ServiceName confirm
    } else {
        sc.exe stop $ServiceName
        sc.exe delete $ServiceName
    }
    Write-Output "Service $ServiceName removed (if existed)."
} catch {
    Write-Error "Error removing service: $_"
}
