param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [string]$SumFile = "SHA256SUMS.txt"
)

$ErrorActionPreference = "Stop"

$rootPath = (Resolve-Path -LiteralPath $Root).Path
$sumPath = Join-Path $rootPath $SumFile

if (-not (Test-Path -LiteralPath $sumPath)) {
    throw "Missing checksum file: $sumPath"
}

$failed = 0
$checked = 0

Get-Content -LiteralPath $sumPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
        return
    }

    $parts = $line -split "\s+", 2
    if ($parts.Count -ne 2) {
        Write-Warning "Skip malformed line: $line"
        return
    }

    $expected = $parts[0].ToLowerInvariant()
    $relative = $parts[1]
    $path = Join-Path $rootPath $relative

    if (-not (Test-Path -LiteralPath $path)) {
        Write-Host "MISSING  $relative"
        $failed++
        return
    }

    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant()
    if ($actual -eq $expected) {
        Write-Host "OK       $relative"
    } else {
        Write-Host "FAILED   $relative"
        Write-Host "  expected: $expected"
        Write-Host "  actual:   $actual"
        $failed++
    }
    $checked++
}

Write-Host "Checked: $checked"
Write-Host "Failed:  $failed"

if ($failed -ne 0) {
    exit 1
}

