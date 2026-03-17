#!/usr/bin/env python3
"""
HVDC Knowledge MCP — Managed ChatGPT Remote Runner

Usage:
    python scripts/remote_mcp.py start
    python scripts/remote_mcp.py supervise
    python scripts/remote_mcp.py status
    python scripts/remote_mcp.py stop
    python scripts/remote_mcp.py install-task
    python scripts/remote_mcp.py remove-task
"""

import argparse
from datetime import datetime, UTC
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen, urlretrieve


ROOT = Path(__file__).parent.parent.resolve()
RUNTIME_DIR = ROOT / ".runtime"
TOOLS_DIR = RUNTIME_DIR / "tools"
STATE_PATH = RUNTIME_DIR / "chatgpt_remote_state.json"
SERVER_STDOUT = RUNTIME_DIR / "remote-mcp.out.log"
SERVER_STDERR = RUNTIME_DIR / "remote-mcp.err.log"
TUNNEL_STDOUT = RUNTIME_DIR / "cloudflared.stdout.log"
TUNNEL_STDERR = RUNTIME_DIR / "cloudflared.stderr.log"
TUNNEL_LOG = RUNTIME_DIR / "cloudflared.log"
TAILSCALE_LOG = RUNTIME_DIR / "tailscale.log"
SERVER_PATH = ROOT / "server.py"
DEFAULT_PORT = 8001
DEFAULT_HEALTH_INTERVAL = 15
TASK_NAME = "HVDC Knowledge Remote MCP"
STARTUP_LAUNCHER_NAME = "HVDC Knowledge Remote MCP.cmd"
TRYCLOUDFLARE_RE = re.compile(r"https://[a-z0-9.-]+\.trycloudflare\.com")
MAX_RECENT_RESTARTS = 10
STREAMABLE_HTTP_RE = re.compile(r"--transport\s+streamable-http")
PORT_ARG_RE = re.compile(r"--port\s+(\d+)")
PUBLIC_BASE_ARG_RE = re.compile(r"--public-base-url\s+(\S+)")
HOST_ARG_RE = re.compile(r"--host\s+(\S+)")


def info(message: str) -> None:
    print(f"[INFO] {message}")


def ok(message: str) -> None:
    print(f"[OK]   {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def fail(message: str) -> None:
    print(f"[ERR]  {message}")


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def normalize_public_base_url(url: str | None) -> str:
    if not url:
        return ""
    return str(url).rstrip("/")


def ensure_runtime_dirs() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)


def read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        public_base_url = normalize_public_base_url(state.get("public_base_url"))
        if public_base_url:
            state.setdefault("status_url", f"{public_base_url}/")
            state.setdefault("health_url", f"{public_base_url}/health")
            state.setdefault("docs_url", f"{public_base_url}/docs")
            state.setdefault("dashboard_url", f"{public_base_url}/dashboard")
            state.setdefault("mcp_url", f"{public_base_url}/mcp")
        return state
    except json.JSONDecodeError:
        warn(f"State file is invalid JSON: {STATE_PATH}")
        return {}


def write_state(payload: dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def clear_state() -> None:
    if STATE_PATH.exists():
        STATE_PATH.unlink()


def infer_mode_from_public_base_url(public_base_url: str) -> str:
    normalized = normalize_public_base_url(public_base_url)
    if not normalized:
        return "local"
    if normalized.endswith(".trycloudflare.com"):
        return "quick"
    if normalized.endswith(".ts.net"):
        return "tailscale-funnel"
    return "external"


def _windows_process_rows() -> list[dict[str, Any]]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            "Select-Object ProcessId,ParentProcessId,ExecutablePath,CommandLine | "
            "ConvertTo-Json -Compress"
        ),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    payload = json.loads(result.stdout)
    if isinstance(payload, dict):
        payload = [payload]
    return [item for item in payload if isinstance(item, dict)]


def _posix_process_rows() -> list[dict[str, Any]]:
    result = subprocess.run(
        ["ps", "-ax", "-o", "pid=,ppid=,command="],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return []
    rows: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split(maxsplit=2)
        if len(parts) < 3:
            continue
        rows.append(
            {
                "ProcessId": int(parts[0]),
                "ParentProcessId": int(parts[1]),
                "ExecutablePath": None,
                "CommandLine": parts[2],
            }
        )
    return rows


def _process_rows() -> list[dict[str, Any]]:
    try:
        return _windows_process_rows() if os.name == "nt" else _posix_process_rows()
    except Exception:
        return []


def _candidate_server_processes() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in _process_rows():
        command_line = str(row.get("CommandLine") or "")
        if str(SERVER_PATH) not in command_line:
            continue
        if not STREAMABLE_HTTP_RE.search(command_line):
            continue
        port_match = PORT_ARG_RE.search(command_line)
        public_match = PUBLIC_BASE_ARG_RE.search(command_line)
        host_match = HOST_ARG_RE.search(command_line)
        candidates.append(
            {
                "server_pid": int(row.get("ProcessId")),
                "parent_pid": _coerce_positive_int(row.get("ParentProcessId")),
                "command_line": command_line,
                "port": int(port_match.group(1)) if port_match else DEFAULT_PORT,
                "public_base_url": normalize_public_base_url(public_match.group(1) if public_match else ""),
                "host": host_match.group(1) if host_match else "127.0.0.1",
            }
        )
    return candidates


def _probe_local_only(port: int) -> tuple[bool, dict[str, Any]]:
    root_url = f"http://127.0.0.1:{port}/"
    health_url = f"http://127.0.0.1:{port}/health"
    docs_url = f"http://127.0.0.1:{port}/docs"
    status_probe = probe_url(root_url, expected_statuses={200}, expect_json=True)
    health_probe = probe_url(health_url, expected_statuses={200}, expect_json=True)
    docs_probe = probe_url(docs_url, expected_statuses={200}, expect_json=True)
    probes = {
        "local_status": summarize_probe(status_probe),
        "local_health": summarize_probe(health_probe),
        "local_docs": summarize_probe(docs_probe),
    }
    ok_local = all(probe.get("ok") for probe in (status_probe, health_probe, docs_probe))
    latencies = [
        probe.get("latency_ms")
        for probe in probes.values()
        if isinstance(probe.get("latency_ms"), int)
    ]
    return ok_local, {
        "health_probe_at": utc_now(),
        "health_probe_ok": ok_local,
        "health_probe_latency_ms": max(latencies) if latencies else None,
        "probes": probes,
        "server_status": status_probe.get("json", {}),
        "error": None if ok_local else "local probes failed",
    }


def discover_orphan_state(
    *,
    preferred_port: int | None = None,
    require_healthy: bool,
) -> tuple[dict[str, Any], dict[str, Any]] | tuple[None, None]:
    candidates = _candidate_server_processes()
    if preferred_port is not None:
        candidates.sort(key=lambda item: (item["port"] != preferred_port, -item["server_pid"]))
    else:
        candidates.sort(key=lambda item: -item["server_pid"])

    for candidate in candidates:
        public_base_url = normalize_public_base_url(candidate.get("public_base_url"))
        if public_base_url:
            healthy, details = probe_server(int(candidate["port"]), public_base_url)
        else:
            healthy, details = _probe_local_only(int(candidate["port"]))
        if require_healthy and not healthy:
            continue
        state = {
            "started_at": None,
            "mode": infer_mode_from_public_base_url(public_base_url),
            "supervisor_pid": None,
            "server_pid": candidate["server_pid"],
            "tunnel_pid": None,
            "port": candidate["port"],
            "public_base_url": public_base_url,
            "mcp_url": f"{public_base_url}/mcp" if public_base_url else None,
            "health_url": f"{public_base_url}/health" if public_base_url else None,
            "status_url": f"{public_base_url}/" if public_base_url else None,
            "docs_url": f"{public_base_url}/docs" if public_base_url else None,
            "dashboard_url": f"{public_base_url}/dashboard" if public_base_url else None,
            "cloudflared_path": "",
            "tailscale_path": "",
            "restart_count": 0,
            "recent_restarts": [],
            "last_health_probe_at": details.get("health_probe_at"),
            "last_health_probe_ok": details.get("health_probe_ok"),
            "last_health_probe_latency_ms": details.get("health_probe_latency_ms"),
            "logs": {
                "server_stdout": str(SERVER_STDOUT),
                "server_stderr": str(SERVER_STDERR),
                "tunnel_stdout": str(TUNNEL_STDOUT),
                "tunnel_stderr": str(TUNNEL_STDERR),
                "tunnel_log": str(TUNNEL_LOG),
                "tailscale_log": str(TAILSCALE_LOG),
            },
            "server_status": details.get("server_status", {}),
            "live_status": details,
        }
        return state, details
    return None, None


def reconcile_state(*, preferred_port: int | None = None, require_healthy: bool = True) -> dict[str, Any]:
    state, details = discover_orphan_state(preferred_port=preferred_port, require_healthy=require_healthy)
    if not state:
        return {}
    write_state(state)
    if details:
        ok(f"Recovered managed state from running server PID {state['server_pid']}")
    return state


def _coerce_positive_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


def is_process_running(pid: int | None) -> bool:
    if not pid:
        return False

    if os.name == "nt":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = result.stdout.strip()
        return bool(output) and not output.startswith("INFO:")

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def terminate_process(pid: int | None) -> None:
    if not pid or not is_process_running(pid):
        return

    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return

    os.killpg(pid, 15)


def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def choose_port(preferred_port: int) -> int:
    if is_port_available(preferred_port):
        return preferred_port

    for candidate in range(preferred_port + 1, preferred_port + 20):
        if is_port_available(candidate):
            warn(f"Port {preferred_port} is in use. Falling back to {candidate}.")
            return candidate

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
    warn(f"Preferred ports are in use. Falling back to {port}.")
    return port


def cloudflared_download_url() -> str | None:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Windows" and machine in {"amd64", "x86_64"}:
        return "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    return None


def ensure_cloudflared(binary_override: str | None = None) -> Path:
    if binary_override:
        path = Path(binary_override).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"cloudflared override not found: {path}")
        return path

    on_path = shutil.which("cloudflared")
    if on_path:
        return Path(on_path).resolve()

    download_url = cloudflared_download_url()
    if not download_url:
        raise RuntimeError(
            "cloudflared is not installed and automatic download is only supported "
            "for Windows amd64 in this repository. Install cloudflared manually."
        )

    target = TOOLS_DIR / "cloudflared.exe"
    if not target.exists():
        info("Downloading cloudflared...")
        urlretrieve(download_url, target)
        ok(f"cloudflared downloaded to {target}")
    return target


def ensure_tailscale() -> Path:
    on_path = shutil.which("tailscale") or shutil.which("tailscale.exe")
    if on_path:
        return Path(on_path).resolve()
    raise RuntimeError("tailscale is not installed or not available on PATH.")


def _coerce_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def append_command_log(
    path: Path,
    command: list[str],
    *,
    returncode: int | None = None,
    stdout: str = "",
    stderr: str = "",
    timed_out: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"[{utc_now()}] {subprocess.list2cmdline(command)}\n")
        if returncode is not None:
            handle.write(f"returncode: {returncode}\n")
        if timed_out:
            handle.write("timed_out: true\n")
        if stdout.strip():
            handle.write("stdout:\n")
            handle.write(stdout.rstrip() + "\n")
        if stderr.strip():
            handle.write("stderr:\n")
            handle.write(stderr.rstrip() + "\n")
        handle.write("\n")


def run_tailscale(
    args: list[str],
    *,
    timeout_sec: int = 30,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    tailscale_path = ensure_tailscale()
    command = [str(tailscale_path), *args]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _coerce_text(exc.stdout)
        stderr = _coerce_text(exc.stderr)
        append_command_log(
            TAILSCALE_LOG,
            command,
            stdout=stdout,
            stderr=stderr,
            timed_out=True,
        )
        message = stdout.strip() or stderr.strip() or f"tailscale command timed out: {subprocess.list2cmdline(command)}"
        raise RuntimeError(message)

    append_command_log(
        TAILSCALE_LOG,
        command,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )

    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or f"tailscale command failed: {subprocess.list2cmdline(command)}"
        raise RuntimeError(message)
    return result


def get_tailscale_status() -> dict[str, Any]:
    result = run_tailscale(["status", "--json"], timeout_sec=20)
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"tailscale status returned invalid JSON: {exc}") from exc


def get_tailscale_funnel_config() -> dict[str, Any]:
    result = run_tailscale(["funnel", "status", "--json"], timeout_sec=20, check=False)
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"tailscale funnel status returned invalid JSON: {exc}") from exc


def find_tailscale_funnel_url(config: dict[str, Any], port: int) -> str | None:
    web = config.get("Web", {})
    allow_funnel = config.get("AllowFunnel", {})
    if not isinstance(web, dict):
        return None

    expected_proxies = {
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
    }

    for host_port, entry in web.items():
        if isinstance(allow_funnel, dict) and allow_funnel and not allow_funnel.get(host_port):
            continue
        if not isinstance(entry, dict):
            continue
        handlers = entry.get("Handlers", {})
        if not isinstance(handlers, dict):
            continue
        root_handler = handlers.get("/")
        if not isinstance(root_handler, dict):
            continue
        proxy = str(root_handler.get("Proxy", ""))
        if proxy not in expected_proxies:
            continue
        host = str(host_port).split(":", 1)[0]
        if host:
            return f"https://{host}"
    return None


def wait_for_tailscale_funnel_url(port: int, timeout_sec: int = 45) -> str:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        config = get_tailscale_funnel_config()
        url = find_tailscale_funnel_url(config, port)
        if url:
            return url
        time.sleep(1)
    raise RuntimeError("Failed to obtain Tailscale Funnel URL from tailscale funnel status.")


def start_tailscale_funnel(port: int) -> tuple[str, Path]:
    status = get_tailscale_status()
    if str(status.get("BackendState")) != "Running":
        raise RuntimeError("Tailscale is installed but not running.")

    dns_name = str(status.get("Self", {}).get("DNSName") or "").rstrip(".")
    if not dns_name:
        raise RuntimeError("Tailscale MagicDNS hostname is unavailable for this node.")

    tailscale_path = ensure_tailscale()
    info(f"Starting Tailscale Funnel on {dns_name}...")
    run_tailscale(["funnel", "--bg", "--yes", str(port)], timeout_sec=45)
    public_base_url = wait_for_tailscale_funnel_url(port)
    return public_base_url, tailscale_path


def disable_tailscale_funnel(verbose: bool) -> None:
    config = get_tailscale_funnel_config()
    if not config:
        if verbose:
            warn("Tailscale Funnel is not currently configured")
        return

    result = run_tailscale(["funnel", "--https=443", "off"], timeout_sec=20, check=False)
    if result.returncode == 0:
        if verbose:
            ok("Disabled Tailscale Funnel")
        return

    if verbose:
        warn(result.stderr.strip() or result.stdout.strip() or "Failed to disable Tailscale Funnel")


def spawn_detached(command: list[str], cwd: Path, stdout_path: Path, stderr_path: Path) -> int:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stderr_path.parent.mkdir(parents=True, exist_ok=True)

    with open(stdout_path, "ab") as stdout_handle, open(stderr_path, "ab") as stderr_handle:
        kwargs: dict[str, Any] = {
            "cwd": str(cwd),
            "stdout": stdout_handle,
            "stderr": stderr_handle,
            "stdin": subprocess.DEVNULL,
        }
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs["start_new_session"] = True

        proc = subprocess.Popen(command, **kwargs)
        return int(proc.pid)


def wait_for_tunnel_url(log_path: Path, tunnel_pid: int, timeout_sec: int = 45) -> str:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if log_path.exists():
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            match = TRYCLOUDFLARE_RE.search(log_text)
            if match:
                return match.group(0)

        if not is_process_running(tunnel_pid):
            break

        time.sleep(1)

    details = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    raise RuntimeError(f"Failed to obtain trycloudflare URL.\n{details}")


def get_json(url: str, timeout_sec: int = 5) -> dict[str, Any]:
    with urlopen(url, timeout=timeout_sec) as response:
        return json.loads(response.read().decode("utf-8"))


def probe_url(
    url: str,
    *,
    expected_statuses: set[int] | None = None,
    timeout_sec: int = 5,
    expect_json: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
    request = Request(
        url,
        headers={
            "User-Agent": "hvdc-knowledge-remote-mcp/1.0",
            "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
        },
    )
    body = b""
    status_code: int | None = None

    try:
        with urlopen(request, timeout=timeout_sec) as response:
            status_code = int(getattr(response, "status", 200))
            body = response.read()
    except HTTPError as exc:
        status_code = int(exc.code)
        body = exc.read()
    except (URLError, TimeoutError, OSError) as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "url": url,
            "ok": False,
            "status_code": None,
            "latency_ms": latency_ms,
            "error": str(exc),
        }

    latency_ms = int((time.perf_counter() - started) * 1000)
    ok = (
        status_code in expected_statuses
        if expected_statuses is not None
        else status_code is not None and 200 <= status_code < 400
    )
    probe: dict[str, Any] = {
        "url": url,
        "ok": ok,
        "status_code": status_code,
        "latency_ms": latency_ms,
    }

    if expect_json and ok:
        try:
            probe["json"] = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            probe["ok"] = False
            probe["error"] = f"invalid JSON: {exc}"

    return probe


def summarize_probe(probe: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in probe.items() if key != "json"}


def probe_server(port: int, public_base_url: str) -> tuple[bool, dict[str, Any]]:
    root_url = f"http://127.0.0.1:{port}/"
    health_url = f"http://127.0.0.1:{port}/health"
    docs_url = f"http://127.0.0.1:{port}/docs"
    status_probe = probe_url(root_url, expected_statuses={200}, expect_json=True)
    local_health_probe = probe_url(health_url, expected_statuses={200}, expect_json=True)
    docs_probe = probe_url(docs_url, expected_statuses={200}, expect_json=True)

    probes: dict[str, Any] = {
        "local_status": summarize_probe(status_probe),
        "local_health": summarize_probe(local_health_probe),
        "local_docs": summarize_probe(docs_probe),
    }

    details: dict[str, Any] = {
        "health_probe_at": utc_now(),
        "health_probe_ok": False,
        "health_probe_latency_ms": None,
        "probes": probes,
    }

    if not status_probe.get("ok"):
        details["error"] = "local status probe failed"
        return False, details
    if not local_health_probe.get("ok"):
        details["error"] = "local health probe failed"
        return False, details
    if not docs_probe.get("ok"):
        details["error"] = "local docs probe failed"
        return False, details

    payload = status_probe.get("json", {})
    docs_payload = docs_probe.get("json", {})
    if normalize_public_base_url(payload.get("public_base_url")) != public_base_url:
        details["error"] = "public_base_url mismatch"
        details["server_status"] = payload
        return False, details

    files = docs_payload.get("files", [])
    if files and not str(files[0].get("url", "")).startswith(f"{public_base_url}/docs/"):
        details["error"] = "doc URL mismatch"
        details["server_status"] = payload
        return False, details

    public_health_probe = probe_url(
        f"{public_base_url}/health",
        expected_statuses={200},
        expect_json=True,
    )
    probes["public_health"] = summarize_probe(public_health_probe)

    if not public_health_probe.get("ok"):
        details["error"] = "public health probe failed"
        details["server_status"] = payload
        return False, details

    latencies = [
        probe.get("latency_ms")
        for probe in probes.values()
        if isinstance(probe.get("latency_ms"), int)
    ]
    details.update(
        {
            "health_probe_ok": True,
            "health_probe_latency_ms": max(latencies) if latencies else None,
            "server_status": payload,
            "docs_summary": {
                "total_files": docs_payload.get("total_files"),
                "sample_doc_url": files[0].get("url") if files else None,
            },
        }
    )
    return True, details


def wait_for_server(port: int, public_base_url: str, timeout_sec: int = 45) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        healthy, payload = probe_server(port, public_base_url)
        if healthy:
            return payload
        time.sleep(1)
    raise RuntimeError("HVDC MCP server did not become healthy within the timeout.")


def build_restart_event(
    previous_state: dict[str, Any],
    reason: str,
    new_public_base_url: str,
) -> dict[str, Any]:
    previous_public_base_url = normalize_public_base_url(previous_state.get("public_base_url"))
    normalized_new_public_base_url = normalize_public_base_url(new_public_base_url)
    return {
        "at": utc_now(),
        "reason": reason,
        "previous_started_at": previous_state.get("started_at"),
        "previous_mode": previous_state.get("mode"),
        "previous_supervisor_pid": _coerce_positive_int(previous_state.get("supervisor_pid")),
        "previous_server_pid": _coerce_positive_int(previous_state.get("server_pid")),
        "previous_tunnel_pid": _coerce_positive_int(previous_state.get("tunnel_pid")),
        "previous_public_base_url": previous_public_base_url or None,
        "new_public_base_url": normalized_new_public_base_url or None,
        "public_url_changed": previous_public_base_url != normalized_new_public_base_url,
    }


def update_state_health(state: dict[str, Any], healthy: bool, details: dict[str, Any]) -> dict[str, Any]:
    updated = dict(state)
    updated["last_health_probe_at"] = details.get("health_probe_at", utc_now())
    updated["last_health_probe_ok"] = healthy
    updated["last_health_probe_latency_ms"] = details.get("health_probe_latency_ms")
    updated["live_status"] = details
    server_status = details.get("server_status")
    if isinstance(server_status, dict) and server_status:
        updated["server_status"] = server_status
    write_state(updated)
    return updated


def current_task_exists() -> bool:
    if os.name != "nt":
        return False
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.returncode == 0


def startup_launcher_path() -> Path:
    if os.name != "nt":
        raise RuntimeError("Startup launcher is only supported on Windows.")
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / STARTUP_LAUNCHER_NAME


def remove_old_logs() -> None:
    for path in [SERVER_STDOUT, SERVER_STDERR, TUNNEL_STDOUT, TUNNEL_STDERR, TUNNEL_LOG, TAILSCALE_LOG]:
        if path.exists():
            path.unlink()


def validate_mode(
    skip_tunnel: bool,
    public_base_url: str,
    tailscale_funnel: bool = False,
    cloudflared_override: str | None = None,
) -> None:
    if skip_tunnel and tailscale_funnel:
        raise ValueError("--skip-tunnel and --tailscale-funnel cannot be used together")
    if skip_tunnel and not public_base_url:
        raise ValueError("--skip-tunnel requires --public-base-url")
    if public_base_url and not skip_tunnel:
        raise ValueError("--public-base-url is only valid together with --skip-tunnel")
    if tailscale_funnel and public_base_url:
        raise ValueError("--public-base-url cannot be used with --tailscale-funnel")
    if tailscale_funnel and cloudflared_override:
        raise ValueError("--cloudflared-path cannot be used with --tailscale-funnel")


def stop_children(state: dict[str, Any], verbose: bool) -> None:
    server_pid = state.get("server_pid")
    tunnel_pid = state.get("tunnel_pid")
    mode = state.get("mode")

    if is_process_running(server_pid):
        terminate_process(server_pid)
        if verbose:
            ok(f"Stopped server PID {server_pid}")
    elif verbose and server_pid:
        warn(f"Server PID {server_pid} is already stopped")

    if is_process_running(tunnel_pid):
        terminate_process(tunnel_pid)
        if verbose:
            ok(f"Stopped tunnel PID {tunnel_pid}")
    elif verbose and tunnel_pid:
        warn(f"Tunnel PID {tunnel_pid} is already stopped")

    if mode == "tailscale-funnel":
        disable_tailscale_funnel(verbose=verbose)


def stop_managed_stack(verbose: bool = True, kill_supervisor: bool = True) -> None:
    state = read_state()
    if not state:
        state = reconcile_state(require_healthy=False)
    if not state:
        if verbose:
            warn("No managed remote MCP state found.")
        return

    supervisor_pid = state.get("supervisor_pid")
    if (
        kill_supervisor
        and supervisor_pid
        and supervisor_pid != os.getpid()
        and is_process_running(supervisor_pid)
    ):
        terminate_process(supervisor_pid)
        if state.get("mode") == "tailscale-funnel":
            disable_tailscale_funnel(verbose=verbose)
        if verbose:
            ok(f"Stopped supervisor PID {supervisor_pid}")
        clear_state()
        return

    stop_children(state, verbose=verbose)
    clear_state()


def build_server_command(port: int, public_base_url: str) -> list[str]:
    return [
        sys.executable,
        "-X",
        "utf8",
        str(SERVER_PATH),
        "--transport",
        "streamable-http",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--public-base-url",
        public_base_url,
    ]


def start_stack(
    preferred_port: int,
    cloudflared_override: str | None,
    public_base_url: str,
    skip_tunnel: bool,
    tailscale_funnel: bool,
    supervisor_pid: int | None,
    restart_reason: str,
) -> dict[str, Any]:
    ensure_runtime_dirs()
    validate_mode(skip_tunnel, public_base_url, tailscale_funnel, cloudflared_override)

    existing = read_state()
    if not existing:
        existing = reconcile_state(preferred_port=preferred_port, require_healthy=True)
        if existing:
            return existing
        orphan_state, _ = discover_orphan_state(preferred_port=preferred_port, require_healthy=False)
        if orphan_state:
            warn(f"Stopping orphaned streamable-http server PID {orphan_state['server_pid']} before restart.")
            stop_children(orphan_state, verbose=False)
    previous_state = dict(existing) if existing else {}
    restart_count = _coerce_positive_int(previous_state.get("restart_count")) or 0
    recent_restarts = (
        list(previous_state.get("recent_restarts", []))
        if isinstance(previous_state.get("recent_restarts"), list)
        else []
    )
    if existing:
        stop_children(existing, verbose=False)
        clear_state()

    port = choose_port(preferred_port)
    remove_old_logs()

    normalized_public_base_url = normalize_public_base_url(public_base_url)
    tunnel_pid: int | None = None
    cloudflared_path: Path | None = None
    tailscale_path: Path | None = None
    mode = "external" if skip_tunnel else "tailscale-funnel" if tailscale_funnel else "quick"

    if skip_tunnel:
        ok(f"Using external HTTPS endpoint: {normalized_public_base_url}")
    elif tailscale_funnel:
        normalized_public_base_url, tailscale_path = start_tailscale_funnel(port)
        ok(f"Public base URL: {normalized_public_base_url}")
    else:
        warn("Quick tunnel mode is for development only. The public URL can change on restart.")
        cloudflared_path = ensure_cloudflared(cloudflared_override)
        info("Starting cloudflared quick tunnel...")
        tunnel_pid = spawn_detached(
            [
                str(cloudflared_path),
                "tunnel",
                "--url",
                f"http://127.0.0.1:{port}",
                "--no-autoupdate",
                "--logfile",
                str(TUNNEL_LOG),
            ],
            cwd=ROOT,
            stdout_path=TUNNEL_STDOUT,
            stderr_path=TUNNEL_STDERR,
        )
        normalized_public_base_url = wait_for_tunnel_url(TUNNEL_LOG, tunnel_pid)
        ok(f"Public base URL: {normalized_public_base_url}")

    info("Starting HVDC MCP server...")
    server_pid = spawn_detached(
        build_server_command(port, normalized_public_base_url),
        cwd=ROOT,
        stdout_path=SERVER_STDOUT,
        stderr_path=SERVER_STDERR,
    )

    live_status = wait_for_server(port, normalized_public_base_url)
    payload = live_status.get("server_status", {})
    ok("HVDC MCP server is healthy")

    if previous_state:
        restart_count += 1
        recent_restarts.append(
            build_restart_event(previous_state, restart_reason, normalized_public_base_url)
        )
        recent_restarts = recent_restarts[-MAX_RECENT_RESTARTS:]

    state = {
        "started_at": utc_now(),
        "mode": mode,
        "supervisor_pid": supervisor_pid,
        "server_pid": server_pid,
        "tunnel_pid": tunnel_pid,
        "port": port,
        "public_base_url": normalized_public_base_url,
        "mcp_url": f"{normalized_public_base_url}/mcp",
        "health_url": f"{normalized_public_base_url}/health",
        "status_url": f"{normalized_public_base_url}/",
        "docs_url": f"{normalized_public_base_url}/docs",
        "dashboard_url": f"{normalized_public_base_url}/dashboard",
        "cloudflared_path": str(cloudflared_path) if cloudflared_path else "",
        "tailscale_path": str(tailscale_path) if tailscale_path else "",
        "restart_count": restart_count,
        "recent_restarts": recent_restarts,
        "last_health_probe_at": live_status.get("health_probe_at"),
        "last_health_probe_ok": live_status.get("health_probe_ok"),
        "last_health_probe_latency_ms": live_status.get("health_probe_latency_ms"),
        "logs": {
            "server_stdout": str(SERVER_STDOUT),
            "server_stderr": str(SERVER_STDERR),
            "tunnel_stdout": str(TUNNEL_STDOUT),
            "tunnel_stderr": str(TUNNEL_STDERR),
            "tunnel_log": str(TUNNEL_LOG),
            "tailscale_log": str(TAILSCALE_LOG),
        },
        "server_status": payload,
        "live_status": live_status,
    }
    write_state(state)
    return state


def print_start_summary(state: dict[str, Any]) -> None:
    print()
    ok(f"Mode: {state['mode']}")
    ok(f"Connector URL: {state['mcp_url']}")
    ok(f"Dashboard URL: {state['dashboard_url']}")
    ok(f"Docs URL: {state['docs_url']}")
    ok(f"Health probe latency: {state.get('last_health_probe_latency_ms')} ms")
    ok(f"Server PID: {state['server_pid']}")
    if state.get("tunnel_pid"):
        ok(f"Tunnel PID: {state['tunnel_pid']}")
    if state.get("supervisor_pid"):
        ok(f"Supervisor PID: {state['supervisor_pid']}")
    if state.get("mode") == "quick":
        print("note          : quick tunnel is dev-only and URL may change on restart")
    if state.get("mode") == "tailscale-funnel":
        print("note          : Tailscale Funnel uses your stable ts.net hostname")
    print()
    print("ChatGPT app setup:")
    print("  1. Settings -> Apps -> Advanced settings -> Developer mode ON")
    print(f"  2. Create app -> MCP URL: {state['mcp_url']}")
    print("  3. Refresh the app details page after tool/schema changes")


def build_supervisor_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "supervise",
        "--port",
        str(args.port),
        "--health-interval",
        str(args.health_interval),
    ]
    if args.cloudflared_path:
        command.extend(["--cloudflared-path", args.cloudflared_path])
    if args.tailscale_funnel:
        command.append("--tailscale-funnel")
    if args.skip_tunnel:
        command.extend(["--skip-tunnel", "--public-base-url", normalize_public_base_url(args.public_base_url)])
    return command


def stack_healthy(state: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    if not state:
        return False, {"error": "state not found"}

    if not is_process_running(state.get("server_pid")):
        return False, {"error": "server process is not running"}

    mode = state.get("mode")

    if mode == "quick" and not is_process_running(state.get("tunnel_pid")):
        return False, {"error": "tunnel process is not running"}
    if mode == "tailscale-funnel":
        current_url = find_tailscale_funnel_url(get_tailscale_funnel_config(), int(state["port"]))
        if not current_url:
            return False, {"error": "tailscale funnel is not running for the configured port"}
        if normalize_public_base_url(current_url) != normalize_public_base_url(state.get("public_base_url")):
            return False, {"error": "tailscale funnel URL mismatch"}

    normalized_public_base_url = normalize_public_base_url(state.get("public_base_url"))
    if normalized_public_base_url:
        healthy, payload = probe_server(int(state["port"]), normalized_public_base_url)
    else:
        healthy, payload = _probe_local_only(int(state["port"]))
    if not healthy:
        return False, payload
    return True, payload


def status_stack(as_json: bool = False) -> int:
    state = read_state()
    if not state:
        state = reconcile_state(require_healthy=True)
    if not state:
        if as_json:
            print(json.dumps({"running": False}, ensure_ascii=False))
        else:
            warn("No managed remote MCP state found.")
        return 1

    healthy, details = stack_healthy(state)
    payload: dict[str, Any] = {
        "running": healthy,
        **state,
    }
    if healthy:
        payload["live_status"] = details
    else:
        payload["live_status"] = {"error": details.get("error", "health check failed")}

    update_state_health(state, healthy, details)

    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if healthy else 1

    print(f"running       : {healthy}")
    print(f"mode          : {state.get('mode')}")
    print(f"supervisor_pid: {state.get('supervisor_pid')}")
    print(f"server_pid    : {state.get('server_pid')}")
    print(f"tunnel_pid    : {state.get('tunnel_pid')}")
    print(f"port          : {state.get('port')}")
    print(f"public_base   : {state.get('public_base_url')}")
    print(f"mcp_url       : {state.get('mcp_url')}")
    print(f"dashboard_url : {state.get('dashboard_url')}")
    print(f"docs_url      : {state.get('docs_url')}")
    print(f"restart_count : {state.get('restart_count')}")
    print(f"probe_latency : {details.get('health_probe_latency_ms')}")
    print(f"started_at    : {state.get('started_at')}")
    if state.get("mode") == "quick":
        print("note          : quick tunnel is dev-only and URL may change on restart")
    if state.get("mode") == "tailscale-funnel":
        print("note          : Tailscale Funnel uses your stable ts.net hostname")
    return 0 if healthy else 1


def supervise_stack(args: argparse.Namespace) -> int:
    validate_mode(
        args.skip_tunnel,
        normalize_public_base_url(args.public_base_url),
        args.tailscale_funnel,
        args.cloudflared_path,
    )
    ensure_runtime_dirs()

    supervisor_pid = os.getpid()
    info(f"Supervisor PID {supervisor_pid} starting")

    try:
        while True:
            state = read_state()
            healthy = False
            if state and state.get("supervisor_pid") == supervisor_pid:
                healthy, _ = stack_healthy(state)

            if not healthy:
                if state and state.get("supervisor_pid") == supervisor_pid:
                    warn("Managed stack is unhealthy. Restarting children.")
                    stop_managed_stack(verbose=False, kill_supervisor=False)

                state = start_stack(
                    preferred_port=args.port,
                    cloudflared_override=args.cloudflared_path,
                    public_base_url=normalize_public_base_url(args.public_base_url),
                    skip_tunnel=args.skip_tunnel,
                    tailscale_funnel=args.tailscale_funnel,
                    supervisor_pid=supervisor_pid,
                    restart_reason="self-heal",
                )
                ok(f"Supervisor applied stack: {state['mcp_url']}")
            elif state and state.get("supervisor_pid") == supervisor_pid:
                update_state_health(state, healthy, _)

            time.sleep(args.health_interval)
    except KeyboardInterrupt:
        info("Stopping supervisor and managed stack...")
        stop_managed_stack(verbose=True, kill_supervisor=False)
        return 0


def install_windows_task(args: argparse.Namespace) -> int:
    if os.name != "nt":
        fail("Task Scheduler integration is only supported on Windows.")
        return 1

    validate_mode(
        args.skip_tunnel,
        normalize_public_base_url(args.public_base_url),
        args.tailscale_funnel,
        args.cloudflared_path,
    )

    command = build_supervisor_command(args)
    if args.tailscale_funnel:
        ok("Installing the task in Tailscale Funnel mode.")
    elif not args.skip_tunnel:
        warn("Installing the task in quick tunnel mode. This keeps the service alive, but the public URL can change on restart.")
    command_line = subprocess.list2cmdline(command)
    result = subprocess.run(
        [
            "schtasks",
            "/Create",
            "/F",
            "/SC",
            "ONLOGON",
            "/TN",
            TASK_NAME,
            "/TR",
            command_line,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        warn(result.stderr.strip() or result.stdout.strip() or "Failed to create scheduled task")
        warn("Falling back to Startup folder launcher.")
        return install_startup_launcher(args)

    ok(f"Scheduled task installed: {TASK_NAME}")
    ok(f"Task command: {command_line}")
    return 0


def remove_windows_task() -> int:
    if os.name != "nt":
        fail("Task Scheduler integration is only supported on Windows.")
        return 1
    if not current_task_exists():
        warn(f"Scheduled task not found: {TASK_NAME}")
        return 0

    result = subprocess.run(
        ["schtasks", "/Delete", "/F", "/TN", TASK_NAME],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        fail(result.stderr.strip() or result.stdout.strip() or "Failed to delete scheduled task")
        return 1
    ok(f"Scheduled task removed: {TASK_NAME}")
    return 0


def install_startup_launcher(args: argparse.Namespace) -> int:
    validate_mode(
        args.skip_tunnel,
        normalize_public_base_url(args.public_base_url),
        args.tailscale_funnel,
        args.cloudflared_path,
    )
    launcher_path = startup_launcher_path()
    command = build_supervisor_command(args)
    command_line = subprocess.list2cmdline(command)

    def ps_quote(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    ps_command = (
        "Start-Process "
        f"-FilePath {ps_quote(command[0])} "
        f"-ArgumentList @({','.join(ps_quote(part) for part in command[1:])}) "
        f"-WorkingDirectory {ps_quote(str(ROOT))} "
        f"-RedirectStandardOutput {ps_quote(str(RUNTIME_DIR / 'supervisor.out.log'))} "
        f"-RedirectStandardError {ps_quote(str(RUNTIME_DIR / 'supervisor.err.log'))} "
        "-WindowStyle Hidden"
    )
    launcher_body = "\n".join(
        [
            "@echo off",
            f'powershell -NoProfile -WindowStyle Hidden -Command "{ps_command}"',
        ]
    )

    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text(launcher_body, encoding="utf-8")
    ok(f"Startup launcher installed: {launcher_path}")
    return 0


def remove_startup_launcher() -> int:
    if os.name != "nt":
        fail("Startup launcher is only supported on Windows.")
        return 1

    launcher_path = startup_launcher_path()
    if not launcher_path.exists():
        warn(f"Startup launcher not found: {launcher_path}")
        return 0

    launcher_path.unlink()
    ok(f"Startup launcher removed: {launcher_path}")
    return 0


def add_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Preferred local port (default: {DEFAULT_PORT})")
    parser.add_argument("--cloudflared-path", help="Optional absolute path to cloudflared binary")
    parser.add_argument("--public-base-url", default="", help="Stable public HTTPS base URL to advertise when using --skip-tunnel")
    parser.add_argument("--skip-tunnel", action="store_true", help="Do not manage a tunnel. Requires --public-base-url.")
    parser.add_argument("--tailscale-funnel", action="store_true", help="Manage a Tailscale Funnel on this machine and advertise its stable ts.net HTTPS URL.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Managed ChatGPT remote MCP runner for HVDC Knowledge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Start the managed remote MCP stack once")
    add_runtime_args(start_parser)

    supervise_parser = subparsers.add_parser("supervise", help="Run a long-lived supervisor that restarts the stack when it fails")
    add_runtime_args(supervise_parser)
    supervise_parser.add_argument(
        "--health-interval",
        type=int,
        default=DEFAULT_HEALTH_INTERVAL,
        help=f"Health check interval in seconds (default: {DEFAULT_HEALTH_INTERVAL})",
    )

    status_parser = subparsers.add_parser("status", help="Show managed stack status")
    status_parser.add_argument("--json", action="store_true", help="Print JSON status")

    subparsers.add_parser("stop", help="Stop the managed remote MCP stack")

    install_parser = subparsers.add_parser("install-task", help="Install a Windows scheduled task for supervised startup")
    add_runtime_args(install_parser)
    install_parser.add_argument(
        "--health-interval",
        type=int,
        default=DEFAULT_HEALTH_INTERVAL,
        help=f"Health check interval in seconds (default: {DEFAULT_HEALTH_INTERVAL})",
    )

    subparsers.add_parser("remove-task", help="Remove the Windows scheduled task")
    install_startup_parser = subparsers.add_parser("install-startup", help="Install a Startup-folder launcher as a Windows fallback")
    add_runtime_args(install_startup_parser)
    install_startup_parser.add_argument(
        "--health-interval",
        type=int,
        default=DEFAULT_HEALTH_INTERVAL,
        help=f"Health check interval in seconds (default: {DEFAULT_HEALTH_INTERVAL})",
    )
    subparsers.add_parser("remove-startup", help="Remove the Startup-folder launcher")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.command == "start":
            state = start_stack(
                preferred_port=args.port,
                cloudflared_override=args.cloudflared_path,
                public_base_url=normalize_public_base_url(args.public_base_url),
                skip_tunnel=args.skip_tunnel,
                tailscale_funnel=args.tailscale_funnel,
                supervisor_pid=None,
                restart_reason="manual-restart",
            )
            print_start_summary(state)
            return 0

        if args.command == "supervise":
            return supervise_stack(args)

        if args.command == "status":
            return status_stack(as_json=args.json)

        if args.command == "stop":
            stop_managed_stack(verbose=True)
            return 0

        if args.command == "install-task":
            return install_windows_task(args)

        if args.command == "remove-task":
            return remove_windows_task()

        if args.command == "install-startup":
            return install_startup_launcher(args)

        if args.command == "remove-startup":
            return remove_startup_launcher()

    except Exception as exc:
        fail(str(exc))
        return 1

    fail(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
