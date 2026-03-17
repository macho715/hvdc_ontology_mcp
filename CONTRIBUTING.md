# Contributing

## Setup
- Create `.venv` in the repo root and install `requirements.txt`.
- For Excel MCP work, also prepare `excel-mcp/.venv` or run `powershell -ExecutionPolicy Bypass -File .\scripts\start-excel-mcp.ps1 -InstallDeps`.
- On Windows, `SETUP_WINDOWS_FULL.cmd` remains the fastest full bootstrap path.

## Before Opening a Change
- Run `python scripts/validate.py` for full changes.
- At minimum, run `python scripts/validate.py --quick` before small patches.
- Do not break existing `search`, `fetch`, or `hvdc_*` tool signatures.
- Keep `structuredContent` changes additive unless a tracked contract change is explicitly approved.

## MCP-Specific Rules
- `stdio` must not write protocol output to stdout.
- Public HTTP additions must stay additive and keep `/health` returning HTTP `200`.
- Dashboard additions should be safe when optional services such as Excel MCP are not configured.
- Excel MCP changes must preserve path safety and `.xlsx` / `.xlsm` restrictions.

## Docs and Generated Files
- Do not hand-edit generated domain artifacts unless the generation source is being updated.
- When adding new operator flows, update the relevant README and validation coverage in the same change.
