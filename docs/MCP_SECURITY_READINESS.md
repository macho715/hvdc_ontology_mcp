# MCP Security Readiness

## Current Posture
- Main HVDC MCP exposes `stdio` and `streamable-http`.
- Public MCP use assumes a trusted HTTPS endpoint such as Railway, Tailscale Funnel, or another controlled reverse proxy.
- `excel-mcp` is intended to remain local/private by default and is only exposed externally by explicit operator action.

## Ready Now
- Path safety checks for document and workbook access.
- Health and dashboard visibility for remote MCP operations.
- Structured logging with correlation IDs for HTTP-facing routes.
- Optional Excel integration via `HVDC_EXCEL_MCP_URL` without hard dependency on the companion service.

## Deferred Until Product Need
- OAuth 2.1 / PRM enforcement.
- Gateway-layer rate limiting and token validation.
- Tenant-aware authorization.
- Centralized telemetry backend beyond local/dashboard observability.

## Recommended Upgrade Path
1. Keep public MCP behind a stable HTTPS host.
2. Add auth at the edge before expanding beyond trusted internal use.
3. Treat quick tunnels as temporary developer tooling, not durable production identity.
4. Validate `/health`, `/dashboard/status`, and `/dashboard/self-test` after every deployment.

## Operator Notes
- `HVDC_EXCEL_MCP_URL` should point to the Excel MCP base URL or `/mcp` endpoint on a private network.
- Do not publish workbook roots or backup files from `excel-mcp/workbooks/`.
- If auth is introduced later, preserve current tool signatures and make auth enforcement a deployment-time capability.
