#!/usr/bin/env python3
"""Railway entrypoint for the HVDC Knowledge MCP server."""

from __future__ import annotations

import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = ROOT / "server.py"


def _public_base_url() -> str:
    explicit = os.getenv("HVDC_PUBLIC_BASE_URL", "").rstrip("/")
    if explicit:
        return explicit
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway_domain:
        return f"https://{railway_domain}"
    return ""


def main() -> int:
    transport = os.getenv("HVDC_MCP_TRANSPORT", "streamable-http")
    host = os.getenv("HVDC_MCP_HOST", "0.0.0.0")
    port = os.getenv("HVDC_MCP_PORT") or os.getenv("PORT") or "8000"
    public_base_url = _public_base_url()

    command = [
        sys.executable,
        "-X",
        "utf8",
        str(SERVER_PATH),
        "--transport",
        transport,
        "--host",
        host,
        "--port",
        str(port),
    ]
    if public_base_url:
        command.extend(["--public-base-url", public_base_url])

    print(
        (
            "Starting HVDC Knowledge MCP on Railway "
            f"(transport={transport}, host={host}, port={port}, public_base={public_base_url or 'not set'})"
        ),
        file=sys.stderr,
    )
    os.execv(sys.executable, command)


if __name__ == "__main__":
    raise SystemExit(main())
