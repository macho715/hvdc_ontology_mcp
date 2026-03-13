param(
    [switch]$Quick,
    [switch]$SkipValidate,
    [switch]$SyncClaude,
    [switch]$SyncCodexGlobal
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"

function Write-Section($Message) {
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Write-Ok($Message) {
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn($Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Resolve-BasePython {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }
    throw "Python was not found. Install Python 3.10+ first."
}

function Ensure-Venv {
    if (Test-Path $VenvPython) {
        Write-Ok ".venv already exists"
        return
    }

    Write-Section "Creating virtual environment"
    $basePython = Resolve-BasePython
    $command = $basePython[0]
    $commandArgs = @()
    if ($basePython.Length -gt 1) {
        $commandArgs += $basePython[1..($basePython.Length - 1)]
    }
    $commandArgs += @("-m", "venv", (Join-Path $Root ".venv"))
    & $command @commandArgs
    if (-not (Test-Path $VenvPython)) {
        throw "Failed to create .venv"
    }
    Write-Ok ".venv created"
}

function Invoke-ProjectPython {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    & $VenvPython @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $($Args -join ' ')"
    }
}

function Sync-CodexGlobal {
    if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
        Write-Warn "codex CLI not found - skip global Codex sync"
        return
    }

    Write-Section "Syncing global Codex MCP config"
    try {
        codex mcp remove hvdc-knowledge *> $null
    } catch {
    }

    codex mcp add hvdc-knowledge -- cmd.exe /d /c "$Root\scripts\cursor_mcp.cmd"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to register global Codex MCP"
    }
    Write-Ok "Global Codex MCP synced"
}

Set-Location $Root

Write-Host ""
Write-Host "+=====================================================+" -ForegroundColor Cyan
Write-Host "|  HVDC Knowledge MCP - Windows Client Setup          |" -ForegroundColor Cyan
Write-Host "+=====================================================+" -ForegroundColor Cyan
Write-Host ""
Write-Host "Root: $Root"

Ensure-Venv

Write-Section "Installing dependencies"
Invoke-ProjectPython -Args @("-m", "pip", "install", "--upgrade", "pip")
Invoke-ProjectPython -Args @("-m", "pip", "install", "-r", "requirements.txt")
Write-Ok "Dependencies installed"

if (-not $SkipValidate) {
    Write-Section "Running validation"
    if ($Quick) {
        Invoke-ProjectPython -Args @("scripts\validate.py", "--quick")
        Write-Ok "Quick validation passed"
    } else {
        Invoke-ProjectPython -Args @("scripts\validate.py")
        Write-Ok "Full validation passed"
    }
}

if ($SyncClaude) {
    Write-Section "Syncing Claude config"
    Invoke-ProjectPython -Args @("scripts\deploy.py", "--target", "both")
    Write-Ok "Claude config synced"
}

if ($SyncCodexGlobal) {
    Sync-CodexGlobal
}

Write-Section "Next steps"
Write-Host "1. Cursor: open this repo, trust the project, reload window."
Write-Host "2. Codex: trust the project. Project-scoped .codex/config.toml will load hvdc-knowledge."
Write-Host "3. ChatGPT: use https://hvdc-knowledge-mcp-service-production.up.railway.app/mcp"
Write-Host "4. Dashboard: https://hvdc-knowledge-mcp-service-production.up.railway.app/dashboard"
Write-Host ""
Write-Ok "Windows client setup complete"
