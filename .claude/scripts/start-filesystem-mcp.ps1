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

function Get-FilesystemRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [string]$EnvPath
    )

    $configuredRoot = $env:OBSIDIAN_VAULT
    if ([string]::IsNullOrWhiteSpace($configuredRoot)) {
        $configuredRoot = Get-DotEnvValue -Path $EnvPath -Name "OBSIDIAN_VAULT"
    }

    if ([string]::IsNullOrWhiteSpace($configuredRoot)) {
        $fallbackRoot = Join-Path $RepoRoot "archive"
        New-Item -ItemType Directory -Path $fallbackRoot -Force | Out-Null
        return $fallbackRoot
    }

    if (-not [System.IO.Path]::IsPathRooted($configuredRoot)) {
        $configuredRoot = Join-Path $RepoRoot $configuredRoot
    }

    $resolvedRoot = [System.IO.Path]::GetFullPath($configuredRoot)

    if (-not (Test-Path -LiteralPath $resolvedRoot)) {
        throw "OBSIDIAN_VAULT points to '$resolvedRoot', but that directory does not exist."
    }

    $item = Get-Item -LiteralPath $resolvedRoot
    if (-not $item.PSIsContainer) {
        throw "OBSIDIAN_VAULT points to '$resolvedRoot', but it is not a directory."
    }

    return $resolvedRoot
}

function Repair-NpxFilesystemCache {
    $cacheRoot = Join-Path $env:LOCALAPPDATA "npm-cache\_npx"
    if (-not (Test-Path -LiteralPath $cacheRoot)) {
        return
    }

    Get-ChildItem -LiteralPath $cacheRoot -Directory | ForEach-Object {
        $tempRoot = $_.FullName
        $ajvDir = Join-Path $tempRoot "node_modules\ajv"
        $ajvPackageJson = Join-Path $ajvDir "package.json"
        $ajvFormatsDir = Join-Path $tempRoot "node_modules\ajv-formats"

        if ((Test-Path -LiteralPath $ajvDir) -and (Test-Path -LiteralPath $ajvFormatsDir) -and -not (Test-Path -LiteralPath $ajvPackageJson)) {
            Remove-Item -LiteralPath $tempRoot -Recurse -Force
        }
    }
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$envPath = Join-Path $repoRoot ".env"
$filesystemRoot = Get-FilesystemRoot -RepoRoot $repoRoot -EnvPath $envPath

Repair-NpxFilesystemCache

$npx = Get-Command npx.cmd -ErrorAction SilentlyContinue
if (-not $npx) {
    $npx = Get-Command npx -ErrorAction Stop
}

Set-Location -LiteralPath $repoRoot
& $npx.Source "-y" "@modelcontextprotocol/server-filesystem@latest" $filesystemRoot
exit $LASTEXITCODE
