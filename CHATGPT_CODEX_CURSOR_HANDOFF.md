# ChatGPT / Codex / Cursor Handoff

Last verified: 2026-03-13

This document records the work completed so far for the three main usage surfaces of this repository:

- ChatGPT
- Codex
- Cursor

It is intended as a root-level handoff note for setup, operations, and troubleshooting.

Related Windows transfer guide:

- `WINDOWS_MULTI_PC_PACKAGE.md`
- `SETUP_WINDOWS_CLIENT.cmd`
- `SETUP_WINDOWS_FULL.cmd`
- `scripts/setup_windows_client.ps1`
- `scripts/build_windows_portable_bundle.ps1`

## 1. What Was Implemented

The repository was expanded from a basic HVDC knowledge MCP into a multi-surface setup that now supports:

- ChatGPT remote MCP over `streamable-http`
- Railway production deployment with stable HTTPS
- A live status dashboard
- A ChatGPT upload widget for CSV/XLSX backlog analysis
- Codex CLI integration through MCP
- Cursor project-scoped MCP + always-on domain rules
- Read-only ops analysis tools on top of the knowledge MCP

Major implementation areas:

- `server.py`
  - MCP server entrypoint
  - knowledge tools
  - ops analysis tools
  - dashboard routes
  - widget resource registration
  - ChatGPT upload and status payloads
- `hvdc_ops/`
  - `ingest.py`
  - `rules.py`
  - `snapshots.py`
  - `reports.py`
- `scripts/`
  - `remote_mcp.py`
  - `railway_run.py`
  - `cursor_mcp.cmd`
  - `validate.py`
- deployment files
  - `Dockerfile`
  - `railway.json`
- ChatGPT widget
  - `widgets/hvdc_backlog_upload_v1.html`
- Cursor integration
  - `.cursor/mcp.json`
  - `.cursor/rules/hvdc-domain-background.mdc`

## 2. Current Verified Production State

As of 2026-03-13, the Railway deployment is the active production endpoint.

Production URLs:

- MCP: `https://hvdc-knowledge-mcp-service-production.up.railway.app/mcp`
- Dashboard: `https://hvdc-knowledge-mcp-service-production.up.railway.app/dashboard`
- Dashboard status JSON: `https://hvdc-knowledge-mcp-service-production.up.railway.app/dashboard/status`
- Health: `https://hvdc-knowledge-mcp-service-production.up.railway.app/health`

Verified live status on 2026-03-13:

- `/health` -> `200`
- `/` -> `200`
- dashboard status -> `health_score=100`
- dashboard status -> `health_state=healthy`
- deployment provider -> `Railway`
- server transport -> `streamable-http`
- server tool count -> `17`
- indexed docs -> `13`
- total docs -> `14`
- ChatGPT upload support -> `supported=true`
- widget submission readiness -> `submission_ready=true`

Validation status on 2026-03-13:

- `python scripts/validate.py`
- Result: `77 passed, 0 failed, 0 warnings`

## 3. ChatGPT Setup And Usage

### 3.1 Current architecture

ChatGPT uses the remote Railway-hosted MCP endpoint.

- Transport: `streamable-http`
- Public base URL: Railway public domain
- Connector target: `/mcp`
- Dashboard target: `/dashboard`

This is the current stable production path. Earlier `trycloudflare` and `Tailscale Funnel` paths were development or transitional steps and are no longer the main operating route.

### 3.2 What was added for ChatGPT

The following ChatGPT-facing capabilities were implemented:

- standard MCP knowledge tools
- HVDC domain tools
- analysis tools for shipment/backlog/ZERO/self-test
- live dashboard
- upload widget for CSV/XLSX analysis
- widget CSP and widget domain metadata for Apps submission readiness

The active tool list includes:

- `search`
- `fetch`
- `hvdc_get_domain_summary`
- `hvdc_search_docs`
- `hvdc_read_doc`
- `hvdc_list_docs`
- `hvdc_get_node_info`
- `hvdc_get_flow_code`
- `hvdc_get_kpi`
- `hvdc_get_regulations`
- `hvdc_hs_code_lookup`
- `hvdc_analyze_shipment_case`
- `hvdc_render_backlog_upload_widget`
- `hvdc_analyze_backlog_batch`
- `hvdc_zero_gate_check`
- `hvdc_compare_snapshots`
- `hvdc_mcp_self_test`

### 3.3 How to connect from ChatGPT

Use this exact connector URL:

```text
https://hvdc-knowledge-mcp-service-production.up.railway.app/mcp
```

Suggested steps:

1. Open ChatGPT connector/app settings.
2. Create a new MCP connector or update the existing one.
3. Enter the exact `/mcp` URL above.
4. Refresh the connector.
5. Start a new chat before retesting tools.

### 3.4 How file upload works in ChatGPT

Direct `sandbox:/mnt/...` paths are not supported by the Railway-hosted remote MCP.

Implemented workaround:

- ChatGPT uses `hvdc_render_backlog_upload_widget`
- The widget uploads the file
- The file is then provided to `hvdc_analyze_backlog_batch` as a temporary HTTP/HTTPS `download_url`

Accepted file types:

- `.csv`
- `.xlsx`

Recommended ChatGPT prompt:

```text
Backlog upload widget을 열어서 XLSX를 올리고 ZERO 후보를 분석해줘
```

### 3.5 ChatGPT troubleshooting

If ChatGPT cannot use the server:

- confirm the connector URL is exactly the Railway `/mcp` URL
- refresh the connector
- open a new chat
- check the dashboard
- verify the widget path if the failure is upload-related rather than server-related

Common failure pattern:

- MCP server is healthy
- direct `sandbox:/...` file handoff fails
- widget-based upload succeeds

### 3.6 ChatGPT-specific implementation notes

The dashboard exposes ChatGPT upload readiness in `server.chatgpt_upload`.

Key fields:

- `supported`
- `widget_tool_available`
- `analysis_tool_available`
- `resource_available`
- `widget_domain_configured`
- `widget_csp_configured`
- `submission_ready`
- `direct_sandbox_paths_supported=false`
- `local_path_stdio_only=true`

## 4. Codex Setup And Usage

### 4.1 What was done on this PC

Codex CLI on this PC was upgraded because the earlier installed version could not correctly load the existing HTTP MCP config.

Codex status after upgrade:

- old version: `0.41.0`
- upgraded version: `0.114.0`

After the upgrade:

- existing MCP config loaded normally
- `hvdc-knowledge` was registered as a global MCP server
- actual tool invocation was verified by running `hvdc_get_domain_summary`
- a project-scoped `.codex/config.toml` was also added so new PCs can use the same MCP setup without editing user-global config first

### 4.2 Codex config location

Codex global config on this PC:

```text
C:\Users\jichu\.codex\config.toml
```

Current relevant entry:

```toml
[mcp_servers.hvdc-knowledge]
command = "cmd.exe"
args = ["/d", "/c", 'C:\Users\jichu\Downloads\hvdc-knowledge-gpt-mcp\scripts\cursor_mcp.cmd']
```

This means Codex launches the repo-local wrapper, which then starts `server.py` in `stdio` mode.

Project-scoped Codex config now also exists in this repository:

```text
<repo>/.codex/config.toml
```

Current project-scoped entry:

```toml
[mcp_servers.hvdc-knowledge]
command = "cmd.exe"
args = ["/d", "/c", ".\\scripts\\cursor_mcp.cmd"]
startup_timeout_sec = 20
tool_timeout_sec = 120
```

This is the preferred multi-PC path because it moves with the repository.

### 4.3 How to verify Codex MCP

Useful commands:

```powershell
codex --version
codex mcp list --json
codex mcp get hvdc-knowledge --json
codex exec --skip-git-repo-check "Call hvdc_get_domain_summary and return only a 3-bullet summary."
```

What was verified successfully:

- `codex mcp list --json`
- `codex mcp get hvdc-knowledge --json`
- `codex exec ... hvdc_get_domain_summary ...`

### 4.4 How to use from Codex

Example prompt:

```text
Call hvdc_get_domain_summary and summarize the HVDC domain rules in 5 bullets.
```

For code work, recommended usage pattern:

- domain refresh first
- tool-backed validation second
- code change third

Example:

```text
Call hvdc_get_domain_summary first. Then use hvdc_get_flow_code and hvdc_get_regulations to review this routing logic and fix only rule violations.
```

### 4.5 Notes for another PC

Codex now has two valid setup paths:

- project-scoped `.codex/config.toml` in this repository
- optional machine-global `%USERPROFILE%\.codex\config.toml`

For another PC, the preferred path is:

1. clone or copy this repository
2. trust the project in Codex
3. install Python dependencies
4. let Codex load `.codex/config.toml`

Only if project-scoped config is not desired should the user add a separate global MCP entry.

## 5. Cursor Setup And Usage

### 5.1 What was implemented

Cursor was set up as a project-scoped MCP consumer with always-on domain context.

Files used:

- `.cursor/mcp.json`
- `.cursor/rules/hvdc-domain-background.mdc`
- `scripts/cursor_mcp.cmd`

### 5.2 How Cursor works in this repo

`Cursor` reads `.cursor/mcp.json`, then launches:

```text
cmd.exe /d /c ${workspaceFolder}/scripts/cursor_mcp.cmd
```

The wrapper:

- sets `HVDC_MCP_TRANSPORT=stdio`
- prefers `.venv\Scripts\python.exe`
- falls back to `py -3`
- falls back to `python`
- runs `server.py`

This avoids hardcoding a machine-specific Python path.

### 5.3 Cursor rule behavior

The file `.cursor/rules/hvdc-domain-background.mdc` is `alwaysApply: true`.

That rule tells Cursor to:

- treat the repo as HVDC UAE logistics software
- not invent domain-critical rules
- use MCP before changing Flow, KPI, regulation, customs, backlog, or ZERO logic

### 5.4 How to use Cursor on this repo

Recommended setup:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Then:

1. Open this repository in Cursor.
2. Reload the window if MCP is not detected immediately.
3. Open Agent chat.
4. Confirm `hvdc-knowledge` appears.
5. Use MCP-backed prompts.

Quick test prompt:

```text
hvdc_get_domain_summary를 호출해서 HVDC 핵심 규칙만 정리해줘
```

### 5.5 Multi-PC Cursor notes

Cursor integration is repo-scoped, so these files travel with the repo:

- `.cursor/mcp.json`
- `.cursor/rules/hvdc-domain-background.mdc`
- `scripts/cursor_mcp.cmd`

That means multi-PC use is straightforward if each PC has:

- Python or `py`
- repo checkout
- installed dependencies

The repo-side Cursor setup is reusable across machines.

## 6. Domain And Ops Features Added

### 6.1 Knowledge tools retained

Existing knowledge retrieval remained available:

- domain summary
- document search
- document read
- document listing
- node info
- Flow Code rules
- KPI lookup
- regulation lookup
- HS lookup

### 6.2 Core ops tools added

The following read-only ops tools were added:

- `hvdc_analyze_shipment_case`
- `hvdc_analyze_backlog_batch`
- `hvdc_zero_gate_check`
- `hvdc_compare_snapshots`
- `hvdc_mcp_self_test`

Behavior highlights:

- CSV/XLSX ingestion
- semantic column normalization
- AGI/DAS Flow Code enforcement
- DOT `> 90t` checks
- ZERO gate evaluation
- snapshot persistence under `.runtime/analysis/`
- Markdown summaries plus structured output

## 7. Dashboard Work Completed

The dashboard was extended from a simple status page into an operations-facing view.

Implemented dashboard capabilities:

- health score
- alert panel
- process and connectivity status
- latency visibility
- recent restart history
- trend/history data
- log sections
- ChatGPT upload readiness card
- Railway deployment visibility

Current dashboard state on 2026-03-13:

- `health_score=100`
- `health_state=healthy`
- `provider=Railway`
- `processes_up=1/1`
- `submission_ready=true`

## 8. Important Domain Rules To Keep Stable

These are the most important implementation constraints that should not drift:

- `AGI` and `DAS` require `MOSB`
- `AGI/DAS` minimum Flow Code is `3`
- `Flow 0/1/2` for `AGI/DAS` must be upgraded to `3`
- `DOT` is required only for cargo `> 90 tons`
- `MOSB` capacity limit is `20,000 sqm`
- missing evidence should not become implicit pass
- `MOIAT_ECAS` and `MOIAT_EQM` should stay separable in code
- remote ChatGPT upload should not rely on direct `sandbox:/mnt/...` paths

## 9. Commands Worth Keeping

### General validation

```powershell
python scripts/validate.py
```

### Local stdio MCP

```powershell
python server.py
```

### Local HTTP dev server

```powershell
python server.py --transport streamable-http --host 127.0.0.1 --port 8000
```

### Codex MCP verification

```powershell
codex mcp list --json
codex mcp get hvdc-knowledge --json
```

### Cursor wrapper verification

```powershell
cmd.exe /d /c scripts\cursor_mcp.cmd --help
```

## 10. Known Constraints

Current known constraints:

- ChatGPT remote MCP cannot directly read `sandbox:/mnt/...` local upload paths
- `local_path` is for `stdio` usage, not for Railway-hosted remote calls
- Codex project config still requires the project to be trusted on each PC
- Cursor setup is project-scoped, but each machine still needs Python/dependencies
- Dashboard live health is Railway-first now; older local tunnel flows are not the production reference

## 11. Recommended Operating Model

Recommended surface-by-surface usage:

- ChatGPT
  - use the Railway `/mcp` connector
  - use the upload widget for CSV/XLSX analysis
- Codex
  - use local `stdio` MCP via project-scoped `.codex/config.toml`
  - use tool-backed prompts before modifying code
- Cursor
  - use project-scoped `stdio` MCP
  - rely on `.cursor/rules` for always-on domain context

Short version:

- ChatGPT = remote Railway MCP
- Codex = local stdio MCP
- Cursor = local stdio MCP + project rules

## 12. Files To Review First

If someone needs to continue this work, start with these files:

- `README.md`
- `server.py`
- `scripts/validate.py`
- `scripts/remote_mcp.py`
- `scripts/railway_run.py`
- `hvdc_ops/ingest.py`
- `hvdc_ops/rules.py`
- `hvdc_ops/snapshots.py`
- `hvdc_ops/reports.py`
- `widgets/hvdc_backlog_upload_v1.html`
- `.cursor/mcp.json`
- `.cursor/rules/hvdc-domain-background.mdc`

## 13. External References

OpenAI and related references used during setup:

- Codex MCP: `https://developers.openai.com/codex/mcp/`
- Codex config: `https://developers.openai.com/codex/config-reference/#configtoml`
- Apps SDK reference: `https://developers.openai.com/apps-sdk/reference/`
- Apps SDK MCP server guide: `https://developers.openai.com/apps-sdk/build/mcp-server/`
- ChatGPT connector guide: `https://developers.openai.com/apps-sdk/deploy/connect-chatgpt/`
- Railway Docker deploy: `https://docs.railway.com/deploy/dockerfiles`
- Railway public domains: `https://docs.railway.com/reference/public-domains`

## 14. Bottom Line

This repository is no longer just a knowledge MCP.

It is now:

- a Railway-hosted remote MCP for ChatGPT
- a locally consumable stdio MCP for Codex
- a project-scoped MCP + rules setup for Cursor
- a domain-aware HVDC operations analysis layer with dashboard, widget upload, and validation coverage
