$ErrorActionPreference = "Stop"

function Resolve-VaultRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [ValidateSet("archive", "error")]
        [string]$OnMissing
    )

    $resolver = Join-Path $RepoRoot ".claude\scripts\resolve-vault-root.ps1"
    if (-not (Test-Path -LiteralPath $resolver)) {
        throw "Vault resolver script '$resolver' does not exist."
    }

    $resolutionJson = & $resolver -RepoRoot $RepoRoot -OnMissing $OnMissing
    if ([string]::IsNullOrWhiteSpace($resolutionJson)) {
        throw "Vault resolver returned no output."
    }

    return $resolutionJson | ConvertFrom-Json
}

function Reset-Directory {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (Test-Path -LiteralPath $Destination) {
        Remove-Item -LiteralPath $Destination -Recurse -Force
    }

    if (Test-Path -LiteralPath $Source) {
        Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$vaultResolution = Resolve-VaultRoot -RepoRoot $repoRoot -OnMissing error
$vaultRoot = $vaultResolution.root
$sourceRoot = Join-Path $vaultRoot ".obsidian"
$destinationRoot = Join-Path $repoRoot ".obsidian-config"

if (-not (Test-Path -LiteralPath $sourceRoot)) {
    throw "Vault config directory '$sourceRoot' does not exist."
}

New-Item -ItemType Directory -Path $destinationRoot -Force | Out-Null

$rootFiles = @(
    "app.json",
    "appearance.json",
    "community-plugins.json",
    "core-plugins.json",
    "hotkeys.json",
    "types.json"
)

$copied = [System.Collections.Generic.List[string]]::new()

foreach ($name in $rootFiles) {
    $sourceFile = Join-Path $sourceRoot $name
    $destinationFile = Join-Path $destinationRoot $name
    if (Test-Path -LiteralPath $sourceFile) {
        Copy-Item -LiteralPath $sourceFile -Destination $destinationFile -Force
        $copied.Add(".obsidian/$name")
    }
    elseif (Test-Path -LiteralPath $destinationFile) {
        Remove-Item -LiteralPath $destinationFile -Force
    }
}

Reset-Directory -Source (Join-Path $sourceRoot "snippets") -Destination (Join-Path $destinationRoot "snippets")
if (Test-Path -LiteralPath (Join-Path $destinationRoot "snippets")) {
    $copied.Add(".obsidian/snippets/**")
}

Reset-Directory -Source (Join-Path $sourceRoot "themes") -Destination (Join-Path $destinationRoot "themes")
if (Test-Path -LiteralPath (Join-Path $destinationRoot "themes")) {
    $copied.Add(".obsidian/themes/**")
}

$pluginDestinationRoot = Join-Path $destinationRoot "plugins"
if (Test-Path -LiteralPath $pluginDestinationRoot) {
    Remove-Item -LiteralPath $pluginDestinationRoot -Recurse -Force
}

Get-ChildItem -LiteralPath (Join-Path $sourceRoot "plugins") -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $dataFile = Join-Path $_.FullName "data.json"
    if (-not (Test-Path -LiteralPath $dataFile)) {
        return
    }

    $targetDir = Join-Path $pluginDestinationRoot $_.Name
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Copy-Item -LiteralPath $dataFile -Destination (Join-Path $targetDir "data.json") -Force
    $copied.Add(".obsidian/plugins/$($_.Name)/data.json")
}

Write-Host "Synced vault config from $sourceRoot to $destinationRoot"
Write-Host "Copied entries:"
$copied | Sort-Object | ForEach-Object { Write-Host " - $_" }
