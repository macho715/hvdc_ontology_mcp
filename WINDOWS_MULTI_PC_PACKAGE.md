# Windows Multi-PC Package Guide

Last verified: 2026-03-13

This guide explains how to move this repository to another Windows PC and use it with:

- Codex
- Cursor
- ChatGPT
- optionally Claude

It is written for the Windows-only setup path.

## 1. Package Goal

The goal is to make this project usable on another Windows PC without manually rebuilding all MCP settings.

The package now includes:

- project-scoped Codex config: `.codex/config.toml`
- project-scoped Cursor config: `.cursor/mcp.json`
- Cursor/Codex shared launcher: `scripts/cursor_mcp.cmd`
- one-click Windows client setup:
  - `SETUP_WINDOWS_CLIENT.cmd`
  - `SETUP_WINDOWS_FULL.cmd`
  - `scripts/setup_windows_client.ps1`
- portable package builder:
  - `scripts/build_windows_portable_bundle.ps1`
- root-level handoff docs

## 2. Fastest Target-PC Setup

On the target Windows PC:

1. Copy or unzip this project anywhere.
2. If you want the full one-shot path, double-click [SETUP_WINDOWS_FULL.cmd](/c:/Users/jichu/Downloads/hvdc-knowledge-gpt-mcp/SETUP_WINDOWS_FULL.cmd)
3. Wait for dependency install and validation.
4. Open the repo in Codex or Cursor.
5. Trust the project.

If you prefer terminal:

```powershell
.\SETUP_WINDOWS_FULL.cmd
```

What `SETUP_WINDOWS_FULL.cmd` does:

- creates `.venv`
- installs dependencies
- runs validation
- syncs Claude Code / Claude Desktop
- syncs global Codex MCP

If you want the lighter setup path instead:

```powershell
.\SETUP_WINDOWS_CLIENT.cmd
```

Quick mode:

```powershell
.\SETUP_WINDOWS_CLIENT.cmd -Quick
```

Optional Claude sync:

```powershell
.\SETUP_WINDOWS_CLIENT.cmd -SyncClaude
```

Optional global Codex sync:

```powershell
.\SETUP_WINDOWS_CLIENT.cmd -SyncCodexGlobal
```

## 3. What The Setup Script Does

`scripts/setup_windows_client.ps1` performs:

1. `.venv` creation if missing
2. `pip install -r requirements.txt`
3. validation
4. optional Claude registration
5. optional global Codex registration

Default behavior is safe for another Windows PC because:

- Codex can use the repo-local `.codex/config.toml`
- Cursor can use the repo-local `.cursor/mcp.json`
- both use `scripts/cursor_mcp.cmd`

## 4. Codex On Another Windows PC

Codex uses:

- `.codex/config.toml`
- `scripts/cursor_mcp.cmd`

What to do:

1. open the repo in Codex
2. trust the project
3. ensure `.venv` or Python exists
4. run a test prompt

Example:

```text
Call hvdc_get_domain_summary and return only 3 bullets.
```

Optional:

- use `-SyncCodexGlobal` if you also want machine-global Codex registration

## 5. Cursor On Another Windows PC

Cursor uses:

- `.cursor/mcp.json`
- `.cursor/rules/hvdc-domain-background.mdc`
- `scripts/cursor_mcp.cmd`

What to do:

1. open the repo in Cursor
2. reload the window if needed
3. open Agent chat
4. confirm `hvdc-knowledge` appears

Example:

```text
hvdc_get_domain_summary를 호출해서 HVDC 핵심 규칙만 정리해줘
```

## 6. ChatGPT On Another Windows PC

ChatGPT does not need local Python on the target PC if you only want remote use.

Use this connector URL:

```text
https://hvdc-knowledge-mcp-service-production.up.railway.app/mcp
```

Useful URLs:

- MCP: `https://hvdc-knowledge-mcp-service-production.up.railway.app/mcp`
- Dashboard: `https://hvdc-knowledge-mcp-service-production.up.railway.app/dashboard`
- Health: `https://hvdc-knowledge-mcp-service-production.up.railway.app/health`

Important:

- direct `sandbox:/mnt/...` file handoff is not supported on the remote Railway MCP
- use the upload widget flow for CSV/XLSX analysis

Recommended prompt:

```text
Backlog upload widget을 열어서 XLSX를 올리고 ZERO 후보를 분석해줘
```

## 7. Optional Claude Use

If the target PC also uses Claude:

```powershell
.\SETUP_WINDOWS_CLIENT.cmd -SyncClaude
```

This runs `scripts/deploy.py --target both` after dependencies and validation.

## 8. How To Build A Portable Package

On the source Windows PC:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows_portable_bundle.ps1
```

This creates:

- package directory under `.dist\hvdc-knowledge-windows-portable`
- zip archive under `.dist\hvdc-knowledge-windows-portable-YYYYMMDD-HHMMSS.zip`

The package excludes runtime noise such as:

- `.venv`
- `.runtime`
- `__pycache__`
- `.ruff_cache`

## 9. Recommended Files To Carry

If you are not using the generated package, at minimum carry:

- `server.py`
- `requirements.txt`
- `README.md`
- `CHATGPT_CODEX_CURSOR_HANDOFF.md`
- `WINDOWS_MULTI_PC_PACKAGE.md`
- `.codex/`
- `.cursor/`
- `scripts/`
- `hvdc_ops/`
- `docs/`
- `widgets/`

## 10. Known Limits

- this setup is Windows-oriented
- `.codex/config.toml` only loads when the project is trusted
- Codex global settings do not automatically sync between PCs
- remote ChatGPT upload still requires widget-based handoff rather than direct sandbox paths

## 11. Recommended Operating Model

For another Windows PC, the recommended split is:

- Codex: local repo-scoped MCP
- Cursor: local repo-scoped MCP + rules
- ChatGPT: remote Railway MCP
- Claude: optional local registration

This keeps code work local and stable while keeping ChatGPT on the central hosted endpoint.
