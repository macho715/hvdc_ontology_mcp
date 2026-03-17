param(
    [string]$OutFile = ""
)

$ErrorActionPreference = "SilentlyContinue"

if (-not $OutFile) {
    $OutFile = Join-Path $PSScriptRoot "env_report.json"
}

function Get-Version($cmd) {
    try {
        return (& $cmd --version 2>&1 | Select-Object -First 1).ToString().Trim()
    }
    catch {
        return $null
    }
}

function Get-CmdPath($cmd) {
    try {
        return (Get-Command $cmd -ErrorAction Stop).Source
    }
    catch {
        return $null
    }
}

$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$memGB = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)

$ports = @{}
foreach ($port in 8000, 8001, 8002) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen | Select-Object -First 1
    if ($conn) {
        $proc = Get-Process -Id $conn.OwningProcess | Select-Object -First 1
        $ports["$port"] = @{
            listening = $true
            address = $conn.LocalAddress
            process = $proc.ProcessName
            pid = $proc.Id
        }
    }
    else {
        $ports["$port"] = @{
            listening = $false
        }
    }
}

$ips = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object InterfaceAlias, IPAddress

$report = [ordered]@{
    generated_at = (Get-Date).ToString("s")
    project = "excel-mcp"
    computer_name = $env:COMPUTERNAME
    os = @{
        caption = $os.Caption
        version = $os.Version
        build = $os.BuildNumber
    }
    cpu = @{
        name = $cpu.Name.Trim()
        logical_cores = $cpu.NumberOfLogicalProcessors
    }
    memory_gb = $memGB
    python = @{
        path = (Get-CmdPath "python")
        version = (Get-Version "python")
        py_launcher = (Get-CmdPath "py")
    }
    pip = @{
        path = (Get-CmdPath "pip")
        version = (Get-Version "pip")
    }
    git = @{
        path = (Get-CmdPath "git")
        version = (Get-Version "git")
    }
    node = @{
        path = (Get-CmdPath "node")
        version = (Get-Version "node")
    }
    npm = @{
        path = (Get-CmdPath "npm")
        version = (Get-Version "npm")
    }
    ngrok = @{
        path = (Get-CmdPath "ngrok")
        version = (Get-Version "ngrok")
    }
    cloudflared = @{
        path = (Get-CmdPath "cloudflared")
        version = (Get-Version "cloudflared")
    }
    local_ipv4 = $ips
    listening_ports = $ports
}

$report | ConvertTo-Json -Depth 6 | Set-Content -Path $OutFile -Encoding UTF8
Write-Host "Saved to $OutFile"
Get-Content $OutFile
