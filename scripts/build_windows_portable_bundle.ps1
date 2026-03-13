param(
    [string]$OutputRoot = ".dist"
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$DistRoot = Join-Path $Root $OutputRoot
$PackageName = "hvdc-knowledge-windows-portable"
$PackageDir = Join-Path $DistRoot $PackageName
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ZipPath = Join-Path $DistRoot "$PackageName-$Timestamp.zip"

$FileList = @(
    "README.md",
    "CHATGPT_CODEX_CURSOR_HANDOFF.md",
    "WINDOWS_MULTI_PC_PACKAGE.md",
    "AGENTS.md",
    "CLAUDE.md",
    "install.py",
    "requirements.txt",
    "server.py",
    "Dockerfile",
    "railway.json",
    "SETUP_WINDOWS_CLIENT.cmd",
    "SETUP_WINDOWS_FULL.cmd"
)

$DirList = @(
    ".codex",
    ".claude",
    ".cursor",
    "docs",
    "hvdc_ops",
    "scripts",
    "tests",
    "widgets"
)

$SkipDirNames = @("__pycache__", ".ruff_cache", ".runtime", ".venv", ".dist")
$SkipFilePatterns = @("*.pyc", "*.pyo", "*.log")

function Copy-FilteredTree {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    New-Item -ItemType Directory -Force -Path $Destination | Out-Null

    Get-ChildItem -LiteralPath $Source -Force | ForEach-Object {
        if ($_.PSIsContainer) {
            if ($SkipDirNames -contains $_.Name) {
                return
            }
            Copy-FilteredTree -Source $_.FullName -Destination (Join-Path $Destination $_.Name)
            return
        }

        foreach ($pattern in $SkipFilePatterns) {
            if ($_.Name -like $pattern) {
                return
            }
        }

        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $Destination $_.Name) -Force
    }
}

if (Test-Path $PackageDir) {
    Remove-Item -LiteralPath $PackageDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $PackageDir | Out-Null
New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null

foreach ($file in $FileList) {
    $source = Join-Path $Root $file
    if (Test-Path $source) {
        $dest = Join-Path $PackageDir $file
        $destParent = Split-Path -Parent $dest
        if ($destParent) {
            New-Item -ItemType Directory -Force -Path $destParent | Out-Null
        }
        Copy-Item -LiteralPath $source -Destination $dest -Force
    }
}

foreach ($dir in $DirList) {
    $source = Join-Path $Root $dir
    if (Test-Path $source) {
        Copy-FilteredTree -Source $source -Destination (Join-Path $PackageDir $dir)
    }
}

$infoPath = Join-Path $PackageDir "PACKAGE_INFO.txt"
@(
    "HVDC Knowledge MCP - Windows Portable Package"
    "Built: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    "Source: $Root"
    "Primary setup entrypoint: SETUP_WINDOWS_CLIENT.cmd"
    "Primary guide: WINDOWS_MULTI_PC_PACKAGE.md"
) | Set-Content -Path $infoPath -Encoding UTF8

if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path (Join-Path $PackageDir "*") -DestinationPath $ZipPath -Force

Write-Host "Package directory: $PackageDir"
Write-Host "Zip archive: $ZipPath"
