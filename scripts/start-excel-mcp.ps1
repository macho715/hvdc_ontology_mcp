param(
    [switch]$InstallDeps,
    [switch]$SmokeTest,
    [int]$Port = 8002,
    [string]$ListenHost = "127.0.0.1",
    [string]$RootPath = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ExcelRoot = Join-Path $RepoRoot "excel-mcp"
$ExcelPython = Join-Path $ExcelRoot ".venv\Scripts\python.exe"
$DefaultWorkbookRoot = Join-Path $ExcelRoot "workbooks"

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
    throw "Python 3.12+ was not found."
}

function Ensure-ExcelVenv {
    if (Test-Path $ExcelPython) {
        return
    }

    Write-Section "Creating excel-mcp virtual environment"
    $basePython = Resolve-BasePython
    $command = $basePython[0]
    $args = @()
    if ($basePython.Length -gt 1) {
        $args += $basePython[1..($basePython.Length - 1)]
    }
    $args += @("-m", "venv", (Join-Path $ExcelRoot ".venv"))
    & $command @args
    if (-not (Test-Path $ExcelPython)) {
        throw "Failed to create excel-mcp .venv"
    }
}

function Invoke-ExcelPython {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args,
        [hashtable]$ExtraEnv = @{}
    )

    $oldValues = @{}
    foreach ($key in $ExtraEnv.Keys) {
        $oldValues[$key] = [Environment]::GetEnvironmentVariable($key, "Process")
        [Environment]::SetEnvironmentVariable($key, [string]$ExtraEnv[$key], "Process")
    }

    try {
        & $ExcelPython @Args
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed: $($Args -join ' ')"
        }
    }
    finally {
        foreach ($key in $ExtraEnv.Keys) {
            [Environment]::SetEnvironmentVariable($key, $oldValues[$key], "Process")
        }
    }
}

function Install-ExcelDeps {
    Ensure-ExcelVenv
    Write-Section "Installing excel-mcp dependencies"
    Invoke-ExcelPython -Args @("-m", "pip", "install", "--upgrade", "pip")
    Invoke-ExcelPython -Args @("-m", "pip", "install", "-r", "requirements.txt") -ExtraEnv @{}
    Write-Ok "excel-mcp dependencies installed"
}

function Invoke-SmokeTest {
    Ensure-ExcelVenv

    $workbookRoot = if ($RootPath) { $RootPath } else { $DefaultWorkbookRoot }
    $oldRoot = $env:EXCEL_MCP_ROOT
    $oldHost = $env:EXCEL_MCP_HOST
    $oldPort = $env:EXCEL_MCP_PORT
    $env:EXCEL_MCP_ROOT = $workbookRoot
    $env:EXCEL_MCP_HOST = $ListenHost
    $env:EXCEL_MCP_PORT = "$Port"

    $proc = Start-Process -FilePath $ExcelPython `
        -ArgumentList "server.py" `
        -WorkingDirectory $ExcelRoot `
        -PassThru `
        -WindowStyle Hidden

    try {
        Write-Section "Waiting for excel-mcp health"
        $deadline = (Get-Date).AddSeconds(20)
        $healthUrl = "http://$ListenHost`:$Port/health"
        do {
            try {
                $health = Invoke-RestMethod -Uri $healthUrl -Method Get -TimeoutSec 2
                if ($health.status -eq "healthy") {
                    Write-Ok "excel-mcp health is ready"
                    break
                }
            }
            catch {
                Start-Sleep -Milliseconds 250
            }
        } while ((Get-Date) -lt $deadline)

        if ((Get-Date) -ge $deadline) {
            throw "Timed out waiting for excel-mcp /health"
        }

        Write-Section "Running MCP initialize smoke"
        $payload = @{
            jsonrpc = "2.0"
            id = "smoke"
            method = "initialize"
            params = @{
                protocolVersion = "2025-06-18"
                capabilities = @{}
                clientInfo = @{
                    name = "excel-smoke"
                    version = "1.0"
                }
            }
        } | ConvertTo-Json -Depth 6

        $response = Invoke-RestMethod -Uri "http://$ListenHost`:$Port/mcp" `
            -Method Post `
            -ContentType "application/json" `
            -Headers @{ Accept = "application/json" } `
            -Body $payload `
            -TimeoutSec 10

        if (-not $response.result.serverInfo.name) {
            throw "excel-mcp initialize returned no serverInfo.name"
        }

        Write-Ok "excel-mcp MCP initialize smoke passed"
    }
    finally {
        if ($proc -and -not $proc.HasExited) {
            Stop-Process -Id $proc.Id -Force
        }
        $env:EXCEL_MCP_ROOT = $oldRoot
        $env:EXCEL_MCP_HOST = $oldHost
        $env:EXCEL_MCP_PORT = $oldPort
    }
}

Set-Location $ExcelRoot

if ($InstallDeps) {
    Install-ExcelDeps
    if (-not $SmokeTest) {
        exit 0
    }
}

if ($SmokeTest) {
    Invoke-SmokeTest
    exit 0
}

Ensure-ExcelVenv
$env:EXCEL_MCP_ROOT = if ($RootPath) { $RootPath } else { $DefaultWorkbookRoot }
$env:EXCEL_MCP_HOST = $ListenHost
$env:EXCEL_MCP_PORT = "$Port"

Write-Section "Starting excel-mcp"
Write-Host "Host: $ListenHost"
Write-Host "Port: $Port"
Write-Host "Root: $env:EXCEL_MCP_ROOT"
& $ExcelPython "server.py"
exit $LASTEXITCODE
