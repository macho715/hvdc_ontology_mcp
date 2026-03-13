#!/usr/bin/env python3
"""
HVDC Knowledge MCP — Auto Deploy
Claude Code / Claude Desktop에 MCP 서버를 자동 등록합니다.

사용법:
    python scripts/deploy.py                  # 자동 감지 (Code + Desktop 둘 다 시도)
    python scripts/deploy.py --target code    # Claude Code만
    python scripts/deploy.py --target desktop # Claude Desktop만
    python scripts/deploy.py --uninstall      # 등록 해제
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

# ──────────────────────────────────────────
# Windows ANSI 색상 활성화 + 인코딩 설정
# ──────────────────────────────────────────
if platform.system() == "Windows":
    os.system("")  # Windows Terminal ANSI escape 활성화

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
SERVER_PY = PROJECT_ROOT / "server.py"
SERVER_NAME = "hvdc-knowledge"
SERVER_DESC = "HVDC domain knowledge MCP - Flow Code, Nodes, KPI, Regulations, HS Code, ontology docs"

# subprocess 공통 옵션 (Windows cp949 문제 방지)
_SP_OPTS = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace"}


def info(msg: str):
    print(f"  {CYAN}INFO{RESET}  {msg}")


def success(msg: str):
    print(f"  {GREEN}OK{RESET}    {msg}")


def error(msg: str):
    print(f"  {RED}ERR{RESET}   {msg}")


def warning(msg: str):
    print(f"  {YELLOW}WARN{RESET}  {msg}")


# ──────────────────────────────────────────
# Python / pip 검증
# ──────────────────────────────────────────
def check_python() -> str:
    """Python 3.10+ 경로 반환"""
    py = sys.executable
    v = sys.version_info
    if v.major == 3 and v.minor >= 10:
        success(f"Python {v.major}.{v.minor}.{v.micro} ({py})")
        return py
    error(f"Python 3.10+ required (current: {v.major}.{v.minor})")
    sys.exit(1)


def install_deps():
    """requirements.txt 의존성 설치"""
    req = PROJECT_ROOT / "requirements.txt"
    if not req.exists():
        warning("requirements.txt not found - skip")
        return

    info("Installing dependencies...")
    cmd = [sys.executable, "-m", "pip", "install", "-r", str(req), "-q"]

    # Linux/Mac에서 시스템 Python이면 --break-system-packages
    if platform.system() != "Windows":
        cmd.append("--break-system-packages")

    result = subprocess.run(cmd, **_SP_OPTS)
    if result.returncode == 0:
        success("pip install done")
    else:
        # --break-system-packages 없이 재시도
        cmd_retry = [sys.executable, "-m", "pip", "install", "-r", str(req), "-q"]
        result2 = subprocess.run(cmd_retry, **_SP_OPTS)
        if result2.returncode == 0:
            success("pip install done")
        else:
            error(f"pip install failed: {result2.stderr[:200]}")


def run_validation() -> bool:
    """validate.py --quick 실행"""
    validate_script = PROJECT_ROOT / "scripts" / "validate.py"
    if not validate_script.exists():
        warning("validate.py not found - skip validation")
        return True

    info("Validating server (--quick)...")
    result = subprocess.run(
        [sys.executable, str(validate_script), "--quick"],
        **_SP_OPTS,
    )
    if result.returncode == 0:
        success("Server validation passed")
        return True
    else:
        error("Server validation failed:")
        print(result.stdout)
        return False


# ──────────────────────────────────────────
# Claude Code 배포
# ──────────────────────────────────────────
def find_claude_cli() -> str | None:
    """claude CLI 경로 찾기"""
    find_cmd = "where" if platform.system() == "Windows" else "which"
    for name in ["claude", "claude.exe"]:
        try:
            result = subprocess.run(
                [find_cmd, name],
                **_SP_OPTS,
            )
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0].strip()
        except FileNotFoundError:
            continue
    return None


def deploy_claude_code(python_path: str, uninstall: bool = False):
    """Claude Code에 MCP 서버 등록/해제"""
    cli = find_claude_cli()
    if not cli:
        warning("claude CLI not found - skip Claude Code deploy")
        warning("Install: https://docs.anthropic.com/en/docs/claude-code")
        return False

    if uninstall:
        info("Removing MCP server from Claude Code...")
        result = subprocess.run(
            [cli, "mcp", "remove", SERVER_NAME],
            **_SP_OPTS,
        )
        if result.returncode == 0:
            success(f"Claude Code: '{SERVER_NAME}' removed")
        else:
            warning(f"Claude Code remove failed (may not exist): {result.stderr[:100]}")
        return True

    info("Registering MCP server to Claude Code...")

    # 기존 등록 제거 (업데이트용)
    subprocess.run(
        [cli, "mcp", "remove", SERVER_NAME],
        **_SP_OPTS,
    )

    # Claude Code CLI 문법: claude mcp add [OPTIONS] <name> -- <command> [args...]
    # --cwd는 지원되지 않으므로 server.py 절대경로 사용
    server_abs = str(SERVER_PY)

    result = subprocess.run(
        [
            cli, "mcp", "add",
            "--transport", "stdio",
            SERVER_NAME,
            "--",
            python_path, server_abs,
        ],
        **_SP_OPTS,
    )

    if result.returncode == 0:
        success(f"Claude Code: '{SERVER_NAME}' registered")
        info(f"  command: {python_path} {server_abs}")
        return True
    else:
        # 대안: -- 없이 시도 (구버전 CLI 호환)
        result2 = subprocess.run(
            [
                cli, "mcp", "add",
                SERVER_NAME,
                python_path, server_abs,
            ],
            **_SP_OPTS,
        )
        if result2.returncode == 0:
            success(f"Claude Code: '{SERVER_NAME}' registered (legacy syntax)")
            return True

        error(f"Claude Code register failed: {result.stderr[:200]}")
        info("Manual registration:")
        info(f"  claude mcp add --transport stdio {SERVER_NAME} -- {python_path} {server_abs}")
        return False


# ──────────────────────────────────────────
# Claude Desktop 배포
# ──────────────────────────────────────────
def get_desktop_config_path() -> Path | None:
    """Claude Desktop 설정 파일 경로 (OS별)"""
    system = platform.system()
    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    return None


def deploy_claude_desktop(python_path: str, uninstall: bool = False):
    """Claude Desktop에 MCP 서버 등록/해제"""
    config_path = get_desktop_config_path()
    if config_path is None:
        warning("Claude Desktop config path not found")
        return False

    # 기존 설정 로드
    config = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            warning(f"Existing config parse failed - creating new: {config_path}")

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    if uninstall:
        if SERVER_NAME in config["mcpServers"]:
            del config["mcpServers"][SERVER_NAME]
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
            success(f"Claude Desktop: '{SERVER_NAME}' removed")
        else:
            warning(f"Claude Desktop: '{SERVER_NAME}' not registered")
        return True

    # 서버 설정 추가/업데이트
    config["mcpServers"][SERVER_NAME] = {
        "command": python_path,
        "args": [str(SERVER_PY)],
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    success(f"Claude Desktop: '{SERVER_NAME}' registered")
    info(f"Config: {config_path}")
    warning("Restart Claude Desktop to activate MCP server")
    return True


# ──────────────────────────────────────────
# 프로젝트 내부 settings.json 동기화
# ──────────────────────────────────────────
def sync_project_settings(python_path: str):
    """프로젝트 내 .claude/settings.json 업데이트"""
    settings_path = PROJECT_ROOT / ".claude" / "settings.json"
    settings = {
        "mcpServers": {
            SERVER_NAME: {
                "command": python_path,
                "args": ["server.py"],
                "cwd": str(PROJECT_ROOT),
                "description": SERVER_DESC,
            }
        }
    }
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")
    success(f".claude/settings.json synced (cwd: {PROJECT_ROOT})")


# ──────────────────────────────────────────
# Main
# ──────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="HVDC Knowledge MCP - Auto Deploy")
    parser.add_argument(
        "--target",
        choices=["code", "desktop", "both"],
        default="both",
        help="Deploy target (default: both)",
    )
    parser.add_argument("--uninstall", action="store_true", help="Unregister MCP server")
    parser.add_argument("--skip-validation", action="store_true", help="Skip validation")
    args = parser.parse_args()

    print(f"\n{BOLD}{'=' * 50}")
    if args.uninstall:
        print(f"  HVDC Knowledge MCP - Uninstall")
    else:
        print(f"  HVDC Knowledge MCP - Auto Deploy")
    print(f"{'=' * 50}{RESET}")
    print(f"  Project: {PROJECT_ROOT}")
    print(f"  OS: {platform.system()} {platform.release()}")
    print()

    # Step 1: Python 확인
    python_path = check_python()

    if args.uninstall:
        if args.target in ("code", "both"):
            deploy_claude_code(python_path, uninstall=True)
        if args.target in ("desktop", "both"):
            deploy_claude_desktop(python_path, uninstall=True)
        print(f"\n{BOLD}{GREEN}Uninstall complete{RESET}\n")
        return

    # Step 2: 의존성 설치
    install_deps()

    # Step 3: 검증
    if not args.skip_validation:
        if not run_validation():
            error("Validation failed - deploy aborted. Use --skip-validation to bypass")
            sys.exit(1)

    # Step 4: 프로젝트 settings.json 동기화
    sync_project_settings(python_path)

    # Step 5: 배포
    results = {}
    if args.target in ("code", "both"):
        results["Claude Code"] = deploy_claude_code(python_path)
    if args.target in ("desktop", "both"):
        results["Claude Desktop"] = deploy_claude_desktop(python_path)

    # 결과 요약
    print(f"\n{BOLD}{'=' * 50}")
    print(f"  Deploy Summary")
    print(f"{'=' * 50}{RESET}")
    for target, result_ok in results.items():
        status = f"{GREEN}OK{RESET}" if result_ok else f"{YELLOW}SKIPPED{RESET}"
        print(f"  {status}  {target}")

    print(f"\n  {BOLD}Usage:{RESET}")
    print(f"  Claude Code    -> run 'claude' then call hvdc_get_domain_summary")
    print(f"  Claude Desktop -> restart app, then use MCP tools")
    print(f"\n{BOLD}{GREEN}Deploy complete{RESET}\n")


if __name__ == "__main__":
    main()
