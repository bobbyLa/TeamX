[CmdletBinding()]
param(
    [switch]$ForceResync,
    [int]$StartupTimeoutSeconds = 10
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-ChromeExecutablePath {
    $command = Get-Command chrome.exe -ErrorAction SilentlyContinue
    if ($command -and -not [string]::IsNullOrWhiteSpace($command.Source)) {
        return $command.Source
    }

    $candidates = @()
    foreach ($basePath in @($env:ProgramFiles, ${env:ProgramFiles(x86)}, $env:LOCALAPPDATA)) {
        if ([string]::IsNullOrWhiteSpace($basePath)) {
            continue
        }

        $candidates += Join-Path $basePath "Google\Chrome\Application\chrome.exe"
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    throw "Chrome executable not found. Install Google Chrome or update this script with the correct path."
}

function Assert-NoChromeProcesses {
    $chromeProcesses = Get-Process chrome -ErrorAction SilentlyContinue
    if ($null -eq $chromeProcesses) {
        return
    }

    $processIds = ($chromeProcesses | Select-Object -ExpandProperty Id | Sort-Object) -join ", "
    throw "Chrome is still running (PID(s): $processIds). Exit all Chrome windows before seeding or re-syncing the TeamX profile."
}

function Remove-ProjectProfileSafely {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $fullRepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)

    if (-not $fullPath.StartsWith($fullRepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to delete outside the repository root: $fullPath"
    }

    if ([System.IO.Path]::GetFileName($fullPath) -ne ".chrome-profile") {
        throw "Refusing to delete an unexpected path: $fullPath"
    }

    Remove-Item -LiteralPath $fullPath -Recurse -Force
}

function Copy-Directory {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    New-Item -ItemType Directory -Path $Destination -Force | Out-Null

    & robocopy $Source $Destination /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "robocopy failed while copying '$Source' to '$Destination' (exit code $LASTEXITCODE)."
    }
}

function Seed-ProjectProfile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourceUserDataRoot,
        [Parameter(Mandatory = $true)]
        [string]$TargetUserDataRoot,
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot
    )

    $sourceLocalState = Join-Path $SourceUserDataRoot "Local State"
    $sourceDefaultProfile = Join-Path $SourceUserDataRoot "Default"

    if (-not (Test-Path -LiteralPath $sourceLocalState)) {
        throw "Source Chrome Local State not found: $sourceLocalState"
    }

    if (-not (Test-Path -LiteralPath $sourceDefaultProfile)) {
        throw "Source Chrome Default profile not found: $sourceDefaultProfile"
    }

    Remove-ProjectProfileSafely -Path $TargetUserDataRoot -RepoRoot $RepoRoot
    New-Item -ItemType Directory -Path $TargetUserDataRoot -Force | Out-Null

    Copy-Item -LiteralPath $sourceLocalState -Destination (Join-Path $TargetUserDataRoot "Local State") -Force
    Copy-Directory -Source $sourceDefaultProfile -Destination (Join-Path $TargetUserDataRoot "Default")
}

function Get-DevToolsVersionInfo {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BaseUrl,
        [int]$TimeoutSeconds = 10
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $probeUrl = "$BaseUrl/json/version"

    do {
        try {
            return Invoke-RestMethod -Uri $probeUrl -UseBasicParsing -TimeoutSec 2
        } catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline)

    return $null
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$projectProfileRoot = Join-Path $repoRoot ".chrome-profile"
$projectDefaultProfile = Join-Path $projectProfileRoot "Default"
$projectLocalState = Join-Path $projectProfileRoot "Local State"
$sourceUserDataRoot = Join-Path $env:LOCALAPPDATA "Google\Chrome\User Data"
$chromeExe = Get-ChromeExecutablePath
$devToolsUrl = "http://127.0.0.1:9333"
$verificationEndpoint = "$devToolsUrl/json/version"
$needsSeed = $ForceResync -or -not (Test-Path -LiteralPath $projectProfileRoot) -or -not (Test-Path -LiteralPath $projectLocalState) -or -not (Test-Path -LiteralPath $projectDefaultProfile)

if (-not $ForceResync -and -not $needsSeed) {
    $existingVersion = Get-DevToolsVersionInfo -BaseUrl $devToolsUrl -TimeoutSeconds 1
    if ($null -ne $existingVersion) {
        Write-Host "Reusing running TeamX Chrome instance."
        Write-Host "Chrome executable: $chromeExe"
        Write-Host "Profile root: $projectProfileRoot"
        Write-Host "DevTools URL: $devToolsUrl"
        Write-Host "Verification endpoint: $verificationEndpoint"
        if ($existingVersion.Browser) {
            Write-Host "Browser: $($existingVersion.Browser)"
        }
        return
    }
}

if ($needsSeed) {
    Assert-NoChromeProcesses
    Seed-ProjectProfile -SourceUserDataRoot $sourceUserDataRoot -TargetUserDataRoot $projectProfileRoot -RepoRoot $repoRoot
    Write-Host "Seeded TeamX profile from system Chrome Default: $(Join-Path $sourceUserDataRoot 'Default')"
} else {
    Write-Host "Reusing existing TeamX project profile."
}

$launchArgs = @(
    "--remote-debugging-port=9333",
    "--user-data-dir=$projectProfileRoot",
    "--profile-directory=Default",
    "--no-first-run",
    "--no-default-browser-check",
    "about:blank"
)

Start-Process -FilePath $chromeExe -ArgumentList $launchArgs | Out-Null

Write-Host "Chrome executable: $chromeExe"
Write-Host "Profile root: $projectProfileRoot"
Write-Host "DevTools URL: $devToolsUrl"
Write-Host "Verification endpoint: $verificationEndpoint"

$versionInfo = Get-DevToolsVersionInfo -BaseUrl $devToolsUrl -TimeoutSeconds $StartupTimeoutSeconds
if ($null -ne $versionInfo) {
    Write-Host "DevTools endpoint is ready."
    if ($versionInfo.Browser) {
        Write-Host "Browser: $($versionInfo.Browser)"
    }
} else {
    Write-Warning "Chrome was launched, but $verificationEndpoint did not respond within the timeout window."
}
