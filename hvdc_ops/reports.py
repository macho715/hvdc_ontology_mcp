from __future__ import annotations

from typing import Any


def _table_lines(mapping: dict[str, int]) -> list[str]:
    if not mapping:
        return ["| Item | Count |", "|------|------:|", "| None | 0 |"]
    lines = ["| Item | Count |", "|------|------:|"]
    for key, value in mapping.items():
        lines.append(f"| {key} | {value} |")
    return lines


def render_shipment_case_markdown(payload: dict[str, Any]) -> str:
    case = payload["normalized_case"]
    flow = payload["flow_assessment"]
    verdict = payload["verdict"]
    gates = payload["zero_gates"]
    blocking_actions = gates["blocking_actions"] or ["None"]
    flow_notes = [f"- {reason}" for reason in flow["reasons"]] or ["- No flow exceptions detected."]
    return "\n".join(
        [
            f"# Shipment Case: {case.get('shipment_id')}",
            "",
            f"- Verdict: **{verdict['status']}**",
            f"- Destination: `{case.get('destination')}`",
            f"- Status: `{case.get('status')}`",
            f"- Observed Flow Code: `{flow['observed_flow_code']}`",
            f"- Recommended Flow Code: `{flow['recommended_flow_code']}`",
            f"- Blocking Actions: {', '.join(blocking_actions)}",
            "",
            "## Flow Notes",
            *flow_notes,
        ]
    )


def render_backlog_batch_markdown(payload: dict[str, Any]) -> str:
    totals = payload["totals"]
    hotspot_lines = [
        f"- {item['destination']} / {item['status']}: {item['count']}"
        for item in payload.get("hotspots", [])[:5]
    ] or ["- None"]
    breach_lines = [f"- {item['code']}: {item['count']}" for item in payload.get("breaches", [])] or ["- None"]
    return "\n".join(
        [
            f"# Backlog Batch: {payload['snapshot_name']}",
            "",
            f"- Total Rows: **{totals['total_rows']}**",
            f"- Backlog Rows: **{totals['backlog_rows']}**",
            f"- ZERO Rows: **{totals['zero_rows']}**",
            f"- WARNING Rows: **{totals['warning_rows']}**",
            "",
            "## Top Hotspots",
            *hotspot_lines,
            "",
            "## Breaches",
            *breach_lines,
        ]
    )


def render_zero_gate_markdown(payload: dict[str, Any]) -> str:
    gate_results = payload["gate_results"]
    blocking_actions = payload.get("blocking_actions") or ["None"]
    lines = [
        "# ZERO Gate Check",
        "",
        f"- Verdict: **{payload['verdict']['status']}**",
        f"- Blocking Actions: {', '.join(blocking_actions)}",
        "",
        "## Gate Results",
    ]
    for name, details in gate_results.items():
        lines.append(f"- {name}: `{details['status']}`")
    return "\n".join(lines)


def render_compare_snapshots_markdown(payload: dict[str, Any]) -> str:
    total_lines = _table_lines(payload["delta_totals"])
    return "\n".join(
        [
            f"# Snapshot Compare: {payload['baseline_snapshot']} -> {payload['candidate_snapshot']}",
            "",
            "## Totals Delta",
            *total_lines,
            "",
            f"- New ZERO Candidates: **{len(payload['new_zero_candidates'])}**",
            f"- Resolved ZERO Candidates: **{len(payload['resolved_zero_candidates'])}**",
        ]
    )


def render_self_test_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# MCP Self Test",
        "",
        f"- Status: **{payload['status']}**",
    ]
    if payload.get("connector_url"):
        lines.append(f"- Connector URL: `{payload['connector_url']}`")
    if payload.get("public_base_url"):
        lines.append(f"- Public Base URL: `{payload['public_base_url']}`")
    lines.extend(["", "## Checks"])
    for check in payload.get("checks", []):
        lines.append(f"- {check['name']}: `{check['status']}`")
    if payload.get("recommendations"):
        lines.extend(["", "## Recommendations"])
        lines.extend(f"- {item}" for item in payload["recommendations"])
    return "\n".join(lines)
