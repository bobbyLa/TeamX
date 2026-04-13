[CmdletBinding()]
param(
    [string]$BrowserUrl = "http://127.0.0.1:9333",
    [int]$StartupTimeoutSeconds = 15,
    [string]$PackageSpec = "chrome-devtools-mcp@latest"
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$startScript = Join-Path $scriptRoot "start-chrome-devtools.ps1"

& $startScript -StartupTimeoutSeconds $StartupTimeoutSeconds | Out-Null

$npx = Get-Command npx.cmd -ErrorAction SilentlyContinue
if (-not $npx) {
    $npx = Get-Command npx -ErrorAction Stop
}

& $npx.Source "-y" $PackageSpec "--browserUrl" $BrowserUrl
