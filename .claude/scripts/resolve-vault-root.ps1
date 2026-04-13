param(
    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,
    [Alias("OnMissing")]
    [ValidateSet("archive", "error")]
    [string]$MissingMode = "error"
)

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
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoRoot,
        [Parameter(Mandatory = $true)]
        [ValidateSet("archive", "error")]
        [string]$MissingMode
    )

    $envPath = Join-Path $RepoRoot ".env"
    $configuredRoot = $env:OBSIDIAN_VAULT
    $source = "env"

    if ([string]::IsNullOrWhiteSpace($configuredRoot)) {
        $configuredRoot = Get-DotEnvValue -Path $envPath -Name "OBSIDIAN_VAULT"
        $source = "dotenv"
    }

    if ([string]::IsNullOrWhiteSpace($configuredRoot)) {
        if ($MissingMode -eq "archive") {
            $fallbackRoot = Join-Path $RepoRoot "archive"
            New-Item -ItemType Directory -Path $fallbackRoot -Force | Out-Null
            return [pscustomobject]@{
                root = [System.IO.Path]::GetFullPath($fallbackRoot)
                source = "archive"
                usedFallback = $true
            }
        }

        throw "OBSIDIAN_VAULT is not set in the environment or .env."
    }

    if (-not [System.IO.Path]::IsPathRooted($configuredRoot)) {
        $configuredRoot = Join-Path $RepoRoot $configuredRoot
    }

    $resolvedRoot = [System.IO.Path]::GetFullPath($configuredRoot)
    if (-not (Test-Path -LiteralPath $resolvedRoot)) {
        throw "OBSIDIAN_VAULT from $source points to '$resolvedRoot', but that directory does not exist."
    }

    $item = Get-Item -LiteralPath $resolvedRoot
    if (-not $item.PSIsContainer) {
        throw "OBSIDIAN_VAULT from $source points to '$resolvedRoot', but it is not a directory."
    }

    return [pscustomobject]@{
        root = $resolvedRoot
        source = $source
        usedFallback = $false
    }
}

$resolvedRepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
$resolution = Resolve-VaultRoot -RepoRoot $resolvedRepoRoot -MissingMode $MissingMode
$resolution | ConvertTo-Json -Compress
