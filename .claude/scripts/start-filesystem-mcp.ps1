$ErrorActionPreference = "Stop"

function Resolve-VaultRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [ValidateSet("archive", "error")]
        [string]$OnMissing
    )

    $resolver = Join-Path $PSScriptRoot "resolve-vault-root.ps1"
    if (-not (Test-Path -LiteralPath $resolver)) {
        throw "Vault resolver script '$resolver' does not exist."
    }

    $resolutionJson = & $resolver -RepoRoot $RepoRoot -OnMissing $OnMissing
    if ([string]::IsNullOrWhiteSpace($resolutionJson)) {
        throw "Vault resolver returned no output."
    }

    return $resolutionJson | ConvertFrom-Json
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
$vaultResolution = Resolve-VaultRoot -RepoRoot $repoRoot -OnMissing archive
$filesystemRoot = $vaultResolution.root

Repair-NpxFilesystemCache

$npx = Get-Command npx.cmd -ErrorAction SilentlyContinue
if (-not $npx) {
    $npx = Get-Command npx -ErrorAction Stop
}

Set-Location -LiteralPath $repoRoot
& $npx.Source "-y" "@modelcontextprotocol/server-filesystem@latest" $filesystemRoot
exit $LASTEXITCODE
