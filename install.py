#!/usr/bin/env python3
"""
HVDC Knowledge MCP — One-Click Installer
Windows / macOS / Linux 공통. 더블클릭 또는 python install.py 로 실행.

수행 작업:
  1. Python 3.10+ 확인
  2. pip install -r requirements.txt
  3. 서버 검증 (quick)
  4. Claude Code + Desktop 자동 등록
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()

# Windows ANSI 색상 활성화
if platform.system() == "Windows":
    os.system("")


def main():
    print("\n+==========================================+")
    print("|  HVDC Knowledge MCP - One-Click Install  |")
    print("+==========================================+\n")

    # Python version check
    v = sys.version_info
    if v.major < 3 or (v.major == 3 and v.minor < 10):
        print(f"[ERROR] Python 3.10+ required (current: {v.major}.{v.minor})")
        print("Download from https://www.python.org/downloads/")
        input("\nPress Enter to exit...")
        sys.exit(1)

    print(f"[OK] Python {v.major}.{v.minor}.{v.micro}")

    # Run deploy script
    deploy_script = ROOT / "scripts" / "deploy.py"
    if not deploy_script.exists():
        print("[ERROR] scripts/deploy.py not found")
        input("\nPress Enter to exit...")
        sys.exit(1)

    # encoding=utf-8 로 subprocess 실행 (Windows cp949 방지)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"  # Python UTF-8 모드 강제

    result = subprocess.run(
        [sys.executable, str(deploy_script), "--target", "both"],
        cwd=str(ROOT),
        env=env,
    )

    if result.returncode != 0:
        print("\n[WARN] Some tasks may have failed. Check the log above.")

    input("\nPress Enter to exit...")


if __name__ == "__main__":
    main()
