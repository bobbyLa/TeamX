$ErrorActionPreference = "Stop"

function Get-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    foreach ($line in Get-Content -LiteralPath $Path) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }

        $parts = $trimmed -split "=", 2
        if ($parts.Count -ne 2 -or $parts[0].Trim() -ne $Name) {
            continue
        }

        $value = $parts[1].Trim()
        if ($value.Length -ge 2) {
            $isDoubleQuoted = $value.StartsWith('"') -and $value.EndsWith('"')
            $isSingleQuoted = $value.StartsWith("'") -and $value.EndsWith("'")
            if ($isDoubleQuoted -or $isSingleQuoted) {
                $value = $value.Substring(1, $value.Length - 2)
            }
        }

        return $value
    }

    return $null
}

function Resolve-VaultRoot {
    param([string]$RepoRoot)

    $envPath = Join-Path $RepoRoot ".env"
    $configuredRoot = $env:OBSIDIAN_VAULT
    if ([string]::IsNullOrWhiteSpace($configuredRoot)) {
        $configuredRoot = Get-DotEnvValue -Path $envPath -Name "OBSIDIAN_VAULT"
    }

    if ([string]::IsNullOrWhiteSpace($configuredRoot)) {
        throw "OBSIDIAN_VAULT is not set in the environment or .env."
    }

    if (-not [System.IO.Path]::IsPathRooted($configuredRoot)) {
        $configuredRoot = Join-Path $RepoRoot $configuredRoot
    }

    $resolvedRoot = [System.IO.Path]::GetFullPath($configuredRoot)
    if (-not (Test-Path -LiteralPath $resolvedRoot)) {
        throw "OBSIDIAN_VAULT points to '$resolvedRoot', but that directory does not exist."
    }

    return $resolvedRoot
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
$vaultRoot = Resolve-VaultRoot -RepoRoot $repoRoot
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
