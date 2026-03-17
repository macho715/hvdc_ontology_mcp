# Security Policy

## Scope
- This repository serves internal HVDC logistics knowledge over MCP.
- Remote access is expected to stay behind a trusted HTTPS endpoint.
- OAuth/PRM is not enabled in this repository by default.

## Reporting
- Do not open public issues for secrets, auth gaps, or connector exposure bugs.
- Report security issues directly to the project owner or internal maintainer channel.
- Include reproduction steps, affected endpoint or tool, and whether the issue affects `stdio`, `/mcp`, `/dashboard`, or `excel-mcp`.

## Baseline Controls
- Keep secrets out of the repository and out of `.runtime/` artifacts.
- Prefer stable HTTPS hosts for public MCP use; quick tunnels are for development only.
- Treat `HVDC_EXCEL_MCP_URL` as optional private infrastructure and do not expose it publicly without operator intent.
- Review `scripts/remote_mcp.py`, `server.py`, and `excel-mcp/server.py` changes for path safety, transport exposure, and logging behavior.

## Dependency Hygiene
- Run `python scripts/validate.py` before release changes.
- Keep both `requirements.txt` and `excel-mcp/requirements.txt` current.
- Recreate virtual environments after Python minor-version upgrades.

## Future Auth Readiness
- If this service becomes multi-tenant or broadly public, add OAuth 2.1 / PRM at the gateway or app layer before expanding access.
- Keep the current auth posture documented in `docs/MCP_SECURITY_READINESS.md`.
